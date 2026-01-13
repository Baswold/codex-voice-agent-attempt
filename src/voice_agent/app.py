from __future__ import annotations

import asyncio
from typing import List

from .config import AgentConfig
from .dialog import DialogManager, DialogTurn
from .providers import build_llm, build_stt, build_tts
from .session_store import SessionStore
from .tool_runner import ToolRunner


class VoiceAgentApp:
    def __init__(self, config: AgentConfig) -> None:
        self.config = config
        self.tool_runner = ToolRunner(config.tools)
        self.session_store = SessionStore(config.sessions.storage_path)
        self.llm_client = build_llm(config.llm)
        self.stt_client = build_stt(config.stt)
        self.tts_client = build_tts(config.tts)
        self.dialog = DialogManager(
            config=config,
            llm=self.llm_client,
            tool_runner=self.tool_runner,
            session_store=self.session_store,
        )

    async def handle_text(self, text: str) -> DialogTurn:
        return await self.dialog.handle_user_text(text)

    async def poll_background(self) -> List[DialogTurn]:
        return await self.dialog.poll_background()


async def interactive_cli() -> None:
    config = AgentConfig.from_env()
    app = VoiceAgentApp(config)
    print("Voice agent CLI prototype. Type 'run <cmd>' for foreground tool or 'runbg <cmd>' for background. Ctrl+C to exit.")

    try:
        while True:
            user_text = await asyncio.to_thread(input, "\nYou: ")
            if not user_text.strip():
                continue
            turn = await app.handle_text(user_text)
            print(f"Agent: {turn.response_text}")
            for result in turn.tool_results:
                status = "timeout" if result.timed_out else str(result.returncode)
                print(f"Tool {result.task_id} ({result.command}) → {status}")
                if result.stdout:
                    print(result.stdout)
                if result.stderr:
                    print(result.stderr)

            background_turns = await app.poll_background()
            for bg in background_turns:
                print(f"Agent (background): {bg.response_text}")

    except KeyboardInterrupt:
        print("\nExiting.")


if __name__ == "__main__":
    asyncio.run(interactive_cli())
