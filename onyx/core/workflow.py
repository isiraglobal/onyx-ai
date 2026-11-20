"""Workflow coordinator for sequential and parallel multi-agent executions."""

import asyncio
from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Dict, List, Optional, Any
from onyx.agents.base import BaseAgent, AgentTask, TaskStatus


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class WorkflowStep:
    id: str
    agent_name: str
    instruction: str
    depends_on: List[str] = field(default_factory=list)
    status: StepStatus = StepStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None
    retries: int = 0
    max_retries: int = 2


@dataclass
class WorkflowPlan:
    workflow_id: str
    title: str
    steps: List[WorkflowStep]
    status: StepStatus = StepStatus.PENDING
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None


class WorkflowEngine:
    """Coordinates execution of multi-step agent plans with dependencies and retries."""

    def __init__(self, agents_map: Dict[str, BaseAgent]):
        self.agents = agents_map

    async def execute_plan(self, plan: WorkflowPlan) -> WorkflowPlan:
        plan.status = StepStatus.RUNNING
        completed_step_ids = set()
        step_results: Dict[str, str] = {}

        while len(completed_step_ids) < len(plan.steps):
            # Find steps that are ready (all dependencies met and status == PENDING)
            ready_steps = [
                s for s in plan.steps
                if s.status == StepStatus.PENDING and all(dep in completed_step_ids for dep in s.depends_on)
            ]

            if not ready_steps:
                # Check if there are any remaining running or failed steps
                has_failed = any(s.status == StepStatus.FAILED for s in plan.steps)
                if has_failed:
                    plan.status = StepStatus.FAILED
                    break
                # Deadlock or empty
                break

            # Execute ready steps (can be run concurrently)
            tasks = [self._execute_step(s, step_results) for s in ready_steps]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for step, res in zip(ready_steps, results):
                if isinstance(res, Exception) or step.status == StepStatus.FAILED:
                    if step.retries < step.max_retries:
                        step.retries += 1
                        step.status = StepStatus.PENDING
                    else:
                        step.status = StepStatus.FAILED
                        plan.status = StepStatus.FAILED
                        return plan
                else:
                    completed_step_ids.add(step.id)
                    step_results[step.id] = step.result or ""

        if all(s.status == StepStatus.COMPLETED for s in plan.steps):
            plan.status = StepStatus.COMPLETED
            plan.completed_at = time.time()
        else:
            plan.status = StepStatus.FAILED

        return plan

    async def _execute_step(self, step: WorkflowStep, previous_results: Dict[str, str]) -> None:
        step.status = StepStatus.RUNNING
        agent = self.agents.get(step.agent_name)
        if not agent:
            step.status = StepStatus.FAILED
            step.error = f"Agent not found: {step.agent_name}"
            return

        # Prepare context with results of prior dependent steps
        context_str = ""
        for dep in step.depends_on:
            if dep in previous_results:
                context_str += f"\nInput from step [{dep}]:\n{previous_results[dep]}\n"

        prompt = f"{step.instruction}\n{context_str}".strip()
        task = AgentTask(goal=prompt, assigned_agent=step.agent_name)

        res_task = await agent.execute_task(task)
        if res_task.status == TaskStatus.COMPLETED:
            step.status = StepStatus.COMPLETED
            step.result = res_task.result
        else:
            step.status = StepStatus.FAILED
            step.error = res_task.error
