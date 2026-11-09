"""PDF rendering for OduwaCoin paper wallets and gift vouchers (ReportLab + qrcode)."""
import io
import os
from decimal import Decimal

import qrcode
from qrcode.constants import ERROR_CORRECT_M
from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfgen import canvas

GOLD = HexColor("#C9A227")
GOLD_DARK = HexColor("#8A6A12")
INK = HexColor("#141414")
CREAM = HexColor("#FBF6E6")
MUTED = HexColor("#5A5A5A")
RED = HexColor("#A3201B")

LOGO = os.path.join(os.path.dirname(__file__), "owc_logo.png")
PAGE_W, PAGE_H = A4


def _qr(data, dark="#000000", light="#FFFFFF"):
    q = qrcode.QRCode(error_correction=ERROR_CORRECT_M, border=2, box_size=10)
    q.add_data(data)
    q.make(fit=True)
    img = q.make_image(fill_color=dark, back_color=light).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    return ImageReader(buf)


def fmt_amount(a):
    a = Decimal(a).normalize()
    s = "{:,f}".format(a)
    return s


def _split_key(text, n):
    return [text[i:i + n] for i in range(0, len(text), n)]


def _dashed_rect(c, x, y, w, h):
    c.saveState()
    c.setDash(3, 3)
    c.setStrokeColor(MUTED)
    c.setLineWidth(0.5)
    c.rect(x, y, w, h)
    c.restoreState()


def _cut_mark(c, x, y, label):
    c.saveState()
    c.setFont("Helvetica", 6.5)
    c.setFillColor(MUTED)
    c.drawString(x, y, label)
    c.restoreState()


def _fold_line(c, y, label):
    c.saveState()
    c.setDash(6, 3)
    c.setStrokeColor(GOLD_DARK)
    c.setLineWidth(0.6)
    c.line(12 * mm, y, PAGE_W - 12 * mm, y)
    c.setFont("Helvetica-Oblique", 7)
    c.setFillColor(GOLD_DARK)
    c.drawCentredString(PAGE_W / 2, y + 2 * mm, label)
    c.restoreState()


def _paragraphs(c, x, y, width, items, size=8.5, leading=11.5, bullet="•"):
    c.setFont("Helvetica", size)
    c.setFillColor(INK)
    for item in items:
        lines = simpleSplit(item, "Helvetica", size, width - 5 * mm)
        for i, line in enumerate(lines):
            if i == 0 and bullet:
                c.drawString(x, y, bullet)
            c.drawString(x + 4 * mm, y, line)
            y -= leading
        y -= 2
    return y


