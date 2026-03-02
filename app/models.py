from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SubmissionStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    done = "done"
    failed = "failed"


class SourceInfo(BaseModel):
    url: str | None = None
    uploadedName: str | None = None


class SearchResult(BaseModel):
    engine: str
    url: str | None = None
    score: float = 0
    publishedAt: str | None = None


class FrameInfo(BaseModel):
    filename: str
    relativePath: str
    timestampSeconds: float
    phash: str


class FrameResult(BaseModel):
    frame: FrameInfo
    results: list[SearchResult] = Field(default_factory=list)
    ranked: list[SearchResult] = Field(default_factory=list)


class SubmissionRecord(BaseModel):
    id: str
    createdAt: str
    updatedAt: str
    status: SubmissionStatus
    source: SourceInfo
    frameCount: int | None = None
    frameResults: list[FrameResult] = Field(default_factory=list)
    earliestKnownMatches: list[SearchResult] = Field(default_factory=list)
    reportUrl: str | None = None
    error: str | None = None

    def to_json_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
