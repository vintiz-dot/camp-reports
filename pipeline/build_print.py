"""Build print.pdf — laser-etch artwork for wooden hearts.

Two pages per camper, 1:1 actual size:
  FRONT  portrait + HEC mark + name (+ full club caption at 60 mm)
  BACK   QR to the camper's journal + caption

Every element is placed against a numerically-derived heart mask and
binary-searched to the largest size that still fits, so nothing can stray
off the wood at either size. The QR is drawn as vector rectangles, and
its payload is uppercase and scheme-less so it encodes in QR alphanumeric
mode — that alone doubles the module size on a small heart.

Outputs (in camp-reports/print/):
  print.pdf                 40 mm hearts, photo-realistic  <- as ordered
  print_60mm.pdf            60 mm hearts, full caption
  print_graphic.pdf         40 mm, high-contrast variant
  print_60mm_graphic.pdf    60 mm, high-contrast variant
  *_noguides.pdf            same without the red alignment outline
"""

import json
import math
from pathlib import Path

import cv2
import numpy as np
import qrcode
from qrcode.constants import ERROR_CORRECT_Q
from PIL import Image
from reportlab.lib.colors import black, red
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas

PROJ = Path(r"C:\Users\Dell\OneDrive\Desktop\hec ads\camp-reports")
SITE = Path(r"C:\Users\Dell\OneDrive\Desktop\hec ads\hec-site\hec-site")
PRINT = PROJ / "print"
HEADSHOTS = PRINT / "headshots"
WORK = PRINT / "_work"
LOGO_SRC = SITE / "assets" / "img" / "logo.png"

QR_ECC = ERROR_CORRECT_Q      # 25% recovery — survives wood grain and burn drift
DPI = 600
MIN_MODULE_MM = 0.45          # below this a laser-etched QR stops scanning reliably

FONT_NAME = "Helvetica-Bold"  # bold survives etching far better than thin serif
FONT_SMALL = "Helvetica-Bold"

CAPTION_CLUB = "HANOI HAPPY ENGLISH CLUB"
CAPTION_TAG_1 = "Learning, an endless"
CAPTION_TAG_2 = "journey to perfection"
CAPTION_YEAR = "2026 SUMMER CAMP"


# ── geometry, recomputed per heart size ──────────────────────────────
class Heart:
    """Heart mask + safe region for one physical size."""

    def __init__(self, width_mm, safe_inset_mm, ppm=20):
        self.W = width_mm
        self.PAGE = width_mm                      # square page, heart centred
        self.k = width_mm / 40.0                  # scale vs the 40 mm design
        self.inset = safe_inset_mm
        self.ppm = ppm

        t = np.linspace(0, 2 * math.pi, 1400)
        x = 16 * np.sin(t) ** 3
        y = (13 * np.cos(t) - 5 * np.cos(2 * t)
             - 2 * np.cos(3 * t) - np.cos(4 * t))
        s = width_mm / (x.max() - x.min())
        x, y = x * s, y * s
        x -= (x.max() + x.min()) / 2
        y -= (y.max() + y.min()) / 2
        self.hx, self.hy = x, y
        self.H = y.max() - y.min()

        n = int(self.PAGE * ppm)
        mask = np.zeros((n, n), np.uint8)
        pts = np.stack([(x + self.PAGE / 2) * ppm,
                        (self.PAGE / 2 - y) * ppm], axis=1).astype(np.int32)
        cv2.fillPoly(mask, [pts], 255)
        er = int(safe_inset_mm * ppm)
        self.safe = cv2.erode(mask, np.ones((er * 2 + 1, er * 2 + 1), np.uint8))
        self.dist = cv2.distanceTransform(self.safe, cv2.DIST_L2, 5) / ppm

    # -- queries -------------------------------------------------------
    def half_width_at(self, y_mm):
        row = int(round((self.PAGE / 2 - y_mm) * self.ppm))
        row = max(0, min(self.safe.shape[0] - 1, row))
        xs = np.flatnonzero(self.safe[row])
        return 0.0 if xs.size == 0 else (xs.max() - xs.min()) / 2 / self.ppm

    def fits(self, cx, cy, w, h):
        x0 = int((self.PAGE / 2 + cx - w / 2) * self.ppm)
        x1 = int((self.PAGE / 2 + cx + w / 2) * self.ppm)
        y0 = int((self.PAGE / 2 - cy - h / 2) * self.ppm)
        y1 = int((self.PAGE / 2 - cy + h / 2) * self.ppm)
        if x0 < 0 or y0 < 0 or x1 >= self.safe.shape[1] or y1 >= self.safe.shape[0]:
            return False
        return bool(self.safe[y0:y1, x0:x1].min() > 0)

    def max_circle_at(self, cx, cy):
        x = int((self.PAGE / 2 + cx) * self.ppm)
        y = int((self.PAGE / 2 - cy) * self.ppm)
        if not (0 <= x < self.dist.shape[1] and 0 <= y < self.dist.shape[0]):
            return 0.0
        return float(self.dist[y, x]) * 2

    def max_box_at(self, cx, cy, aspect, limit=40.0):
        lo, hi = 0.0, limit
        for _ in range(28):
            mid = (lo + hi) / 2
            if self.fits(cx, cy, mid, mid / aspect):
                lo = mid
            else:
                hi = mid
        return lo

    def best_qr(self, reserve_below, max_size=None):
        """Largest scannable QR that still leaves a usable band beneath it.

        Capping the size matters: left unbounded the QR fills the widest
        part of the heart and pushes every caption line down into the
        taper, where nothing legible fits.
        """
        best = (0.0, 0.0)
        for cy in np.arange(-2.0 * self.k, 12.0 * self.k, 0.1):
            s = self.max_box_at(0.0, float(cy), 1.0)
            if max_size:
                s = min(s, max_size)
            if cy - s / 2 < -(self.H / 2) + reserve_below:
                continue
            if s > best[0] + 1e-6:
                best = (s, float(cy))
        return best


