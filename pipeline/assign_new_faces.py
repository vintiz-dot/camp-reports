"""Assign newly scanned faces to EXISTING clusters — IDs stay stable.

Never re-clusters or renumbers: students_map.json keys must keep meaning.
New faces that match no centroid are clustered among themselves; groups of
MIN_NEW or more become new clusters (cluster_114+), with montages for naming.
"""

import json
from pathlib import Path

import cv2
import numpy as np
from sklearn.cluster import AgglomerativeClustering

PROJ = Path(r"C:\Users\Dell\OneDrive\Desktop\hec ads\camp-reports")
DATA = PROJ / "data"
THUMBS = DATA / "face_thumbs"

ASSIGN_SIM = 0.42
CLUSTER_DIST = 0.55
MIN_NEW = 4


def main():
    clusters_doc = json.loads((DATA / "clusters.json").read_text(encoding="utf-8"))
    clusters = clusters_doc["clusters"]
    emb = np.load(DATA / "embeddings.npy")
    emb = emb / np.linalg.norm(emb, axis=1, keepdims=True)

    recs = [json.loads(l) for l in open(DATA / "faces.jsonl", encoding="utf-8")]
    fid_meta = {}
    for r in recs:
        for f in r["faces"]:
            fid_meta[f["fid"]] = {"file": r["file"], "size": min(f["box"][2], f["box"][3])}

    known = set()
    for c in clusters:
        known.update(c["fids"])
    new_fids = [fid for fid in fid_meta if fid not in known and fid < len(emb)]
    print(f"{len(new_fids)} unassigned faces to test against {len(clusters)} clusters")

    ids = [c["id"] for c in clusters]
    cmat = np.stack([
        (v := emb[c["fids"]].mean(axis=0)) / np.linalg.norm(v) for c in clusters
    ])

    assigned, leftovers = 0, []
    for fid in new_fids:
        sims = cmat @ emb[fid]
        best = int(np.argmax(sims))
        if sims[best] >= ASSIGN_SIM:
            c = clusters[best]
            c["fids"].append(fid)
            if fid_meta[fid]["file"] not in c["files"]:
                c["files"].append(fid_meta[fid]["file"])
            assigned += 1
        else:
            leftovers.append(fid)

    # try to form NEW clusters from leftovers (append-only numbering)
    new_clusters = []
    if len(leftovers) >= MIN_NEW:
        L = emb[leftovers]
        labels = AgglomerativeClustering(
            n_clusters=None, metric="cosine", linkage="average",
            distance_threshold=CLUSTER_DIST).fit_predict(L)
        next_no = max(int(c["id"].split("_")[1]) for c in clusters) + 1
        from collections import defaultdict
        groups = defaultdict(list)
        for fid, lab in zip(leftovers, labels):
            groups[lab].append(fid)
        for lab, fids in sorted(groups.items(), key=lambda kv: -len(kv[1])):
            if len(fids) < MIN_NEW:
                continue
            cid = f"cluster_{next_no}"
            next_no += 1
            files = sorted({fid_meta[f]["file"] for f in fids})
            clusters.append({"id": cid, "size": len(fids), "n_images": len(files),
                             "fids": fids, "files": files})
            new_clusters.append(cid)
            # montage for naming
            cell, cols = 112, 8
            fids_sorted = sorted(fids, key=lambda f: -fid_meta[f]["size"])[:32]
            rows = (len(fids_sorted) + cols - 1) // cols
            sheet = np.full((rows * cell, cols * cell, 3), 245, np.uint8)
            for i, f in enumerate(fids_sorted):
                img = cv2.imread(str(THUMBS / f"{f}.jpg"))
                if img is None:
                    continue
                r_, c_ = divmod(i, cols)
                sheet[r_ * cell:(r_ + 1) * cell, c_ * cell:(c_ + 1) * cell] = cv2.resize(img, (cell, cell))
            (DATA / "clusters").mkdir(exist_ok=True)
            cv2.imwrite(str(DATA / "clusters" / f"{cid}.jpg"), sheet)

    for c in clusters:
        c["size"] = len(c["fids"])
        c["n_images"] = len(set(c["files"]))
    (DATA / "clusters.json").write_text(
        json.dumps(clusters_doc, indent=1), encoding="utf-8")

    print(f"assigned {assigned} to existing clusters; "
          f"{len(leftovers)} leftovers; new clusters: {new_clusters or 'none'}")


if __name__ == "__main__":
    main()
