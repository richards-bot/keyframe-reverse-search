from dataclasses import dataclass
from pathlib import Path

from app.services.dedupe import dedupe_frames


class FakeHash:
    def __init__(self, value: int):
        self.value = value

    def __sub__(self, other: "FakeHash") -> int:
        return abs(self.value - other.value)


@dataclass
class DummyFrame:
    path: Path
    timestamp_seconds: float
    phash: FakeHash


def test_dedupe_frames_removes_near_duplicates():
    frames = [
        DummyFrame(Path("a.jpg"), 0.0, FakeHash(10)),
        DummyFrame(Path("b.jpg"), 1.0, FakeHash(12)),
        DummyFrame(Path("c.jpg"), 2.0, FakeHash(40)),
    ]
    out = dedupe_frames(frames, distance_threshold=3)
    assert [f.path.name for f in out] == ["a.jpg", "c.jpg"]
