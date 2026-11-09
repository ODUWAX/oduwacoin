"""Unit tests: python3 -m unittest discover -s tests   (run from contrib/paperwallet)

Set OWC_DATADIR to a running (it may be offline/unsynced) oduwacoind data dir to also
check generated keys and sweep signing against OduwaCoin Core itself.
"""
import csv
import hashlib
import json
import os
import sys
import tempfile
import unittest
from decimal import Decimal
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from owc_paper import cli, keys, rpc  # noqa: E402
from owc_paper._ripemd160 import ripemd160  # noqa: E402


class KeyTests(unittest.TestCase):
    def test_core_vector(self):
        # Produced by OduwaCoin Core v2.0.0.3 getnewaddress / dumpprivkey
        self.assertEqual(keys.address_from_wif("PQywksjED8mtBGLGocdDxN7sva3JiHEqLxpyDb6mbAeZAeXsVzoj"),
                         "AWpwKuYkb92XU3o8aZaxR6Xk3idCHLwZe4")
        keys.self_test()

    def test_roundtrip_and_prefixes(self):
        for _ in range(25):
            addr, wif = keys.new_keypair()
            self.assertTrue(addr.startswith("A"))
            self.assertTrue(wif.startswith("P"))
            self.assertEqual(len(wif), 52)
            self.assertTrue(keys.is_valid_address(addr))
            self.assertEqual(keys.address_from_wif(wif), addr)

    def test_rejects_bad_input(self):
        addr, wif = keys.new_keypair()
        bad = wif[:-1] + ("a" if wif[-1] != "a" else "b")
        with self.assertRaises(ValueError):
            keys.wif_to_secret(bad)
        with self.assertRaises(ValueError):
            keys.wif_to_secret("5HueCGU8rMjxEXxiPuD5BDku4MkFqeZyd4dZ1jvhTVqvbTLvyTJ")  # bitcoin WIF
        self.assertFalse(keys.is_valid_address("1BoatSLRHtKNngkdXEeobR76b53LETtpyT"))
        self.assertFalse(keys.is_valid_address(addr[:-1] + ("1" if addr[-1] != "1" else "2")))

    def test_ripemd_fallback(self):
        try:
            hashlib.new("ripemd160")
        except ValueError:
            self.skipTest("hashlib has no ripemd160 to compare against")
        for d in (b"", b"abc", b"a" * 1000, os.urandom(55), os.urandom(56), os.urandom(64)):
            self.assertEqual(ripemd160(d), hashlib.new("ripemd160", d).digest())


class FakeRPC:
    def __init__(self, locked=True, balance=1000):
        self.locked, self.balance, self.calls = locked, balance, []

    def __getattr__(self, name):
        def f(*p):
            self.calls.append((name, p))
            if name == "validateaddress":
                return {"isvalid": True}
            if name == "getwalletinfo":
                return {"balance": self.balance}
            if name == "sendmany":
                if self.locked:
                    raise rpc.RPCError("sendmany: Error: Please enter the wallet passphrase with "
                                       "walletpassphrase first.")
                return "ab" * 32
            if name == "walletpassphrase":
                self.locked = False
            return None
        return f


class FundTests(unittest.TestCase):
    def _manifest(self, d):
        items = []
        for i in range(3):
            addr, _ = keys.new_keypair()
            items.append({"serial": "GV-%d" % i, "address": addr, "amount": "10.5"})
        path = os.path.join(d, "m.json")
        json.dump({"format": "owc-paper/1", "kind": "voucher", "network": "main", "items": items},
                  open(path, "w"))
        return path

    def test_fund_encrypted_wallet(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._manifest(d)
            fake = FakeRPC(locked=True)
            with mock.patch.object(cli, "_rpc", return_value=fake), \
                    mock.patch("getpass.getpass", return_value="pw"):
                cli.main(["fund", path, "-y"])
            man = json.load(open(path))
            self.assertTrue(all(it["funding_txid"] == "ab" * 32 for it in man["items"]))
            names = [c[0] for c in fake.calls]
            self.assertIn("walletpassphrase", names)
            self.assertEqual(names[-1], "walletlock")
            sent = [c for c in fake.calls if c[0] == "sendmany"][-1][1][1]
            self.assertEqual(len(sent), 3)
            self.assertAlmostEqual(sum(sent.values()), 31.5)
            # second run is a no-op
            with mock.patch.object(cli, "_rpc", return_value=fake):
                cli.main(["fund", path, "-y"])
            self.assertEqual(len([c for c in fake.calls if c[0] == "sendmany"]), 2)

    def test_fund_insufficient(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._manifest(d)
            with mock.patch.object(cli, "_rpc", return_value=FakeRPC(locked=False, balance=1)):
                with self.assertRaises(SystemExit):
                    cli.main(["fund", path, "-y"])


class GenerateTests(unittest.TestCase):
    def test_generate_vouchers_from_csv(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "gifts.csv")
            with open(src, "w", newline="") as fh:
                w = csv.writer(fh)
                w.writerow(["amount", "to", "from", "message"])
                w.writerow(["100", "Ada", "Oduwa", "Happy birthday"])
                w.writerow(["2.5", "Kwame", "Etinosa", ""])
            cli.main(["generate", "voucher", "--csv", src, "--out", d, "--name", "v",
                      "--allow-online", "--export-keys", os.path.join(d, "k.csv")])
            man = json.load(open(os.path.join(d, "v.manifest.json")))
            self.assertEqual([i["amount"] for i in man["items"]], ["100.00000000", "2.50000000"])
            self.assertNotIn("wif", json.dumps(man))  # manifest is public-only
            rows = list(csv.DictReader(open(os.path.join(d, "k.csv"))))
            for row, it in zip(rows, man["items"]):
                self.assertEqual(keys.address_from_wif(row["wif"]), it["address"])
            self.assertGreater(os.path.getsize(os.path.join(d, "v.pdf")), 10000)


@unittest.skipUnless(os.environ.get("OWC_DATADIR"), "set OWC_DATADIR to test against oduwacoind")
class CoreIntegration(unittest.TestCase):
    def setUp(self):
        self.rpc = rpc.CoreRPC(datadir=os.environ["OWC_DATADIR"])

    def test_core_accepts_generated_keys(self):
        addr, wif = keys.new_keypair()
        self.rpc.importprivkey(wif, "owc-paper-test", False)
        info = self.rpc.validateaddress(addr)
        self.assertTrue(info["isvalid"] and info["ismine"])

    def test_sweep_signs(self):
        addr, wif = keys.new_keypair()
        dest, _ = keys.new_keypair()
        script = cli._p2pkh_script(addr)
        raw = self.rpc.createrawtransaction([{"txid": "11" * 32, "vout": 0}], {dest: 1.0})
        signed = self.rpc.signrawtransaction(raw, [{"txid": "11" * 32, "vout": 0, "scriptPubKey": script}],
                                             [wif])
        self.assertTrue(signed["complete"])


if __name__ == "__main__":
    unittest.main()
