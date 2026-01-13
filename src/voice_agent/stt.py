from __future__ import annotations

import asyncio
import io
import wave
from dataclasses import dataclass
from typing import AsyncIterator, List, Optional

import httpx

from .audio import AudioFrame


@dataclass
class TranscriptChunk:
    text: str
    final: bool = False


class STTClient:
    async def stream_transcribe(self, frames: AsyncIterator[AudioFrame]) -> AsyncIterator[TranscriptChunk]:
        raise NotImplementedError

    async def transcribe_text(self, text: str) -> TranscriptChunk:
        await asyncio.sleep(0)
        return TranscriptChunk(text=text, final=True)


class EchoSTT(STTClient):
    async def stream_transcribe(self, frames: AsyncIterator[AudioFrame]) -> AsyncIterator[TranscriptChunk]:
        buffer = []
        async for frame in frames:
            buffer.append(frame.data)
            yield TranscriptChunk(text=f"captured {len(buffer)} audio chunks", final=False)
        yield TranscriptChunk(text=f"captured {len(buffer)} audio chunks", final=True)


class WhisperAPIClient(STTClient):
    def __init__(self, api_key: str, model: str = "whisper-1", language: Optional[str] = None, sample_rate: int = 16000) -> None:
        self.api_key = api_key
        self.model = model
        self.language = language
        self.sample_rate = sample_rate

    async def stream_transcribe(self, frames: AsyncIterator[AudioFrame]) -> AsyncIterator[TranscriptChunk]:
        collected: List[bytes] = []
        async for frame in frames:
            collected.append(frame.data)
        if not collected:
            return
        audio_bytes = b"".join(collected)
        wav_bytes = self._pcm_to_wav(audio_bytes)
        text = await self._send(wav_bytes)
        yield TranscriptChunk(text=text, final=True)

    def _pcm_to_wav(self, pcm: bytes) -> bytes:
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(pcm)
        return buffer.getvalue()

    async def _send(self, wav_bytes: bytes) -> str:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        data = {"model": self.model}
        if self.language:
            data["language"] = self.language
        files = {"file": ("audio.wav", wav_bytes, "audio/wav")}
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers=headers,
                data=data,
                files=files,
            )
            resp.raise_for_status()
            payload = resp.json()
            return payload.get("text", "")


class ElevenLabsSTT(STTClient):
    def __init__(self, api_key: str, model: str = "eleven_multilingual_v2", sample_rate: int = 16000) -> None:
        self.api_key = api_key
        self.model = model
        self.sample_rate = sample_rate

    async def stream_transcribe(self, frames: AsyncIterator[AudioFrame]) -> AsyncIterator[TranscriptChunk]:
        collected: List[bytes] = []
        async for frame in frames:
            collected.append(frame.data)
        if not collected:
            return
        audio_bytes = b"".join(collected)
        # ElevenLabs expects audio in supported formats (mp3, wav, etc.)
        wav_bytes = self._pcm_to_wav(audio_bytes)
        text = await self._send(wav_bytes)
        yield TranscriptChunk(text=text, final=True)

    def _pcm_to_wav(self, pcm: bytes) -> bytes:
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(pcm)
        return buffer.getvalue()

    async def _send(self, wav_bytes: bytes) -> str:
        headers = {"xi-api-key": self.api_key}
        files = {"audio": ("audio.wav", wav_bytes, "audio/wav")}
        data = {"model_id": self.model}
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://api.elevenlabs.io/v1/speech-to-text",
                headers=headers,
                data=data,
                files=files,
            )
            resp.raise_for_status()
            payload = resp.json()
            return payload.get("text", "")
