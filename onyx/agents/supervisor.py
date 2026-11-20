"""Supervisor agent for task decomposition, specialist delegation, and synthesis."""

import json
import time
from typing import Dict, List, Optional, Any
from onyx.agents.base import BaseAgent, AgentTask, TaskStatus, AgentMessage
from onyx.models.base import ModelAdapter
from onyx.tools.registry import ToolRegistry
from onyx.memory.manager import MemoryManager


class SupervisorAgent(BaseAgent):
    """Orchestrates specialist agents, reviews execution results, and ensures high quality."""

    name = "supervisor"
    role_description = "Coordinates specialist agents, decomposes multi-stage tasks, and reviews outputs."
    system_prompt = (
        "You are the ONYX Supervisor Agent. You oversee end-to-end task execution. "
        "For simple queries or direct commands, provide direct answers. "
        "For complex development or research goals, break them into focused steps, coordinate specialists, and synthesize the result."
    )
    allowed_tools: List[str] = ["terminal_run", "file_read", "file_list"]

    def __init__(
        self,
        model: ModelAdapter,
        specialists: Optional[Dict[str, BaseAgent]] = None,
        tools: Optional[ToolRegistry] = None,
        memory: Optional[MemoryManager] = None,
    ):
        super().__init__(model=model, tools=tools, memory=memory)
        self.specialists: Dict[str, BaseAgent] = specialists or {}

    def register_specialist(self, agent: BaseAgent) -> None:
        self.specialists[agent.name] = agent

    async def coordinate(self, goal: str, context: Optional[Dict[str, Any]] = None) -> AgentTask:
        """Analyze user goal, dispatch to specialist if appropriate, and synthesize final response."""
        main_task = AgentTask(goal=goal, assigned_agent=self.name, context=context or {})
        main_task.status = TaskStatus.RUNNING

        # 1. Check if simple task or if routing to specific specialist is needed
        lower_goal = goal.lower()
        target_specialist: Optional[BaseAgent] = None

        if any(w in lower_goal for w in ["research", "investigate", "look up", "find articles", "find documentation", "search online", "search web", "browse", "google", "news"]):
            target_specialist = self.specialists.get("research")
        elif any(w in lower_goal for w in ["write code", "implement", "create script", "debug", "fix bug", "execute command", "run terminal"]):
            target_specialist = self.specialists.get("developer")
        elif any(w in lower_goal for w in ["design", "architecture", "schema", "tradeoffs"]):
            target_specialist = self.specialists.get("architect")
        elif any(w in lower_goal for w in ["evaluate", "benchmark", "run tests"]):
            target_specialist = self.specialists.get("evaluation")
        elif any(w in lower_goal for w in ["security", "audit", "vulnerability"]):
            target_specialist = self.specialists.get("security")

        if target_specialist:
            subtask = AgentTask(goal=goal, assigned_agent=target_specialist.name, context=context or {})
            res_subtask = await target_specialist.execute_task(subtask)

            # Synthesize supervisor response
            if res_subtask.status == TaskStatus.COMPLETED:
                main_task.status = TaskStatus.COMPLETED
                main_task.result = res_subtask.result
                main_task.messages = res_subtask.messages
                main_task.completed_at = time.time()
                return main_task
            else:
                main_task.status = TaskStatus.FAILED
                main_task.error = res_subtask.error
                return main_task

        # Default: Supervisor handles directly
        return await self.execute_task(main_task)
