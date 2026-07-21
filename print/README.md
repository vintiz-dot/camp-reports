# HEC Summer Camp 2026 — wooden heart engraving

Artwork for laser-etching a keepsake heart for each of the 21 campers.
Every file is **1:1 actual size** — import at 100%, do not "fit to page".

## Files

| File | Heart | Portraits | Notes |
|---|---|---|---|
| `print.pdf` | 40 mm | photo-realistic | **as ordered** |
| `print_60mm.pdf` | 60 mm | photo-realistic | full club caption fits |
| `print_graphic.pdf` | 40 mm | high-contrast | forgiving on cheaper lasers |
| `print_60mm_graphic.pdf` | 60 mm | high-contrast | |
| `*_noguides.pdf` | — | — | same, without the red outline |

Page order is **front, back, front, back…** in alphabetical order of camper.
Page size equals the heart's bounding box, with the heart centred.

## The red outline

The thin red heart in each file is an **alignment guide only — never etch it.**
It shows where the wood edge falls so you can line the piece up in a jig.
Filter it out by colour in LightBurn (set that layer to "Tool"/skip), or use
the `_noguides.pdf` files, which omit it entirely.

## Recommended settings

Start on scrap from the same batch — wood varies far more than settings do.

- **Portraits** — greyscale image engraving. Let your software dither
  (Jarvis or Stucki); the images are supplied as continuous-tone greyscale,
  already contrast-shaped for wood: black point lifted so shadows don't blob,
  highlights held at pure white so the background burns away to nothing.
- **QR + text** — these are true vector, so engrave them as such where
  possible. Do not scale the QR independently of the page.
- If the photo-realistic portraits come out muddy, switch to the `_graphic`
  files rather than fighting the laser: they carry far fewer tones.

## The QR codes

Each back face carries that child's own QR, pointing at their summer journal.

- Payload: `HANOIENGLISH.COM/C/<NAME>` — uppercase and without `https://`
  on purpose. That encodes in QR *alphanumeric* mode, which needs far fewer
  modules than normal text, so the squares come out roughly twice the size
  they otherwise would. Phones still open it as a link.
- 25 × 25 modules, error correction **Q (25 % recovery)** — tolerates wood
  grain, a little burn spread, and minor damage.
- Module size: **0.56 mm** at 40 mm, **0.91 mm** at 60 mm.
- **Test one before running the batch.** Etch a single back face, scan it
  with a phone, and confirm it opens the journal. If it struggles, the fix
  is more contrast (slower/hotter), not a bigger code.

The QR points at a redirect on HEC's own domain, so the journals can be
moved or restructured later without the etched codes ever going dead.

## Regenerating

```powershell
$py = "C:\Users\Dell\.venvs\camp-reports\Scripts\python.exe"
& $py pipeline\pick_headshots.py    # choose + align portraits
& $py pipeline\make_short_links.py  # /c/<slug> redirects + QR payloads
& $py pipeline\build_print.py       # all PDFs
```

`headshots/_contact_sheet.jpg` shows every chosen portrait on one sheet —
check it before committing to a batch. To override any child's portrait,
drop a square photo in as `headshots/<slug>.jpg` and re-run `build_print.py`.
