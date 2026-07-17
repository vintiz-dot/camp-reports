"""Cluster face embeddings into unique students.

Strategy:
  1. Cluster only high-confidence, reasonably-sized faces (cleaner identities).
  2. Assign the remaining faces to the nearest cluster centroid if similar enough.
  3. Emit montage sheets + an HTML review page so the coach can name each cluster.

Outputs:
  data/clusters.json            {"clusters": [{id, size, fids, files}], "unassigned": n}
  data/clusters/cluster_XX.jpg  montage per cluster
  data/clusters/review.html     one-page contact sheet for naming students
"""

import json
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
from sklearn.cluster import AgglomerativeClustering

PROJ = Path(r"C:\Users\Dell\OneDrive\Desktop\hec ads\camp-reports")
DATA = PROJ / "data"
THUMBS = DATA / "face_thumbs"
OUT = DATA / "clusters"

# SFace: cosine similarity >= 0.363 is OpenCV's same-identity threshold.
CLUSTER_DIST = 0.55      # 1 - cosine_sim; conservative so clusters stay pure
ASSIGN_SIM = 0.42        # centroid similarity needed to absorb leftover faces
SEED_SCORE = 0.90        # detection confidence for clustering seeds
SEED_SIZE = 60           # min face box side (px) for clustering seeds
MIN_CLUSTER = 4          # clusters smaller than this are listed as "minor"


def load_manifest():
    recs = []
    with open(DATA / "faces.jsonl", encoding="utf-8") as f:
        for line in f:
            recs.append(json.loads(line))
    return recs


def montage(fids, out_path, cols=8, cell=112, max_faces=32):
    fids = fids[:max_faces]
    rows = (len(fids) + cols - 1) // cols
    sheet = np.full((rows * cell, cols * cell, 3), 245, np.uint8)
    for i, fid in enumerate(fids):
        img = cv2.imread(str(THUMBS / f"{fid}.jpg"))
        if img is None:
            continue
        img = cv2.resize(img, (cell, cell))
        r, c = divmod(i, cols)
        sheet[r * cell:(r + 1) * cell, c * cell:(c + 1) * cell] = img
    cv2.imwrite(str(out_path), sheet)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    recs = load_manifest()
    emb = np.load(DATA / "embeddings.npy")
    emb = emb / np.linalg.norm(emb, axis=1, keepdims=True)

    fid_meta = {}
    for rec in recs:
        for face in rec["faces"]:
            fid_meta[face["fid"]] = {
                "file": rec["file"],
                "box": face["box"],
                "score": face["score"],
                "size": min(face["box"][2], face["box"][3]),
            }

    seeds = [fid for fid, m in fid_meta.items()
             if m["score"] >= SEED_SCORE and m["size"] >= SEED_SIZE]
    rest = [fid for fid in fid_meta if fid not in set(seeds)]
    print(f"{len(fid_meta)} faces total; {len(seeds)} clustering seeds, {len(rest)} to assign")

    seed_emb = emb[seeds]
    labels = AgglomerativeClustering(
        n_clusters=None, metric="cosine", linkage="average",
        distance_threshold=CLUSTER_DIST,
    ).fit_predict(seed_emb)

    by_label = defaultdict(list)
    for fid, lab in zip(seeds, labels):
        by_label[int(lab)].append(fid)

    # centroids from seeds only
    centroids = {}
    for lab, fids in by_label.items():
        c = emb[fids].mean(axis=0)
        centroids[lab] = c / np.linalg.norm(c)

    # absorb leftover faces
    labs = list(centroids)
    cmat = np.stack([centroids[l] for l in labs])
    unassigned = 0
    for fid in rest:
        sims = cmat @ emb[fid]
        best = int(np.argmax(sims))
        if sims[best] >= ASSIGN_SIM:
            by_label[labs[best]].append(fid)
        else:
            unassigned += 1

    # order clusters by size, largest first
    ordered = sorted(by_label.items(), key=lambda kv: -len(kv[1]))
    clusters = []
    for i, (lab, fids) in enumerate(ordered, 1):
        fids_sorted = sorted(fids, key=lambda f: -fid_meta[f]["size"])
        cid = f"cluster_{i:02d}"
        clusters.append({
            "id": cid,
            "size": len(fids),
            "n_images": len({fid_meta[f]['file'] for f in fids}),
            "fids": fids_sorted,
            "files": sorted({fid_meta[f]["file"] for f in fids}),
        })
        montage(fids_sorted, OUT / f"{cid}.jpg")

    with open(DATA / "clusters.json", "w", encoding="utf-8") as f:
        json.dump({"clusters": clusters, "unassigned": unassigned}, f, indent=1)

    major = [c for c in clusters if c["size"] >= MIN_CLUSTER]
    html = ["<!doctype html><meta charset='utf-8'><title>HEC face clusters</title>",
            "<style>body{font-family:sans-serif;margin:24px}img{max-width:100%;border:1px solid #ccc}",
            "h2{margin:28px 0 4px}p{color:#555;margin:2px 0 8px}</style>",
            f"<h1>Face clusters — name the students ({len(major)} major, "
            f"{len(clusters) - len(major)} minor, {unassigned} unassigned faces)</h1>"]
    for c in clusters:
        tag = "" if c["size"] >= MIN_CLUSTER else " (minor)"
        html.append(f"<h2>{c['id']}{tag}</h2><p>{c['size']} faces across "
                    f"{c['n_images']} photos</p><img src='{c['id']}.jpg'>")
    (OUT / "review.html").write_text("\n".join(html), encoding="utf-8")

    print(f"DONE: {len(clusters)} clusters ({len(major)} major), {unassigned} unassigned")
    for c in major:
        print(f"  {c['id']}: {c['size']} faces / {c['n_images']} photos")


if __name__ == "__main__":
    main()
