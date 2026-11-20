"""Experimentation harness, benchmark comparison, verified promotion, and rollback."""

from dataclasses import dataclass, asdict
import json
from pathlib import Path
import time
from typing import Dict, List, Optional, Any
from onyx.learning.evaluation import BenchmarkEvaluator, EvalSummary
from onyx.models.base import ModelAdapter
from onyx.self_improvement.analyzer import ImprovementHypothesis


@dataclass
class PromotionRecord:
    version_id: str
    target_component: str
    target_name: str
    previous_value: str
    promoted_value: str
    baseline_score: float
    experiment_score: float
    promoted_at: float
    active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SelfImprovementEngine:
    """Safely runs isolated experiments, verifies improvements against benchmarks, and handles rollback."""

    def __init__(
        self,
        evaluator: Optional[BenchmarkEvaluator] = None,
        records_dir: str = "data/learning/experiments",
    ):
        self.evaluator = evaluator or BenchmarkEvaluator()
        self.records_dir = Path(records_dir)
        self.records_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.records_dir / "promotion_history.json"
        self._promotions: List[PromotionRecord] = []
        self._load_history()

    def _load_history(self) -> None:
        if self.history_file.exists():
            try:
                data = json.loads(self.history_file.read_text(encoding="utf-8"))
                self._promotions = [PromotionRecord(**item) for item in data]
            except Exception:
                pass

    def _save_history(self) -> None:
        data = [p.to_dict() for p in self._promotions]
        self.history_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    async def evaluate_and_promote(
        self,
        hypothesis: ImprovementHypothesis,
        baseline_adapter: ModelAdapter,
        candidate_adapter: ModelAdapter,
        improvement_threshold: float = 0.05,
    ) -> Dict[str, Any]:
        """Test candidate vs baseline on standard benchmarks and promote only if verified better."""
        baseline_eval: EvalSummary = await self.evaluator.evaluate_model(baseline_adapter)
        candidate_eval: EvalSummary = await self.evaluator.evaluate_model(candidate_adapter)

        score_delta = candidate_eval.pass_rate - baseline_eval.pass_rate
        is_verified = (score_delta >= improvement_threshold)

        if is_verified:
            version_id = f"imp_{int(time.time())}"
            record = PromotionRecord(
                version_id=version_id,
                target_component=hypothesis.target_component,
                target_name=hypothesis.target_name,
                previous_value="baseline_configuration",
                promoted_value=hypothesis.proposed_modification,
                baseline_score=baseline_eval.pass_rate,
                experiment_score=candidate_eval.pass_rate,
                promoted_at=time.time(),
                active=True,
            )
            self._promotions.append(record)
            self._save_history()

            return {
                "promoted": True,
                "version_id": version_id,
                "baseline_pass_rate": baseline_eval.pass_rate,
                "candidate_pass_rate": candidate_eval.pass_rate,
                "delta": round(score_delta, 4),
                "record": record.to_dict(),
            }
        else:
            return {
                "promoted": False,
                "reason": f"Candidate failed to exceed baseline by threshold ({score_delta:.2f} < {improvement_threshold:.2f})",
                "baseline_pass_rate": baseline_eval.pass_rate,
                "candidate_pass_rate": candidate_eval.pass_rate,
                "delta": round(score_delta, 4),
            }

    def rollback(self) -> Optional[PromotionRecord]:
        """Rollback the most recently promoted improvement."""
        active_records = [p for p in self._promotions if p.active]
        if not active_records:
            return None

        latest = active_records[-1]
        latest.active = False
        self._save_history()
        return latest

    def list_promotions(self) -> List[Dict[str, Any]]:
        return [p.to_dict() for p in self._promotions]
