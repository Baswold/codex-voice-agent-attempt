from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import AsyncIterator, Optional

import httpx


@dataclass
class SpeechChunk:
    audio: bytes
    is_final: bool = False


class TTSClient:
    async def synthesize(self, text: str) -> bytes:
        raise NotImplementedError

    async def stream_synthesize(self, text: str) -> AsyncIterator[SpeechChunk]:
        audio = await self.synthesize(text)
        yield SpeechChunk(audio=audio, is_final=True)


class DummyTTS(TTSClient):
    async def synthesize(self, text: str) -> bytes:
        await asyncio.sleep(0)
        return text.encode()


class ElevenLabsTTS(TTSClient):
    def __init__(self, api_key: str, voice_id: str, model: str = "eleven_multilingual_v2") -> None:
        self.api_key = api_key
        self.voice_id = voice_id
        self.model = model

    async def synthesize(self, text: str) -> bytes:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}",
                headers={
                    "xi-api-key": self.api_key,
                    "accept": "audio/mpeg",
                    "Content-Type": "application/json",
                },
                json={"text": text, "model_id": self.model},
            )
            resp.raise_for_status()
            return resp.content

    async def stream_synthesize(self, text: str) -> AsyncIterator[SpeechChunk]:
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}/stream",
                headers={
                    "xi-api-key": self.api_key,
                    "accept": "audio/mpeg",
                    "Content-Type": "application/json",
                },
                json={"text": text, "model_id": self.model},
            ) as resp:
                resp.raise_for_status()
                async for chunk in resp.aiter_bytes():
                    yield SpeechChunk(audio=chunk, is_final=False)
        yield SpeechChunk(audio=b"", is_final=True)


class OpenAITTS(TTSClient):
    def __init__(self, api_key: str, model: str = "tts-1", voice: str = "alloy") -> None:
        self.api_key = api_key
        self.model = model
        self.voice = voice

    async def synthesize(self, text: str) -> bytes:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://api.openai.com/v1/audio/speech",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={"model": self.model, "voice": self.voice, "input": text},
            )
            resp.raise_for_status()
            return resp.content

    async def stream_synthesize(self, text: str) -> AsyncIterator[SpeechChunk]:
        # OpenAI TTS doesn't support streaming yet, so we'll get the full audio and yield it
        audio = await self.synthesize(text)
        # Split into chunks for smoother playback
        chunk_size = 4096
        for i in range(0, len(audio), chunk_size):
            chunk = audio[i : i + chunk_size]
            yield SpeechChunk(audio=chunk, is_final=(i + chunk_size >= len(audio)))
        yield SpeechChunk(audio=b"", is_final=True)
