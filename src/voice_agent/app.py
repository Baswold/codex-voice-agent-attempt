from __future__ import annotations

import asyncio
from typing import List, Optional

from .config import AgentConfig
from .dialog import DialogManager, DialogTurn
from .providers import build_llm, build_stt, build_tts
from .session_store import SessionStore
from .sub_agent import AgentOrchestrator, AgentResult
from .tool_runner import ToolRunner


class VoiceAgentApp:
    def __init__(self, config: AgentConfig, enable_sub_agents: bool = True) -> None:
        self.config = config
        self.tool_runner = ToolRunner(config.tools)
        self.session_store = SessionStore(config.sessions.storage_path)
        self.llm_client = build_llm(config.llm)
        self.stt_client = build_stt(config.stt)
        self.tts_client = build_tts(config.tts)

        # Initialize sub-agent orchestrator
        self.orchestrator = AgentOrchestrator(llm=self.llm_client, tool_runner=self.tool_runner) if enable_sub_agents else None

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

    def spawn_sub_agent(self, task: str, specialty: Optional[str] = None) -> Optional[str]:
        """Spawn a sub-agent to handle a task in the background.

        Args:
            task: Description of the task
            specialty: Optional specialty/role (e.g., "coding", "research", "system")

        Returns:
            Agent ID if spawned, None if sub-agents disabled
        """
        if self.orchestrator:
            return self.orchestrator.spawn_agent(task, specialty)
        return None

    async def poll_sub_agents(self) -> List[AgentResult]:
        """Poll for completed sub-agent results.

        Returns:
            List of completed agent results
        """
        if not self.orchestrator:
            return []

        results = []
        while True:
            result = await self.orchestrator.next_result(timeout=0)
            if result is None:
                break
            results.append(result)
        return results

    def list_sub_agents(self) -> List[dict]:
        """List all sub-agents and their status."""
        if self.orchestrator:
            return self.orchestrator.list_agents()
        return []


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
