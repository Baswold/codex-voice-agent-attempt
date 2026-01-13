from __future__ import annotations

import asyncio
import time
from typing import Awaitable, Callable, Optional


class IdleManager:
    def __init__(
        self,
        ask_after_seconds: int,
        suspend_after_seconds: int,
        speak: Callable[[str], Awaitable[None]],
        idle_prompt: str = "Are you still there?",
        suspend_prompt: str = "Going idle. Say the wake word to resume.",
        on_suspend: Optional[Callable[[], Awaitable[None]]] = None,
    ) -> None:
        self.ask_after_seconds = ask_after_seconds
        self.suspend_after_seconds = suspend_after_seconds
        self.idle_prompt = idle_prompt
        self.suspend_prompt = suspend_prompt
        self.speak = speak
        self.on_suspend = on_suspend
        self._task: Optional[asyncio.Task[None]] = None
        self._running = False
        self._last_active = time.monotonic()
        self._asked = False
        self._suspended = False

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._last_active = time.monotonic()
        self._asked = False
        self._suspended = False
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None

    def touch(self) -> None:
        self._last_active = time.monotonic()
        self._asked = False
        self._suspended = False

    async def _loop(self) -> None:
        while self._running:
            now = time.monotonic()
            idle_for = now - self._last_active

            if not self._asked and idle_for >= self.ask_after_seconds:
                self._asked = True
                await self.speak(self.idle_prompt)

            if not self._suspended and idle_for >= self.suspend_after_seconds:
                self._suspended = True
                if self.suspend_prompt:
                    await self.speak(self.suspend_prompt)
                if self.on_suspend:
                    await self.on_suspend()

            await asyncio.sleep(1)
