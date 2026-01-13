from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass
from typing import Dict, Optional

import httpx

from .config import ToolConfig


@dataclass
class ToolResult:
    task_id: str
    command: str
    stdout: str
    stderr: str
    returncode: int
    duration: float
    timed_out: bool = False


class ToolRunner:
    def __init__(self, config: ToolConfig) -> None:
        self.config = config
        self._tasks: Dict[str, asyncio.Task[ToolResult]] = {}
        self._results: asyncio.Queue[ToolResult] = asyncio.Queue()

    async def run_command(self, command: str, timeout: Optional[int] = None) -> ToolResult:
        timeout = timeout or self.config.default_timeout
        start = time.perf_counter()
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        timed_out = False
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            timed_out = True
            process.kill()
            await process.communicate()
            stdout_bytes, stderr_bytes = b"", b""

        duration = time.perf_counter() - start
        stdout = stdout_bytes.decode(errors="replace")[: self.config.max_output_chars]
        stderr = stderr_bytes.decode(errors="replace")[: self.config.max_output_chars]

        return ToolResult(
            task_id="",
            command=command,
            stdout=stdout,
            stderr=stderr,
            returncode=process.returncode if not timed_out else -1,
            duration=duration,
            timed_out=timed_out,
        )

    async def fetch_url(self, url: str, method: str = "GET", timeout: Optional[int] = None) -> ToolResult:
        timeout = timeout or self.config.default_timeout
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.request(method, url)
                content = resp.text[: self.config.max_output_chars]
                status = resp.status_code
                duration = time.perf_counter() - start
                return ToolResult(
                    task_id="",
                    command=f"web {method} {url}",
                    stdout=content,
                    stderr="",
                    returncode=status,
                    duration=duration,
                )
        except Exception as exc:  # noqa: BLE001
            duration = time.perf_counter() - start
            return ToolResult(
                task_id="",
                command=f"web {method} {url}",
                stdout="",
                stderr=str(exc),
                returncode=-1,
                duration=duration,
            )

    async def run_ssh(self, host: str, command: str, username: Optional[str] = None, port: int = 22) -> ToolResult:
        start = time.perf_counter()
        try:
            import asyncssh  # type: ignore

            conn = await asyncssh.connect(host, username=username, port=port)
            try:
                result = await conn.run(command, check=False)
            finally:
                conn.close()
            duration = time.perf_counter() - start
            return ToolResult(
                task_id="",
                command=f"ssh {host}:{port} {command}",
                stdout=result.stdout[: self.config.max_output_chars],
                stderr=result.stderr[: self.config.max_output_chars],
                returncode=result.exit_status,
                duration=duration,
            )
        except Exception as exc:  # noqa: BLE001
            duration = time.perf_counter() - start
            return ToolResult(
                task_id="",
                command=f"ssh {host}:{port} {command}",
                stdout="",
                stderr=str(exc),
                returncode=-1,
                duration=duration,
            )

    async def run_serial(self, port: str, payload: str, baudrate: int = 115200, read_seconds: int = 2) -> ToolResult:
        start = time.perf_counter()
        try:
            import serial  # type: ignore

            ser = serial.Serial(port, baudrate=baudrate, timeout=1)
            try:
                ser.write(payload.encode())
                await asyncio.sleep(read_seconds)
                output = ser.read(ser.in_waiting or 1).decode(errors="replace")
            finally:
                ser.close()
            duration = time.perf_counter() - start
            return ToolResult(
                task_id="",
                command=f"serial {port}",
                stdout=output[: self.config.max_output_chars],
                stderr="",
                returncode=0,
                duration=duration,
            )
        except Exception as exc:  # noqa: BLE001
            duration = time.perf_counter() - start
            return ToolResult(
                task_id="",
                command=f"serial {port}",
                stdout="",
                stderr=str(exc),
                returncode=-1,
                duration=duration,
            )

    def submit_background(self, command: str, timeout: Optional[int] = None) -> str:
        task_id = str(uuid.uuid4())
        task = asyncio.create_task(self._run_and_queue(task_id, command, timeout))
        self._tasks[task_id] = task
        task.add_done_callback(lambda _: self._tasks.pop(task_id, None))
        return task_id

    async def _run_and_queue(self, task_id: str, command: str, timeout: Optional[int]) -> None:
        result = await self.run_command(command, timeout=timeout)
        result.task_id = task_id
        await self._results.put(result)

    async def next_result(self, timeout: float = 0) -> Optional[ToolResult]:
        try:
            return await asyncio.wait_for(self._results.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None
