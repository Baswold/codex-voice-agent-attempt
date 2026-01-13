## Voice Agent Goals (Desk Speaker)

- Always-on wake word ("Hey Claude/Claude") with <500ms detect latency.
- Natural, interruptible speech; short latency TTS playback and smooth barge-in.
- Cheap STT/TTS (default cloud) with optional local fallback sized for Pi 4 (4GB).
- Primary tools: terminal execution, web fetch, USB/serial (Arduino, etc.); SSH supported.
- Background tasks with quiet execution; notify on completion and resume conversation.
- Conversational memory with post-turn summaries saved per session.
- Idle handling: ask if user is present after long wait, auto-suspend if no reply.

## Constraints & Defaults

- Prototype on macOS; target deployment Raspberry Pi 4 (4GB).
- Use inexpensive hosted STT/TTS for now (e.g., Whisper API for STT, ElevenLabs for TTS).
- Keep LLM pluggable; default to Minimax, allow Claude/OpenAI swap.
- Trust-first execution (no prompts for permission); add safety layer later.
- Wake word/VAD local where possible; fall back to cloud if needed.

## High-Level Pipeline

1) Mic → Wake-word + VAD (local) → streaming audio frames.
2) Frames → STT stream → partial/final transcripts.
3) Transcript → Dialog manager + LLM → tool plans + replies.
4) Tool runner executes commands (silent) and streams status; buffers stdout/stderr.
5) LLM post-processes tool output → concise response.
6) TTS synth → audio smoothing → playback with barge-in support.
7) After each conversation: LLM summary → persisted (e.g., SQLite/JSONL).

## Components

- **Audio Frontend**: local wake-word (Porcupine/Snowboy alt), VAD (Silero/WebRTC), circular buffer, gain control.
- **STT**: default cloud (Whisper/Deepgram-like API); optional local (Faster-Whisper small/int8) if RAM allows.
- **TTS**: ElevenLabs default; local fallback (Piper) for offline/cheap mode.
- **LLM Adapter**: swappable client with streaming; Minimax primary, Claude/OpenAI optional.
- **Dialog Manager**: turn state, interruption handling, “skip a turn” pause, idle timers, summarization.
- **Tool Orchestrator**: runs terminal commands, web fetchers, USB/serial ops; queues background tasks and returns when complete.
- **Capability Registry**: tool metadata (cost/latency expectations) to allow “this may take a while” messaging.
- **Playback**: chunked TTS buffering, crossfade to avoid chopped audio, barge-in to stop playback on new speech.

## Interaction Behaviors

- **Wake & Listen**: wake-word arms STT; VAD ends utterance; supports manual push-to-talk override.
- **Interruptibility**: user speech during playback stops TTS and starts a new turn.
- **Long Tasks**: agent warns “This may take a bit, hold on”; tool output is silent unless summarized.
- **Completion Notify**: background jobs trigger a short prompt; if no reply after 10 minutes, auto-suspend.
- **Idle Check**: periodic “Are you still there?” when awaiting user after long silence.
- **Session Summaries**: after each exchange or task, store summary for later recall.

## Storage & State

- Per-session store (SQLite/JSONL) for transcripts, tool outputs, summaries, timestamps.
- Config for API keys (Minimax, ElevenLabs, STT) via env vars; pluggable keys per provider.

## Near-Term Build Steps (infra)

1) Scaffold core services: audio frontend, STT/TTS adapters, LLM adapter, tool runner, dialog manager. ✅
2) Wire a streaming loop using Pypecat (or similar) with buffered playback to avoid chopped audio. (loop + idle + barge-in in place; Pypecat integration TBD)
3) Implement terminal/web/SSH/serial tools with background queue and completion callbacks. ✅ (background for shell; sync for others)
4) Add session summary persistence after each conversation. ✅
5) Add idle/keep-alive timers and auto-suspend logic. ✅
6) Provide configuration for macOS dev; profile for Pi 4 later. ✅
