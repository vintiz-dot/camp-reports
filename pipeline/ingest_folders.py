"""Ingest hand-curated per-student folders (camp-reports/<slug>/).

The coach drops chosen media into a folder named after the student.
Photos are web-sized WITHOUT face-cropping (they are already curated);
videos are transcoded whole (capped at 60s, skip anything > 500 MB and
Live-Photo MOV twins of a same-stem HEIC). Items land at the FRONT of
the student's gallery. Unknown slugs become new student pages.

Idempotent: previous extra_* entries are rebuilt each run.
"""

import json
import subprocess
import unicodedata
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps
import pillow_heif
import imageio_ffmpeg

pillow_heif.register_heif_opener()

PROJ = Path(r"C:\Users\Dell\OneDrive\Desktop\hec ads\camp-reports")
DATA = PROJ / "data"
SITE_PUB = PROJ / "site" / "public"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

SKIP_DIRS = {"site", "docs", "data", "models", "pipeline", "docs-guide",
             "node_modules", ".git"}
MAX_VIDEO_BYTES = 500 * 1024 * 1024
MAX_CLIP_S = 60.0
LONG_SIDE = 1600
VIDEO_LONG_SIDE = 1280

PHOTO_EXTS = {".heic", ".jpg", ".jpeg", ".png"}
VIDEO_EXTS = {".mov", ".mp4"}


def transcode(src, dst):
    cmd = [FFMPEG, "-y", "-t", f"{MAX_CLIP_S}", "-i", str(src),
           "-vf", f"scale='if(gt(iw,ih),{VIDEO_LONG_SIDE},-2)':'if(gt(iw,ih),-2,{VIDEO_LONG_SIDE})'",
           "-c:v", "libx264", "-preset", "medium", "-crf", "25",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k",
           "-movflags", "+faststart", str(dst)]
    subprocess.run(cmd, check=True, capture_output=True)


def poster(video, out_path):
    cap = cv2.VideoCapture(str(video))
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, n // 3))
    ok, frame = cap.read()
    cap.release()
    if ok:
        h, w = frame.shape[:2]
        s = min(1.0, VIDEO_LONG_SIDE / max(h, w))
        if s < 1.0:
            frame = cv2.resize(frame, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        cv2.imwrite(str(out_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        return frame.shape[1] > frame.shape[0]
    return False


def main():
    interviews = json.loads((DATA / "interviews.json").read_text(encoding="utf-8")) \
        if (DATA / "interviews.json").exists() else {}
    remarks = {}
    for lang in ("en", "vi"):
        p = DATA / f"remarks_{lang}.json"
        if p.exists():
            for slug, r in json.loads(p.read_text(encoding="utf-8")).items():
                remarks.setdefault(slug, {})[lang] = r

    idx_path = SITE_PUB / "data" / "students.json"
    idx = json.loads(idx_path.read_text(encoding="utf-8"))
    sdir = SITE_PUB / "data" / "students"

    folders = [d for d in PROJ.iterdir()
               if d.is_dir() and d.name.lower() not in SKIP_DIRS
               and not d.name.startswith(".")]

    for folder in sorted(folders):
        slug = folder.name.lower()
        name = slug.replace("-", " ").title()
        media_dir = SITE_PUB / "media" / slug
        media_dir.mkdir(parents=True, exist_ok=True)

        spath = sdir / f"{slug}.json"
        is_new = not spath.exists()
        if not is_new:
            student = json.loads(spath.read_text(encoding="utf-8"))
        else:
            student = {"slug": slug, "name": name, "displayName": name,
                       "camp": {"name": "HEC Summer Camp 2026",
                                "dates": "June — July 2026", "class": ""},
                       "hero": None,
                       "remarks": remarks.get(slug, {}),
                       "interviews": interviews.get(slug, []),
                       "stats": {}, "gallery": []}
        # rebuild curated entries idempotently
        student["gallery"] = [g for g in student["gallery"]
                              if "/extra_" not in g.get("src", "")]

        stems_with_photo = {f.stem for f in folder.iterdir()
                            if f.suffix.lower() in PHOTO_EXTS}
        curated = []
        n_img = n_vid = 0
        for f in sorted(folder.iterdir()):
            ext = f.suffix.lower()
            try:
                if ext in PHOTO_EXTS:
                    n_img += 1
                    out = media_dir / f"extra_photo_{n_img:02d}.jpg"
                    im = ImageOps.exif_transpose(Image.open(f)).convert("RGB")
                    im.thumbnail((LONG_SIDE, LONG_SIDE))
                    im.save(out, "JPEG", quality=85)
                    curated.append({"type": "image", "src": f"media/{slug}/{out.name}",
                                    "w": im.size[0], "h": im.size[1]})
                elif ext in VIDEO_EXTS:
                    if f.stat().st_size > MAX_VIDEO_BYTES:
                        print(f"   SKIP heavy video {f.name} "
                              f"({f.stat().st_size/1e9:.1f} GB)")
                        continue
                    if f.stem in stems_with_photo:
                        continue  # Live-Photo twin; the still already covers it
                    n_vid += 1
                    out = media_dir / f"extra_clip_{n_vid:02d}.mp4"
                    transcode(f, out)
                    landscape = poster(out, media_dir / f"extra_clip_{n_vid:02d}.jpg")
                    curated.append({"type": "video",
                                    "src": f"media/{slug}/{out.name}",
                                    "poster": f"media/{slug}/extra_clip_{n_vid:02d}.jpg",
                                    "landscape": landscape})
            except Exception as e:  # noqa: BLE001
                print(f"   FAILED {f.name}: {type(e).__name__}: {e}")

        student["gallery"] = curated + student["gallery"]

        if not student.get("hero") and curated:
            vids = [c for c in curated if c["type"] == "video"]
            pick = next((v for v in vids if v.get("landscape")), None) \
                or (vids[0] if vids else None)
            if pick:
                student["hero"] = {"type": "video", "src": pick["src"],
                                   "poster": pick["poster"]}
            else:
                student["hero"] = {"type": "image", "src": curated[0]["src"],
                                   "poster": curated[0]["src"]}

        if not student.get("stats"):
            en = [{"value": str(sum(1 for c in student['gallery'] if c['type']=='image')), "label": "Photographs"},
                  {"value": str(sum(1 for c in student['gallery'] if c['type']=='video')), "label": "Film moments"},
                  {"value": "1", "label": "Unforgettable summer"}]
            vi = [{"value": en[0]["value"], "label": "Bức ảnh"},
                  {"value": en[1]["value"], "label": "Thước phim"},
                  {"value": "1", "label": "Mùa hè đáng nhớ"}]
            student["stats"] = {"en": en, "vi": vi}

        student["interviews"] = interviews.get(slug, student.get("interviews", []))
        spath.write_text(json.dumps(student, ensure_ascii=False, indent=1),
                         encoding="utf-8")

        if not any(s["slug"] == slug for s in idx["students"]):
            idx["students"].append({
                "slug": slug, "name": student["name"], "class": "",
                "thumb": (student.get("hero") or {}).get("poster", ""),
            })
        print(f"== {slug}: +{n_img} photos, +{n_vid} clips "
              f"({'new page' if is_new else 'merged'})")

    idx["students"] = sorted(idx["students"], key=lambda s: s["name"])
    idx_path.write_text(json.dumps(idx, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    print("DONE")


if __name__ == "__main__":
    main()
