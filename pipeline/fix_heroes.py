"""Targeted hero fixes for elsa, luka, gia-minh.

elsa: identify her via her YouTube interview thumbnail (SFace match),
      then pick the clip frame where SHE is biggest as hero poster.
luka: solo clips — pick the sharpest, largest frontal-face frame.
gia-minh: cluster-based — hero from the photo where his face is largest
      AND dominant, cropped tight.
"""

import json
import urllib.request
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps
import pillow_heif

pillow_heif.register_heif_opener()

ROOT = Path(r"C:\Users\Dell\OneDrive\Desktop\hec ads")
PROJ = ROOT / "camp-reports"
DATA = PROJ / "data"
PUB = PROJ / "site" / "public"
MODELS = PROJ / "models"

detector = cv2.FaceDetectorYN.create(
    str(MODELS / "face_detection_yunet_2023mar.onnx"), "", (320, 320), 0.7, 0.3, 5000)
recognizer = cv2.FaceRecognizerSF.create(
    str(MODELS / "face_recognition_sface_2021dec.onnx"), "")


def faces_of(img):
    h, w = img.shape[:2]
    detector.setInputSize((w, h))
    _, faces = detector.detect(img)
    return [] if faces is None else list(faces)


def embed(img, face):
    v = recognizer.feature(recognizer.alignCrop(img, face)).flatten().astype(np.float32)
    return v / np.linalg.norm(v)


def frames(video, step_s=1.0):
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    dur = n / fps
    t = 0.3
    while t < dur:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, fr = cap.read()
        if ok:
            yield t, fr
        t += step_s
    cap.release()


def save_poster(frame, out, long_side=1280):
    h, w = frame.shape[:2]
    s = min(1.0, long_side / max(h, w))
    if s < 1.0:
        frame = cv2.resize(frame, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(out), frame, [cv2.IMWRITE_JPEG_QUALITY, 88])