# ── portrait preparation for wood ────────────────────────────────────
def wood_tone_lut():
    """Wood loses detail in deep shadow and shows nothing in highlight:
    lift the black point, hold a true white, expand the midtones."""
    x = np.arange(256, dtype=np.float32) / 255.0
    s = 1 / (1 + np.exp(-11 * (x - 0.47)))
    s = (s - s[0]) / (s[-1] - s[0])
    out = 0.10 + s * 0.90
    out[x > 0.93] = 1.0
    return np.clip(out * 255, 0, 255).astype(np.uint8)


LUT = wood_tone_lut()


def prep_portrait(bgr, out_px, style="photo"):
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    g = cv2.bilateralFilter(g, 9, 45, 45)             # calm skin, keep edges
    g = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8)).apply(g)
    blur = cv2.GaussianBlur(g, (0, 0), max(1.0, g.shape[0] / 260))
    g = cv2.addWeighted(g, 1.55, blur, -0.55, 0)      # hair + eyes pop
    g = cv2.LUT(g, LUT)

    if style == "graphic":
        g = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(6, 6)).apply(g)
        g = np.clip(np.floor(g.astype(np.float32) / 255 * 4) / 3 * 255, 0, 255
                    ).astype(np.uint8)

    g = cv2.resize(g, (out_px, out_px), interpolation=cv2.INTER_AREA)

    # Tight feathered vignette. Classroom walls and whiteboards otherwise
    # bleed into the frame and etch as distracting noise around the face;
    # fading to white early keeps the burn on the child alone.
    yy, xx = np.mgrid[0:out_px, 0:out_px].astype(np.float32)
    r = np.sqrt((xx - out_px / 2) ** 2 +
                ((yy - out_px * 0.47) * 1.06) ** 2) / (out_px / 2)
    fade = np.clip((0.88 - r) / 0.24, 0, 1)
    out = g.astype(np.float32) * fade + 255.0 * (1 - fade)
    return cv2.cvtColor(np.clip(out, 0, 255).astype(np.uint8), cv2.COLOR_GRAY2RGB)


_logo_cache = {}


def logo_bw(out_px):
    """HEC mark as black artwork on white (the alpha channel is the art)."""
    if out_px in _logo_cache:
        return _logo_cache[out_px]
    im = Image.open(LOGO_SRC).convert("RGBA")
    a = np.array(im.getchannel("A"))
    ys, xs = np.nonzero(a > 40)
    a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    h, w = a.shape
    s = out_px / max(h, w)
    a = cv2.resize(a, (max(1, int(w * s)), max(1, int(h * s))),
                   interpolation=cv2.INTER_AREA)
    art = cv2.cvtColor((255 - a).astype(np.uint8), cv2.COLOR_GRAY2RGB)
    _logo_cache[out_px] = art
    return art


LOGO_ASPECT = (lambda a: a.shape[1] / a.shape[0])(logo_bw(240))


