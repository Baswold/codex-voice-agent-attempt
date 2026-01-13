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
    def __init__(
        self,
        api_key: str,
        model: str,
        max_tokens: int = 512,
        api_url: str = "https://api.minimax.chat/v1/text/chatcompletion_pro",
        enable_streaming: bool = True,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.api_url = api_url
        self.enable_streaming = enable_streaming

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
            "stream": self.enable_streaming,
            "max_tokens": self.max_tokens,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}

        if self.enable_streaming:
            # Streaming mode: yield chunks as they arrive
            async with httpx.AsyncClient(timeout=120) as client:
                async with client.stream("POST", self.api_url, headers=headers, json=payload) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:].strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                import json

                                data = json.loads(data_str)
                                choices = data.get("choices") or data.get("data") or []
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        yield content
                            except Exception:
                                # Skip malformed chunks
                                continue
        else:
            # Non-streaming mode: yield full response at once
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
