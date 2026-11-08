"""Read-only client for the OduwaCoin Blockbook explorer (ex1.oduwacoin.io)."""
import json
import urllib.request
from decimal import Decimal

DEFAULT_EXPLORER = "https://ex1.oduwacoin.io"
SAT = Decimal("0.00000001")


class Explorer:
    def __init__(self, base=DEFAULT_EXPLORER):
        self.base = base.rstrip("/")

    def _get(self, path):
        req = urllib.request.Request(self.base + path, headers={"User-Agent": "owc-paper/1.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())

    def status(self):
        return self._get("/api/")

    def height(self):
        return int(self.status()["blockbook"]["bestHeight"])

    def address(self, addr):
        d = self._get("/api/v2/address/%s?details=basic" % addr)
        return {
            "address": addr,
            "balance": Decimal(d["balance"]) * SAT,
            "unconfirmed": Decimal(d.get("unconfirmedBalance", "0")) * SAT,
            "received": Decimal(d.get("totalReceived", "0")) * SAT,
            "sent": Decimal(d.get("totalSent", "0")) * SAT,
            "txs": d.get("txs", 0),
        }

    def utxos(self, addr):
        out = []
        for u in self._get("/api/v2/utxo/%s" % addr):
            out.append({
                "txid": u["txid"],
                "vout": int(u["vout"]),
                "amount": Decimal(u["value"]) * SAT,
                "confirmations": int(u.get("confirmations", 0)),
            })
        return out

    def sendtx(self, hex_tx):
        req = urllib.request.Request(self.base + "/api/v2/sendtx/", data=hex_tx.encode(),
                                     headers={"User-Agent": "owc-paper/1.0", "Content-Type": "text/plain"})
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read())
        if "result" not in d:
            raise RuntimeError("explorer rejected transaction: %s" % d)
        return d["result"]

    def tx_url(self, txid):
        return "%s/tx/%s" % (self.base, txid)

    def address_url(self, addr):
        return "%s/address/%s" % (self.base, addr)
