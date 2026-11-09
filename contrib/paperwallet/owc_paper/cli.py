"""owc-paper – OduwaCoin paper wallet and gift voucher tool.

  generate  create keys offline and print PDFs (paper wallets or vouchers)
  fund      load a batch from OduwaCoin Core in one transaction (sendmany)
  balance   check balances of a batch, an address or a private key
  sweep     move everything from a paper wallet / voucher key to an address
"""
import argparse
import csv
import datetime as dt
import getpass
import json
import os
import secrets
import socket
import sys
from decimal import Decimal, ROUND_UP, InvalidOperation

from . import keys
from .explorer import DEFAULT_EXPLORER, Explorer
from .rpc import CoreRPC, RPCError

COIN_DECIMALS = Decimal("0.00000001")
MIN_FEE_PER_KB = Decimal("0.0001")  # DEFAULT_MIN_RELAY_TX_FEE / DEFAULT_TRANSACTION_MINFEE
SERIAL_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _d(v):
    try:
        return Decimal(str(v)).quantize(COIN_DECIMALS)
    except InvalidOperation:
        raise SystemExit("invalid amount: %r" % v)


def _f(v):
    return "{:,.8f}".format(Decimal(v))


def _serial(prefix):
    body = "".join(secrets.choice(SERIAL_ALPHABET) for _ in range(8))
    return "%s-%s-%s" % (prefix, body[:4], body[4:])


def _online():
    try:
        socket.create_connection(("1.1.1.1", 53), timeout=1.5).close()
        return True
    except OSError:
        return False


def _rpc(args):
    return CoreRPC(url=args.rpcurl, user=args.rpcuser, password=args.rpcpassword,
                   datadir=args.datadir, conf=args.conf, network=args.network)


def _load_manifest(path):
    with open(path) as fh:
        return json.load(fh)