# ── drawing ──────────────────────────────────────────────────────────
def centred_text(c, H, text, y_mm, font, max_pt, min_pt, tracking=0.0,
                 warn=None, label=""):
    """Draw centred text auto-fitted to the heart's width at that height.

    Returns None (drawing nothing) when the heart is too narrow there even
    at min_pt — silently spilling text past the wood edge is worse than
    omitting it, and the caller gets told.
    """
    # measure at the text's own cap height, not just its baseline row
    cap = max_pt / 72 * 25.4 * 0.72
    avail = min(H.half_width_at(y_mm),
                H.half_width_at(y_mm + cap)) * 2 * 0.92
    size = max_pt
    fitted = False
    while size >= min_pt:
        w = pdfmetrics.stringWidth(text, font, size) + tracking * mm * (len(text) - 1)
        if w <= avail * mm:
            fitted = True
            break
        size -= 0.05
    if not fitted:
        if warn is not None:
            warn.append(f"no room for {label or text!r} at y={y_mm:+.1f} "
                        f"(only {avail:.1f} mm wide)")
        return None

    c.setFillColor(black)
    w = pdfmetrics.stringWidth(text, font, size) + tracking * mm * (len(text) - 1)
    t = c.beginText((H.PAGE / 2) * mm - w / 2, (H.PAGE / 2 + y_mm) * mm)
    t.setFont(font, size)
    if tracking:
        t.setCharSpace(tracking * mm)
    t.textOut(text)
    c.drawText(t)
    return size


def stack_text(c, H, lines, y_start, warn):
    """Lay out successive lines downward, tightening as the heart narrows.
    lines: [(text, font, max_pt, min_pt, tracking, gap_after)]"""
    y = y_start
    for text, font, max_pt, min_pt, tracking, gap in lines:
        got = centred_text(c, H, text, y, font, max_pt, min_pt, tracking,
                           warn=warn, label=text)
        y -= gap if got is None else max(gap, got / 72 * 25.4 * 1.05)
    return y


def place_image(c, H, rgb, cx, cy, w, h, tmp_name):
    """cx/cy are centre-origin mm (y up) — convert to page points."""
    path = WORK / tmp_name
    Image.fromarray(rgb).save(path, "PNG")
    c.drawImage(str(path), (H.PAGE / 2 + cx - w / 2) * mm,
                (H.PAGE / 2 + cy - h / 2) * mm, w * mm, h * mm, mask=None)


def draw_guide(c, H):
    """Hairline heart outline in red — alignment reference, never etch."""
    c.setStrokeColor(red)
    c.setLineWidth(0.2)
    p = c.beginPath()
    p.moveTo((H.PAGE / 2 + H.hx[0]) * mm, (H.PAGE / 2 + H.hy[0]) * mm)
    for x, y in zip(H.hx[1:], H.hy[1:]):
        p.lineTo((H.PAGE / 2 + x) * mm, (H.PAGE / 2 + y) * mm)
    p.close()
    c.drawPath(p, stroke=1, fill=0)


def draw_qr(c, H, data, cx, cy, size):
    q = qrcode.QRCode(error_correction=QR_ECC, border=0)
    q.add_data(data)
    q.make(fit=True)
    m = q.get_matrix()
    n = len(m)
    mod = size / n
    x0 = H.PAGE / 2 + cx - size / 2
    y0 = H.PAGE / 2 + cy - size / 2
    c.setFillColor(black)
    for r, row in enumerate(m):
        start = None
        for col in range(n + 1):                       # merge runs
            on = col < n and row[col]
            if on and start is None:
                start = col
            elif not on and start is not None:
                c.rect((x0 + start * mod) * mm, (y0 + (n - r - 1) * mod) * mm,
                       (col - start) * mod * mm, mod * mm, stroke=0, fill=1)
                start = None
    return n, mod


