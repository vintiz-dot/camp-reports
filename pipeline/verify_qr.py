"""Detector-independent QR check: sample each module from the rendered
page and compare it to the matrix the encoder produced."""
import fitz, numpy as np, cv2, json, qrcode
from qrcode.constants import ERROR_CORRECT_Q

PRINT = 'print'
W, H, INSET = 74.0, 44.0, 2.5
links = json.load(open(f'{PRINT}/qr_links.json', encoding='utf-8'))
slugs = [s['slug'] for s in json.load(
    open('site/public/data/students.json', encoding='utf-8'))['students']]

qsize = min(H - 2 * INSET - 1.0, 34.0)
qx = -W / 2 + INSET + qsize / 2

doc = fitz.open(f'{PRINT}/print.pdf')
dpi = 600
bad = []
for i, slug in enumerate(slugs):
    url = links[slug]['qr']
    q = qrcode.QRCode(error_correction=ERROR_CORRECT_Q, border=0)
    q.add_data(url); q.make(fit=True)
    expect = np.array(q.get_matrix(), dtype=bool)
    n = expect.shape[0]

    pix = doc[i * 2 + 1].get_pixmap(dpi=dpi)
    a = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    g = cv2.cvtColor(a, cv2.COLOR_RGB2GRAY if pix.n == 3 else cv2.COLOR_RGBA2GRAY)
    ppmm = pix.width / W
    mod = qsize / n
    x0 = (W / 2 + qx - qsize / 2) * ppmm
    y0 = (H / 2 - 0.0 - qsize / 2) * ppmm      # QR centred on y=0

    got = np.zeros_like(expect)
    for r in range(n):
        for c_ in range(n):
            cx = int(x0 + (c_ + 0.5) * mod * ppmm)
            cy = int(y0 + (r + 0.5) * mod * ppmm)
            got[r, c_] = g[cy, cx] < 128
    diff = int((got != expect).sum())
    if diff:
        bad.append((slug, diff, n * n))

print(f'checked {len(slugs)} QR codes, {n}x{n} modules each')
if not bad:
    print('PASS: every module matches the encoder output exactly')
else:
    print(f'FAIL: {len(bad)} mismatched')
    for s, d, tot in bad[:5]:
        print(f'   {s}: {d}/{tot} modules differ')
