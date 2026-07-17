# HEC Summer Camp 2026 — Student Journals

Personalized, premium web reports for each summer camp student at
**Happy English Club** (Đống Đa, Hà Nội · [hanoienglish.vip](https://hanoienglish.vip)).

## Structure

```
camp-reports/
├── pipeline/            Python media pipeline (face recognition + editing)
│   ├── scan_faces.py    detect + embed faces in all photos (YuNet + SFace)
│   ├── cluster_faces.py group faces into unique students, montages for naming
│   ├── assign_videos.py match videos to students via frame sampling
│   └── process_media.py subject-centred crops, video trims, web transcode
├── models/              ONNX models (OpenCV Zoo: YuNet detector, SFace embedder)
├── data/                pipeline outputs (embeddings, clusters, manifests)
├── site/                Vite + Tailwind v4 frontend (source)
│   ├── index.html       journal directory
│   ├── student.html     per-student report (?s=<slug>)
│   ├── src/             JS modules (data layer, personalization, UI)
│   └── public/
│       ├── data/        students.json + per-student JSON configs
│       └── media/       processed per-student photos & clips
└── docs/                production build → GitHub Pages
```

## Pipeline (Python 3.13, venv at `C:\Users\Dell\.venvs\camp-reports`)

```powershell
$py = "C:\Users\Dell\.venvs\camp-reports\Scripts\python.exe"
& $py pipeline\scan_faces.py      # 1. scan photos
& $py pipeline\cluster_faces.py   # 2. cluster -> data/clusters/review.html
# 3. name clusters in data/students_map.json
& $py pipeline\assign_videos.py   # 4. match videos
& $py pipeline\process_media.py   # 5. crops + trims + per-student JSON
```

The pipeline never modifies original media; everything is written to
`data/` and `site/public/`.

## Site

```powershell
cd site
npm install
npm run dev     # local preview
npm run build   # -> ../docs (GitHub Pages-ready, relative base)
```

Dynamic personalization: each student page extracts a bespoke accent
palette from the hero image (ColorThief), adapts the masonry layout to
media aspect ratios, and renders bilingual (EN/VI) remarks from the
student's JSON config.

### Supabase later

All data access goes through `site/src/data.js`. To move from static
JSON to Supabase, replace the two fetches there with supabase-js
queries — no UI changes needed.

## Deploy (GitHub Pages)

1. Repo → Settings → Pages → "Deploy from a branch" → `main` / `docs/`.
2. `npm run build` in `site/`, then commit `docs/` and push.
