from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ToolRequest:
    """A request to execute a tool."""

    tool_type: str  # "shell", "web", "ssh", "serial"
    args: dict
    silent: bool = True  # Whether to execute silently in background


@dataclass
class ParsedResponse:
    """Parsed LLM response with separated speech and tool requests."""

    speech_text: str
    tool_requests: List[ToolRequest]


class ToolParser:
    """Parser to extract tool requests from LLM responses.

    The LLM can include tool requests in its response using XML-like tags:
    <tool type="shell" silent="true">ls -la</tool>
    <tool type="web">https://example.com</tool>
    <tool type="ssh" host="192.168.1.1">uptime</tool>

    These will be parsed out and executed, while the remaining text
    is spoken to the user.
    """

    TOOL_PATTERN = re.compile(
        r'<tool\s+type="([^"]+)"(?:\s+silent="(true|false)")?(?:\s+(\w+)="([^"]+)")*>(.*?)</tool>', re.DOTALL
    )
    TOOL_JSON_PATTERN = re.compile(r"```tool\s*\n(.*?)\n```", re.DOTALL)

    @classmethod
    def parse_response(cls, llm_response: str) -> ParsedResponse:
        """Parse an LLM response to extract tool requests and speech text.

        Args:
            llm_response: The raw response from the LLM

        Returns:
            ParsedResponse with separated speech text and tool requests
        """
        tool_requests: List[ToolRequest] = []
        remaining_text = llm_response

        # Parse XML-style tool tags
        for match in cls.TOOL_PATTERN.finditer(llm_response):
            full_match = match.group(0)
            tool_type = match.group(1)
            silent_str = match.group(2)
            content = match.group(5).strip()

            silent = silent_str != "false"  # Default to true

            # Extract additional attributes
            args = {"command": content}
            # Simple attribute parsing (can be enhanced)
            attr_pattern = re.compile(r'(\w+)="([^"]+)"')
            for attr_match in attr_pattern.finditer(match.group(0)):
                attr_name = attr_match.group(1)
                attr_value = attr_match.group(2)
                if attr_name not in ["type", "silent"]:
                    args[attr_name] = attr_value

            tool_requests.append(ToolRequest(tool_type=tool_type, args=args, silent=silent))
            remaining_text = remaining_text.replace(full_match, "")

        # Parse JSON-style tool blocks
        for match in cls.TOOL_JSON_PATTERN.finditer(llm_response):
            full_match = match.group(0)
            json_content = match.group(1).strip()
            try:
                tool_data = json.loads(json_content)
                if isinstance(tool_data, dict):
                    tool_type = tool_data.get("type", "shell")
                    args = {k: v for k, v in tool_data.items() if k not in ["type", "silent"]}
                    silent = tool_data.get("silent", True)
                    tool_requests.append(ToolRequest(tool_type=tool_type, args=args, silent=silent))
                    remaining_text = remaining_text.replace(full_match, "")
            except json.JSONDecodeError:
                # Invalid JSON, leave it in the text
                pass

        # Clean up the remaining text
        speech_text = remaining_text.strip()

        return ParsedResponse(speech_text=speech_text, tool_requests=tool_requests)

    @classmethod
    def get_tool_system_prompt(cls) -> str:
        """Get the system prompt that explains tool usage to the LLM."""
        return """You are a helpful voice assistant with access to tools. You can execute commands silently in the background while continuing the conversation.

Available tools:
- shell commands: Execute terminal commands
- web requests: Fetch URLs and web content
- ssh: Execute commands on remote hosts
- serial: Communicate with devices over serial/USB

To use a tool, include a tool tag in your response:
<tool type="shell">ls -la</tool>
<tool type="web">https://example.com</tool>
<tool type="ssh" host="192.168.1.1">uptime</tool>

By default, tools execute silently in the background. You should:
1. Acknowledge the user's request naturally
2. Include tool tags for any commands you need to run
3. Tell the user you'll get back to them with results if needed

The tool execution happens in the background, so you can continue the conversation.
When results are ready, you'll be notified and can share them with the user.

Example response:
"I'll check the current directory contents for you. <tool type="shell">ls -la</tool> Give me just a moment."
"""
