# Voice Agent for Raspberry Pi Desk Speaker

A production-ready voice agent system with pluggable STT/TTS/LLM adapters, intelligent tool execution, sub-agent delegation, and session management. Designed for Raspberry Pi 4 deployment with macOS development support.

## Features

### Core Capabilities
- **Multi-Provider Support**: Pluggable STT/TTS/LLM with real provider implementations
  - STT: Whisper API (OpenAI), ElevenLabs STT ✅ NEW
  - TTS: ElevenLabs with buffered playback for smooth audio ✅ IMPROVED
  - LLM: Minimax with streaming support ✅ IMPROVED
- **Intelligent Tool Execution**: LLM-driven tool execution with silent background operation ✅ NEW
- **Sub-Agent System**: Delegate complex tasks to specialized background agents ✅ NEW
- **Wake Word Detection**: Trigger conversations with custom wake words
- **Voice Activity Detection (VAD)**: Automatic speech detection and segmentation
- **Barge-In Support**: Interrupt agent speech naturally
- **Session Management**: Persistent conversation history and summaries
- **Background Task Handling**: Non-blocking command execution with result polling

## Architecture

### Voice Loop
The voice loop handles the full conversation flow:
1. **Audio Capture**: Wake word detection → Voice Activity Detection → Audio frames
2. **Speech-to-Text**: Convert audio to text using STT provider
3. **Dialog Processing**: Parse user intent, execute tools, get LLM response
4. **Text-to-Speech**: Stream response audio with buffered playback
5. **Background Polling**: Monitor long-running tasks and sub-agents

### Smart Tool Execution
The LLM can request tools using XML-style tags in responses:
```
<tool type="shell">ls -la</tool>
<tool type="web">https://example.com</tool>
<tool type="ssh" host="192.168.1.1">uptime</tool>
```

Tools execute silently in the background while the agent continues speaking.

### Sub-Agent System
Spawn specialized agents for complex tasks:
- **Coding**: Write, debug, analyze code
- **Research**: Gather and synthesize information
- **System**: System administration and operations
- **Network**: Remote system management
- **Hardware**: USB/serial device interaction

### Example Usage
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

## Provider Configuration

### STT (Speech-to-Text)
- **Whisper API** (OpenAI): `VA_STT_PROVIDER=whisper_api` with `VA_STT_API_KEY`
  - Cost: ~$0.006/min
  - Good accuracy for development
- **ElevenLabs STT**: `VA_STT_PROVIDER=elevenlabs` with `VA_STT_API_KEY`
  - Free tier available (limited usage)
  - Good for testing
- Falls back to echo stub if no API key provided

### TTS (Text-to-Speech)
- **ElevenLabs**: `VA_TTS_PROVIDER=elevenlabs` with `VA_TTS_API_KEY` and `VA_TTS_VOICE_ID`
  - Streams with buffered playback for smooth audio
  - Free tier available
  - Natural, high-quality voices
- Falls back to dummy TTS if no API key provided

### LLM (Language Model)
- **Minimax**: `VA_LLM_PROVIDER=minimax` with `VA_LLM_API_KEY`
  - Streaming enabled by default for better responsiveness
  - Cost-effective compared to Claude/GPT-4
  - Good reasoning capabilities
- Falls back to stub if no API key provided

### Tool Extras
- SSH: `pip install -e .[ssh]` enables remote command execution
- Serial/USB: `pip install -e .[serial]` enables Arduino and device communication
- Enhanced VAD: `pip install -e .[vad]` for webrtcvad support

## New Features in Detail

### 1. ElevenLabs STT Support
Added ElevenLabs as a speech-to-text provider alongside Whisper API. Supports the free tier for testing.

```bash
export VA_STT_PROVIDER=elevenlabs
export VA_STT_API_KEY=your_elevenlabs_api_key
```

### 2. Buffered Audio Playback
TTS audio is now buffered to prevent choppy playback. The `BufferedAudioPlayer` accumulates chunks before playback and manages pacing for smooth output.

### 3. Silent Tool Execution
The LLM can now request tools to be executed in the background. Tools run silently without blocking conversation flow:

```python
# The LLM responds naturally while executing tools
"I'll check the current directory for you. <tool type="shell">ls -la</tool> Give me just a moment."
```

### 4. Sub-Agent System
Delegate complex tasks to specialized sub-agents that work independently:

```python
# Spawn a coding sub-agent
agent_id = app.spawn_sub_agent(
    task="Analyze the Python files in /src and identify potential bugs",
    specialty="coding"
)

# Poll for results
results = await app.poll_sub_agents()
for result in results:
    print(f"Agent {result.agent_id}: {result.result_text}")
```

Available specialties: `coding`, `research`, `system`, `network`, `hardware`, `general`

### 5. Minimax Streaming
Minimax LLM responses now stream in real-time for better responsiveness and lower latency.

## Production Deployment

### Cost Estimates
For detailed pricing comparison, see [docs/STT_TTS_PRICING.md](docs/STT_TTS_PRICING.md)

**Budget Option (~$1.50/hour):**
- STT: AssemblyAI ($0.15/hr)
- TTS: Speechmatics (~$1.10/hr)
- LLM: Minimax

**Balanced Option (~$2.50/hour):**
- STT: Deepgram Nova-3 ($0.26/hr)
- TTS: Cartesia (~$2/hr)
- LLM: Minimax

**Current Testing Setup (Free tier):**
- STT: ElevenLabs free tier
- TTS: ElevenLabs free tier
- LLM: Minimax

### Raspberry Pi 4 Deployment
The agent is designed to run on Raspberry Pi 4 (4GB RAM):
- Hosted STT/TTS recommended (local models are slow on RPi4)
- Minimax LLM for cost-effectiveness
- Wake word detection runs locally
- Tool execution via SSH, serial/USB, shell commands
- Sub-agents handle complex tasks without blocking main conversation

### Local Alternatives (for offline operation)
- **STT**: Vosk (lightweight), Whisper.cpp (accurate but slower)
- **TTS**: Piper TTS (fast, lightweight), Coqui TTS (higher quality)
- Trade-off: Lower cost but reduced quality and higher latency

## Next Steps

### Completed ✅
- ✅ ElevenLabs STT integration
- ✅ Buffered audio playback for smooth TTS
- ✅ Silent tool execution with LLM control
- ✅ Sub-agent system for task delegation
- ✅ Minimax streaming for responsiveness

### Recommended Improvements
- Add Deepgram/AssemblyAI STT for production
- Add Cartesia TTS for ultra-low latency
- Implement conversation memory with summarization
- Add voice cloning for personalized responses
- Build web dashboard for agent monitoring
- Add more sub-agent specialties (data analysis, code generation, etc.)
- Implement proper error recovery and retry logic
