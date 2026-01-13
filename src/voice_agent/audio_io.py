from __future__ import annotations

import asyncio
import time
from typing import AsyncIterator, Optional

from .audio import AudioFrame, AudioFrontend

try:
    import sounddevice as sd
except ImportError:  # pragma: no cover - optional dependency
    sd = None


class MicUnavailable(Exception):
    pass


class SoundDeviceMic:
    def __init__(self, sample_rate: int, chunk_ms: int, channels: int = 1, dtype: str = "int16") -> None:
        if sd is None:
            raise MicUnavailable("sounddevice not installed; install with 'pip install sounddevice'")
        self.sample_rate = sample_rate
        self.chunk_ms = chunk_ms
        self.channels = channels
        self.dtype = dtype
        self.blocksize = int(sample_rate * chunk_ms / 1000)
        self._queue: asyncio.Queue[Optional[bytes]] = asyncio.Queue()
        self._stream: Optional[sd.RawInputStream] = None
        self._running = False

    async def __aenter__(self) -> "SoundDeviceMic":
        self._start_stream()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.stop()

    def _callback(self, indata, frames, time_info, status) -> None:  # type: ignore[override]
        del frames, time_info
        if status:
            # Drop status warnings for now
            pass
        if not self._running:
            return
        try:
            self._queue.put_nowait(bytes(indata))
        except asyncio.QueueFull:
            pass

    def _start_stream(self) -> None:
        if self._stream is not None:
            return
        self._running = True
        self._stream = sd.RawInputStream(
            samplerate=self.sample_rate,
            blocksize=self.blocksize,
            channels=self.channels,
            dtype=self.dtype,
            callback=self._callback,
        )
        self._stream.start()

    async def stop(self) -> None:
        self._running = False
        if self._stream is not None:
            try:
                self._stream.stop()
            finally:
                self._stream.close()
        self._stream = None
        await self._queue.put(None)

    async def frames(self) -> asyncio.Queue:
        return self._queue

    async def forward_to(self, frontend: AudioFrontend) -> None:
        while True:
            data = await self._queue.get()
            if data is None:
                await frontend.end_utterance()
                break
            await frontend.enqueue_frame(data)

    async def stream_frames(self) -> AsyncIterator[AudioFrame]:
        self._start_stream()
        while True:
            data = await self._queue.get()
            if data is None:
                break
            yield AudioFrame(timestamp=time.time(), data=data)


class SoundDeviceSpeaker:
    def __init__(self, sample_rate: int, channels: int = 1, dtype: str = "int16") -> None:
        if sd is None:
            raise MicUnavailable("sounddevice not installed; install with 'pip install sounddevice'")
        self.sample_rate = sample_rate
        self.channels = channels
        self.dtype = dtype
        self._stream: Optional[sd.RawOutputStream] = None

    def _ensure_stream(self) -> None:
        if self._stream is None:
            self._stream = sd.RawOutputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=self.dtype,
                blocksize=0,
            )
            self._stream.start()

    async def play_chunk(self, data: bytes, is_final: bool = False) -> None:
        self._ensure_stream()
        assert self._stream is not None
        self._stream.write(data)
        if is_final:
            await asyncio.sleep(0)

    async def close(self) -> None:
        if self._stream is not None:
            try:
                self._stream.stop()
            finally:
                self._stream.close()
        self._stream = None