def set_hero(slug, hero):
    p = PUB / "data" / "students" / f"{slug}.json"
    s = json.loads(p.read_text(encoding="utf-8"))
    s["hero"] = hero
    p.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
    idx_p = PUB / "data" / "students.json"
    idx = json.loads(idx_p.read_text(encoding="utf-8"))
    for st in idx["students"]:
        if st["slug"] == slug:
            st["thumb"] = hero.get("poster") or hero["src"]
    idx_p.write_text(json.dumps(idx, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{slug}: hero -> {hero}")


# ---------- ELSA ----------
def fix_elsa():
    thumb_path = DATA / "elsa_yt.jpg"
    for quality in ("maxresdefault", "hqdefault"):
        try:
            urllib.request.urlretrieve(
                f"https://i.ytimg.com/vi/FLwcYgen6ro/{quality}.jpg", thumb_path)
            if thumb_path.stat().st_size > 5000:
                break
        except Exception:  # noqa: BLE001
            continue
    ref_img = cv2.imread(str(thumb_path))
    ref_faces = faces_of(ref_img)
    if not ref_faces:
        print("elsa: no face in YT thumbnail; aborting")
        return
    ref = embed(ref_img, max(ref_faces, key=lambda f: f[2] * f[3]))

    best = None  # (sim*size, clip_name, t, frame)
    for clip in sorted((PUB / "media" / "elsa").glob("extra_clip_*.mp4")):
        for t, fr in frames(clip, step_s=1.0):
            for f in faces_of(fr):
                sim = float(ref @ embed(fr, f))
                if sim < 0.35:
                    continue
                size = min(f[2], f[3])
                score = sim * size
                if best is None or score > best[0]:
                    best = (score, clip.name, t, fr.copy(), sim, size)
    if best:
        save_poster(best[3], PUB / "media" / "elsa" / "hero_poster.jpg")
        set_hero("elsa", {"type": "video", "src": f"media/elsa/{best[1]}",
                          "poster": "media/elsa/hero_poster.jpg"})
        print(f"   matched Elsa in {best[1]} at t={best[2]:.1f}s "
              f"(sim {best[4]:.2f}, face {best[5]}px)")
    else:
        print("elsa: no matching face found in clips")


# ---------- LUKA ----------
def fix_luka():
    best = None
    for clip in sorted((PUB / "media" / "luka").glob("extra_clip_*.mp4")):
        for t, fr in frames(clip, step_s=1.0):
            fs = faces_of(fr)
            if not fs:
                continue
            f = max(fs, key=lambda x: x[2] * x[3])
            size = min(f[2], f[3])
            score = float(f[14]) * size  # confidence x size favours frontal
            sharp = cv2.Laplacian(cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var()
            if sharp < 40:
                continue
            if best is None or score > best[0]:
                best = (score, clip.name, t, fr.copy())
    if best:
        save_poster(best[3], PUB / "media" / "luka" / "hero_poster.jpg")
        set_hero("luka", {"type": "video", "src": f"media/luka/{best[1]}",
                          "poster": "media/luka/hero_poster.jpg"})
        print(f"   luka poster from {best[1]} t={best[2]:.1f}s")
    else:
        print("luka: no good frame found")


# ---------- GIA MINH ----------
def fix_gia_minh():
    clusters = {c["id"]: c for c in
                json.loads((DATA / "clusters.json").read_text(encoding="utf-8"))["clusters"]}
    recs = {}
    for line in open(DATA / "faces.jsonl", encoding="utf-8"):
        r = json.loads(line)
        recs[r["file"]] = r
    fid_info = {}
    for r in recs.values():
        for f in r["faces"]:
            fid_info[f["fid"]] = (r["file"], f)

    cands = []
    for fid in clusters["cluster_18"]["fids"]:
        file, f = fid_info[fid]
        own = min(f["box"][2], f["box"][3])
        others = max((min(g["box"][2], g["box"][3]) for g in recs[file]["faces"]
                      if g["fid"] != fid), default=0)
        if own >= others:  # strictly dominant
            cands.append((own, file, f))
    cands.sort(key=lambda c: -c[0])

    for own, file, f in cands[:6]:
        src = ROOT / file
        if not src.exists():
            continue
        im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
        img = cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)
        sharp = cv2.Laplacian(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var()
        if sharp < 60:
            continue
        h, w = img.shape[:2]
        x, y, fw, fh = f["box"]
        cx, cy = x + fw / 2, y + fh / 2
        win_h = min(h, fh * 5.0)   # tighter than the default hero crop
        win_w = min(w, win_h * 16 / 10)
        win_h = min(win_h, win_w / (16 / 10))
        x0 = int(np.clip(cx - win_w / 2, 0, w - win_w))
        y0 = int(np.clip(cy - win_h * 0.4, 0, h - win_h))
        crop = img[y0:int(y0 + win_h), x0:int(x0 + win_w)]
        ch, cw = crop.shape[:2]
        s = min(1.0, 1920 / max(ch, cw))
        if s < 1.0:
            crop = cv2.resize(crop, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        cv2.imwrite(str(PUB / "media" / "gia-minh" / "hero.jpg"), crop,
                    [cv2.IMWRITE_JPEG_QUALITY, 85])
        print(f"   gia-minh hero from {file} (face {own}px, sharp {sharp:.0f})")
        # keep hero as image poster; preserve spotlight video if hero was video
        p = PUB / "data" / "students" / "gia-minh.json"
        st = json.loads(p.read_text(encoding="utf-8"))
        hero = st["hero"] or {}
        if hero.get("type") == "video":
            hero["poster"] = "media/gia-minh/hero.jpg"
        else:
            hero = {"type": "image", "src": "media/gia-minh/hero.jpg",
                    "poster": "media/gia-minh/hero.jpg"}
        set_hero("gia-minh", hero)
        return
    print("gia-minh: no better candidate found")


if __name__ == "__main__":
    fix_elsa()
    fix_luka()
    fix_gia_minh()
    print("DONE")
