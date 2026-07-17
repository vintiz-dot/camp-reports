"""Scan still images for faces: detect (YuNet) + embed (SFace).

Non-destructive: reads originals, writes only to camp-reports/data/.
Resumable: skips files already present in the .jsonl manifest.

Outputs:
  data/faces.jsonl        one record per image: file, faces[{box,score,fid}]
  data/embeddings.npy     float32 [N,128], row index == fid
  data/face_thumbs/<fid>.jpg   aligned 112x112 face crops (for montages)
"""

import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps
import pillow_heif
from tqdm import tqdm

pillow_heif.register_heif_opener()

ROOT = Path(r"C:\Users\Dell\OneDrive\Desktop\hec ads")
PROJ = ROOT / "camp-reports"
DATA = PROJ / "data"
THUMBS = DATA / "face_thumbs"
MODELS = PROJ / "models"

DET_MODEL = str(MODELS / "face_detection_yunet_2023mar.onnx")
REC_MODEL = str(MODELS / "face_recognition_sface_2021dec.onnx")

MAX_SIDE = 1600          # downscale long side for detection speed
SCORE_THRESHOLD = 0.8    # YuNet confidence
MIN_FACE_PX = 40         # skip tiny background faces (in detection-scale px)

IMAGE_EXTS = {".heic", ".jpg", ".jpeg", ".png"}


def load_image_bgr(path: Path):
    """Load HEIC/JPG/PNG with EXIF orientation applied; return BGR ndarray."""
    im = Image.open(path)
    im = ImageOps.exif_transpose(im)
    im = im.convert("RGB")
    return cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    THUMBS.mkdir(parents=True, exist_ok=True)

    manifest_path = DATA / "faces.jsonl"
    done_files = set()
    next_fid = 0
    embeddings = []

    emb_path = DATA / "embeddings.npy"
    if manifest_path.exists():
        with open(manifest_path, encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                done_files.add(rec["file"])
                for face in rec["faces"]:
                    next_fid = max(next_fid, face["fid"] + 1)
        if emb_path.exists():
            embeddings = list(np.load(emb_path))
    assert len(embeddings) == next_fid, (
        f"manifest/embedding mismatch: {next_fid} fids vs {len(embeddings)} embeddings"
    )

    files = sorted(
        p for p in ROOT.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS and p.name not in done_files
    )
    print(f"{len(done_files)} already scanned, {len(files)} to go", flush=True)

    detector = cv2.FaceDetectorYN.create(DET_MODEL, "", (320, 320), SCORE_THRESHOLD, 0.3, 5000)
    recognizer = cv2.FaceRecognizerSF.create(REC_MODEL, "")

    mf = open(manifest_path, "a", encoding="utf-8")
    try:
        for path in tqdm(files, unit="img", mininterval=5, file=sys.stdout):
            rec = {"file": path.name, "faces": [], "error": None}
            try:
                img = load_image_bgr(path)
                h, w = img.shape[:2]
                scale = min(1.0, MAX_SIDE / max(h, w))
                det_img = cv2.resize(img, None, fx=scale, fy=scale) if scale < 1.0 else img
                dh, dw = det_img.shape[:2]
                rec["width"], rec["height"] = w, h

                detector.setInputSize((dw, dh))
                _, faces = detector.detect(det_img)
                if faces is not None:
                    for face in faces:
                        x, y, fw, fh = face[:4]
                        score = float(face[14])
                        if min(fw, fh) < MIN_FACE_PX:
                            continue
                        aligned = recognizer.alignCrop(det_img, face)
                        emb = recognizer.feature(aligned).flatten().astype(np.float32)
                        fid = next_fid
                        next_fid += 1
                        embeddings.append(emb)
                        cv2.imwrite(str(THUMBS / f"{fid}.jpg"), aligned)
                        # box stored in original-image coordinates
                        rec["faces"].append({
                            "fid": fid,
                            "box": [round(v / scale) for v in (x, y, fw, fh)],
                            "score": round(score, 3),
                        })
            except Exception as e:  # noqa: BLE001 - log and continue over corrupt files
                rec["error"] = f"{type(e).__name__}: {e}"
            mf.write(json.dumps(rec) + "\n")
            mf.flush()
    finally:
        mf.close()
        if embeddings:
            np.save(emb_path, np.stack(embeddings))

    n_faces = next_fid
    print(f"DONE: {len(done_files) + len(files)} images scanned, {n_faces} faces embedded", flush=True)


if __name__ == "__main__":
    main()
