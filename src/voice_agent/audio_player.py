from __future__ import annotations

import asyncio
import time
from collections import deque
from typing import Optional


class BufferedAudioPlayer:
    """Audio player with buffering to prevent choppy playback.

    Buffers audio chunks and plays them at a steady rate to avoid
    the choppy playback that occurs when streaming TTS audio.
    """

    def __init__(
        self,
        sample_rate: int = 24000,
        min_buffer_ms: int = 100,
        max_buffer_ms: int = 500,
        playback_callback=None,
    ) -> None:
        """Initialize the buffered audio player.

        Args:
            sample_rate: Audio sample rate in Hz
            min_buffer_ms: Minimum buffer time before starting playback
            max_buffer_ms: Maximum buffer time to prevent excessive latency
            playback_callback: Function to call with audio chunks (bytes) for actual playback
        """
        self.sample_rate = sample_rate
        self.min_buffer_ms = min_buffer_ms
        self.max_buffer_ms = max_buffer_ms
        self.playback_callback = playback_callback

        self._queue: deque[bytes] = deque()
        self._playing = False
        self._task: Optional[asyncio.Task[None]] = None
        self._lock = asyncio.Lock()
        self._cancelled = False

    async def start_stream(self) -> None:
        """Start a new audio stream."""
        await self.stop()
        async with self._lock:
            self._queue.clear()
            self._playing = True
            self._cancelled = False
            self._task = asyncio.create_task(self._playback_loop())

    async def add_chunk(self, audio_chunk: bytes) -> None:
        """Add an audio chunk to the playback queue."""
        if self._playing and not self._cancelled:
            async with self._lock:
                self._queue.append(audio_chunk)

    async def finish_stream(self) -> None:
        """Signal that no more chunks will be added and wait for playback to complete."""
        # Wait for queue to drain
        while self._playing and len(self._queue) > 0 and not self._cancelled:
            await asyncio.sleep(0.01)
        await self.stop()

    async def stop(self) -> None:
        """Stop playback immediately and clear the queue."""
        self._cancelled = True
        async with self._lock:
            self._playing = False
            self._queue.clear()

        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None

    def is_playing(self) -> bool:
        """Check if audio is currently playing."""
        return self._playing and self._task is not None and not self._task.done()

    async def _playback_loop(self) -> None:
        """Main playback loop that handles buffering and pacing."""
        # Wait for minimum buffer
        buffer_start = time.perf_counter()
        while self._playing and not self._cancelled:
            buffer_duration = (time.perf_counter() - buffer_start) * 1000
            if buffer_duration >= self.min_buffer_ms or len(self._queue) > 5:
                break
            await asyncio.sleep(0.01)

        # Play buffered chunks
        while self._playing and not self._cancelled:
            async with self._lock:
                if not self._queue:
                    # Queue is empty, check if we should stop
                    if not self._playing:
                        break
                    # Otherwise wait for more data
                    await asyncio.sleep(0.01)
                    continue

                chunk = self._queue.popleft()

            # Play the chunk
            if self.playback_callback and chunk:
                try:
                    result = self.playback_callback(chunk)
                    if asyncio.iscoroutine(result) or asyncio.isfuture(result):
                        await result
                except Exception:
                    # Ignore playback errors to prevent crashes
                    pass

            # Small delay to prevent CPU spinning
            await asyncio.sleep(0.001)

        self._playing = False
