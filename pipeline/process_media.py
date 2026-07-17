"""Build per-student web media from labeled clusters.

Requires data/students_map.json (written after the coach names clusters):
  { "cluster_01": {"slug": "minh-anh", "name": "Minh Anh", "class": "Jupiter"}, ... }
Clusters absent from the map are ignored (teachers, parents, minor clusters).

Per student:
  * rank photos by face prominence (size x score, solo-shot bonus, sharpness)
  * hero: largest-face sharp photo, cropped ~3:2 around the face (rule of thirds)
  * gallery: top photos, subject-centred crop, long side 1600px, JPEG q85
  * videos: rank by hit density x face size; trim the densest window
    (<= 30s), transcode H.264/AAC 1280px, +faststart, poster frame
  * write site/public/data/students/<slug>.json + update students.json

Non-destructive: writes only to site/public/. Resumable per student.
"""

import json
import re
import subprocess
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps
import pillow_heif
import imageio_ffmpeg

pillow_heif.register_heif_opener()

ROOT = Path(r"C:\Users\Dell\OneDrive\Desktop\hec ads")
PROJ = ROOT / "camp-reports"
DATA = PROJ / "data"
SITE_PUB = PROJ / "site" / "public"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

MAX_PHOTOS = 14
MAX_VIDEOS = 3
GALLERY_LONG_SIDE = 1600
HERO_WIDTH = 1920
VIDEO_MAX_S = 24.0
VIDEO_LONG_SIDE = 1280
VIDEO_CRF = "25"


def slugify(name):
    s = unicodedata.normalize("NFD", name)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.replace("đ", "d").replace("Đ", "D").lower()
    return "".join(c if c.isalnum() else "-" for c in s).strip("-").replace("--", "-")


def load_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def load_image(path):
    im = Image.open(path)
    im = ImageOps.exif_transpose(im).convert("RGB")
    return cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)


def sharpness(img_gray):
    return cv2.Laplacian(img_gray, cv2.CV_64F).var()


def crop_around_face(img, box, aspect, zoom=5.2):
    """Crop `aspect` (w/h) window around face box; face lands near upper third."""
    h, w = img.shape[:2]
    x, y, fw, fh = box
    cx, cy = x + fw / 2, y + fh / 2
    win_h = min(h, fh * zoom)
    win_w = win_h * aspect
    if win_w > w:
        win_w = w
        win_h = win_w / aspect
    x0 = np.clip(cx - win_w / 2, 0, w - win_w)
    y0 = np.clip(cy - win_h * 0.38, 0, h - win_h)  # face above centre
    return img[int(y0):int(y0 + win_h), int(x0):int(x0 + win_w)]


def save_jpeg(img, out_path, long_side):
    h, w = img.shape[:2]
    s = min(1.0, long_side / max(h, w))
    if s < 1.0:
        img = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(out_path), img, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return img.shape[1], img.shape[0]


def best_window(times, max_len):
    """Densest [start, end] window covering the most hit timestamps."""
    if not times:
        return None
    times = sorted(times)
    best = (times[0], times[0], 1)
    for i, t0 in enumerate(times):
        j = i
        while j + 1 < len(times) and times[j + 1] - t0 <= max_len:
            j += 1
        if j - i + 1 > best[2]:
            best = (t0, times[j], j - i + 1)
    start = max(0.0, best[0] - 1.0)
    end = best[1] + 1.5
    return start, min(end, start + max_len)