def _save_manifest(path, man):
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(man, fh, indent=2, default=str)
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
def cmd_generate(args):
    keys.self_test()
    from .render import render  # heavy import only when needed

    if _online() and not args.allow_online:
        raise SystemExit(
            "This machine appears to be online. Generate keys on an offline computer "
            "(disconnect network / boot a live USB) or pass --allow-online to override.")

    rows = []
    if args.csv:
        with open(args.csv, newline="", encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                rows.append({k.strip().lower(): (v or "").strip() for k, v in r.items()})
    else:
        rows = [{} for _ in range(args.count)]

    created = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    prefix = args.serial_prefix or ("GV" if args.kind == "voucher" else "PW")
    records = []
    for r in rows:
        amount = r.get("amount") or args.amount
        if args.kind == "voucher" and not amount:
            raise SystemExit("vouchers need an amount (--amount or an 'amount' CSV column)")
        addr, wif = keys.new_keypair(args.network)
        records.append({
            "serial": r.get("serial") or _serial(prefix),
            "address": addr,
            "wif": wif,
            "amount": str(_d(amount)) if amount else None,
            "to": r.get("to", args.to or ""),
            "from": r.get("from", args.sender or ""),
            "message": r.get("message", args.message or ""),
            "created": created,
        })

    os.makedirs(args.out, exist_ok=True)
    stem = args.name or "%s-%s" % ("vouchers" if args.kind == "voucher" else "paperwallets",
                                   created[:19].replace(":", ""))
    pdf_path = os.path.join(args.out, stem + ".pdf")
    explorer = Explorer(args.explorer)
    render(records, pdf_path, args.kind, explorer, issuer=args.issuer, claim_url=args.claim_url or None)
    os.chmod(pdf_path, 0o600)

    manifest = {
        "format": "owc-paper/1",
        "kind": args.kind,
        "network": args.network,
        "created": created,
        "issuer": args.issuer,
        "items": [{k: v for k, v in rec.items() if k != "wif"} for rec in records],
    }
    man_path = os.path.join(args.out, stem + ".manifest.json")
    _save_manifest(man_path, manifest)

    if args.export_keys:
        with open(args.export_keys, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["serial", "address", "wif", "amount"])
            for rec in records:
                w.writerow([rec["serial"], rec["address"], rec["wif"], rec["amount"] or ""])
        os.chmod(args.export_keys, 0o600)

    print("Created %d %s" % (len(records), "vouchers" if args.kind == "voucher" else "paper wallets"))
    print("  PDF (contains PRIVATE KEYS): %s" % pdf_path)
    print("  Manifest (public only):      %s" % man_path)
    if args.export_keys:
        print("  Key backup CSV (SECRET):     %s" % args.export_keys)
    print("\nNext: print the PDF on a printer that is not networked, then securely delete it:")
    print("  shred -u %s   (Linux)  |  rm -P %s   (macOS)" % (pdf_path, pdf_path))
    print("Then copy ONLY the manifest to your online computer and run:  owc-paper fund %s" % man_path)


# ---------------------------------------------------------------------------
def cmd_fund(args):
    man = _load_manifest(args.manifest)
    rpc = _rpc(args)
    payouts, items = {}, []
    for it in man["items"]:
        if it.get("funding_txid") and not args.refund:
            continue
        amt = _d(args.amount or it.get("amount") or 0)
        if amt <= 0:
            raise SystemExit("no amount for %s; pass --amount" % it["serial"])
        if not keys.is_valid_address(it["address"], man.get("network", "main")):
            raise SystemExit("manifest contains an invalid address: %s" % it["address"])
        v = rpc.validateaddress(it["address"])
        if not v.get("isvalid"):
            raise SystemExit("OduwaCoin Core rejects address %s" % it["address"])
        payouts[it["address"]] = payouts.get(it["address"], Decimal(0)) + amt
        items.append(it)
    if not payouts:
        print("Nothing to fund – every item already has a funding_txid (use --refund to top up).")
        return

    total = sum(payouts.values())
    info = rpc.getwalletinfo()
    bal = Decimal(str(info.get("balance", 0)))
    print("Funding %d %s from OduwaCoin Core" % (len(payouts), man["kind"] + "s"))
    for it in items:
        print("  %-14s %s  %s OWC" % (it["serial"], it["address"], _d(args.amount or it["amount"])))
    print("  Total: %s OWC  (+ network fee)   Wallet balance: %s OWC" % (_f(total), _f(bal)))
    if bal < total:
        raise SystemExit("Insufficient spendable balance.")
    if not args.yes and input("Send now? [y/N] ").strip().lower() != "y":
        raise SystemExit("Cancelled.")

    amounts = {a: float(v) for a, v in payouts.items()}
    comment = args.comment or "owc-paper %s" % man["kind"]
    unlocked = False
    try:
        try:
            txid = rpc.sendmany("", amounts, 1, comment)
        except RPCError as e:
            # Encrypted wallet, or unlocked for staking only: ask for the passphrase once.
            if not any(w in str(e).lower() for w in ("unlock", "passphrase", "staking only")):
                raise
            pw = getpass.getpass("Wallet passphrase: ")
            try:
                rpc.walletlock()
            except RPCError:
                pass
            rpc.walletpassphrase(pw, 60, False)
            unlocked = True
            txid = rpc.sendmany("", amounts, 1, comment)
    finally:
        if unlocked:
            try:
                rpc.walletlock()
            except RPCError:
                pass
            print("Note: wallet re-locked. If you stake, unlock it for staking again in OduwaCoin Core.")

    for it in items:
        it["funding_txid"] = txid
        it["funded_amount"] = str(_d(args.amount or it["amount"]))
    man.setdefault("history", []).append({"action": "fund", "txid": txid, "total": str(total),
                                          "at": dt.datetime.now(dt.timezone.utc).isoformat()})
    _save_manifest(args.manifest, man)
    print("Sent %s OWC. txid %s" % (_f(total), txid))
    print("Explorer: %s" % Explorer(args.explorer).tx_url(txid))


# ---------------------------------------------------------------------------
def cmd_balance(args):
    ex = Explorer(args.explorer)
    targets = []
    if os.path.isfile(args.target):
        man = _load_manifest(args.target)
        targets = [(it["serial"], it["address"]) for it in man["items"]]
    elif keys.is_valid_address(args.target, args.network):
        targets = [("-", args.target)]
    else:
        try:
            targets = [("-", keys.address_from_wif(args.target, args.network))]
        except ValueError as e:
            raise SystemExit("not a manifest, address or private key: %s" % e)
    total = Decimal(0)
    print("%-14s %-35s %16s %14s  %s" % ("serial", "address", "balance OWC", "unconfirmed", "status"))
    for serial, addr in targets:
        a = ex.address(addr)
        status = "empty" if a["balance"] == 0 and a["received"] == 0 else (
            "REDEEMED" if a["balance"] == 0 else "funded")
        total += a["balance"]
        print("%-14s %-35s %16s %14s  %s" % (serial, addr, _f(a["balance"]), _f(a["unconfirmed"]), status))
    if len(targets) > 1:
        print("Total: %s OWC" % _f(total))


# ---------------------------------------------------------------------------
def _p2pkh_script(addr):
    h160 = keys.b58check_decode(addr)[1:]
    return "76a914" + h160.hex() + "88ac"


def cmd_sweep(args):
    keys.self_test()
    wif = args.wif or getpass.getpass("Private key (input hidden): ").strip()
    try:
        src = keys.address_from_wif(wif, args.network)
    except ValueError as e:
        raise SystemExit("invalid private key: %s" % e)
    if not keys.is_valid_address(args.to, args.network):
        raise SystemExit("destination is not a valid OduwaCoin address: %s" % args.to)
    if args.to == src:
        raise SystemExit("destination must differ from the paper wallet address")

    ex = Explorer(args.explorer)
    rpc = _rpc(args)
    utxos = [u for u in ex.utxos(src) if u["confirmations"] >= args.minconf]
    if not utxos:
        raise SystemExit("No confirmed coins found at %s" % src)

    # If the local node is synced, double-check every coin is still unspent.
    try:
        synced = rpc.getblockcount() >= ex.height() - 3
    except RPCError:
        synced = False
    script = _p2pkh_script(src)
    checked = []
    for u in utxos:
        if synced:
            out = rpc.gettxout(u["txid"], u["vout"], True)
            if not out:
                print("  skipping %s:%d (already spent per local node)" % (u["txid"], u["vout"]))
                continue
            if _d(out["value"]) != u["amount"] or out["scriptPubKey"]["hex"] != script:
                raise SystemExit("explorer data disagrees with local node for %s:%d" % (u["txid"], u["vout"]))
        checked.append(u)
    if not checked:
        raise SystemExit("Nothing left to sweep.")

    total = sum(u["amount"] for u in checked)
    size_kb = Decimal(10 + 148 * len(checked) + 34) / 1000
    fee_rate = _d(args.feerate) if args.feerate else MIN_FEE_PER_KB
    fee = max(fee_rate, (size_kb.to_integral_value(ROUND_UP) * fee_rate)).quantize(COIN_DECIMALS)
    send = total - fee
    if send <= 0:
        raise SystemExit("balance %s OWC does not cover the %s OWC fee" % (total, fee))

    inputs = [{"txid": u["txid"], "vout": u["vout"]} for u in checked]
    raw = rpc.createrawtransaction(inputs, {args.to: float(send)})
    prev = [{"txid": u["txid"], "vout": u["vout"], "scriptPubKey": script} for u in checked]
    signed = rpc.signrawtransaction(raw, prev, [wif])
    if not signed.get("complete"):
        raise SystemExit("signing failed: %s" % signed.get("errors"))
    dec = rpc.decoderawtransaction(signed["hex"])
    outs = [(o["scriptPubKey"].get("addresses", ["?"])[0], _d(o["value"])) for o in dec["vout"]]
    if outs != [(args.to, send)]:
        raise SystemExit("decoded transaction does not match expectations: %s" % outs)

    print("Sweep %s" % src)
    print("  inputs : %d coin(s), %s OWC" % (len(checked), _f(total)))
    print("  fee    : %s OWC" % _f(fee))
    print("  send   : %s OWC -> %s" % (_f(send), args.to))
    if not args.broadcast:
        print("\nDry run only. Re-run with --broadcast to send. Signed hex:\n%s" % signed["hex"])
        return
    try:
        txid = rpc.sendrawtransaction(signed["hex"])
    except RPCError as e:
        if not args.explorer_broadcast:
            raise SystemExit("node rejected/failed to relay: %s (try --explorer-broadcast)" % e)
        txid = ex.sendtx(signed["hex"])
    print("Broadcast. txid %s\n%s" % (txid, ex.tx_url(txid)))
    if args.manifest:
        man = _load_manifest(args.manifest)
        for it in man["items"]:
            if it["address"] == src:
                it["redeemed_txid"] = txid
        _save_manifest(args.manifest, man)


# ---------------------------------------------------------------------------
def main(argv=None):
    p = argparse.ArgumentParser(prog="owc-paper", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--network", choices=["main", "test"], default="main")
    p.add_argument("--explorer", default=DEFAULT_EXPLORER)
    rpcg = p.add_argument_group("OduwaCoin Core RPC")
    rpcg.add_argument("--datadir", help="wallet data directory (reads OduwaCoin.conf)")
    rpcg.add_argument("--conf")
    rpcg.add_argument("--rpcurl")
    rpcg.add_argument("--rpcuser")
    rpcg.add_argument("--rpcpassword")
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="create keys offline and render PDFs")
    g.add_argument("kind", choices=["wallet", "voucher"])
    g.add_argument("-n", "--count", type=int, default=1)
    g.add_argument("--amount", help="amount per item (required for vouchers unless in CSV)")
    g.add_argument("--csv", help="CSV with columns amount,to,from,message[,serial] – one row per item")
    g.add_argument("--to", help="recipient name (vouchers)")
    g.add_argument("--from", dest="sender", help="giver name (vouchers)")
    g.add_argument("--message", help="gift message (vouchers)")
    g.add_argument("--issuer", default="OduwaCoin", help="brand line on the voucher")
    g.add_argument("--claim-url", default="https://oduwacoin.io/gift?a={address}",
                   help="URL for the voucher's front QR; {address} is replaced. Use '' to link the explorer instead")
    g.add_argument("--serial-prefix")
    g.add_argument("--out", default="owc-paper-out")
    g.add_argument("--name", help="output file stem")
    g.add_argument("--export-keys", metavar="CSV", help="also write a SECRET key backup (for reclaiming)")
    g.add_argument("--allow-online", action="store_true", help="skip the offline-machine safety check")
    g.set_defaults(func=cmd_generate)

    f = sub.add_parser("fund", help="load a batch from OduwaCoin Core (one sendmany transaction)")
    f.add_argument("manifest")
    f.add_argument("--amount", help="override amount per item")
    f.add_argument("--comment")
    f.add_argument("--refund", action="store_true", help="fund again even if already funded (top-up)")
    f.add_argument("-y", "--yes", action="store_true")
    f.set_defaults(func=cmd_fund)

    b = sub.add_parser("balance", help="balance of a manifest, address or private key")
    b.add_argument("target")
    b.set_defaults(func=cmd_balance)

    s = sub.add_parser("sweep", help="redeem a paper wallet / voucher into an address")
    s.add_argument("wif", nargs="?", help="private key (omit to be prompted without echo)")
    s.add_argument("--to", required=True, help="destination OduwaCoin address")
    s.add_argument("--minconf", type=int, default=1)
    s.add_argument("--feerate", help="OWC per kB (default 0.0001)")
    s.add_argument("--broadcast", action="store_true", help="actually send (default is a dry run)")
    s.add_argument("--explorer-broadcast", action="store_true",
                   help="if the node cannot relay, broadcast through the explorer")
    s.add_argument("--manifest", help="record the redemption txid in this manifest")
    s.set_defaults(func=cmd_sweep)

    args = p.parse_args(argv)
    try:
        args.func(args)
    except RPCError as e:
        raise SystemExit("OduwaCoin Core: %s" % e)


if __name__ == "__main__":
    main()
