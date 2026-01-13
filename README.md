# Voice Agent Scaffold

Scaffold for a desk-speaker voice agent with pluggable STT/TTS/LLM adapters, a tool runner, and session storage. It targets macOS for development with Raspberry Pi deployment later.

## What Exists
- Config loader for audio, STT, TTS, LLM, tools, and session storage.
- STT/TTS/LLM stubs to be swapped for real providers.
- Wired providers: Whisper API STT (OpenAI), ElevenLabs TTS, Minimax LLM (falls back to stubs if keys missing).
- Tool runner with foreground and background command execution plus completion polling.
- Dialog manager that routes user text to tools or LLM, summarizes turns, and logs to a session store.
- CLI prototype in `voice_agent.app` for quick interaction.

## Voice Loop Scaffold (audio integration)
- `voice_agent.voice_loop.VoiceLoop` glues `AudioFrontend` → STT → dialog → TTS playback with barge-in.
- `providers.build_stt/build_tts/build_llm` create swappable adapters (stubs by default).
- `TTSPlayer` supports canceling playback when new speech arrives.
- Optional `IdleManager` can prompt after inactivity and auto-suspend.
- Example wiring (replace stubs with real engines):
```python
import asyncio
from voice_agent.audio import AudioFrontend
from voice_agent.providers import build_stt, build_tts, build_llm
from voice_agent.voice_loop import TTSPlayer, VoiceLoop
from voice_agent.app import VoiceAgentApp
from voice_agent.config import AgentConfig

async def main():
    cfg = AgentConfig.from_env()
    app = VoiceAgentApp(cfg)
    audio = AudioFrontend(cfg.audio.wake_word, cfg.audio.sample_rate, cfg.audio.chunk_ms)
    loop = VoiceLoop(audio, app.stt_client, app.dialog, TTSPlayer(app.tts_client))
    await loop.start()
    # Feed audio.enqueue_frame(...) with mic frames, then:
    # turn = await loop.run_once(audio.frames())
    # print(turn.response_text)
    await loop.stop()

asyncio.run(main())
```

## Quick Start (text-only loop)
```bash
pip install -e .
python -m voice_agent.app
```
- `run <command>` executes a foreground shell command.
- `runbg <command>` starts a background command; completions are polled each loop.
- `web <url>` fetches a URL.
- `ssh <host> <cmd>` runs a remote command (asyncssh extra).
- `serial <port> <payload>` writes/reads over serial (pyserial extra).

## Mic Demo (optional audio deps)
- Install with audio extras: `pip install -e .[audio]`
- Run mic loop: `python -m voice_agent.voice_cli --listen-seconds 5`
- Press Enter to capture a short window, `q` to quit. Playback uses the TTS stub (replace with real TTS for audio).
- Continuous mode with VAD/wake: `python -m voice_agent.voice_cli --auto`

## Configuration
Set env vars as needed:
- `VA_WAKE_WORD`, `VA_SAMPLE_RATE`, `VA_CHUNK_MS`
- `VA_STT_PROVIDER`, `VA_STT_API_KEY`, `VA_STT_LANGUAGE`
- `VA_TTS_PROVIDER`, `VA_TTS_API_KEY`, `VA_TTS_VOICE_ID`
- `VA_LLM_PROVIDER`, `VA_LLM_API_KEY`, `VA_LLM_MODEL`, `VA_LLM_MAX_TOKENS`
- `VA_ALLOW_RISKY`, `VA_TOOL_TIMEOUT`, `VA_TOOL_MAX_OUTPUT`
- `VA_SESSION_PATH`
- `VA_IDLE_ASK_AFTER`, `VA_IDLE_SUSPEND_AFTER`, `VA_IDLE_PROMPT`, `VA_IDLE_SUSPEND_PROMPT`
- `VA_VAD_THRESHOLD`, `VA_VAD_SPEECH_FRAMES`, `VA_VAD_SILENCE_FRAMES`
- `VA_WAKE_ENABLED`, `VA_WAKE_THRESHOLD`, `VA_WAKE_CONSECUTIVE`

Provider notes:
- STT: `VA_STT_PROVIDER=whisper_api` with `VA_STT_API_KEY` uses OpenAI Whisper API; otherwise falls back to echo stub.
- TTS: `VA_TTS_PROVIDER=elevenlabs` with `VA_TTS_API_KEY` and `VA_TTS_VOICE_ID` streams ElevenLabs; otherwise dummy.
- LLM: `VA_LLM_PROVIDER=minimax` with `VA_LLM_API_KEY` uses Minimax API; otherwise stub.
- Extras: `pip install -e .[ssh]` for SSH, `.[serial]` for USB/serial, `.[vad]` for webrtcvad if you swap in a stronger VAD.

## Next Integration Steps
- Replace STT/TTS stubs with hosted or local engines (e.g., Whisper API, ElevenLabs, Piper).
- Wire wake-word/VAD capture into `AudioFrontend` and stream into the STT adapter.
- Swap `MinimaxStubClient` for the real Minimax client with streaming responses.
- Connect Pypecat or similar for low-chop TTS playback with barge-in.
