"""Central ONYX intelligence orchestrator linking all subsystems."""

import asyncio
import time
from typing import AsyncIterator, Dict, List, Optional, Any
from onyx.config import OnyxConfig, load_config
from onyx.core.identity import IdentityEngine
from onyx.core.context import ContextManager
from onyx.core.router import TaskRouter, RouteDecision
from onyx.core.workflow import WorkflowEngine
from onyx.models.registry import ModelRegistry
from onyx.models.base import ModelAdapter, GenerationChunk
from onyx.memory.manager import MemoryManager
from onyx.memory.categories import MemoryCategory
from onyx.tools.registry import ToolRegistry
from onyx.tools.terminal import TerminalTool
from onyx.tools.filesystem import FileReadTool, FileWriteTool, FileListTool
from onyx.tools.browser import WebPageReadTool
from onyx.tools.web_search import WebSearchTool
from onyx.tools.code_exec import PythonExecTool
from onyx.tools.git_tools import GitOperationsTool
from onyx.tools.document import DocumentExtractTool
from onyx.tools.scheduler import ScheduledTaskTool
from onyx.tools.qla_tools import (
    QLADealFlowTool,
    QLAFinancialAnalysisTool,
    QLADreamTeamTool,
    QLAFinancingTool,
    QLANegotiationTool,
    QLAExecutionTool,
)
from onyx.execution.sandbox import WorkspaceSandbox
from onyx.execution.permissions import PermissionManager
from onyx.agents.pool import AgentPool
from onyx.agents.base import AgentTask, TaskStatus
from onyx.self_improvement.tracker import OutcomeTracker


class OnyxCore:
    """The central intelligence and orchestration layer of ONYX."""

    def __init__(self, config: Optional[OnyxConfig] = None):
        self.config = config or load_config()
        self.identity = IdentityEngine(
            system_name=self.config.identity.role,
            owner=self.config.identity.owner,
            operating_principles=self.config.identity.operating_principles,
        )
        self.permissions = PermissionManager()
        self.sandbox = WorkspaceSandbox(
            workspace_id="main",
            base_dir=self.config.execution.sandbox_root,
            permissions=self.permissions,
        )

        # Initialize tools
        self.tools = ToolRegistry(permissions=self.permissions)
        self._register_default_tools()

        # Initialize memory
        self.memory = MemoryManager(db_path=self.config.memory.sqlite_path)

        # Initialize models
        self.model_registry = ModelRegistry(config=self.config.models.__dict__)

        # Will be instantiated after model auto-configure in initialize()
        self.agent_pool: Optional[AgentPool] = None
        self.context = ContextManager(max_context_tokens=self.config.models.context_window)
        self.router = TaskRouter()
        self.tracker = OutcomeTracker(log_path="data/learning/experiments/task_outcomes.jsonl")
        self.is_initialized = False

    def _register_default_tools(self) -> None:
        self.tools.register(TerminalTool(sandbox=self.sandbox))
        self.tools.register(FileReadTool(sandbox=self.sandbox))
        self.tools.register(FileWriteTool(sandbox=self.sandbox))
        self.tools.register(FileListTool(sandbox=self.sandbox))
        self.tools.register(WebPageReadTool())
        self.tools.register(WebSearchTool())
        self.tools.register(PythonExecTool(sandbox=self.sandbox))
        self.tools.register(GitOperationsTool(sandbox=self.sandbox))
        self.tools.register(DocumentExtractTool())
        self.tools.register(ScheduledTaskTool())
        self.tools.register(QLADealFlowTool())
        self.tools.register(QLAFinancialAnalysisTool())
        self.tools.register(QLADreamTeamTool())
        self.tools.register(QLAFinancingTool())
        self.tools.register(QLANegotiationTool())
        self.tools.register(QLAExecutionTool())

    async def initialize(self) -> None:
        """Bootstrap database schema, verify hardware, and initialize active model and agents."""
        if self.is_initialized:
            return

        # 1. Initialize Memory
        await self.memory.initialize()

        # 2. Store default identity and principles if empty
        principles = await self.memory.store.filter_metadata(category=MemoryCategory.OPERATING_PRINCIPLES)
        if not principles:
            for p in self.identity.operating_principles:
                await self.memory.remember(
                    content=p,
                    category=MemoryCategory.OPERATING_PRINCIPLES,
                    source="system_bootstrap",
                )

        # 3. Auto-configure Model Engine
        active_model = await self.model_registry.auto_configure()

        # 4. Initialize Agent Pool
        self.agent_pool = AgentPool(model=active_model, tools=self.tools, memory=self.memory)
        self.is_initialized = True

    async def process_message(self, message: str) -> str:
        """Process an incoming user message through classification, agent execution, and memory persistence."""
        if not self.is_initialized:
            await self.initialize()

        start_time = time.perf_counter()
        self.context.add_turn(role="user", content=message)

        # Route task
        route: RouteDecision = self.router.route_task(message)

        # Dispatch via supervisor or assigned agent
        supervisor = self.agent_pool.get_agent("supervisor")
        target_agent = self.agent_pool.get_agent(route.target_agent) or supervisor

        task = AgentTask(goal=message, assigned_agent=target_agent.name)
        res_task = await target_agent.execute_task(task)

        elapsed = time.perf_counter() - start_time
        success = (res_task.status == TaskStatus.COMPLETED)
        response_text = res_task.result or res_task.error or "Task processed."

        # Record turn in context
        self.context.add_turn(role="assistant", content=response_text)

        # Record episodic memory
        await self.memory.remember(
            content=f"User: {message}\nONYX: {response_text[:300]}",
            category=MemoryCategory.EPISODIC,
            metadata={"agent": target_agent.name, "success": success},
            source="conversation",
        )

        # Log telemetry for self-improvement
        self.tracker.record_outcome(
            task_id=task.id,
            agent_name=target_agent.name,
            goal=message,
            success=success,
            duration_seconds=elapsed,
            error=res_task.error,
        )

        return response_text

    async def stream_message(self, message: str) -> AsyncIterator[GenerationChunk]:
        """Stream conversational response."""
        if not self.is_initialized:
            await self.initialize()

        full_response = await self.process_message(message)
        words = full_response.split(" ")
        for i, word in enumerate(words):
            chunk = word + (" " if i < len(words) - 1 else "")
            await asyncio.sleep(0.005)
            yield GenerationChunk(delta=chunk, is_finished=(i == len(words) - 1))
