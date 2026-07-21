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
from reportlab.pdfbase.ttfonts import TTFont
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

# Fonts are EMBEDDED, not the PDF base-14. Base-14 Helvetica is not
# carried in the file, so every renderer substitutes its own face — the
# oblique substitute measured 13% wider than reportlab's metrics and ran
# text off the edge of the wood. Embedding guarantees the laser operator
# sees exactly these glyph widths.
_FONT_DIR = Path(r"C:\Windows\Fonts")
for _alias, _file in [("HecSans", "arial.ttf"),
                      ("HecSans-Bold", "arialbd.ttf"),
                      ("HecSans-Italic", "ariali.ttf")]:
    pdfmetrics.registerFont(TTFont(_alias, str(_FONT_DIR / _file)))

FONT_NAME = "HecSans-Bold"    # bold survives etching far better than thin faces
FONT_SMALL = "HecSans-Bold"
FONT_ITALIC = "HecSans-Italic"

CAPTION_CLUB = "HANOI HAPPY ENGLISH CLUB"
CAPTION_TAG_1 = "Learning, an endless"
CAPTION_TAG_2 = "journey to perfection"
CAPTION_YEAR = "2026 SUMMER CAMP"
CAPTION_TAG_FULL = "Learning, an endless journey to perfection"


# ── geometry ─────────────────────────────────────────────────────────
class Panel:
    """A blank's outline plus its safe region, in centre-origin mm.

    Subclasses only supply the outline; every placement query works off
    the rasterised mask, so a heart and a rectangle behave identically to
    the layout code.
    """

    def __init__(self, page_w, page_h, safe_inset_mm, ppm=20):
        self.PAGE_W, self.PAGE_H = page_w, page_h
        self.inset = safe_inset_mm
        self.ppm = ppm
        self.ox, self.oy = self.outline()

        mask = np.zeros((int(page_h * ppm), int(page_w * ppm)), np.uint8)
        pts = np.stack([(self.ox + page_w / 2) * ppm,
                        (page_h / 2 - self.oy) * ppm], axis=1).astype(np.int32)
        cv2.fillPoly(mask, [pts], 255)
        er = max(1, int(safe_inset_mm * ppm))
        # borderValue=0 is essential: by default erode treats the image
        # border as solid, so a blank that reaches the canvas edge (any
        # rectangle) would never be inset at all.
        self.safe = cv2.erode(mask, np.ones((er * 2 + 1, er * 2 + 1), np.uint8),
                              borderType=cv2.BORDER_CONSTANT, borderValue=0)
        self.dist = cv2.distanceTransform(
            cv2.copyMakeBorder(self.safe, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0),
            cv2.DIST_L2, 5)[1:-1, 1:-1] / ppm

    def outline(self):
        raise NotImplementedError

    # -- queries -------------------------------------------------------
    def half_width_at(self, y_mm):
        row = int(round((self.PAGE_H / 2 - y_mm) * self.ppm))
        row = max(0, min(self.safe.shape[0] - 1, row))
        xs = np.flatnonzero(self.safe[row])
        return 0.0 if xs.size == 0 else (xs.max() - xs.min()) / 2 / self.ppm

    def fits(self, cx, cy, w, h):
        x0 = int((self.PAGE_W / 2 + cx - w / 2) * self.ppm)
        x1 = int((self.PAGE_W / 2 + cx + w / 2) * self.ppm)
        y0 = int((self.PAGE_H / 2 - cy - h / 2) * self.ppm)
        y1 = int((self.PAGE_H / 2 - cy + h / 2) * self.ppm)
        if x0 < 0 or y0 < 0 or x1 >= self.safe.shape[1] or y1 >= self.safe.shape[0]:
            return False
        return bool(self.safe[y0:y1, x0:x1].min() > 0)

    def max_circle_at(self, cx, cy):
        x = int((self.PAGE_W / 2 + cx) * self.ppm)
        y = int((self.PAGE_H / 2 - cy) * self.ppm)
        if not (0 <= x < self.dist.shape[1] and 0 <= y < self.dist.shape[0]):
            return 0.0
        return float(self.dist[y, x]) * 2

    def max_box_at(self, cx, cy, aspect, limit=80.0):
        lo, hi = 0.0, limit
        for _ in range(30):
            mid = (lo + hi) / 2
            if self.fits(cx, cy, mid, mid / aspect):
                lo = mid
            else:
                hi = mid
        return lo

    def width_between(self, y_lo, y_hi, cx=0.0):
        """Narrowest safe width across a vertical band — what a text block
        must actually fit inside."""
        return min(self.half_width_at(y) * 2
                   for y in np.arange(y_lo, y_hi + 0.01, 0.5))