# ---------------------------------------------------------------------------
# Paper wallet
# ---------------------------------------------------------------------------
def draw_paper_wallet(c, rec, explorer):
    addr, wif = rec["address"], rec["wif"]
    serial = rec["serial"]
    W, H = 186 * mm, 82 * mm
    x0, y0 = (PAGE_W - W) / 2, PAGE_H - 18 * mm - H

    _cut_mark(c, x0 - 3 * mm, y0 + H + 5 * mm, "cut along the dashed line")
    _dashed_rect(c, x0 - 3 * mm, y0 - 3 * mm, W + 6 * mm, H + 6 * mm)

    # Card background
    c.setFillColor(CREAM)
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.6)
    c.roundRect(x0, y0, W, H, 4 * mm, fill=1, stroke=1)

    # Public (left) panel
    qr = 46 * mm
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x0 + 6 * mm, y0 + H - 9 * mm, "LOAD & VERIFY")
    c.setFont("Helvetica", 6.8)
    c.setFillColor(MUTED)
    c.drawString(x0 + 6 * mm, y0 + H - 13 * mm, "Public address – safe to share")
    c.drawImage(_qr(addr), x0 + 6 * mm, y0 + 15 * mm, qr, qr)
    c.setFillColor(INK)
    c.setFont("Courier-Bold", 7.4)
    c.drawString(x0 + 6 * mm, y0 + 10 * mm, addr[:17])
    c.drawString(x0 + 6 * mm, y0 + 6.5 * mm, addr[17:])

    # Centre branding
    cx = x0 + W / 2
    c.drawImage(ImageReader(LOGO), cx - 15 * mm, y0 + H - 38 * mm, 30 * mm, 30 * mm, mask="auto")
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(cx, y0 + H - 45 * mm, "OduwaCoin")
    c.setFont("Helvetica", 8.5)
    c.setFillColor(GOLD_DARK)
    c.drawCentredString(cx, y0 + H - 50 * mm, "PAPER WALLET")
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 6.8)
    c.drawCentredString(cx, y0 + H - 56 * mm, "No. %s" % serial)
    c.drawCentredString(cx, y0 + H - 60 * mm, "Created %s" % rec["created"][:10])
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.6)
    c.line(cx - 18 * mm, y0 + 14 * mm, cx + 18 * mm, y0 + 14 * mm)
    c.setFont("Helvetica", 6.5)
    c.drawCentredString(cx, y0 + 10.5 * mm, "Amount loaded")
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 9)
    label = ("%s OWC" % fmt_amount(rec["amount"])) if rec.get("amount") else "________ OWC"
    c.drawCentredString(cx, y0 + 6 * mm, label)

    # Private (right) panel – dark
    px = x0 + W - 6 * mm - qr - 6 * mm
    c.setFillColor(INK)
    c.roundRect(px, y0, W - (px - x0), H, 4 * mm, fill=1, stroke=0)
    c.rect(px, y0, 6 * mm, H, fill=1, stroke=0)
    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(px + 6 * mm, y0 + H - 9 * mm, "SPEND / REDEEM")
    c.setFont("Helvetica", 6.8)
    c.setFillColor(white)
    c.drawString(px + 6 * mm, y0 + H - 13 * mm, "Private key – NEVER share")
    c.drawImage(_qr(wif), px + 6 * mm, y0 + 15 * mm, qr, qr)
    c.setFont("Courier-Bold", 6.6)
    c.setFillColor(white)
    parts = _split_key(wif, 26)
    for i, p in enumerate(parts):
        c.drawString(px + 6 * mm, y0 + 10 * mm - i * 3.4 * mm, p)

    # Instructions
    y = y0 - 14 * mm
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x0, y, "How to use this paper wallet")
    y -= 8 * mm
    col_w = (W - 8 * mm) / 2
    left = [
        "LOAD: send OWC from OduwaCoin Core (Send tab) to the public address on the left. You can add "
        "more at any time.",
        "VERIFY: scan the left QR with any QR app, or search the address on %s, to see the balance. "
        "Anyone can check; nobody can spend without the private key." % explorer.base.replace("https://", ""),
        "STORE: keep the card dry, out of sunlight and out of sight. A laminated copy or a second "
        "printout in another safe place protects against loss.",
    ]
    right = [
        "SPEND: in OduwaCoin Core open Help > Debug window > Console and run "
        "importprivkey \"<private key>\" \"paper\" true. The wallet rescans and the full balance "
        "appears. Alternatively sweep it with: owc-paper sweep.",
        "AFTER SPENDING: treat the card as used. Do not load it again once the key has been typed "
        "or scanned into any device.",
        "Anyone who sees the private key (photo, copier, cloud printer) can take the funds.",
    ]
    _paragraphs(c, x0, y, col_w, left)
    _paragraphs(c, x0 + col_w + 8 * mm, y, col_w, right)

    c.setFont("Helvetica", 6.5)
    c.setFillColor(MUTED)
    c.drawCentredString(PAGE_W / 2, 10 * mm,
                        "Generated offline by owc-paper (contrib/paperwallet, OduwaCoin Core). "
                        "Keys use compressed secp256k1, address prefix A, WIF prefix P.")


# ---------------------------------------------------------------------------
# Gift voucher / certificate
# ---------------------------------------------------------------------------
def _ornament_border(c, x, y, w, h):
    c.setStrokeColor(GOLD)
    c.setLineWidth(2.2)
    c.roundRect(x, y, w, h, 5 * mm)
    c.setLineWidth(0.6)
    c.roundRect(x + 3 * mm, y + 3 * mm, w - 6 * mm, h - 6 * mm, 3.5 * mm)
    for (ax, ay) in [(x + 3 * mm, y + 3 * mm), (x + w - 3 * mm, y + 3 * mm),
                     (x + 3 * mm, y + h - 3 * mm), (x + w - 3 * mm, y + h - 3 * mm)]:
        c.setFillColor(GOLD)
        c.circle(ax, ay, 1.4 * mm, fill=1, stroke=0)


