from __future__ import annotations

from app.services.keyframes import Frame


def dedupe_frames(frames: list[Frame], distance_threshold: int = 8) -> list[Frame]:
    deduped: list[Frame] = []
    for frame in frames:
        is_dup = any((frame.phash - existing.phash) <= distance_threshold for existing in deduped)
        if not is_dup:
            deduped.append(frame)
    return deduped
