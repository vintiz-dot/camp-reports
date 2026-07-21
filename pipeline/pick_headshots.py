"""Select and align the best headshot per camper, for laser etching.

Scores every clustered face on size, sharpness, frontality (from YuNet's
5 landmarks) and exposure, then re-detects on the winning photo to align
the eyes level and crop classic headshot proportions (eye line at 40%
from the top, generous headroom, shoulders included).

Curated-folder students (elsa, luka) have no cluster, so their frames are
harvested from the ingested clips instead.

Output: print/headshots/<slug>.jpg  (square, 1600px, colour)
        print/headshots/_contact_sheet.jpg
"""

import json
import math
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
OUT = PROJ / "print" / "headshots"

OUT_PX = 1600
TOP_CANDIDATES = 22          # re-examine this many best faces per student

detector = cv2.FaceDetectorYN.create(
    str(MODELS / "face_detection_yunet_2023mar.onnx"), "", (320, 320), 0.7, 0.3, 5000)
recognizer = cv2.FaceRecognizerSF.create(
    str(MODELS / "face_recognition_sface_2021dec.onnx"), "")

# A detector will happily lock onto a pencil drawing, a face seen through
# glass, or the back of a head. Verifying every candidate against the
# student's own embedding centroid is what keeps the wrong child (or a
# sketch) off a permanent wooden keepsake.
IDENTITY_MIN = 0.42


def embed(img, face):
    v = recognizer.feature(recognizer.alignCrop(img, face)).flatten().astype(np.float32)
    n = np.linalg.norm(v)
    return v / n if n else v


def load_bgr(path):
    im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    return cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)


def detect(img):
    h, w = img.shape[:2]
    detector.setInputSize((w, h))
    _, faces = detector.detect(img)
    return [] if faces is None else list(faces)


def landmarks(face):
    """YuNet: [x,y,w,h, re_x,re_y, le_x,le_y, nose_x,nose_y, rm, lm, score]"""
    pts = face[4:14].reshape(5, 2)
    return {"reye": pts[0], "leye": pts[1], "nose": pts[2],
            "rmouth": pts[3], "lmouth": pts[4]}


def frontality(face):
    """1.0 = perfectly frontal. Uses nose offset from the eye midpoint,
    normalised by eye distance, plus eye-line vs mouth-line parallelism."""
    lm = landmarks(face)
    eye_mid = (lm["reye"] + lm["leye"]) / 2
    eye_d = np.linalg.norm(lm["leye"] - lm["reye"])
    if eye_d < 1:
        return 0.0
    yaw_off = abs(lm["nose"][0] - eye_mid[0]) / eye_d      # 0 = centred
    mouth_mid = (lm["rmouth"] + lm["lmouth"]) / 2
    vert = np.linalg.norm(mouth_mid - eye_mid) / eye_d      # ~0.9-1.2 frontal
    vert_pen = abs(vert - 1.05)
    return max(0.0, 1.0 - yaw_off * 2.2 - vert_pen * 0.8)


def occlusion_penalty(img, face):
    """A face mask, a raised hand or a cup in front of the mouth all break
    the skin-tone continuity between forehead and mouth. Compare the two
    regions in HSV; a large mismatch means something is covering the face.
    Returns a multiplier in (0, 1].
    """
    lm = landmarks(face)
    x, y, w, h = face[:4]
    eye_y = (lm["reye"][1] + lm["leye"][1]) / 2
    mouth = (lm["rmouth"] + lm["lmouth"]) / 2
    r = max(4, int(w * 0.13))

    def patch(cx, cy):
        y0, y1 = int(max(cy - r, 0)), int(cy + r)
        x0, x1 = int(max(cx - r, 0)), int(cx + r)
        p = img[y0:y1, x0:x1]
        return None if p.size == 0 else cv2.cvtColor(p, cv2.COLOR_BGR2HSV)

    fore = patch(x + w / 2, eye_y - (mouth[1] - eye_y) * 0.55)
    low = patch(mouth[0], mouth[1])
    if fore is None or low is None:
        return 1.0

    fh, fs = float(fore[..., 0].mean()), float(fore[..., 1].mean())
    lh, ls = float(low[..., 0].mean()), float(low[..., 1].mean())
    hue_gap = min(abs(fh - lh), 180 - abs(fh - lh)) / 90.0   # 0..1
    sat_gap = abs(fs - ls) / 128.0
    # a cloth mask reads as a big saturation drop; a hand shifts hue/edges
    gap = min(1.0, hue_gap * 1.3 + sat_gap)
    return float(max(0.25, 1.0 - gap * 1.5))


