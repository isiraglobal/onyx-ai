"""Error pattern analysis and candidate improvement hypothesis generation."""

from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from onyx.self_improvement.tracker import TaskRecord, OutcomeTracker


@dataclass
class ImprovementHypothesis:
    target_component: str  # agent_instructions | tool_selection | routing
    target_name: str       # developer | research | supervisor
    error_pattern: str
    proposed_modification: str
    rationale: str


class ErrorPatternAnalyzer:
    """Analyzes task failure logs and formulates actionable hypotheses for improvement."""

    def __init__(self, tracker: Optional[OutcomeTracker] = None):
        self.tracker = tracker or OutcomeTracker()

    def analyze_failures(self, lookback_count: int = 100) -> List[ImprovementHypothesis]:
        records = self.tracker.get_recent_outcomes(limit=lookback_count)
        failures = [r for r in records if not r.success]
        if not failures:
            return []

        # Count failure signatures per agent
        agent_errors = Counter([(f.agent_name, (f.error or 'unknown')[:60]) for f in failures])
        hypotheses: List[ImprovementHypothesis] = []

        for (agent_name, err_prefix), count in agent_errors.most_common(5):
            if count >= 1:
                if "json" in err_prefix.lower() or "tool" in err_prefix.lower():
                    hypotheses.append(
                        ImprovementHypothesis(
                            target_component="agent_instructions",
                            target_name=agent_name,
                            error_pattern=f"Tool/JSON parsing error ({count} occurrences): {err_prefix}",
                            proposed_modification="Ensure tool call JSON is wrapped strictly in triple backtick ```json blocks and contains only valid keys.",
                            rationale="Eliminates formatting mismatches during agent tool dispatch.",
                        )
                    )
                elif "timeout" in err_prefix.lower():
                    hypotheses.append(
                        ImprovementHypothesis(
                            target_component="tool_selection",
                            target_name=agent_name,
                            error_pattern=f"Execution timeout ({count} occurrences)",
                            proposed_modification="Add --timeout flag and recommend chunked batch commands.",
                            rationale="Prevents terminal hanging on long running operations.",
                        )
                    )
                elif "permission" in err_prefix.lower():
                    hypotheses.append(
                        ImprovementHypothesis(
                            target_component="agent_instructions",
                            target_name=agent_name,
                            error_pattern=f"Permission restriction violated ({count} occurrences)",
                            proposed_modification="Instruct agent to only access files located within the active workspace root.",
                            rationale="Prevents wasted cycles attempting path traversal outside boundaries.",
                        )
                    )

        return hypotheses
