# OduwaCoin Paper Wallets & Gift Vouchers (`owc-paper`)

Create OduwaCoin (OWC) **paper wallets** for cold storage and **gift vouchers** (gift
certificates) that hold real OWC, load them from **OduwaCoin Core**, and let recipients
redeem them back into OduwaCoin Core.

```
 OFFLINE computer                    ONLINE computer (OduwaCoin Core)          Recipient
 ───────────────                     ────────────────────────────────          ─────────
 owc-paper generate ──► PDF ─► print                                            
                    └─► manifest.json ──► owc-paper fund  ──► sendmany tx ──►  paper holds OWC
                                          owc-paper balance (status)            
                                                                        importprivkey / owc-paper sweep
```

- Keys are generated on your own computer with the OS secure random generator, in the
  exact format OduwaCoin Core uses (compressed secp256k1, addresses start with **A**,
  private keys start with **P**). Every key is self-checked before it is printed.
- Generated keys have been tested against OduwaCoin Core v2.0.0.3: `importprivkey`
  accepts them as the wallet's own, and sweep transactions sign with `complete: true`.
- The manifest only ever holds **public** data (serials, addresses, amounts, txids), so it
  is safe to copy to the online wallet computer. Private keys exist only on paper (plus an
  optional backup CSV you ask for explicitly).
- Funding uses one `sendmany` transaction from your OduwaCoin Core wallet, so a batch of
  100 vouchers costs one network fee.

## Install

Python 3.8+.

```bash
cd contrib/paperwallet
pip install .            # installs the `owc-paper` command
# or without installing:  pip install -r requirements.txt && python3 -m owc_paper --help
```

OduwaCoin Core must allow RPC for `fund` and `sweep`. Add the following to `OduwaCoin.conf`
(Linux `~/.OduwaCoin/`, Windows `%APPDATA%\OduwaCoin\`, macOS
`~/Library/Application Support/OduwaCoin/`) and restart the wallet:

```
server=1
rpcuser=choose-a-user
rpcpassword=choose-a-long-random-password
```

## 1. Generate (offline)

Use a computer that is disconnected from the network (a live USB is ideal). The tool
refuses to run online unless you pass `--allow-online`.

Paper wallets:

```bash
owc-paper generate wallet -n 5 --amount 1000 --out batch1
```

Gift vouchers, one row per voucher (see `example-gifts.csv`):

```bash
owc-paper generate voucher --csv example-gifts.csv \
    --issuer "Oduwa Blockchain Solutions" --out xmas2026
# or simply:
owc-paper generate voucher -n 20 --amount 50 --message "Welcome to OduwaCoin" --out promo
```

Outputs:

| File | Contents | Handle as |
|---|---|---|
| `*.pdf` | printable wallets / vouchers **with private keys** | print, then `shred -u` |
| `*.manifest.json` | serials, addresses, amounts | public, copy to the online PC |
| `--export-keys keys.csv` (optional) | serial + private key | secret; only if you want to reclaim unredeemed vouchers |

**Voucher layout:** a tri-fold A4 sheet (folds to DL envelope size). Top panel: gift
certificate (amount, to/from, message, serial, balance-check QR). Middle panel: claim
instructions. Bottom panel: private key. Fold the key panel up first (key faces inward),
fold the certificate down over the outside, and seal the edges with tape or a
tamper-evident sticker.

**Paper wallet layout:** a cut-out card with the public address QR (load/verify) on the
left and the private key QR (spend) on the right, with usage instructions below.

Print on a printer that is directly connected (USB) and has no cloud or Wi-Fi print
queue, then securely delete the PDF.

## 2. Fund from OduwaCoin Core (online)

Copy only the manifest to the computer that runs your OduwaCoin Core wallet:

```bash
owc-paper fund xmas2026/vouchers-….manifest.json
```

The tool lists every serial, address and amount, checks each address with the node
(`validateaddress`), shows the total against your balance, and asks for confirmation. It
then sends one `sendmany` transaction. If the wallet is encrypted, or unlocked for staking
only, it asks for the passphrase, unlocks for 60 seconds and re-locks afterwards (unlock it
for staking again if you stake). The funding txid is written back into the manifest, so
running `fund` again does not double-pay. Use `--refund --amount X` to top up.

If you prefer the GUI, open the Send tab, choose "Add Recipient" for each address in the
manifest and send. `owc-paper balance` will still track status.

## 3. Check status

```bash
owc-paper balance xmas2026/vouchers-….manifest.json   # whole batch: funded / REDEEMED / empty
owc-paper balance AXXZK27umncW1YCQURYGjCnbYWTHfMjx5Q   # one address
```

Balances come from the public explorer at `ex1.oduwacoin.io` (Blockbook).

## 4. Redeem / spend

**In OduwaCoin Core (recipients):** Help → Debug window → Console:

```
importprivkey "P…private key…" "gift" true
```

The wallet rescans and the balance appears. Then send the coins to a fresh address of
your own, and treat the paper as spent.

**One-step sweep (`owc-paper`):** moves everything to an address in a single transaction
without adding the key to the wallet permanently:

```bash
owc-paper sweep --to AYourOwnAddress...            # prompts for the key (hidden)
owc-paper sweep --to AYourOwnAddress... --broadcast
```

Sweep finds the coins through the explorer and, if your node is synced, double-checks
every coin with `gettxout`. It builds the transaction with `createrawtransaction`, signs it
in OduwaCoin Core with `signrawtransaction` (which handles OduwaCoin's timestamped
transaction format), decodes it to confirm the single output, and only broadcasts with
`--broadcast`. Default fee: 0.0001 OWC per started kB (the network minimum). If your node
cannot relay, add `--explorer-broadcast`.

## Security notes

- Anyone who sees a private key can take the funds. Photos, scanners, cloud printers and
  synced folders all count as seeing it.
- Keep the backup CSV (if you created one) encrypted and offline. Without it, issued
  vouchers cannot be reclaimed. That is intentional for true gifts.
- Vouchers do not expire on-chain. If you need expiry, keep `--export-keys` and sweep
  unredeemed vouchers back after your deadline (`owc-paper balance` shows which).
- Run `python3 -m unittest discover -s tests` before a large batch. Set
  `OWC_DATADIR=<datadir>` with oduwacoind running to include checks against
  OduwaCoin Core.

## Tests

```bash
python3 -m unittest discover -s tests             # unit tests
OWC_DATADIR=~/.OduwaCoin python3 -m unittest discover -s tests   # plus OduwaCoin Core checks
```
