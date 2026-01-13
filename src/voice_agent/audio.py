from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import AsyncIterator, Optional


@dataclass
class AudioFrame:
    timestamp: float
    data: bytes


class AudioFrontend:
    def __init__(self, wake_word: str, sample_rate: int, chunk_ms: int) -> None:
        self.wake_word = wake_word
        self.sample_rate = sample_rate
        self.chunk_ms = chunk_ms
        self._frames: asyncio.Queue[Optional[AudioFrame]] = asyncio.Queue()
        self._running = False
        self._stopped = asyncio.Event()

    async def start(self) -> None:
        self._running = True
        self._stopped.clear()

    async def stop(self) -> None:
        self._running = False
        self._stopped.set()
        await self._frames.put(None)

    async def enqueue_frame(self, data: Optional[bytes]) -> None:
        if not self._running:
            return
        if data is None:
            await self._frames.put(None)
            return
        frame = AudioFrame(timestamp=time.time(), data=data)
        await self._frames.put(frame)

    async def end_utterance(self) -> None:
        if not self._running:
            return
        await self._frames.put(None)

    async def frames(self) -> AsyncIterator[AudioFrame]:
        while True:
            frame = await self._frames.get()
            if frame is None:
                break
            yield frame

    async def wait_stopped(self) -> None:
        await self._stopped.wait()
