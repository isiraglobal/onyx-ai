"""Task scheduling and interval job runner tool."""

import asyncio
from dataclasses import dataclass, field
import time
from typing import Dict, List, Optional, Any, Callable
from onyx.tools.base import Tool, ToolResult


@dataclass
class ScheduledJob:
    job_id: str
    description: str
    interval_seconds: int
    last_run: float = 0.0
    run_count: int = 0
    is_active: bool = True


class ScheduledTaskTool(Tool):
    """Manages scheduled recurring tasks and delayed timers."""

    name = "task_scheduler"
    description = "Schedule or list background periodic tasks and timer alarms."
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["schedule", "list", "cancel"],
                "description": "Action to perform",
            },
            "job_id": {"type": "string", "description": "Unique job identifier"},
            "description": {"type": "string", "description": "Task description"},
            "interval_seconds": {"type": "integer", "description": "Interval between runs in seconds"},
        },
        "required": ["action"],
    }

    def __init__(self):
        self.jobs: Dict[str, ScheduledJob] = {}

    async def execute(
        self,
        action: str,
        job_id: Optional[str] = None,
        description: Optional[str] = None,
        interval_seconds: int = 3600,
        **kwargs,
    ) -> ToolResult:
        if action == "schedule":
            if not job_id:
                return ToolResult(success=False, output="", error="job_id is required to schedule a task.")
            self.jobs[job_id] = ScheduledJob(
                job_id=job_id,
                description=description or "Scheduled recurring task",
                interval_seconds=interval_seconds,
                last_run=time.time(),
            )
            return ToolResult(
                success=True,
                output=f"Task '{job_id}' scheduled to run every {interval_seconds}s.",
                data={"job_id": job_id, "interval": interval_seconds},
            )

        elif action == "list":
            if not self.jobs:
                return ToolResult(success=True, output="No scheduled tasks active.", data={"count": 0})
            lines = [f"- [{j.job_id}] {j.description} (every {j.interval_seconds}s, ran {j.run_count} times)" for j in self.jobs.values()]
            return ToolResult(success=True, output="\n".join(lines), data={"count": len(self.jobs)})

        elif action == "cancel":
            if not job_id or job_id not in self.jobs:
                return ToolResult(success=False, output="", error=f"Job not found: {job_id}")
            del self.jobs[job_id]
            return ToolResult(success=True, output=f"Task '{job_id}' cancelled.", data={"job_id": job_id})

        return ToolResult(success=False, output="", error=f"Unknown action: {action}")
