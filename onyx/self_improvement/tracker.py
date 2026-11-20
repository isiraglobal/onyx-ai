"""Task execution outcome tracking and telemetry logging."""

from dataclasses import dataclass, asdict
import json
from pathlib import Path
import time
from typing import Dict, List, Optional, Any


@dataclass
class TaskRecord:
    task_id: str
    agent_name: str
    goal: str
    success: bool
    duration_seconds: float
    error: Optional[str] = None
    tools_used: List[str] = None
    timestamp: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class OutcomeTracker:
    """Logs and indexes all agent task outcomes for self-improvement analytics."""

    def __init__(self, log_path: str = "data/learning/experiments/task_outcomes.jsonl"):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def record_outcome(
        self,
        task_id: str,
        agent_name: str,
        goal: str,
        success: bool,
        duration_seconds: float,
        error: Optional[str] = None,
        tools_used: Optional[List[str]] = None,
    ) -> TaskRecord:
        record = TaskRecord(
            task_id=task_id,
            agent_name=agent_name,
            goal=goal,
            success=success,
            duration_seconds=round(duration_seconds, 4),
            error=error,
            tools_used=tools_used or [],
            timestamp=time.time(),
        )
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record.to_dict()) + "\n")
        return record

    def get_recent_outcomes(self, limit: int = 100) -> List[TaskRecord]:
        if not self.log_path.exists():
            return []
        records = []
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        records.append(TaskRecord(**json.loads(line.strip())))
                    except Exception:
                        pass
        return records[-limit:]