def face_quality(img, face, ref=None):
    x, y, w, h = face[:4]
    x0, y0 = max(int(x), 0), max(int(y), 0)
    patch = img[y0:int(y + h), x0:int(x + w)]
    if patch.size == 0:
        return None
    gray = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)
    sharp = cv2.Laplacian(gray, cv2.CV_64F).var()
    mean = gray.mean()
    # penalise blown-out or very dark faces
    expo = 1.0 - min(1.0, abs(mean - 128) / 128) ** 1.5
    front = frontality(face)
    size = min(w, h)
    conf = float(face[14])

    sim = 1.0
    if ref is not None:
        sim = float(ref @ embed(img, face))
        if sim < IDENTITY_MIN:
            return None                       # not this child (or not a real face)

    occl = occlusion_penalty(img, face)
    return {"sharp": sharp, "expo": expo, "front": front, "sim": sim,
            "size": size, "conf": conf, "occl": occl,
            "score": (size ** 0.9) * conf * (front ** 1.6)
                     * min(sharp / 120.0, 1.6) * (0.55 + 0.45 * expo)
                     * (0.5 + 0.5 * min(sim / 0.6, 1.0))
                     * (occl ** 2.0)}


def align_and_crop(img, face, out_px=OUT_PX):
    """Rotate so the eyes are level, then crop a classic headshot."""
    lm = landmarks(face)
    reye, leye = lm["reye"], lm["leye"]
    eye_mid = (reye + leye) / 2
    dx, dy = (leye - reye)
    angle = math.degrees(math.atan2(dy, dx))
    eye_d = float(np.linalg.norm(leye - reye))

    # head width ~ 2.9x inter-ocular; frame = 3.5x for shoulders + headroom
    frame = eye_d * 3.9
    M = cv2.getRotationMatrix2D(tuple(eye_mid.astype(float)), angle, out_px / frame)
    # place eye midpoint at 42% height, horizontally centred
    M[0, 2] += out_px * 0.50 - eye_mid[0]
    M[1, 2] += out_px * 0.42 - eye_mid[1]
    return cv2.warpAffine(img, M, (out_px, out_px),
                          flags=cv2.INTER_LANCZOS4,
                          borderMode=cv2.BORDER_REPLICATE)


def candidates_from_clusters():
    """Returns {slug: ([(box, file)], centroid_embedding)}"""
    clusters = {c["id"]: c for c in
                json.loads((DATA / "clusters.json").read_text(encoding="utf-8"))["clusters"]}
    smap = json.loads((DATA / "students_map.json").read_text(encoding="utf-8"))
    emb = np.load(DATA / "embeddings.npy")
    emb = emb / np.linalg.norm(emb, axis=1, keepdims=True)

    fid_file, fid_box = {}, {}
    for line in open(DATA / "faces.jsonl", encoding="utf-8"):
        r = json.loads(line)
        for f in r["faces"]:
            fid_file[f["fid"]] = r["file"]
            fid_box[f["fid"]] = f["box"]

    per_student, fids_by_slug = {}, {}
    for cid, meta in smap.items():
        slug = meta.get("slug")
        if cid not in clusters:
            continue
        entries = per_student.setdefault(slug, [])
        fids = fids_by_slug.setdefault(slug, [])
        for fid in clusters[cid]["fids"]:
            entries.append((fid_box[fid], fid_file[fid]))
            fids.append(fid)

    out = {}
    for slug, entries in per_student.items():
        v = emb[fids_by_slug[slug]].mean(axis=0)
        out[slug] = (entries, v / np.linalg.norm(v))
    return out


def reference_from_youtube(video_id):
    """Elsa has no cluster — her verified likeness comes from the
    thumbnail of her own interview video."""
    import urllib.request
    tmp = DATA / f"_yt_{video_id}.jpg"
    for q in ("maxresdefault", "hqdefault"):
        try:
            urllib.request.urlretrieve(
                f"https://i.ytimg.com/vi/{video_id}/{q}.jpg", tmp)
            if tmp.stat().st_size > 5000:
                break
        except Exception:  # noqa: BLE001
            continue
    if not tmp.exists():
        return None
    img = cv2.imread(str(tmp))
    faces = detect(img)
    if not faces:
        return None
    return embed(img, max(faces, key=lambda f: f[2] * f[3]))