def draw_voucher(c, rec, explorer, issuer, claim_url=None):
    """Tri-fold A4 voucher: three 210 x 99 mm panels (folds to DL envelope size).

    Panel 1 (top)    – the gift certificate front, stays visible.
    Panel 2 (middle) – claim instructions.
    Panel 3 (bottom) – private key. Fold it up over panel 2 first (key faces inward),
                       then fold panel 1 down over the outside and seal.
    """
    addr, wif, serial = rec["address"], rec["wif"], rec["serial"]
    amount = fmt_amount(rec["amount"])
    ph = PAGE_H / 3
    m = 7 * mm
    W = PAGE_W - 2 * m
    p1, p2, p3 = 2 * ph, ph, 0  # panel bottoms

    # ---------------- Panel 1: certificate front ----------------
    x0, y0, H = m, p1 + m, ph - 2 * m
    c.setFillColor(CREAM)
    c.roundRect(x0, y0, W, H, 5 * mm, fill=1, stroke=0)
    _ornament_border(c, x0, y0, W, H)
    c.drawImage(ImageReader(LOGO), x0 + 9 * mm, y0 + H - 43 * mm, 34 * mm, 34 * mm, mask="auto")
    tx = x0 + 49 * mm
    c.setFillColor(GOLD_DARK)
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(tx, y0 + H - 14 * mm, (issuer or "ODUWACOIN").upper())
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 25)
    c.drawString(tx, y0 + H - 25 * mm, "Gift Certificate")
    c.setFont("Helvetica-Bold", 30)
    c.setFillColor(GOLD_DARK)
    c.drawString(tx, y0 + H - 38 * mm, "%s OWC" % amount)

    qs = 25 * mm
    qx, qy = x0 + W - qs - 9 * mm, y0 + H - qs - 9 * mm
    check_url = claim_url.format(address=addr) if claim_url else explorer.address_url(addr)
    c.drawImage(_qr(check_url), qx, qy, qs, qs)
    c.setFont("Helvetica", 6)
    c.setFillColor(MUTED)
    c.drawCentredString(qx + qs / 2, qy - 3 * mm, "Scan to check balance")

    fy = y0 + H - 52 * mm
    for label, val in (("To", rec.get("to", "")), ("From", rec.get("from", ""))):
        c.setFont("Helvetica", 8.5)
        c.setFillColor(MUTED)
        c.drawString(x0 + 11 * mm, fy, label)
        c.setStrokeColor(GOLD)
        c.setLineWidth(0.5)
        c.line(x0 + 22 * mm, fy - 1.3 * mm, x0 + 104 * mm, fy - 1.3 * mm)
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 10.5)
        c.drawString(x0 + 24 * mm, fy, val)
        fy -= 8 * mm
    msg = rec.get("message") or ""
    if msg:
        c.setFont("Helvetica-Oblique", 9.5)
        c.setFillColor(INK)
        for line in simpleSplit("\u201c%s\u201d" % msg, "Helvetica-Oblique", 9.5, 95 * mm)[:2]:
            c.drawString(x0 + 11 * mm, fy, line)
            fy -= 4.4 * mm

    lx = x0 + 116 * mm
    rows = (("Voucher No.", serial, "Helvetica-Bold", 9), ("Issued", rec["created"][:10], "Helvetica-Bold", 9),
            ("Address", addr, "Courier", 6.6))
    ry = y0 + 24 * mm
    for label, val, font, size in rows:
        c.setFont("Helvetica", 7)
        c.setFillColor(MUTED)
        c.drawString(lx, ry, label)
        c.setFont(font, size)
        c.setFillColor(INK)
        c.drawString(lx + 17 * mm, ry, val)
        ry -= 6.5 * mm

    # ---------------- Panel 2: instructions ----------------
    x0, y0, H = m, p2 + m, ph - 2 * m
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.8)
    c.roundRect(x0, y0, W, H, 4 * mm)
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(x0 + 9 * mm, y0 + H - 12 * mm, "How to claim your %s OWC" % amount)
    c.setFont("Helvetica", 7.5)
    c.setFillColor(MUTED)
    c.drawString(x0 + 9 * mm, y0 + H - 17 * mm,
                 "Your private key is on the panel below. Whoever holds it controls the coins, so claim them soon.")
    steps = [
        ("Install the wallet", "Download OduwaCoin Core from the Releases page at "
                               "github.com/ODUWAX/oduwacoin and let it finish syncing."),
        ("Open the console", "In the wallet choose Help > Debug window > Console."),
        ("Import the key", "Type  importprivkey \"<your private key>\" \"gift\" true  and press Enter. "
                           "The wallet rescans and the balance appears within minutes."),
        ("Make it yours", "Send the coins to a fresh address in your own wallet. Once moved, this voucher "
                          "is empty and can be kept as a keepsake."),
    ]
    colw = (W - 18 * mm - 3 * 6 * mm) / 4
    for i, (head, body) in enumerate(steps):
        sx = x0 + 9 * mm + i * (colw + 6 * mm)
        sy = y0 + H - 30 * mm
        c.setFillColor(GOLD)
        c.circle(sx + 4 * mm, sy + 1.2 * mm, 4 * mm, fill=1, stroke=0)
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(sx + 4 * mm, sy - 0.2 * mm, str(i + 1))
        c.setFont("Helvetica-Bold", 8.6)
        c.drawString(sx + 10 * mm, sy, head)
        yy = sy - 8 * mm
        for line in simpleSplit(body, "Helvetica", 7.6, colw):
            c.setFont("Helvetica", 7.6)
            c.drawString(sx, yy, line)
            yy -= 3.6 * mm
    c.setFont("Helvetica", 7)
    c.setFillColor(MUTED)
    c.drawString(x0 + 9 * mm, y0 + 7 * mm,
                 "Advanced: owc-paper sweep <private key> --to <your address> moves everything in one transaction.")
    c.drawRightString(x0 + W - 9 * mm, y0 + 7 * mm, "Voucher %s" % serial)

    # ---------------- Panel 3: private key ----------------
    x0, y0, H = m, p3 + m, ph - 2 * m
    c.setFillColor(INK)
    c.roundRect(x0, y0, W, H, 5 * mm, fill=1, stroke=0)
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.2)
    c.roundRect(x0 + 3 * mm, y0 + 3 * mm, W - 6 * mm, H - 6 * mm, 3.5 * mm)
    qs = 66 * mm
    qx, qy = x0 + 10 * mm, y0 + (H - qs) / 2
    c.drawImage(_qr(wif), qx, qy, qs, qs)
    ix = qx + qs + 10 * mm
    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(ix, y0 + H - 15 * mm, "PRIVATE KEY")
    c.setFont("Helvetica", 8)
    c.setFillColor(white)
    c.drawString(ix, y0 + H - 21 * mm, "Scan or type this into OduwaCoin Core to claim %s OWC." % amount)
    c.setFont("Courier-Bold", 10.5)
    for i, part in enumerate(_split_key(wif, 26)):
        c.drawString(ix, y0 + H - 33 * mm - i * 5.5 * mm, part)
    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 7.6)
    yy = y0 + 22 * mm
    for line in simpleSplit("Keep secret. Anyone who sees or photographs this key can spend the gift. If the "
                            "seal was broken before you received it, ask the giver to check the balance.",
                            "Helvetica-Bold", 7.6, W - (ix - x0) - 10 * mm):
        c.drawString(ix, yy, line)
        yy -= 3.8 * mm
    c.setFont("Helvetica", 6.5)
    c.setFillColor(HexColor("#BBBBBB"))
    c.drawString(ix, y0 + 8 * mm, "Voucher %s" % serial)

    # Fold guides
    _fold_line(c, p2 + ph, "fold 2 – fold the certificate down over the outside, then seal")
    _fold_line(c, ph, "fold 1 – fold the key panel up first so the key faces inward")


DEFAULT_CLAIM_URL = "https://oduwacoin.io/gift?a={address}"


def render(records, path, kind, explorer, issuer=None, title=None, claim_url=DEFAULT_CLAIM_URL):
    c = canvas.Canvas(path, pagesize=A4)
    c.setTitle(title or ("OduwaCoin %s" % ("Gift Vouchers" if kind == "voucher" else "Paper Wallets")))
    c.setAuthor(issuer or "OduwaCoin")
    c.setSubject("Contains private keys – print offline, then delete this file")
    for rec in records:
        if kind == "voucher":
            draw_voucher(c, rec, explorer, issuer, claim_url)
        else:
            draw_paper_wallet(c, rec, explorer)
        c.showPage()
    c.save()