class Rect(Panel):
    """Rectangular blank with slightly eased corners."""

    def __init__(self, w, h, safe_inset_mm=2.5, corner=2.0, ppm=20):
        self.w, self.h, self.corner = w, h, corner
        super().__init__(w, h, safe_inset_mm, ppm)

    def outline(self):
        w, h, r = self.w, self.h, self.corner
        pts = []
        for cx, cy, a0 in [(w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90),
                           (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)]:
            a = np.linspace(math.radians(a0), math.radians(a0 + 90), 24)
            pts.append(np.stack([cx + r * np.cos(a), cy + r * np.sin(a)], axis=1))
        p = np.concatenate(pts)
        return p[:, 0], p[:, 1]


class Heart(Panel):
    """Heart blank, kept for the earlier 40/60 mm hearts."""

    def __init__(self, width_mm, safe_inset_mm=1.6, ppm=20):
        self.W = width_mm
        t = np.linspace(0, 2 * math.pi, 1400)
        x = 16 * np.sin(t) ** 3
        y = (13 * np.cos(t) - 5 * np.cos(2 * t)
             - 2 * np.cos(3 * t) - np.cos(4 * t))
        s = width_mm / (x.max() - x.min())
        x, y = x * s, y * s
        self._x = x - (x.max() + x.min()) / 2
        self._y = y - (y.max() + y.min()) / 2
        self.H = self._y.max() - self._y.min()
        self.k = width_mm / 40.0
        super().__init__(width_mm, width_mm, safe_inset_mm, ppm)

    def outline(self):
        return self._x, self._y


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
    t = c.beginText((H.PAGE_W / 2) * mm - w / 2, (H.PAGE_H / 2 + y_mm) * mm)
    t.setFont(font, size)
    t.setCharSpace(tracking * mm)   # see note in _col_text: Tc persists
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
    c.drawImage(str(path), (H.PAGE_W / 2 + cx - w / 2) * mm,
                (H.PAGE_H / 2 + cy - h / 2) * mm, w * mm, h * mm, mask=None)


def draw_guide(c, H):
    """Hairline heart outline in red — alignment reference, never etch."""
    c.setStrokeColor(red)
    c.setLineWidth(0.2)
    p = c.beginPath()
    p.moveTo((H.PAGE_W / 2 + H.ox[0]) * mm, (H.PAGE_H / 2 + H.oy[0]) * mm)
    for x, y in zip(H.ox[1:], H.oy[1:]):
        p.lineTo((H.PAGE_W / 2 + x) * mm, (H.PAGE_H / 2 + y) * mm)
    p.close()
    c.drawPath(p, stroke=1, fill=0)


def draw_qr(c, H, data, cx, cy, size):
    q = qrcode.QRCode(error_correction=QR_ECC, border=0)
    q.add_data(data)
    q.make(fit=True)
    m = q.get_matrix()
    n = len(m)
    mod = size / n
    x0 = H.PAGE_W / 2 + cx - size / 2
    y0 = H.PAGE_H / 2 + cy - size / 2
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


# ── rectangular blank: 74 x 44 mm ────────────────────────────────────
def _col_text(c, P, lines, x_centre, col_w, y_top, warn):
    """Stack centred lines inside a fixed-width column.

    y_top is the top of the block, not a baseline — each line is dropped
    by its own cap height first, so a stack can never ride up into
    whatever sits above it.
    """
    y = y_top
    for text, font, max_pt, min_pt, tracking, gap in lines:
        size = max_pt
        while size > min_pt:
            w = pdfmetrics.stringWidth(text, font, size) + tracking * mm * (len(text) - 1)
            if w <= col_w * mm:
                break
            size -= 0.05
        w = pdfmetrics.stringWidth(text, font, size) + tracking * mm * (len(text) - 1)
        if w > col_w * mm + 0.05 and warn is not None:
            warn.append(f"{text!r} needs {w/mm:.1f} mm but column is {col_w:.1f} mm")
        cap = size / 72 * 25.4 * 0.72
        y -= cap                                   # y was the top of this line
        c.setFillColor(black)
        t = c.beginText((P.PAGE_W / 2 + x_centre) * mm - w / 2,
                        (P.PAGE_H / 2 + y) * mm)
        t.setFont(font, size)
        # always set it: PDF character spacing is text state that persists
        # in the content stream, so a previous tracked line would silently
        # widen this one (that overflowed the blank by exactly 4.1 mm).
        t.setCharSpace(tracking * mm)
        t.textOut(text)
        c.drawText(t)
        y -= gap
    return y


