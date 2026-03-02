# Keyframe Reverse Search

Production-oriented web app + REST API to:
1. ingest video (URL or upload),
2. extract scene-change keyframes with FFmpeg,
3. dedupe frames with perceptual hash,
4. run reverse-image search engines in parallel,
5. rank by earliest publication evidence,
6. publish shareable report + JSON/PDF exports.

## Stack
- FastAPI + async workers
- Vanilla HTML/CSS/JS frontend
- FFmpeg + yt-dlp pipeline
- pHash via `imagehash`

## Current production features
- Typed API/domain models (Pydantic)
- Worker queue abstraction (`InMemoryJobQueue` for now)
- Robust partial-failure handling per reverse-search provider
- API key auth support (optional) via `X-API-Key`
- In-process rate limiting middleware
- Upload size limits
- Health/readiness probes: `/healthz`, `/readyz`
- CI with lint + tests

## Quick start

```bash
cd keyframe-reverse-search
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# fill keys as needed
set -a; source .env; set +a
uvicorn app.main:app --reload
```

Open http://localhost:8000

## Environment variables

```bash
# Engine keys
GOOGLE_VISION_API_KEY=
TINEYE_API_URL=
TINEYE_API_USER=
TINEYE_API_KEY=
SERPAPI_KEY=

# App/runtime
APP_NAME=Keyframe Reverse Search
APP_ENV=dev
LOG_LEVEL=INFO
QUEUE_WORKERS=2
MAX_UPLOAD_MB=300
RATE_LIMIT_REQUESTS=30
RATE_LIMIT_WINDOW_SECONDS=60
API_KEY=
```

## API

### Create submission
`POST /api/submissions` (multipart form)
- `url` (optional)
- `file` (optional)
- Requires `X-API-Key` header only when `API_KEY` is configured

Returns `{ id, statusUrl }`

### Poll status
`GET /api/submissions/{id}`

### Share report
`GET /r/{id}`

### Export
- `GET /api/submissions/{id}/export.json`
- `GET /api/submissions/{id}/export.pdf`
(Protected by `X-API-Key` when configured)

## Running tests + lint

```bash
ruff check .
pytest -q
```

## CI/CD
GitHub Actions now runs:
- lint + tests
- Docker image build
- image push to GHCR on `main`
- optional SSH deploy on `main`

Set these repository secrets to enable deploy:
- `DEPLOY_HOST`
- `DEPLOY_USER`
- `DEPLOY_SSH_KEY`
- `GHCR_PAT` (read access to GHCR on target host)

On the server, create `/opt/keyframe-reverse-search/.env` for runtime env vars.

## Queue strategy
Current queue is in-memory for simplicity. For durable production workers use Redis/RQ/Celery or SQS-based workers.
See: `docs/job_queue_strategy.md`.

## Important caveats
- Yandex does not provide a stable official reverse-image API; current adapter is a pragmatic bridge path.
- Earliest publication date is evidence-based inference and should be presented with confidence levels.
- Filesystem submission storage should migrate to object storage + DB for large-scale use.

## No-key fallback mode
If no reverse-search API keys are configured, reports still include per-frame manual links (Google Lens, Yandex, Bing) so investigations can continue without paid API access.
