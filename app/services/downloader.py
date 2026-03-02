from __future__ import annotations

import asyncio
from pathlib import Path


async def download_video(url: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    proc = await asyncio.create_subprocess_exec(
        "yt-dlp",
        "-f",
        "mp4/best",
        "-o",
        str(output_path),
        url,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"yt-dlp failed: {stderr.decode('utf-8', errors='ignore')}")
