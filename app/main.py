from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.models import FrameInfo, FrameResult, SearchResult, SourceInfo, SubmissionRecord, SubmissionStatus
from app.middleware import RateLimitMiddleware
from app.security import require_api_key
from app.services.dedupe import dedupe_frames
from app.services.downloader import download_video
from app.services.keyframes import extract_keyframes
from app.services.queue import InMemoryJobQueue
from app.services.ranking import rank_results
from app.services.report import build_pdf_report
from app.services.reverse_search import reverse_search_frame
from app.settings import settings

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "submissions"
DATA_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name, version="0.3.0")
app.add_middleware(RateLimitMiddleware)
app.mount("/static", StaticFiles(directory=ROOT / "app" / "static"), name="static")
templates = Jinja2Templates(directory=str(ROOT / "app" / "templates"))
job_queue = InMemoryJobQueue(workers=settings.queue_workers)


@app.on_event("startup")
async def _startup() -> None:
    await job_queue.start()


@app.on_event("shutdown")
async def _shutdown() -> None:
    await job_queue.stop()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _submission_path(submission_id: str) -> Path:
    return DATA_DIR / submission_id


def _save_status(submission_id: str, payload: SubmissionRecord) -> None:
    sub_dir = _submission_path(submission_id)
    sub_dir.mkdir(parents=True, exist_ok=True)
    with (sub_dir / "status.json").open("w", encoding="utf-8") as f:
        json.dump(payload.to_json_dict(), f, indent=2)


def _load_status(submission_id: str) -> SubmissionRecord:
    status_path = _submission_path(submission_id) / "status.json"
    if not status_path.exists():
        raise HTTPException(status_code=404, detail="Submission not found")
    with status_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return SubmissionRecord.model_validate(data)


async def process_submission(submission_id: str, source_url: str | None, uploaded_name: str | None) -> None:
    sub_dir = _submission_path(submission_id)
    video_path = sub_dir / "input.mp4"
    frames_dir = sub_dir / "frames"

    status = _load_status(submission_id)
    status.status = SubmissionStatus.processing
    status.updatedAt = _now_iso()
    _save_status(submission_id, status)

    try:
        if source_url:
            await download_video(source_url, video_path)

        if not video_path.exists() or video_path.stat().st_size == 0:
            raise RuntimeError("No input video available for processing")

        extracted = await extract_keyframes(video_path=video_path, output_dir=frames_dir)
        deduped = dedupe_frames(extracted, distance_threshold=8)

        frame_results: list[FrameResult] = []
        for frame in deduped:
            results = await reverse_search_frame(frame.path)
            ranked = rank_results(results)
            frame_results.append(
                FrameResult(
                    frame=FrameInfo(
                        filename=frame.path.name,
                        relativePath=f"/api/submissions/{submission_id}/frames/{frame.path.name}",
                        timestampSeconds=frame.timestamp_seconds,
                        phash=str(frame.phash),
                    ),
                    results=[SearchResult.model_validate(r) for r in results],
                    ranked=[SearchResult.model_validate(r) for r in ranked],
                )
            )

        earliest: list[SearchResult] = []
        for fr in frame_results:
            if fr.ranked:
                earliest.append(fr.ranked[0])

        earliest = sorted(earliest, key=lambda x: x.publishedAt or "9999-12-31T00:00:00+00:00")

        status.status = SubmissionStatus.done
        status.updatedAt = _now_iso()
        status.source = SourceInfo(url=source_url, uploadedName=uploaded_name)
        status.frameCount = len(deduped)
        status.frameResults = frame_results
        status.earliestKnownMatches = earliest[:25]
        status.reportUrl = f"/r/{submission_id}"
        status.error = None
        _save_status(submission_id, status)

        pdf_path = sub_dir / "report.pdf"
        build_pdf_report(status.to_json_dict(), pdf_path)
    except Exception as exc:
        logger.exception("Submission processing failed id=%s", submission_id)
        status.status = SubmissionStatus.failed
        status.updatedAt = _now_iso()
        status.error = str(exc)
        _save_status(submission_id, status)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/healthz")
async def healthz():
    return {"ok": True, "service": settings.app_name}


@app.get("/readyz")
async def readyz():
    # For now we are ready if queue workers were started.
    return {"ready": True, "workers": settings.queue_workers}


@app.post("/api/submissions")
async def create_submission(
    request: Request,
    _: None = Depends(require_api_key),
    url: str | None = Form(default=None),
    file: UploadFile | None = File(default=None),
):
    if not url and not file:
        raise HTTPException(status_code=400, detail="Provide either a URL or uploaded file")

    submission_id = str(uuid.uuid4())
    sub_dir = _submission_path(submission_id)
    sub_dir.mkdir(parents=True, exist_ok=True)
    input_path = sub_dir / "input.mp4"

    uploaded_name = None
    if file:
        uploaded_name = file.filename
        if not uploaded_name:
            raise HTTPException(status_code=400, detail="Uploaded file must have a filename")

        max_bytes = settings.max_upload_mb * 1024 * 1024
        written = 0
        with input_path.open("wb") as out:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                written += len(chunk)
                if written > max_bytes:
                    raise HTTPException(status_code=413, detail=f"Upload too large. Max {settings.max_upload_mb}MB")
                out.write(chunk)

    payload = SubmissionRecord(
        id=submission_id,
        createdAt=_now_iso(),
        updatedAt=_now_iso(),
        status=SubmissionStatus.queued,
        source=SourceInfo(url=url, uploadedName=uploaded_name),
    )
    _save_status(submission_id, payload)

    await job_queue.enqueue(submission_id, lambda: process_submission(submission_id, url, uploaded_name))
    return JSONResponse({"id": submission_id, "status": "queued", "statusUrl": f"/api/submissions/{submission_id}"})


@app.get("/api/submissions/{submission_id}")
async def get_submission(submission_id: str):
    return _load_status(submission_id).to_json_dict()


@app.get("/api/submissions/{submission_id}/frames/{filename}")
async def get_frame(submission_id: str, filename: str):
    path = _submission_path(submission_id) / "frames" / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Frame not found")
    return FileResponse(path)


@app.get("/r/{submission_id}", response_class=HTMLResponse)
async def report_page(request: Request, submission_id: str):
    status = _load_status(submission_id)
    return templates.TemplateResponse("report.html", {"request": request, "submission": status.to_json_dict()})


@app.get("/api/submissions/{submission_id}/export.json")
async def export_json(submission_id: str, _: None = Depends(require_api_key)):
    return _load_status(submission_id).to_json_dict()


@app.get("/api/submissions/{submission_id}/export.pdf")
async def export_pdf(submission_id: str, _: None = Depends(require_api_key)):
    pdf_path = _submission_path(submission_id) / "report.pdf"
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF report not generated yet")
    return FileResponse(pdf_path, filename=f"{submission_id}.pdf", media_type="application/pdf")
