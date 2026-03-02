from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)


class InMemoryJobQueue:
    """Simple bounded queue with worker tasks.

    Good for local/dev. For production use a durable external queue (see docs/job_queue_strategy.md).
    """

    def __init__(self, workers: int = 2, maxsize: int = 100):
        self._queue: asyncio.Queue[tuple[str, Callable[[], Awaitable[None]]]] = asyncio.Queue(maxsize=maxsize)
        self._workers = workers
        self._tasks: list[asyncio.Task[None]] = []
        self._started = False

    async def start(self) -> None:
        if self._started:
            return
        self._started = True
        for i in range(self._workers):
            self._tasks.append(asyncio.create_task(self._worker(i), name=f"job-queue-worker-{i}"))

    async def stop(self) -> None:
        if not self._started:
            return
        self._started = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    async def enqueue(self, job_id: str, fn: Callable[[], Awaitable[None]]) -> None:
        await self._queue.put((job_id, fn))

    async def _worker(self, worker_id: int) -> None:
        while True:
            job_id, fn = await self._queue.get()
            try:
                await fn()
            except Exception:
                logger.exception("Job failed in worker %s for id=%s", worker_id, job_id)
            finally:
                self._queue.task_done()
