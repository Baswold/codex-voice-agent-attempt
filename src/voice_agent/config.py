from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class AudioConfig:
    wake_word: str = "claude"
    sample_rate: int = 16000
    chunk_ms: int = 30
    vad_sensitivity: float = 0.6


@dataclass
class STTConfig:
    provider: str = "whisper_api"
    api_key: Optional[str] = None
    language: Optional[str] = None


@dataclass
class TTSConfig:
    provider: str = "elevenlabs"
    api_key: Optional[str] = None
    voice_id: Optional[str] = None


@dataclass
class LLMConfig:
    provider: str = "minimax"
    api_key: Optional[str] = None
    model: str = "abab5.5-chat"
    max_tokens: int = 512


@dataclass
class ToolConfig:
    allow_risky: bool = True
    default_timeout: int = 180
    max_output_chars: int = 4000


@dataclass
class SessionConfig:
    storage_path: Path = Path("data/sessions.jsonl")


@dataclass
class VADConfig:
    threshold: int = 500
    speech_frames: int = 3
    silence_frames: int = 5


@dataclass
class WakeConfig:
    enabled: bool = True
    threshold: int = 1200
    consecutive: int = 5


@dataclass
class IdleConfig:
    ask_after_seconds: int = 120
    suspend_after_seconds: int = 600
    idle_prompt: str = "Are you still there?"
    suspend_prompt: str = "Going idle. Say the wake word to resume."


@dataclass
class AgentConfig:
    audio: AudioConfig
    stt: STTConfig
    tts: TTSConfig
    llm: LLMConfig
    tools: ToolConfig
    sessions: SessionConfig
    idle: IdleConfig
    vad: VADConfig
    wake: WakeConfig

    @classmethod
    def from_env(cls) -> "AgentConfig":
        audio = AudioConfig(
            wake_word=os.getenv("VA_WAKE_WORD", AudioConfig.wake_word),
            sample_rate=int(os.getenv("VA_SAMPLE_RATE", AudioConfig.sample_rate)),
            chunk_ms=int(os.getenv("VA_CHUNK_MS", AudioConfig.chunk_ms)),
            vad_sensitivity=float(os.getenv("VA_VAD_SENSITIVITY", AudioConfig.vad_sensitivity)),
        )

        stt = STTConfig(
            provider=os.getenv("VA_STT_PROVIDER", STTConfig.provider),
            api_key=os.getenv("VA_STT_API_KEY"),
            language=os.getenv("VA_STT_LANGUAGE"),
        )

        tts = TTSConfig(
            provider=os.getenv("VA_TTS_PROVIDER", TTSConfig.provider),
            api_key=os.getenv("VA_TTS_API_KEY"),
            voice_id=os.getenv("VA_TTS_VOICE_ID"),
        )

        llm = LLMConfig(
            provider=os.getenv("VA_LLM_PROVIDER", LLMConfig.provider),
            api_key=os.getenv("VA_LLM_API_KEY"),
            model=os.getenv("VA_LLM_MODEL", LLMConfig.model),
            max_tokens=int(os.getenv("VA_LLM_MAX_TOKENS", LLMConfig.max_tokens)),
        )

        tools = ToolConfig(
            allow_risky=os.getenv("VA_ALLOW_RISKY", str(ToolConfig.allow_risky)).lower() == "true",
            default_timeout=int(os.getenv("VA_TOOL_TIMEOUT", ToolConfig.default_timeout)),
            max_output_chars=int(os.getenv("VA_TOOL_MAX_OUTPUT", ToolConfig.max_output_chars)),
        )

        sessions = SessionConfig(
            storage_path=Path(os.getenv("VA_SESSION_PATH", str(SessionConfig.storage_path))),
        )

        idle = IdleConfig(
            ask_after_seconds=int(os.getenv("VA_IDLE_ASK_AFTER", IdleConfig.ask_after_seconds)),
            suspend_after_seconds=int(os.getenv("VA_IDLE_SUSPEND_AFTER", IdleConfig.suspend_after_seconds)),
            idle_prompt=os.getenv("VA_IDLE_PROMPT", IdleConfig.idle_prompt),
            suspend_prompt=os.getenv("VA_IDLE_SUSPEND_PROMPT", IdleConfig.suspend_prompt),
        )

        vad = VADConfig(
            threshold=int(os.getenv("VA_VAD_THRESHOLD", VADConfig.threshold)),
            speech_frames=int(os.getenv("VA_VAD_SPEECH_FRAMES", VADConfig.speech_frames)),
            silence_frames=int(os.getenv("VA_VAD_SILENCE_FRAMES", VADConfig.silence_frames)),
        )

        wake = WakeConfig(
            enabled=os.getenv("VA_WAKE_ENABLED", str(WakeConfig.enabled)).lower() == "true",
            threshold=int(os.getenv("VA_WAKE_THRESHOLD", WakeConfig.threshold)),
            consecutive=int(os.getenv("VA_WAKE_CONSECUTIVE", WakeConfig.consecutive)),
        )

        sessions.storage_path.parent.mkdir(parents=True, exist_ok=True)

        return cls(
            audio=audio,
            stt=stt,
            tts=tts,
            llm=llm,
            tools=tools,
            sessions=sessions,
            idle=idle,
            vad=vad,
            wake=wake,
        )
