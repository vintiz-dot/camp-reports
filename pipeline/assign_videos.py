"""Assign videos to student clusters by sampling frames.

For each video: sample ~1 frame every 2s (max 40), detect + embed faces,
match against cluster centroids, and record per-cluster hit timestamps.
The timestamps later drive per-student trim windows.

Resumable via data/videos.jsonl. Originals untouched.
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
from tqdm import tqdm

ROOT = Path(r"C:\Users\Dell\OneDrive\Desktop\hec ads")
PROJ = ROOT / "camp-reports"
DATA = PROJ / "data"
MODELS = PROJ / "models"

MATCH_SIM = 0.42
SCORE_THRESHOLD = 0.8
MIN_FACE_PX = 36
SAMPLE_EVERY_S = 2.0
MAX_SAMPLES = 40
MAX_SIDE = 1280

VIDEO_EXTS = {".mov", ".mp4"}


def build_centroids(emb):
    with open(DATA / "clusters.json", encoding="utf-8") as f:
        clusters = json.load(f)["clusters"]
    emb = emb / np.linalg.norm(emb, axis=1, keepdims=True)
    ids, mat = [], []
    for c in clusters:
        v = emb[c["fids"]].mean(axis=0)
        ids.append(c["id"])
        mat.append(v / np.linalg.norm(v))
    return ids, np.stack(mat)


def main():
    emb = np.load(DATA / "embeddings.npy")
    cluster_ids, cmat = build_centroids(emb)

    out_path = DATA / "videos.jsonl"
    done = set()
    if out_path.exists():
        with open(out_path, encoding="utf-8") as f:
            for line in f:
                done.add(json.loads(line)["file"])

    files = sorted(
        p for p in ROOT.iterdir()
        if p.is_file() and p.suffix.lower() in VIDEO_EXTS and p.name not in done
    )
    print(f"{len(done)} videos done, {len(files)} to go", flush=True)

    detector = cv2.FaceDetectorYN.create(
        str(MODELS / "face_detection_yunet_2023mar.onnx"), "", (320, 320),
        SCORE_THRESHOLD, 0.3, 5000)
    recognizer = cv2.FaceRecognizerSF.create(
        str(MODELS / "face_recognition_sface_2021dec.onnx"), "")

    out = open(out_path, "a", encoding="utf-8")
    try:
        for path in tqdm(files, unit="vid", mininterval=10, file=sys.stdout):
            rec = {"file": path.name, "duration": None, "hits": {}, "error": None}
            try:
                cap = cv2.VideoCapture(str(path))
                fps = cap.get(cv2.CAP_PROP_FPS) or 30
                n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
                duration = n_frames / fps if fps else 0
                rec["duration"] = round(duration, 2)

                n_samples = min(MAX_SAMPLES, max(3, int(duration / SAMPLE_EVERY_S)))
                times = np.linspace(0.3, max(duration - 0.3, 0.4), n_samples)
                hits = defaultdict(list)
                for t in times:
                    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
                    ok, frame = cap.read()
                    if not ok or frame is None:
                        continue
                    h, w = frame.shape[:2]
                    scale = min(1.0, MAX_SIDE / max(h, w))
                    if scale < 1.0:
                        frame = cv2.resize(frame, None, fx=scale, fy=scale)
                    dh, dw = frame.shape[:2]
                    detector.setInputSize((dw, dh))
                    _, faces = detector.detect(frame)
                    if faces is None:
                        continue
                    for face in faces:
                        if min(face[2], face[3]) < MIN_FACE_PX:
                            continue
                        aligned = recognizer.alignCrop(frame, face)
                        v = recognizer.feature(aligned).flatten().astype(np.float32)
                        v = v / np.linalg.norm(v)
                        sims = cmat @ v
                        best = int(np.argmax(sims))
                        if sims[best] >= MATCH_SIM:
                            hits[cluster_ids[best]].append({
                                "t": round(float(t), 2),
                                "sim": round(float(sims[best]), 3),
                                "size": int(min(face[2], face[3])),
                            })
                cap.release()
                rec["hits"] = dict(hits)
            except Exception as e:  # noqa: BLE001
                rec["error"] = f"{type(e).__name__}: {e}"
            out.write(json.dumps(rec) + "\n")
            out.flush()
    finally:
        out.close()
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
