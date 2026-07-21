import fitz, numpy as np, cv2, importlib.util, sys
spec = importlib.util.spec_from_file_location('bp', 'pipeline/build_print.py')
bp = importlib.util.module_from_spec(spec); spec.loader.exec_module(bp)

W, H, INSET = 74.0, 44.0, 2.5
P = bp.Rect(W, H, INSET)
doc = fitz.open('print/print_noguides.pdf')
ppm = 20
bad = []
for i in range(doc.page_count):
    pix = doc[i].get_pixmap(dpi=508)      # match mask resolution
    a = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    g = cv2.cvtColor(a, cv2.COLOR_RGB2GRAY if pix.n == 3 else cv2.COLOR_RGBA2GRAY)
    g = cv2.resize(g, (P.safe.shape[1], P.safe.shape[0]))
    # red guide outline is not ink; drop near-red pixels by using the RGB
    rgb = cv2.resize(a[:, :, :3], (P.safe.shape[1], P.safe.shape[0]))
    is_red = (rgb[:, :, 0] > 150) & (rgb[:, :, 1] < 120) & (rgb[:, :, 2] < 120)
    ink = (g < 200) & (~is_red)
    outside = ink & (P.safe == 0)
    n = int(outside.sum())
    if n > 0:
        ys, xs = np.nonzero(outside)
        bad.append((i, n, xs.min()/ppm - W/2, xs.max()/ppm - W/2,
                    H/2 - ys.max()/ppm, H/2 - ys.min()/ppm))
print(f"pages checked: {doc.page_count}")
if not bad:
    print("PASS: no ink outside the safe area on any page")
else:
    print(f"FAIL: {len(bad)} page(s) with ink outside safe area")
    for i, n, x0, x1, y0, y1 in bad[:6]:
        print(f"   page {i} ({'front' if i%2==0 else 'back'}, camper {i//2}): "
              f"{n} px, x {x0:+.1f}..{x1:+.1f} mm, y {y0:+.1f}..{y1:+.1f} mm")
