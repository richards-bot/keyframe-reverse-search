from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

import imagehash
from PIL import Image


@dataclass
class Frame:
    path: Path
    timestamp_seconds: float
    phash: imagehash.ImageHash


async def extract_keyframes(video_path: Path, output_dir: Path) -> list[Frame]:
    output_dir.mkdir(parents=True, exist_ok=True)

    pattern = output_dir / "frame_%05d.jpg"
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-i",
        str(video_path),
        "-vf",
        "select='gt(scene,0.3)',showinfo",
        "-vsync",
        "vfr",
        str(pattern),
        "-y",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg keyframe extraction failed: {stderr.decode('utf-8', errors='ignore')}")

    # derive timestamps by probing each frame from ffmpeg logs is brittle; fallback to index spacing.
    # For MVP we include approximate second index.
    frames = sorted(output_dir.glob("frame_*.jpg"))
    result: list[Frame] = []
    for i, f in enumerate(frames):
        with Image.open(f) as img:
            ph = imagehash.phash(img)
        result.append(Frame(path=f, timestamp_seconds=float(i), phash=ph))
    return result
