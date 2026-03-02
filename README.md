# Keyframe Reverse Search (MVP)

Web app + REST API to:
1. ingest video (URL or upload),
2. extract scene-change keyframes with FFmpeg,
3. dedupe frames with perceptual hash,
4. run reverse-image search engines in parallel,
5. rank by earliest publication date,
6. produce shareable report + JSON/PDF exports.

## Stack
- FastAPI (backend + API)
- Vanilla HTML/CSS/JS (frontend)
- FFmpeg + yt-dlp
- pHash via `imagehash`

## Quick start

```bash
cd keyframe-reverse-search
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# fill any API keys you have
set -a; source .env; set +a
uvicorn app.main:app --reload
```

Open http://localhost:8000

## API

### Create submission
`POST /api/submissions` (multipart form)
- `url` (optional)
- `file` (optional)

Returns `{ id, statusUrl }`

### Poll status
`GET /api/submissions/{id}`

### Share report
`GET /r/{id}`

### Export
- `GET /api/submissions/{id}/export.json`
- `GET /api/submissions/{id}/export.pdf`

## Engine support
- Google Vision: implemented via `GOOGLE_VISION_API_KEY`
- TinEye: implemented via API credentials
- Yandex: implemented through SerpAPI fallback (`SERPAPI_KEY`) because Yandex does not provide a stable official reverse-image API.

## Notes
- FFmpeg scene extraction currently uses `select='gt(scene,0.3)'`; tune threshold for your content.
- Timestamp is approximate (index-based) in MVP; can be upgraded with ffprobe/frame metadata parsing.
- Date extraction uses page meta tags and JSON-LD heuristics.
- Submission storage is local filesystem (`data/submissions`).
