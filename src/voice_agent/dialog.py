from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import List, Optional

from .config import AgentConfig
from .llm import ChatMessage, LLMClient
from .session_store import SessionStore
from .tool_runner import ToolResult, ToolRunner


@dataclass
class DialogTurn:
    user_text: str
    response_text: str
    tool_results: List[ToolResult]
    summary: Optional[str] = None


class DialogManager:
    def __init__(self, config: AgentConfig, llm: LLMClient, tool_runner: ToolRunner, session_store: SessionStore) -> None:
        self.config = config
        self.llm = llm
        self.tool_runner = tool_runner
        self.session_store = session_store
        self.session_id = str(uuid.uuid4())

    async def handle_user_text(self, text: str) -> DialogTurn:
        tool_results: List[ToolResult] = []

        if text.startswith("runbg "):
            command = text[len("runbg ") :].strip()
            task_id = self.tool_runner.submit_background(command)
            response_text = f"Started background task {task_id} for: {command}"
            summary = await self._summarize(text, response_text, tool_results)
            self._record(text, response_text, tool_results, summary)
            return DialogTurn(user_text=text, response_text=response_text, tool_results=tool_results, summary=summary)

        if text.startswith("run "):
            command = text[len("run ") :].strip()
            result = await self.tool_runner.run_command(command)
            result.task_id = result.task_id or "foreground"
            tool_results.append(result)

        if text.startswith("web "):
            url = text[len("web ") :].strip()
            result = await self.tool_runner.fetch_url(url)
            result.task_id = result.task_id or "web"
            tool_results.append(result)

        if text.startswith("ssh "):
            parts = text.split(maxsplit=2)
            if len(parts) >= 3:
                host = parts[1]
                command = parts[2]
                result = await self.tool_runner.run_ssh(host, command)
                result.task_id = result.task_id or "ssh"
                tool_results.append(result)

        if text.startswith("serial "):
            parts = text.split(maxsplit=2)
            if len(parts) >= 3:
                port = parts[1]
                payload = parts[2]
                result = await self.tool_runner.run_serial(port, payload)
                result.task_id = result.task_id or "serial"
                tool_results.append(result)

        response_text = await self._llm_response(text, tool_results)
        summary = await self._summarize(text, response_text, tool_results)
        self._record(text, response_text, tool_results, summary)
        return DialogTurn(user_text=text, response_text=response_text, tool_results=tool_results, summary=summary)

    async def poll_background(self) -> List[DialogTurn]:
        turns: List[DialogTurn] = []
        while True:
            result = await self.tool_runner.next_result(timeout=0)
            if result is None:
                break
            text = f"[background task {result.task_id} complete]"
            tool_results = [result]
            response_text = await self._background_response(result)
            summary = await self._summarize(text, response_text, tool_results)
            self._record(text, response_text, tool_results, summary)
            turns.append(DialogTurn(user_text=text, response_text=response_text, tool_results=tool_results, summary=summary))
        return turns

    async def _llm_response(self, text: str, tool_results: List[ToolResult]) -> str:
        context = "\n".join(
            [
                "You are a natural, concise voice agent that can run tools silently and report summaries.",
                "If tools were run, summarize their outcome briefly.",
            ]
        )

        tool_summary = " \n".join(
            f"tool {res.task_id} exit {res.returncode}: {res.stdout[:200]}" for res in tool_results
        )

        messages = [
            ChatMessage(role="system", content=context),
            ChatMessage(role="user", content=text),
        ]
        if tool_summary:
            messages.append(ChatMessage(role="assistant", content=f"Tools: {tool_summary}"))

        parts: List[str] = []
        async for chunk in self.llm.complete(messages):
            parts.append(chunk)
        return "".join(parts).strip()

    async def _background_response(self, result: ToolResult) -> str:
        prompt = f"Background task {result.task_id} finished with code {result.returncode}. Output: {result.stdout[:300]}"
        messages = [
            ChatMessage(role="system", content="Summarize background tool completion concisely."),
            ChatMessage(role="user", content=prompt),
        ]
        return await self.llm.chat(messages)

    async def _summarize(self, user_text: str, response_text: str, tool_results: List[ToolResult]) -> Optional[str]:
        summary_prompt = "Summarize this exchange for memory: " + user_text + " | " + response_text
        tool_note = "; ".join(f"task {res.task_id} exit {res.returncode}" for res in tool_results)
        if tool_note:
            summary_prompt += " | tools: " + tool_note

        messages = [
            ChatMessage(role="system", content="Keep summaries under 40 words."),
            ChatMessage(role="user", content=summary_prompt),
        ]
        summary = await self.llm.chat(messages)
        return summary.strip() if summary else None

    def _record(self, user_text: str, response_text: str, tool_results: List[ToolResult], summary: Optional[str]) -> None:
        tool_payloads = [
            {
                "task_id": res.task_id,
                "command": res.command,
                "returncode": res.returncode,
                "stdout": res.stdout,
                "stderr": res.stderr,
                "duration": res.duration,
                "timed_out": res.timed_out,
            }
            for res in tool_results
        ]
        self.session_store.record_turn(self.session_id, user_text, response_text, tool_payloads)
        if summary:
            self.session_store.record_summary(self.session_id, summary)
