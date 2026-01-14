from __future__ import annotations

from .config import LLMConfig, STTConfig, TTSConfig
from .llm import LLMClient, MinimaxClient, MinimaxStubClient, OpenRouterClient
from .stt import EchoSTT, ElevenLabsSTT, STTClient, WhisperAPIClient
from .tts import DummyTTS, ElevenLabsTTS, OpenAITTS, TTSClient


def build_llm(cfg: LLMConfig) -> LLMClient:
    if cfg.provider == "openrouter" and cfg.api_key:
        return OpenRouterClient(api_key=cfg.api_key, model=cfg.model, max_tokens=cfg.max_tokens)
    if cfg.api_key:
        return MinimaxClient(api_key=cfg.api_key, model=cfg.model, max_tokens=cfg.max_tokens)
    return MinimaxStubClient(model=cfg.model, max_tokens=cfg.max_tokens)


def build_stt(cfg: STTConfig) -> STTClient:
    if cfg.provider == "whisper_api" and cfg.api_key:
        return WhisperAPIClient(api_key=cfg.api_key, language=cfg.language)
    if cfg.provider == "elevenlabs" and cfg.api_key:
        return ElevenLabsSTT(api_key=cfg.api_key)
    return EchoSTT()


def build_tts(cfg: TTSConfig) -> TTSClient:
    if cfg.provider == "elevenlabs" and cfg.api_key and cfg.voice_id:
        return ElevenLabsTTS(api_key=cfg.api_key, voice_id=cfg.voice_id)
    if cfg.provider == "openai" and cfg.api_key:
        # Use voice_id if provided, otherwise default to "alloy"
        voice = cfg.voice_id if cfg.voice_id else "alloy"
        return OpenAITTS(api_key=cfg.api_key, voice=voice)
    return DummyTTS()
