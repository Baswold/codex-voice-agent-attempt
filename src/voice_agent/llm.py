from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import AsyncIterator, Iterable, List

import httpx


@dataclass
class ChatMessage:
    role: str
    content: str


class LLMClient:
    async def complete(self, messages: Iterable[ChatMessage]) -> AsyncIterator[str]:
        raise NotImplementedError


class MinimaxStubClient(LLMClient):
    def __init__(self, model: str, max_tokens: int) -> None:
        self.model = model
        self.max_tokens = max_tokens

    async def complete(self, messages: Iterable[ChatMessage]) -> AsyncIterator[str]:
        msgs: List[ChatMessage] = list(messages)
        last = msgs[-1].content if msgs else ""
        await asyncio.sleep(0)
        yield f"Minimax reply: {last}"[: self.max_tokens]

    async def chat(self, messages: Iterable[ChatMessage]) -> str:
        parts = []
        async for chunk in self.complete(messages):
            parts.append(chunk)
        return "".join(parts)


class MinimaxClient(LLMClient):
    def __init__(self, api_key: str, model: str, max_tokens: int = 512, api_url: str = "https://api.minimax.chat/v1/text/chatcompletion_pro") -> None:
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.api_url = api_url

    async def complete(self, messages: Iterable[ChatMessage]) -> AsyncIterator[str]:
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": m.role,
                    "content": m.content,
                }
                for m in messages
            ],
            "stream": False,
            "max_tokens": self.max_tokens,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(self.api_url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            choices = data.get("choices") or data.get("data") or []
            if choices:
                content = choices[0].get("message", {}).get("content", "")
            else:
                content = data.get("reply", "")
            yield str(content)
