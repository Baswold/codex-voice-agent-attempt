from __future__ import annotations

import argparse
import asyncio
from .app import VoiceAgentApp
from .audio import AudioFrontend
from .audio_io import MicUnavailable, SoundDeviceMic, SoundDeviceSpeaker
from .config import AgentConfig
from .idle import IdleManager
from .vad import EnergyVAD
from .voice_loop import TTSPlayer, VoiceLoop
from .wake import EnergyWakeDetector


async def run_voice(listen_seconds: float, auto: bool) -> None:
    cfg = AgentConfig.from_env()
    app = VoiceAgentApp(cfg)

    try:
        mic = SoundDeviceMic(cfg.audio.sample_rate, cfg.audio.chunk_ms)
        speaker = SoundDeviceSpeaker(cfg.audio.sample_rate)
    except MicUnavailable as exc:
        print(f"Audio dependencies missing: {exc}")
        print("Install optional audio deps with: pip install .[audio]")
        return

    player = TTSPlayer(app.tts_client, playback_hook=speaker.play_chunk)
    idle = IdleManager(
        cfg.idle.ask_after_seconds,
        cfg.idle.suspend_after_seconds,
        speak=player.play,
        idle_prompt=cfg.idle.idle_prompt,
        suspend_prompt=cfg.idle.suspend_prompt,
    )
    audio = AudioFrontend(cfg.audio.wake_word, cfg.audio.sample_rate, cfg.audio.chunk_ms)
    loop = VoiceLoop(audio=audio, stt=app.stt_client, dialog=app.dialog, tts_player=player, idle=idle)

    await loop.start()

    if auto:
        vad = EnergyVAD(
            threshold=cfg.vad.threshold,
            speech_frames=cfg.vad.speech_frames,
            silence_frames=cfg.vad.silence_frames,
        )
        wake = EnergyWakeDetector(threshold=cfg.wake.threshold, consecutive=cfg.wake.consecutive) if cfg.wake.enabled else None
        try:
            async with mic:
                await loop.run_stream(mic.stream_frames(), vad=vad, wake=wake)
        except KeyboardInterrupt:
            print("\nExiting.")
        finally:
            await loop.stop()
            await speaker.close()
    else:
        try:
            while True:
                user = await asyncio.to_thread(input, "Press Enter to capture, or 'q' + Enter to quit: ")
                if user.strip().lower() == "q":
                    break

                async with mic:
                    pump = asyncio.create_task(mic.forward_to(audio))
                    await asyncio.sleep(listen_seconds)
                    await mic.stop()
                    await pump

                turn = await loop.run_once(audio.frames())
                if turn:
                    print(f"Agent: {turn.response_text}")
                    for result in turn.tool_results:
                        status = "timeout" if result.timed_out else str(result.returncode)
                        print(f"Tool {result.task_id} ({result.command}) → {status}")
                        if result.stdout:
                            print(result.stdout)
                        if result.stderr:
                            print(result.stderr)

        except KeyboardInterrupt:
            print("\nExiting.")
        finally:
            await loop.stop()
            await speaker.close()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Voice agent mic demo")
    parser.add_argument("--listen-seconds", type=float, default=5.0, help="Capture window per utterance")
    parser.add_argument("--auto", action="store_true", help="Continuous capture with VAD/wake word")
    args = parser.parse_args(argv)
    asyncio.run(run_voice(args.listen_seconds, args.auto))


if __name__ == "__main__":
    main()
