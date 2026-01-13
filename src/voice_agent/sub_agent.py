from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from .llm import ChatMessage, LLMClient
from .tool_runner import ToolResult, ToolRunner


class AgentStatus(Enum):
    """Status of a sub-agent."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentResult:
    """Result from a sub-agent execution."""

    agent_id: str
    task_description: str
    status: AgentStatus
    result_text: str
    tool_results: List[ToolResult]
    error: Optional[str] = None


class SubAgent:
    """An independent agent that can execute tasks in the background.

    Sub-agents have their own task context and can use tools to accomplish
    complex tasks without blocking the main conversation flow.
    """

    def __init__(
        self,
        agent_id: str,
        task_description: str,
        llm: LLMClient,
        tool_runner: ToolRunner,
        specialty: Optional[str] = None,
    ) -> None:
        """Initialize a sub-agent.

        Args:
            agent_id: Unique identifier for this agent
            task_description: Description of the task to accomplish
            llm: LLM client for decision-making
            tool_runner: Tool runner for executing commands
            specialty: Optional specialty/role for this agent (e.g., "coding", "research")
        """
        self.agent_id = agent_id
        self.task_description = task_description
        self.llm = llm
        self.tool_runner = tool_runner
        self.specialty = specialty or "general"
        self.status = AgentStatus.PENDING
        self._task: Optional[asyncio.Task] = None
        self._result: Optional[AgentResult] = None

    async def start(self) -> None:
        """Start the agent's execution in the background."""
        if self._task is not None:
            return
        self.status = AgentStatus.RUNNING
        self._task = asyncio.create_task(self._execute())

    async def wait(self) -> AgentResult:
        """Wait for the agent to complete and return the result."""
        if self._task:
            await self._task
        return self._result or AgentResult(
            agent_id=self.agent_id,
            task_description=self.task_description,
            status=self.status,
            result_text="No result",
            tool_results=[],
            error="Agent did not execute",
        )

    async def cancel(self) -> None:
        """Cancel the agent's execution."""
        if self._task and not self._task.done():
            self._task.cancel()
            self.status = AgentStatus.CANCELLED
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    def is_done(self) -> bool:
        """Check if the agent has completed."""
        return self.status in [AgentStatus.COMPLETED, AgentStatus.FAILED, AgentStatus.CANCELLED]

    async def _execute(self) -> None:
        """Execute the agent's task."""
        try:
            # Build system prompt based on specialty
            system_prompt = self._get_system_prompt()

            # Create a plan for the task
            planning_messages = [
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(
                    role="user",
                    content=f"Task: {self.task_description}\n\nCreate a brief plan (2-4 steps) to accomplish this task.",
                ),
            ]

            plan = await self.llm.chat(planning_messages)

            # Execute the plan
            execution_messages = [
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content=f"Task: {self.task_description}"),
                ChatMessage(role="assistant", content=f"Plan:\n{plan}"),
                ChatMessage(role="user", content="Execute this plan now. Use tools as needed and provide a summary of results."),
            ]

            tool_results: List[ToolResult] = []
            result_text_parts: List[str] = []

            # Stream the execution response
            async for chunk in self.llm.complete(execution_messages):
                result_text_parts.append(chunk)

            result_text = "".join(result_text_parts)

            # Mark as completed
            self.status = AgentStatus.COMPLETED
            self._result = AgentResult(
                agent_id=self.agent_id,
                task_description=self.task_description,
                status=self.status,
                result_text=result_text,
                tool_results=tool_results,
            )

        except asyncio.CancelledError:
            self.status = AgentStatus.CANCELLED
            self._result = AgentResult(
                agent_id=self.agent_id,
                task_description=self.task_description,
                status=self.status,
                result_text="Task was cancelled",
                tool_results=[],
            )
            raise
        except Exception as e:
            self.status = AgentStatus.FAILED
            self._result = AgentResult(
                agent_id=self.agent_id,
                task_description=self.task_description,
                status=self.status,
                result_text=f"Task failed: {e!s}",
                tool_results=[],
                error=str(e),
            )

    def _get_system_prompt(self) -> str:
        """Get the system prompt based on agent specialty."""
        base_prompt = "You are a helpful sub-agent executing a specific task. You can use tools to accomplish your goals."

        specialty_prompts = {
            "coding": "You specialize in writing, debugging, and analyzing code. You understand multiple programming languages and can use command-line tools effectively.",
            "research": "You specialize in researching information, gathering data from various sources, and synthesizing findings. You can search the web and analyze documents.",
            "system": "You specialize in system administration and operations. You can execute shell commands, manage files, and interact with the system.",
            "network": "You specialize in network operations. You can SSH into remote systems, check network connectivity, and manage network resources.",
            "hardware": "You specialize in hardware interaction. You can communicate with devices over serial ports, USB, and other interfaces.",
        }

        specialty_prompt = specialty_prompts.get(self.specialty, "")
        if specialty_prompt:
            return f"{base_prompt}\n\n{specialty_prompt}"
        return base_prompt


class AgentOrchestrator:
    """Manages multiple sub-agents and their execution."""

    def __init__(self, llm: LLMClient, tool_runner: ToolRunner) -> None:
        self.llm = llm
        self.tool_runner = tool_runner
        self._agents: dict[str, SubAgent] = {}
        self._results_queue: asyncio.Queue[AgentResult] = asyncio.Queue()

    def spawn_agent(self, task_description: str, specialty: Optional[str] = None) -> str:
        """Spawn a new sub-agent for a task.

        Args:
            task_description: Description of the task
            specialty: Optional specialty/role for the agent

        Returns:
            The agent ID
        """
        agent_id = str(uuid.uuid4())[:8]  # Short ID for readability
        agent = SubAgent(
            agent_id=agent_id,
            task_description=task_description,
            llm=self.llm,
            tool_runner=self.tool_runner,
            specialty=specialty,
        )
        self._agents[agent_id] = agent
        asyncio.create_task(self._run_agent(agent))
        return agent_id

    async def _run_agent(self, agent: SubAgent) -> None:
        """Run an agent and queue its result."""
        await agent.start()
        result = await agent.wait()
        await self._results_queue.put(result)

    def get_agent(self, agent_id: str) -> Optional[SubAgent]:
        """Get an agent by ID."""
        return self._agents.get(agent_id)

    async def cancel_agent(self, agent_id: str) -> bool:
        """Cancel an agent's execution."""
        agent = self._agents.get(agent_id)
        if agent:
            await agent.cancel()
            return True
        return False

    async def next_result(self, timeout: float = 0) -> Optional[AgentResult]:
        """Get the next completed agent result."""
        try:
            return await asyncio.wait_for(self._results_queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

    def list_agents(self) -> List[dict]:
        """List all agents and their status."""
        return [
            {
                "agent_id": agent.agent_id,
                "task": agent.task_description,
                "specialty": agent.specialty,
                "status": agent.status.value,
            }
            for agent in self._agents.values()
        ]

    async def cancel_all(self) -> None:
        """Cancel all running agents."""
        for agent in self._agents.values():
            if not agent.is_done():
                await agent.cancel()
