# HEC Summer Camp 2026 — wood engraving artwork

Artwork for laser-etching a keepsake for each of the 21 campers, sized for
**74 × 44 mm** blanks. Every file is **1:1 actual size** — import at 100 %,
never "fit to page".

## Files

| File | Portraits | Notes |
|---|---|---|
| `print.pdf` | photo-realistic | **the main file** |
| `print_graphic.pdf` | high-contrast | fewer tones, forgiving on cheaper lasers |
| `print_noguides.pdf` | photo-realistic | no red outline |

Pages run **front, back, front, back…** in alphabetical order of camper,
42 pages total.

## Layout

**Front** — portrait (34 mm circle), HEC mark, the camper's name, and the
full caption: *Hanoi Happy English Club · Learning, an endless journey to
perfection · 2026 Summer Camp*.

**Back** — the camper's personal QR (34 mm), their name, and the caption.

## The red outline

The thin red rectangle is an **alignment guide — never etch it.** It marks
the blank's edge so you can line the piece up in a jig. Filter it out by
colour in LightBurn (set that layer to "Tool"), or use `print_noguides.pdf`.

All artwork sits at least **2.5 mm inside** that edge. This is verified
automatically: every page is rasterised and checked for ink outside the
safe area before release.

## Recommended settings

Always test on scrap from the same batch — wood varies far more than
settings do.

- **Portraits** — greyscale image engraving; let the software dither
  (Jarvis or Stucki). The images are already contrast-shaped for wood:
  black point lifted so shadows don't blob, highlights held at pure white
  so the background burns away to nothing.
- **QR and text** — true vector; engrave as such where possible. Never
  scale the QR independently of the page.
- If the photo-realistic portraits come out muddy, switch to
  `print_graphic.pdf` rather than fighting the laser.

Fonts are **embedded**, so text renders at exactly these widths on any
machine — nothing to install, and no substitution surprises.

## The QR codes

Each back face carries that camper's own code, pointing at their journal.

- Payload: `https://hanoienglish.com/c/<name>` — plain lowercase with an
  explicit `https://`, which every phone camera linkifies.
- 33 × 33 modules, error correction **Q (25 % recovery)**.
- Module size **1.03 mm** — roughly twice the practical minimum, so wood
  grain and a little burn spread won't stop a scan.
- Verified two ways: every code decoded from the rendered PDF, and every
  module compared cell-by-cell against the encoder's own output.

The codes point at a redirect on HEC's own domain, so journals can be moved
or restructured later without the etched codes ever going dead.

**Still: etch one back face on scrap and scan it with a phone before running
the batch.** That single test proves your burn settings, which no amount of
digital checking can.

## Regenerating

```powershell
$py = "C:\Users\Dell\.venvs\camp-reports\Scripts\python.exe"
& $py pipeline\pick_headshots.py    # choose + align portraits
& $py pipeline\make_short_links.py  # /c/<name> redirects + QR payloads
& $py pipeline\build_print.py       # all PDFs
```

`headshots/_contact_sheet.jpg` shows every chosen portrait on one sheet —
**check it before committing to a batch.**

To change any portrait:

```powershell
& $py pipeline\pick_candidates.py <name>          # writes a numbered grid
& $py pipeline\pick_candidates.py --apply <name> 3
```

Or simply drop your own square photo in as `headshots/<name>.jpg` and
re-run `build_print.py`.