def transcode(src, dst, start, end):
    cmd = [
        FFMPEG, "-y", "-ss", f"{start:.2f}", "-to", f"{end:.2f}", "-i", str(src),
        "-vf", f"scale='if(gt(iw,ih),{VIDEO_LONG_SIDE},-2)':'if(gt(iw,ih),-2,{VIDEO_LONG_SIDE})'",
        "-c:v", "libx264", "-preset", "medium", "-crf", VIDEO_CRF,
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k",
        "-movflags", "+faststart", str(dst),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def poster_frame(video_path, t, out_path):
    cap = cv2.VideoCapture(str(video_path))
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
    ok, frame = cap.read()
    cap.release()
    if ok:
        save_jpeg(frame, out_path, VIDEO_LONG_SIDE)
    return ok


DATE_RE = re.compile(r"^(\d{4})_(\d{2})_(\d{2})_")


def build_stats(photo_files, video_files, n_photos, n_videos):
    days = {m.group(0) for f in list(photo_files) + list(video_files)
            if (m := DATE_RE.match(f))}
    en, vi = [], []
    if days:
        en.append({"value": str(len(days)), "label": "Days of English immersion"})
        vi.append({"value": str(len(days)), "label": "Ngày hòa mình cùng tiếng Anh"})
    en.append({"value": str(n_photos), "label": "Photographs"})
    vi.append({"value": str(n_photos), "label": "Bức ảnh"})
    if n_videos:
        en.append({"value": str(n_videos), "label": "Film moments"})
        vi.append({"value": str(n_videos), "label": "Thước phim"})
    en.append({"value": "1", "label": "Unforgettable summer"})
    vi.append({"value": "1", "label": "Mùa hè đáng nhớ"})
    return {"en": en, "vi": vi}


def load_remarks():
    remarks = {}
    for lang in ("en", "vi"):
        p = DATA / f"remarks_{lang}.json"
        if p.exists():
            for slug, r in json.loads(p.read_text(encoding="utf-8")).items():
                remarks.setdefault(slug, {})[lang] = r
    return remarks


def load_interviews():
    p = DATA / "interviews.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def main():
    students_map = json.loads((DATA / "students_map.json").read_text(encoding="utf-8"))
    all_remarks = load_remarks()
    all_interviews = load_interviews()
    clusters = {c["id"]: c for c in
                json.loads((DATA / "clusters.json").read_text(encoding="utf-8"))["clusters"]}
    face_recs = load_jsonl(DATA / "faces.jsonl")
    video_recs = load_jsonl(DATA / "videos.jsonl") if (DATA / "videos.jsonl").exists() else []

    faces_by_file = {r["file"]: r for r in face_recs}
    fid_info = {}
    for r in face_recs:
        for f in r["faces"]:
            fid_info[f["fid"]] = {"file": r["file"], "box": f["box"], "score": f["score"]}

    index_students = []
    only = sys.argv[1] if len(sys.argv) > 1 else None

    # a student may span several clusters (e.g. split by age/lighting)
    groups = {}
    for cid, meta in students_map.items():
        slug = meta.get("slug") or slugify(meta["name"])
        g = groups.setdefault(slug, {"meta": meta, "cids": []})
        if cid in clusters:
            g["cids"].append(cid)
        else:
            print(f"!! {cid} not in clusters.json, ignoring")

    for slug, g in groups.items():
        meta, cids = g["meta"], g["cids"]
        if (only and slug != only) or not cids:
            continue
        print(f"== {meta['name']} ({'+'.join(cids)} -> {slug})", flush=True)
        media_dir = SITE_PUB / "media" / slug
        media_dir.mkdir(parents=True, exist_ok=True)

        merged_fids, seen_fids = [], set()
        merged_files = set()
        for cid in cids:
            merged_files.update(clusters[cid]["files"])
            for fid in clusters[cid]["fids"]:
                if fid not in seen_fids:
                    seen_fids.add(fid)
                    merged_fids.append(fid)

        # ---- rank photos ----
        candidates = []
        for fid in merged_fids:
            info = fid_info[fid]
            rec = faces_by_file[info["file"]]
            n_faces = len(rec["faces"])
            size = min(info["box"][2], info["box"][3])
            prominence = size * info["score"] * (1.6 if n_faces == 1 else 1.0)
            candidates.append((prominence, fid, info))
        candidates.sort(key=lambda c: -c[0])

        # diversity: at most one photo per capture-minute (kills burst
        # duplicates) and at most three per camp day, so galleries span
        # the whole summer instead of one photogenic afternoon
        gallery, used_files = [], set()
        used_minutes, day_counts = set(), {}
        hero = None
        for prom, fid, info in candidates:
            if info["file"] in used_files:
                continue
            m = DATE_RE.match(info["file"])
            minute_key = info["file"][:16] if m else None
            day_key = m.group(0) if m else None
            if minute_key and minute_key in used_minutes:
                continue
            if day_key and day_counts.get(day_key, 0) >= 3:
                continue
            src = ROOT / info["file"]
            if not src.exists():
                continue
            try:
                img = load_image(src)
            except Exception as e:  # noqa: BLE001
                print(f"   skip {info['file']}: {e}")
                continue
            used_files.add(info["file"])
            if minute_key:
                used_minutes.add(minute_key)
            if day_key:
                day_counts[day_key] = day_counts.get(day_key, 0) + 1
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            if hero is None and sharpness(gray) > 60:
                crop = crop_around_face(img, info["box"], aspect=16 / 10, zoom=6.5)
                save_jpeg(crop, media_dir / "hero.jpg", HERO_WIDTH)
                hero = {"type": "image", "src": f"media/{slug}/hero.jpg",
                        "poster": f"media/{slug}/hero.jpg"}
                continue
            portrait = img.shape[0] >= img.shape[1]
            aspect = 4 / 5 if portrait else 3 / 2
            crop = crop_around_face(img, info["box"], aspect=aspect)
            name = f"photo_{len(gallery) + 1:02d}.jpg"
            w, h = save_jpeg(crop, media_dir / name, GALLERY_LONG_SIDE)
            gallery.append({"type": "image", "src": f"media/{slug}/{name}", "w": w, "h": h})
            if len(gallery) >= MAX_PHOTOS:
                break

        # ---- rank + trim videos ----
        vid_ranked = []
        for vr in video_recs:
            hits = [h for cid in cids for h in vr.get("hits", {}).get(cid, [])]
            if len(hits) < 2 or not vr.get("duration"):
                continue
            # total face-time weighted by prominence, not density —
            # otherwise 3-second clips outrank rich 60-second footage
            avg_size = np.mean([h["size"] for h in hits])
            vid_ranked.append((len(hits) * avg_size, vr, hits))
        vid_ranked.sort(key=lambda v: -v[0])

        n_vid = 0
        clip_entries = []
        used_stems = set()
        for _, vr, hits in vid_ranked:
            if n_vid >= MAX_VIDEOS:
                break
            src = ROOT / vr["file"]
            if not src.exists():
                continue
            # "name (1).mp4" duplicates of an already-picked "name.mp4"
            stem = re.sub(r"\s*\(\d+\)$", "", src.stem)
            if stem in used_stems:
                continue
            used_stems.add(stem)
            window = best_window([h["t"] for h in hits], VIDEO_MAX_S)
            if not window:
                continue
            if window[1] - window[0] < 5.0 and n_vid >= 2:
                continue  # short snippets only make the cut while slots remain
            n_vid += 1
            name = f"clip_{n_vid:02d}"
            try:
                transcode(src, media_dir / f"{name}.mp4", *window)
            except subprocess.CalledProcessError as e:
                print(f"   ffmpeg failed on {vr['file']}: {e.stderr[-300:] if e.stderr else e}")
                n_vid -= 1
                continue
            best_hit = max(hits, key=lambda h: h["size"])
            poster_frame(src, best_hit["t"], media_dir / f"{name}.jpg")
            cap = cv2.VideoCapture(str(media_dir / f"{name}.mp4"))
            vw, vh = cap.get(cv2.CAP_PROP_FRAME_WIDTH), cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            cap.release()
            entry = {"type": "video", "src": f"media/{slug}/{name}.mp4",
                     "poster": f"media/{slug}/{name}.jpg"}
            clip_entries.append((entry, vw > vh))
            gallery.insert(min(2, len(gallery)), entry)
            print(f"   video {vr['file']} [{window[0]:.1f}-{window[1]:.1f}s]", flush=True)

        # spotlight video becomes the hero — prefer a landscape clip (fills
        # the full-viewport banner without cropping the subject away)
        if clip_entries and hero and hero["type"] == "image":
            spotlight = next((e for e, landscape in clip_entries if landscape),
                             clip_entries[0][0])
            hero = {"type": "video", "src": spotlight["src"], "poster": hero["poster"]}

        # ---- student JSON ----
        video_files = {vr["file"] for _, vr, _ in vid_ranked}
        out = {
            "slug": slug, "name": meta["name"], "displayName": meta["name"],
            "camp": {"name": "HEC Summer Camp 2026", "dates": "June — July 2026",
                     "class": meta.get("class", "")},
            "hero": hero or (gallery[0] if gallery else None),
            "remarks": all_remarks.get(slug, meta.get("remarks", {})),
            "interviews": all_interviews.get(slug, []),
            "stats": build_stats(merged_files, video_files,
                                 len(merged_files), len(video_files)),
            "gallery": gallery,
        }
        sdir = SITE_PUB / "data" / "students"
        sdir.mkdir(parents=True, exist_ok=True)
        (sdir / f"{slug}.json").write_text(
            json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

        index_students.append({
            "slug": slug, "name": meta["name"], "class": meta.get("class", ""),
            "thumb": (hero or {}).get("poster") or (gallery[0]["src"] if gallery else ""),
        })
        print(f"   {len(gallery)} gallery items ({n_vid} videos)", flush=True)

    if not only:
        idx_path = SITE_PUB / "data" / "students.json"
        idx_path.write_text(json.dumps({
            "camp": {"name": "HEC Summer Camp 2026", "dates": "June — July 2026"},
            "students": sorted(index_students, key=lambda s: s["name"]),
        }, ensure_ascii=False, indent=1), encoding="utf-8")
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