def rect_front(c, P, slug, name, style, guides, warn):
    if guides:
        draw_guide(c, P)

    # portrait fills the left third; the caption column takes the rest
    pd = min(P.max_circle_at(-P.PAGE_W / 2 + 2.5 + 17.5, 0.0) * 2, 0)  # placeholder
    px_c = -P.PAGE_W / 2 + P.inset + 17.0
    pd = min(P.max_circle_at(px_c, 0.0), P.PAGE_H - 2 * P.inset)
    head = cv2.imread(str(HEADSHOTS / f"{slug}.jpg"))
    place_image(c, P, prep_portrait(head, int(pd / 25.4 * DPI), style),
                px_c, 0.0, pd, pd, f"{slug}_{style}_rect.png")

    col_x0 = px_c + pd / 2 + 2.5
    col_x1 = P.PAGE_W / 2 - P.inset
    col_w = col_x1 - col_x0
    col_c = (col_x0 + col_x1) / 2

    lw = min(col_w * 0.62, 17.0)
    place_image(c, P, logo_bw(int(lw / 25.4 * DPI)), col_c,
                P.PAGE_H / 2 - P.inset - lw / LOGO_ASPECT / 2 - 0.5,
                lw, lw / LOGO_ASPECT, f"logo_rect_{int(lw*10)}.png")

    y = P.PAGE_H / 2 - P.inset - lw / LOGO_ASPECT - 3.4
    _col_text(c, P, [
        (name.upper(), FONT_NAME, 15.0, 6.0, 0.06, 5.6),
        (CAPTION_CLUB, FONT_SMALL, 5.6, 3.2, 0.10, 3.4),
        (CAPTION_TAG_FULL, FONT_ITALIC, 4.6, 2.8, 0, 3.0),
        (CAPTION_YEAR, FONT_SMALL, 5.0, 3.0, 0.14, 2.8),
    ], col_c, col_w, y, warn)
    return pd, lw


def rect_back(c, P, slug, name, url, guides, warn):
    if guides:
        draw_guide(c, P)

    qsize = min(P.PAGE_H - 2 * P.inset - 1.0, 34.0)
    qx = -P.PAGE_W / 2 + P.inset + qsize / 2
    n, mod = draw_qr(c, P, url, qx, 0.0, qsize)
    if mod < MIN_MODULE_MM:
        warn.append(f"{slug}: QR module {mod:.2f} mm — below reliable etch size")

    col_x0 = qx + qsize / 2 + 3.0
    col_x1 = P.PAGE_W / 2 - P.inset
    col_w = col_x1 - col_x0
    col_c = (col_x0 + col_x1) / 2

    _col_text(c, P, [
        (name.upper(), FONT_NAME, 12.0, 5.5, 0.06, 5.0),
        ("SCAN TO SEE", FONT_SMALL, 5.0, 3.0, 0.10, 3.0),
        ("MY SUMMER STORY", FONT_SMALL, 5.0, 3.0, 0.10, 3.4),
        (CAPTION_CLUB, FONT_SMALL, 4.4, 2.8, 0.06, 2.9),
        (CAPTION_YEAR, "HecSans", 4.2, 2.8, 0.06, 2.6),
    ], col_c, col_w, P.PAGE_H / 2 - P.inset - 5.0, warn)
    return n, mod, qsize


def build_rect(students, out_pdf, w, h, style="photo", guides=True, inset=2.5):
    P = Rect(w, h, inset)
    c = canvas.Canvas(str(out_pdf), pagesize=(P.PAGE_W * mm, P.PAGE_H * mm))
    c.setTitle(f"HEC Summer Camp 2026 — {w:.0f} x {h:.0f} mm engraving")
    warn, info = [], {}
    for s in students:
        if not (HEADSHOTS / f"{s['slug']}.jpg").exists():
            print(f"!! no headshot for {s['slug']}, skipping")
            continue
        pd, lw = rect_front(c, P, s["slug"], s["name"], style, guides, warn)
        c.showPage()
        n, mod, qsz = rect_back(c, P, s["slug"], s["name"], s["url"], guides, warn)
        c.showPage()
        info = {"portrait": pd, "logo": lw, "qr": qsz, "mods": n, "mod": mod}
    c.save()
    for m in dict.fromkeys(warn):
        print(f"  WARN {m}")
    return P, info


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

    W, Hh = 74.0, 44.0
    P, i = build_rect(students, PRINT / "print.pdf", W, Hh, "photo", True)
    print(f"{W:.0f} x {Hh:.0f} mm blank: portrait {i['portrait']:.1f} mm | "
          f"logo {i['logo']:.1f} mm | QR {i['qr']:.1f} mm @ "
          f"{i['mod']:.2f} mm/module ({i['mods']}x{i['mods']})")
    build_rect(students, PRINT / "print_graphic.pdf", W, Hh, "graphic", True)
    build_rect(students, PRINT / "print_noguides.pdf", W, Hh, "photo", False)
    print(f"DONE: {len(students)} campers -> {PRINT}")


if __name__ == "__main__":
    main()
