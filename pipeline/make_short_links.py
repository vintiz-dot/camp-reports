"""Generate /c/<slug>/ redirect pages on the main site.

The QR codes etched into the wooden hearts point here — permanently.
Keeping the redirect layer on HEC's own domain means the journals can be
re-hosted, renamed or restructured forever without reprinting a single
heart. The page itself is branded, so a slow connection still shows
something on-brand rather than a blank screen.
"""

import json
from pathlib import Path

PROJ = Path(r"C:\Users\Dell\OneDrive\Desktop\hec ads\camp-reports")
SITE = Path(r"C:\Users\Dell\OneDrive\Desktop\hec ads\hec-site\hec-site")
PUB = PROJ / "site" / "public"

DOMAIN = "hanoienglish.com"                   # verified live 2026-07-21
TARGET = "../../camp/student.html?s={slug}"   # relative: survives domain moves

TEMPLATE = """<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>{name} — HEC Summer Camp 2026</title>
<link rel="canonical" href="https://hanoienglish.com/camp/student.html?s={slug}">
<meta http-equiv="refresh" content="0; url={target}">
<style>
  body{{margin:0;min-height:100vh;display:grid;place-items:center;
       background:#0a1628;color:#faf8f3;
       font-family:Georgia,'Times New Roman',serif;text-align:center;padding:2rem}}
  .k{{font-size:.7rem;letter-spacing:.28em;text-transform:uppercase;
      color:#cdb277;font-family:system-ui,sans-serif}}
  h1{{font-weight:400;font-size:2rem;margin:.6rem 0 1rem}}
  a{{color:#cdb277}}
</style>
</head>
<body>
  <div>
    <p class="k">Happy English Club · Hà Nội</p>
    <h1>{name}</h1>
    <p>Summer Camp 2026 · <span id="s">Đang mở nhật ký…</span></p>
    <p><a href="{target}">Mở nhật ký của con / Open the journal</a></p>
  </div>
  <script>location.replace("{target}");</script>
</body>
</html>
"""


def main():
    index = json.loads((PUB / "data" / "students.json").read_text(encoding="utf-8"))
    out_root = SITE / "c"
    out_root.mkdir(parents=True, exist_ok=True)

    links = {}
    for i, s in enumerate(index["students"], start=1):
        slug, name = s["slug"], s["name"]
        d = out_root / slug
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(
            TEMPLATE.format(name=name, slug=slug, target=TARGET.format(slug=slug)),
            encoding="utf-8")
        # A plain lowercase https URL. An uppercase payload encodes in QR
        # alphanumeric mode and needs fewer modules, but some phone cameras
        # refuse to linkify an uppercase scheme — and on 74x44 mm wood there
        # is ample room, so universal scannability wins over density.
        # The numeric /NN/ paths stay as a short backup route.
        code = f"{i:02d}"
        cdir = SITE / code
        cdir.mkdir(parents=True, exist_ok=True)
        (cdir / "index.html").write_text(
            TEMPLATE.format(name=name, slug=slug, target=f"../camp/student.html?s={slug}"),
            encoding="utf-8")
        links[slug] = {"name": name,
                       "url": f"https://{DOMAIN}/c/{slug}",
                       "code": code,
                       "qr": f"https://{DOMAIN}/c/{slug}"}
        print(f"  /c/{slug}  ->  camp/student.html?s={slug}")

    (PROJ / "print").mkdir(exist_ok=True)
    (PROJ / "print" / "qr_links.json").write_text(
        json.dumps(links, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nDONE: {len(links)} short links")


if __name__ == "__main__":
    main()
