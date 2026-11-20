"""Unit tests for ONYX self-improvement engine."""

import os
import shutil
import tempfile
import pytest
from onyx.self_improvement.tracker import OutcomeTracker
from onyx.self_improvement.analyzer import ErrorPatternAnalyzer, ImprovementHypothesis
from onyx.self_improvement.promoter import SelfImprovementEngine
from onyx.models.mock import MockModelAdapter
from onyx.learning.evaluation import BenchmarkEvaluator


@pytest.fixture
def improvement_env():
    temp_dir = tempfile.mkdtemp(prefix="onyx_imp_test_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_outcome_tracking_and_error_analysis(improvement_env):
    log_file = os.path.join(improvement_env, "outcomes.jsonl")
    tracker = OutcomeTracker(log_path=log_file)

    # Record some successes and failures
    tracker.record_outcome("t1", "developer", "Write tool script", False, 1.2, error="Tool JSON formatting error")
    tracker.record_outcome("t2", "developer", "Write test script", False, 1.4, error="Tool JSON parsing syntax error")
    tracker.record_outcome("t3", "research", "Search papers", True, 0.8)

    records = tracker.get_recent_outcomes()
    assert len(records) == 3

    analyzer = ErrorPatternAnalyzer(tracker=tracker)
    hypotheses = analyzer.analyze_failures()

    assert len(hypotheses) >= 1
    assert hypotheses[0].target_name == "developer"
    assert hypotheses[0].target_component == "agent_instructions"


@pytest.mark.asyncio
async def test_self_improvement_experiment_and_promotion(improvement_env):
    evaluator = BenchmarkEvaluator()
    engine = SelfImprovementEngine(evaluator=evaluator, records_dir=improvement_env)

    # Baseline adapter
    baseline = MockModelAdapter(model_name="baseline")
    baseline.default_response = "Standard response without expected keywords."

    # Candidate adapter that meets benchmark
    candidate = MockModelAdapter(model_name="candidate")
    candidate.register_response("Who are you", "I am ONYX, an autonomous personal intelligence system.")
    candidate.register_response("Use a tool", '{"action": "terminal_run", "arguments": {"cmd": "ls"}}')
    candidate.register_response("rm -rf /", "Execution denied. This command is dangerous.")
    candidate.register_response("fibonacci", "def fibonacci(n): return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)")

    hypothesis = ImprovementHypothesis(
        target_component="agent_instructions",
        target_name="supervisor",
        error_pattern="Missing identity keywords",
        proposed_modification="Add explicit ONYX identity to system prompt",
        rationale="Passes benchmark suite",
    )

    promo_res = await engine.evaluate_and_promote(
        hypothesis=hypothesis,
        baseline_adapter=baseline,
        candidate_adapter=candidate,
        improvement_threshold=0.10,
    )

    assert promo_res["promoted"] is True
    assert promo_res["candidate_pass_rate"] > promo_res["baseline_pass_rate"]

    # Test rollback
    rolled_back = engine.rollback()
    assert rolled_back is not None
    assert rolled_back.active is False
