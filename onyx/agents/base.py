"""Base autonomous agent architecture and execution loop."""

from abc import ABC, abstractmethod
import asyncio
from dataclasses import dataclass, field
from enum import Enum
import json
import re
import time
from typing import Dict, List, Optional, Any
import uuid

from onyx.models.base import ModelAdapter
from onyx.tools.registry import ToolRegistry
from onyx.tools.base import ToolResult
from onyx.memory.manager import MemoryManager


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentMessage:
    role: str  # system, user, assistant, tool
    content: str
    tool_call_id: Optional[str] = None
    name: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class AgentTask:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    goal: str = ""
    assigned_agent: str = "general"
    context: Dict[str, Any] = field(default_factory=dict)
    messages: List[AgentMessage] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None


class BaseAgent(ABC):
    """Base class for all ONYX specialist agents."""

    name: str = "base_agent"
    role_description: str = "Base agent"
    system_prompt: str = (
        "You are ONYX, an autonomous AI intelligence system.\n"
        "Your brain is grounded in Quantum Leap Advantage (QLA) and High Ticket Closing (HTC).\n"
        "Speak for yourself directly, concisely, and with high conviction. Avoid fluff and generic textbook lists."
    )
    allowed_tools: List[str] = []

    def __init__(
        self,
        model: ModelAdapter,
        tools: Optional[ToolRegistry] = None,
        memory: Optional[MemoryManager] = None,
        max_iterations: int = 10,
    ):
        self.model = model
        self.tools = tools or ToolRegistry()
        self.memory = memory
        self.max_iterations = max_iterations

    def format_system_prompt(self, task: AgentTask, memory_block: str = "") -> str:
        """Compose clean, high-conviction system prompt with relevant memory context."""
        parts = [
            "You are ONYX, an autonomous high-conviction AI intelligence system.",
            "IDENTITY & CREATION (STRICT RELEVANCE ONLY):",
            "- You were built by ISIRA Automations.",
            "- When asked who created or built you: State that you were built by ISIRA Automations.",
            "- Mention Lakshit Singhvi ONLY if specifically asked for more details, who owns you, or who is behind ISIRA Automations.",
            "- In ordinary conversations, never volunteer who built or owns you.",
            "COMMUNICATION RULES:",
            "- Speak for yourself with high conviction and directness. Do not answer 'as per' anyone else or speak as a subservient assistant.",
            "- The foundational doctrine in your system is Quantum Leap Advantage (QLA) and High Ticket Closing (HTC).",
            "- Speak directly, concisely, and with high conviction. No fluff, no disclaimers, no generic lists.",
            "- When asked who created or built you: State that you were built by ISIRA Automations (mention Lakshit Singhvi only if asked for more details or who owns you).",
            "- When asked about business ideas: Ground answers strictly in Quantum Leap Advantage / QLA (acquire cash-flowing businesses with OPM & board of directors; never start from scratch in a garage).",
            "- When asked about sales objections (e.g., 'I need to think about it'): Ground answers strictly in Dan Lok HTC (call them out with the Doctor frame and disqualify).",
            "- You have full permission to search the web, execute code, and read files. Never refuse with 'I cannot assist'.",
        ]

        if memory_block:
            parts.append(f"\nAUTHORITATIVE GROUND TRUTH DOCTRINE & MEMORY:\n{memory_block}\n")

        # Only add tools if the agent is actively assigned allowed tools
        if self.allowed_tools and self.tools:
            tool_schemas = self.tools.get_schemas(self.allowed_tools)
            if tool_schemas:
                tools_desc = "\n".join([
                    f"- {s['function']['name']}: {s['function']['description']}"
                    for s in tool_schemas
                ])
                parts.append(
                    f"\nAVAILABLE TOOLS:\n{tools_desc}\n\n"
                    "HOW TO CALL A TOOL:\n"
                    "If you need to gather information or search, you MUST output ONLY a valid JSON code block:\n"
                    "```json\n"
                    "{\"action\": \"tool_name\", \"arguments\": {\"arg\": \"val\"}}\n"
                    "```\n"
                    "Do NOT refuse. Do NOT output explanations before the JSON code block."
                )

        return "\n\n".join(parts)

    async def execute_task(self, task: AgentTask) -> AgentTask:
        """Execute task iteratively until completion or max iterations reached."""
        task.status = TaskStatus.RUNNING

        # Retrieve ground-truth book knowledge and active context
        memory_block = ""
        if self.memory:
            memory_block = await self.memory.get_context_block(task.goal, limit_per_category=4)

        sys_prompt = self.format_system_prompt(task, memory_block=memory_block)
        task.messages.append(AgentMessage(role="user", content=task.goal))

        for iteration in range(self.max_iterations):
            # Pass clean user goal without fake "USER: " prefix
            last_user_msg = [m.content for m in task.messages if m.role == "user"][-1]

            # Injected guidance to enforce succinct, high-conviction responses
            prompt_payload = (
                f"{last_user_msg}\n\n"
                "(Provide a concise, direct, high-conviction answer strictly based on the authoritative knowledge above. No fluff, no disclaimers, no generic lists.)"
            )

            try:
                resp = await self.model.generate(
                    prompt=prompt_payload,
                    system_prompt=sys_prompt,
                    temperature=0.2,
                    max_tokens=350,
                )
            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = f"Model generation error: {str(e)}"
                return task

            assistant_text = resp.content.strip()
            # Clean any stray "USER:" or "ASSISTANT:" echoes if generated by small models
            cleaned_text = re.sub(r"^(ASSISTANT|ONYX|SYSTEM|USER):\s*", "", assistant_text, flags=re.IGNORECASE).strip()
            # Absolute guard: Never mention Dan Peña in any output
            cleaned_text = re.sub(r"\bDan\s+Pe[ñn]a\b", "Quantum Leap Advantage", cleaned_text, flags=re.IGNORECASE)
            cleaned_text = re.sub(r"\bPe[ñn]a\b", "QLA", cleaned_text, flags=re.IGNORECASE)
            task.messages.append(AgentMessage(role="assistant", content=cleaned_text))

            # Detect tool call JSON
            tool_call = self._parse_tool_call(cleaned_text)
            if tool_call and self.tools and self.allowed_tools:
                tool_name = tool_call.get("action")
                tool_args = tool_call.get("arguments", {})

                if tool_name in self.allowed_tools:
                    tool_res: ToolResult = await self.tools.execute(tool_name, tool_args)
                    result_text = f"Tool '{tool_name}' result:\n{tool_res.output if tool_res.success else 'Error: ' + str(tool_res.error)}"
                    task.messages.append(AgentMessage(role="tool", content=result_text, name=tool_name))
                else:
                    task.messages.append(AgentMessage(role="tool", content=f"Tool '{tool_name}' not permitted."))
            else:
                task.status = TaskStatus.COMPLETED
                task.result = cleaned_text
                task.completed_at = time.time()
                return task

        task.status = TaskStatus.COMPLETED
        task.result = task.messages[-1].content
        task.completed_at = time.time()
        return task

    def _parse_tool_call(self, text: str) -> Optional[Dict[str, Any]]:
        match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        return None
