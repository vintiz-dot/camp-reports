"""Dump the top N identity-verified headshot candidates per camper.

Automated scoring gets ~15 of 21 right, but for a keepsake that is etched
into wood permanently the last few need a human eye. This writes a
numbered grid per camper so a choice can be made by looking, then locked
in with `apply_choice`.

    print/candidates/<slug>.jpg          numbered grid
    print/candidates/<slug>_<n>.jpg      each candidate, full size

To lock one in:
    python pipeline/pick_candidates.py --apply <slug> <n>
"""

import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import pick_headshots as ph          # noqa: E402  (reuse the whole toolchain)

OUT = ph.PROJ / "print" / "candidates"
HEADSHOTS = ph.PROJ / "print" / "headshots"
N = 8


def candidates_for(slug, from_clusters, interviews):
    pair = from_clusters.get(slug)
    results = []

    if pair:
        entries, ref = pair
        ranked = sorted(entries, key=lambda e: -min(e[0][2], e[0][3]))[:80]
        seen = set()
        for box, fname in ranked:
            if fname in seen or len(results) >= N * 4:
                continue
            seen.add(fname)
            src = ph.ROOT / fname
            if not src.exists():
                continue
            try:
                img = ph.load_bgr(src)
            except Exception:  # noqa: BLE001
                continue
            target = np.array([box[0] + box[2] / 2, box[1] + box[3] / 2])
            for face in ph.detect(img):
                c = np.array([face[0] + face[2] / 2, face[1] + face[3] / 2])
                if np.linalg.norm(c - target) > max(box[2], box[3]) * 0.6:
                    continue
                q = ph.face_quality(img, face, ref)
                if q:
                    results.append((q, ph.align_and_crop(img, face), fname))
    else:
        ref = None
        if slug in interviews:
            ref = ph.reference_from_youtube(interviews[slug][0]["youtubeId"])
        if ref is None:
            ref = ph.reference_from_own_clips(slug)
        media = ph.PUB / "media" / slug
        for clip in sorted(media.glob("*.mp4")):
            cap = cv2.VideoCapture(str(clip))
            fps = cap.get(cv2.CAP_PROP_FPS) or 30
            n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            for i in range(0, n, max(1, int(fps / 2))):
                cap.set(cv2.CAP_PROP_POS_FRAMES, i)
                ok, fr = cap.read()
                if not ok:
                    continue
                for face in ph.detect(fr):
                    if min(face[2], face[3]) < 90:
                        continue
                    q = ph.face_quality(fr, face, ref)
                    if q:
                        results.append((q, ph.align_and_crop(fr, face),
                                        f"{clip.name}@{i/fps:.1f}s"))
            cap.release()

    results.sort(key=lambda r: -r[0]["score"])
    # de-duplicate near-identical frames so the grid shows real variety
    kept = []
    for q, crop, fname in results:
        small = cv2.resize(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY), (32, 32))
        if any(np.mean(np.abs(small.astype(int) - k.astype(int))) < 9
               for k in [x[3] for x in kept]):
            continue
        kept.append((q, crop, fname, small))
        if len(kept) >= N:
            break
    return kept


def main():
    if "--apply" in sys.argv:
        i = sys.argv.index("--apply")
        slug, n = sys.argv[i + 1], int(sys.argv[i + 2])
        src = OUT / f"{slug}_{n}.jpg"
        if not src.exists():
            print(f"no candidate {n} for {slug}")
            return
        cv2.imwrite(str(HEADSHOTS / f"{slug}.jpg"), cv2.imread(str(src)),
                    [cv2.IMWRITE_JPEG_QUALITY, 95])
        print(f"{slug}: locked in candidate {n}")
        return

    OUT.mkdir(parents=True, exist_ok=True)
    import json
    from_clusters = ph.candidates_from_clusters()
    interviews = json.loads((ph.DATA / "interviews.json").read_text(encoding="utf-8"))
    slugs = sys.argv[1:] or sorted(from_clusters)

    for slug in slugs:
        kept = candidates_for(slug, from_clusters, interviews)
        if not kept:
            print(f"!! {slug}: none")
            continue
        cell = 260
        cols = min(4, len(kept))
        rows = (len(kept) + cols - 1) // cols
        sheet = np.full((rows * (cell + 28), cols * cell, 3), 255, np.uint8)
        for i, (q, crop, fname, _) in enumerate(kept):
            cv2.imwrite(str(OUT / f"{slug}_{i}.jpg"), crop,
                        [cv2.IMWRITE_JPEG_QUALITY, 95])
            r, c = divmod(i, cols)
            y0 = r * (cell + 28)
            sheet[y0:y0 + cell, c * cell:(c + 1) * cell] = cv2.resize(crop, (cell, cell))
            cv2.putText(sheet, f"[{i}] id{q['sim']:.2f} f{q['front']:.2f}",
                        (c * cell + 6, y0 + cell + 19),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 0, 0), 1, cv2.LINE_AA)
        cv2.imwrite(str(OUT / f"{slug}.jpg"), sheet, [cv2.IMWRITE_JPEG_QUALITY, 92])
        print(f"{slug}: {len(kept)} candidates")


if __name__ == "__main__":
    main()
