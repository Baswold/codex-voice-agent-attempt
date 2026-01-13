from __future__ import annotations

import asyncio
from typing import AsyncIterator, Callable, Optional

from .audio import AudioFrame, AudioFrontend
from .audio_player import BufferedAudioPlayer
from .dialog import DialogManager, DialogTurn
from .idle import IdleManager
from .stt import STTClient
from .tts import TTSClient
from .vad import EnergyVAD
from .wake import WakeDetector

PlaybackHook = Callable[[bytes, bool], asyncio.Future | None]


class TTSPlayer:
    def __init__(self, tts: TTSClient, playback_hook: Optional[PlaybackHook] = None, sample_rate: int = 24000) -> None:
        self.tts = tts
        self.playback_hook = playback_hook
        self._task: Optional[asyncio.Task[None]] = None
        self._buffered_player = BufferedAudioPlayer(
            sample_rate=sample_rate,
            min_buffer_ms=100,
            max_buffer_ms=500,
            playback_callback=lambda chunk: self._play_chunk(chunk) if self.playback_hook else None,
        )

    def _play_chunk(self, chunk: bytes) -> Optional[asyncio.Future]:
        """Internal method to play a single audio chunk."""
        if self.playback_hook:
            maybe_future = self.playback_hook(chunk, False)
            if asyncio.isfuture(maybe_future) or asyncio.iscoroutine(maybe_future):
                return maybe_future
        return None

    def is_playing(self) -> bool:
        return self._task is not None and not self._task.done()

    async def stop(self) -> None:
        await self._buffered_player.stop()
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None

    async def play(self, text: str) -> None:
        await self.stop()
        self._task = asyncio.create_task(self._stream(text))

    async def _stream(self, text: str) -> None:
        await self._buffered_player.start_stream()
        try:
            async for chunk in self.tts.stream_synthesize(text):
                if chunk.audio:
                    await self._buffered_player.add_chunk(chunk.audio)
                if chunk.is_final:
                    break
            await self._buffered_player.finish_stream()
        except asyncio.CancelledError:
            await self._buffered_player.stop()
            raise
        except Exception:
            await self._buffered_player.stop()
            raise


class VoiceLoop:
    def __init__(
        self,
        audio: AudioFrontend,
        stt: STTClient,
        dialog: DialogManager,
        tts_player: TTSPlayer,
        idle: Optional[IdleManager] = None,
        background_poll_interval: float = 0.5,
    ) -> None:
        self.audio = audio
        self.stt = stt
        self.dialog = dialog
        self.tts_player = tts_player
        self.idle = idle
        self.background_poll_interval = background_poll_interval
        self._background_task: Optional[asyncio.Task[None]] = None
        self._running = False

    async def start(self) -> None:
        self._running = True
        await self.audio.start()
        self._background_task = asyncio.create_task(self._background_loop())
        if self.idle:
            await self.idle.start()

    async def stop(self) -> None:
        self._running = False
        await self.audio.stop()
        if self._background_task:
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass
        await self.tts_player.stop()
        if self.idle:
            await self.idle.stop()

    async def run_once(self, frames: AsyncIterator[AudioFrame]) -> Optional[DialogTurn]:
        transcript = await self._collect_transcript(frames)
        if not transcript:
            return None
        await self.tts_player.stop()  # barge-in: stop current playback
        turn = await self.dialog.handle_user_text(transcript)
        await self.tts_player.play(turn.response_text)
        if self.idle:
            self.idle.touch()
        return turn

    async def run_stream(self, frames: AsyncIterator[AudioFrame], vad: EnergyVAD, wake: Optional[WakeDetector] = None) -> None:
        current_frames: list[AudioFrame] = []
        listening = wake is None
        vad.reset()
        if wake:
            wake.reset()

        async for frame in frames:
            if wake and not listening:
                if await wake.process(frame):
                    listening = True
                    vad.reset()
                continue

            if vad.is_speech(frame):
                current_frames.append(frame)
                continue

            if current_frames:
                await self._handle_utterance(current_frames)
                current_frames = []
                listening = wake is None
                if wake:
                    wake.reset()
                vad.reset()

        if current_frames:
            await self._handle_utterance(current_frames)

    async def _collect_transcript(self, frames: AsyncIterator[AudioFrame]) -> str:
        text = ""
        async for chunk in self.stt.stream_transcribe(frames):
            if chunk.text:
                text = chunk.text if chunk.final else chunk.text
            if chunk.final:
                break
        return text.strip()

    async def _handle_utterance(self, frames: list[AudioFrame]) -> None:
        async def gen() -> AsyncIterator[AudioFrame]:
            for frame in frames:
                yield frame

        await self.run_once(gen())

    async def _background_loop(self) -> None:
        while self._running:
            turns = await self.dialog.poll_background()
            for turn in turns:
                await self.tts_player.play(turn.response_text)
                if self.idle:
                    self.idle.touch()
            await asyncio.sleep(self.background_poll_interval)