def reference_from_own_clips(slug):
    """No cluster and no interview: the child is the subject of their own
    folder, so the most frequently recurring identity across their clips
    is them."""
    media = PUB / "media" / slug
    vecs = []
    for clip in sorted(media.glob("*.mp4")):
        cap = cv2.VideoCapture(str(clip))
        n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        for i in range(0, n, max(1, n // 12)):
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ok, fr = cap.read()
            if not ok:
                continue
            for f in detect(fr):
                if min(f[2], f[3]) >= 90:
                    vecs.append(embed(fr, f))
        cap.release()
    if not vecs:
        return None
    V = np.stack(vecs)
    sims = V @ V.T                     # densest identity = the subject
    best = int(np.argmax(sims.sum(axis=1)))
    grp = V[sims[best] >= IDENTITY_MIN]
    v = grp.mean(axis=0)
    return v / np.linalg.norm(v)


def best_from_photos(entries, ref):
    """entries: [(box, filename)] -> (score_dict, aligned_image, source)"""
    ranked = sorted(entries, key=lambda e: -min(e[0][2], e[0][3]))[:TOP_CANDIDATES * 4]
    best = None
    seen = set()
    checked = 0
    for box, fname in ranked:
        if fname in seen or checked >= TOP_CANDIDATES * 2:
            continue
        seen.add(fname)
        src = ROOT / fname
        if not src.exists():
            continue
        try:
            img = load_bgr(src)
        except Exception:  # noqa: BLE001
            continue
        checked += 1
        # find the detection matching this box (largest overlap)
        target = np.array([box[0] + box[2] / 2, box[1] + box[3] / 2])
        for face in detect(img):
            c = np.array([face[0] + face[2] / 2, face[1] + face[3] / 2])
            if np.linalg.norm(c - target) > max(box[2], box[3]) * 0.6:
                continue
            q = face_quality(img, face, ref)
            if q and (best is None or q["score"] > best[0]["score"]):
                best = (q, img, face, fname)
    if not best:
        return None
    q, img, face, fname = best
    return q, align_and_crop(img, face), fname


def best_from_clips(slug, ref):
    """For curated-folder students: scan their processed clips for the
    best identity-verified frontal frame."""
    media = PUB / "media" / slug
    best = None
    for clip in sorted(media.glob("*.mp4")):
        cap = cv2.VideoCapture(str(clip))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        step = max(1, int(fps / 3))          # ~3 samples per second
        for i in range(0, n, step):
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ok, fr = cap.read()
            if not ok:
                continue
            for face in detect(fr):
                if min(face[2], face[3]) < 90:
                    continue
                q = face_quality(fr, face, ref)
                if q and (best is None or q["score"] > best[0]["score"]):
                    best = (q, fr.copy(), face, f"{clip.name}@{i/fps:.1f}s")
        cap.release()
    if not best:
        return None
    q, img, face, fname = best
    return q, align_and_crop(img, face), fname


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    index = json.loads((PUB / "data" / "students.json").read_text(encoding="utf-8"))
    slugs = [s["slug"] for s in index["students"]]
    from_clusters = candidates_from_clusters()

    interviews = json.loads((DATA / "interviews.json").read_text(encoding="utf-8"))

    report = {}
    for slug in slugs:
        pair = from_clusters.get(slug)
        if pair:
            entries, ref = pair
            res = best_from_photos(entries, ref)
        else:
            # no cluster: verify identity from their interview, else from
            # the recurring subject of their own folder
            ref = None
            if slug in interviews:
                ref = reference_from_youtube(interviews[slug][0]["youtubeId"])
            if ref is None:
                ref = reference_from_own_clips(slug)
            res = best_from_clips(slug, ref)
        if res is None:
            print(f"!! {slug}: no identity-verified face found")
            continue
        q, crop, fname = res
        cv2.imwrite(str(OUT / f"{slug}.jpg"), crop,
                    [cv2.IMWRITE_JPEG_QUALITY, 95])
        report[slug] = {"source": str(fname), "face_px": int(q["size"]),
                        "front": round(float(q["front"]), 2),
                        "identity": round(float(q["sim"]), 2),
                        "clear": round(float(q["occl"]), 2),
                        "sharp": int(q["sharp"]), "score": int(q["score"])}
        print(f"{slug:12s} face={int(q['size']):4d}px front={q['front']:.2f} "
              f"id={q['sim']:.2f} clear={q['occl']:.2f} sharp={q['sharp']:5.0f}  <- {fname}")

    (OUT / "_sources.json").write_text(json.dumps(report, indent=1), encoding="utf-8")

    # contact sheet for a quick human check
    cols, cell = 7, 240
    slugs_done = sorted(report)
    rows = (len(slugs_done) + cols - 1) // cols
    sheet = np.full((rows * (cell + 26), cols * cell, 3), 255, np.uint8)
    for i, slug in enumerate(slugs_done):
        img = cv2.imread(str(OUT / f"{slug}.jpg"))
        img = cv2.resize(img, (cell, cell))
        r, c = divmod(i, cols)
        y0 = r * (cell + 26)
        sheet[y0:y0 + cell, c * cell:(c + 1) * cell] = img
        cv2.putText(sheet, slug, (c * cell + 6, y0 + cell + 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1, cv2.LINE_AA)
    cv2.imwrite(str(OUT / "_contact_sheet.jpg"), sheet,
                [cv2.IMWRITE_JPEG_QUALITY, 92])
    print(f"\nDONE: {len(report)} headshots -> {OUT}")


if __name__ == "__main__":
    main()