# ── page composition ─────────────────────────────────────────────────
def front_page(c, H, slug, name, style, guides, full_caption, warn):
    if guides:
        draw_guide(c, H)
    k = H.k
    sx, sy = 7.3 * k, 4.2 * k

    pd = H.max_circle_at(-sx, sy) * 0.96
    head = cv2.imread(str(HEADSHOTS / f"{slug}.jpg"))
    place_image(c, H, prep_portrait(head, int(pd / 25.4 * DPI), style),
                -sx, sy, pd, pd, f"{slug}_{style}_{int(H.W)}.png")

    lw = H.max_box_at(sx, sy, LOGO_ASPECT) * 0.96
    place_image(c, H, logo_bw(int(lw / 25.4 * DPI)), sx, sy,
                lw, lw / LOGO_ASPECT, f"logo_{int(lw*10)}.png")

    centred_text(c, H, name.upper(), -5.9 * k, FONT_NAME,
                 max_pt=9.5 * k, min_pt=5.0, tracking=0.05 * k,
                 warn=warn, label=f"name {name}")
    # the heart has narrowed to a point by here, so the front keeps the
    # short form; the back carries the full "2026 SUMMER CAMP" line
    centred_text(c, H, "2026", -9.8 * k, FONT_SMALL,
                 max_pt=4.8 * k, min_pt=3.0, tracking=0.16 * k,
                 warn=warn, label="front year")
    return pd, lw


def back_page(c, H, slug, name, url, guides, full_caption, warn):
    if guides:
        draw_guide(c, H)
    k = H.k
    reserve = (13.5 if full_caption else 3.4) * k
    qsize, qcy = H.best_qr(reserve, max_size=21.0 if full_caption else None)
    n, mod = draw_qr(c, H, url, 0.0, qcy, qsize * 0.98)
    if mod < MIN_MODULE_MM:
        warn.append(f"{slug}: QR module {mod:.2f} mm — below reliable etch size")

    y = qcy - qsize / 2 - 2.6 * k
    if full_caption:
        # the back has no portrait competing for the wide band, so the
        # club name and tagline get their space here
        # Two lines is what the taper allows beneath a QR this size. The
        # year lives on the front, and the tagline rings the logo itself.
        stack_text(c, H, [
            ("HANOI HAPPY", FONT_SMALL, 6.2 * k, 3.0, 0.08 * k, 2.4 * k),
            ("ENGLISH CLUB", FONT_SMALL, 6.2 * k, 3.0, 0.08 * k, 2.4 * k),
        ], y, warn)
    else:
        centred_text(c, H, "HEC · 2026", y, FONT_SMALL,
                     max_pt=4.8, min_pt=3.0, tracking=0.12,
                     warn=warn, label="back year line")
    return n, mod, qsize


def build(students, out_pdf, heart_w, style="photo", guides=True,
          full_caption=False, safe_inset=1.6):
    H = Heart(heart_w, safe_inset)
    c = canvas.Canvas(str(out_pdf), pagesize=(H.PAGE * mm, H.PAGE * mm))
    c.setTitle(f"HEC Summer Camp 2026 — {heart_w:.0f} mm heart engraving")
    warn, info = [], {}
    for s in students:
        if not (HEADSHOTS / f"{s['slug']}.jpg").exists():
            print(f"!! no headshot for {s['slug']}, skipping")
            continue
        pd, lw = front_page(c, H, s["slug"], s["name"], style, guides, full_caption, warn)
        c.showPage()
        n, mod, qsz = back_page(c, H, s["slug"], s["name"], s["url"],
                                guides, full_caption, warn)
        c.showPage()
        info = {"portrait": pd, "logo": lw, "qr": qsz, "mods": n, "mod": mod}
    c.save()
    for w in dict.fromkeys(warn):
        print(f"  WARN {w}")
    return H, info


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    links = json.loads((PRINT / "qr_links.json").read_text(encoding="utf-8"))
    index = json.loads((PROJ / "site" / "public" / "data" / "students.json")
                       .read_text(encoding="utf-8"))
    students = [{"slug": s["slug"], "name": s["name"],
                 "url": links[s["slug"]].get("qr") or links[s["slug"]]["url"]}
                for s in index["students"] if s["slug"] in links]

    for w_mm, tag, full in [(40.0, "", False), (60.0, "_60mm", True)]:
        H, i = build(students, PRINT / f"print{tag}.pdf", w_mm,
                     "photo", True, full)
        print(f"{w_mm:.0f} mm heart ({H.W:.0f} x {H.H:.1f} mm): "
              f"portrait {i['portrait']:.1f} | logo {i['logo']:.1f} | "
              f"QR {i['qr']:.1f} mm @ {i['mod']:.2f} mm/module ({i['mods']}x{i['mods']})")
        build(students, PRINT / f"print{tag}_graphic.pdf", w_mm,
              "graphic", True, full)
        build(students, PRINT / f"print{tag}_noguides.pdf", w_mm,
              "photo", False, full)

    print(f"DONE: {len(students)} campers -> {PRINT}")


if __name__ == "__main__":
    main()
