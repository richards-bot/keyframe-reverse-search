from __future__ import annotations

import asyncio
import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.services.dedupe import dedupe_frames
from app.services.downloader import download_video
from app.services.keyframes import extract_keyframes
from app.services.ranking import rank_results
from app.services.report import build_pdf_report
from app.services.reverse_search import reverse_search_frame

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "submissions"
DATA_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Keyframe Reverse Search", version="0.1.0")
app.mount("/static", StaticFiles(directory=ROOT / "app" / "static"), name="static")
templates = Jinja2Templates(directory=str(ROOT / "app" / "templates"))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _submission_path(submission_id: str) -> Path:
    return DATA_DIR / submission_id


def _save_status(submission_id: str, payload: dict[str, Any]) -> None:
    sub_dir = _submission_path(submission_id)
    sub_dir.mkdir(parents=True, exist_ok=True)
    with (sub_dir / "status.json").open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def _load_status(submission_id: str) -> dict[str, Any]:
    status_path = _submission_path(submission_id) / "status.json"
    if not status_path.exists():
        raise HTTPException(status_code=404, detail="Submission not found")
    with status_path.open("r", encoding="utf-8") as f:
        return json.load(f)


async def process_submission(submission_id: str, source_url: str | None, uploaded_name: str | None) -> None:
    sub_dir = _submission_path(submission_id)
    video_path = sub_dir / "input.mp4"
    frames_dir = sub_dir / "frames"

    status = _load_status(submission_id)
    status["status"] = "processing"
    status["updatedAt"] = _now_iso()
    _save_status(submission_id, status)

    try:
        if source_url:
            await download_video(source_url, video_path)

        extracted = await extract_keyframes(video_path=video_path, output_dir=frames_dir)
        deduped = dedupe_frames(extracted, distance_threshold=8)

        frame_results = []
        for frame in deduped:
            results = await reverse_search_frame(frame.path)
            frame_results.append(
                {
                    "frame": {
                        "filename": frame.path.name,
                        "relativePath": f"/api/submissions/{submission_id}/frames/{frame.path.name}",
                        "timestampSeconds": frame.timestamp_seconds,
                        "phash": str(frame.phash),
                    },
                    "results": results,
                    "ranked": rank_results(results),
                }
            )

        earliest = []
        for fr in frame_results:
            if fr["ranked"]:
                earliest.append(fr["ranked"][0])

        earliest = sorted(
            earliest,
            key=lambda x: x.get("publishedAt") or "9999-12-31T00:00:00+00:00",
        )

        status.update(
            {
                "status": "done",
                "updatedAt": _now_iso(),
                "source": {"url": source_url, "uploadedName": uploaded_name},
                "frameCount": len(deduped),
                "frameResults": frame_results,
                "earliestKnownMatches": earliest[:25],
                "reportUrl": f"/r/{submission_id}",
            }
        )
        _save_status(submission_id, status)

        pdf_path = sub_dir / "report.pdf"
        build_pdf_report(status, pdf_path)
    except Exception as exc:
        status["status"] = "failed"
        status["updatedAt"] = _now_iso()
        status["error"] = str(exc)
        _save_status(submission_id, status)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/submissions")
async def create_submission(
    background_tasks: BackgroundTasks,
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
        with input_path.open("wb") as out:
            shutil.copyfileobj(file.file, out)

    payload = {
        "id": submission_id,
        "createdAt": _now_iso(),
        "updatedAt": _now_iso(),
        "status": "queued",
        "source": {"url": url, "uploadedName": uploaded_name},
    }
    _save_status(submission_id, payload)

    background_tasks.add_task(process_submission, submission_id, url, uploaded_name)
    return JSONResponse({"id": submission_id, "status": "queued", "statusUrl": f"/api/submissions/{submission_id}"})


@app.get("/api/submissions/{submission_id}")
async def get_submission(submission_id: str):
    return _load_status(submission_id)


@app.get("/api/submissions/{submission_id}/frames/{filename}")
async def get_frame(submission_id: str, filename: str):
    path = _submission_path(submission_id) / "frames" / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Frame not found")
    return FileResponse(path)


@app.get("/r/{submission_id}", response_class=HTMLResponse)
async def report_page(request: Request, submission_id: str):
    status = _load_status(submission_id)
    return templates.TemplateResponse("report.html", {"request": request, "submission": status})


@app.get("/api/submissions/{submission_id}/export.json")
async def export_json(submission_id: str):
    return _load_status(submission_id)


@app.get("/api/submissions/{submission_id}/export.pdf")
async def export_pdf(submission_id: str):
    pdf_path = _submission_path(submission_id) / "report.pdf"
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF report not generated yet")
    return FileResponse(pdf_path, filename=f"{submission_id}.pdf", media_type="application/pdf")
