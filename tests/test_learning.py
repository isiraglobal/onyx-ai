"""Unit tests for ONYX Learning Lab."""

import os
import shutil
import tempfile
import pytest
from onyx.memory.manager import MemoryManager
from onyx.learning.ingestion import IngestionPipeline
from onyx.learning.dataset import DatasetBuilder, TrainingExample
from onyx.learning.finetune import TrainingConfig, CheckpointManager, FinetuneWorkflow
from onyx.learning.evaluation import BenchmarkEvaluator, EvalCase
from onyx.models.mock import MockModelAdapter


@pytest.fixture
def test_env():
    temp_dir = tempfile.mkdtemp(prefix="onyx_learning_test_")
    db_path = os.path.join(temp_dir, "test_mem.db")
    memory = MemoryManager(db_path=db_path)
    yield temp_dir, memory
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_ingestion_pipeline(test_env):
    temp_dir, memory = test_env
    await memory.initialize()

    # Create a test document
    doc_file = os.path.join(temp_dir, "sample_guide.md")
    content = "ONYX Architecture Guide.\n\nSection 1: Portable Model Adapters.\n\nSection 2: Dual Memory Store."
    with open(doc_file, "w", encoding="utf-8") as f:
        f.write(content)

    pipeline = IngestionPipeline(memory=memory, chunk_size=50)
    res = await pipeline.ingest_file(doc_file)

    assert res["file_name"] == "sample_guide.md"
    assert res["chunks_count"] >= 1
    assert len(res["record_ids"]) == res["chunks_count"]

    # Verify searchable in memory
    recalled = await memory.recall("Adapters")
    assert len(recalled) >= 1


def test_dataset_builder(test_env):
    temp_dir, _ = test_env
    builder = DatasetBuilder(output_dir=os.path.join(temp_dir, "datasets"))

    examples = [
        TrainingExample(instruction="Explain ONYX", output="ONYX is a portable AI.", source="docs"),
        TrainingExample(instruction="How to build?", output="Run onyx setup and onyx start.", source="docs"),
        TrainingExample(instruction="bad", output="", source="invalid"),  # Should be rejected
    ]

    meta = builder.create_dataset(name="onyx_eval_ds", examples=examples, format_type="chatml", val_split=0.5)

    assert meta["total_examples"] == 2
    assert meta["rejected_count"] == 1
    assert os.path.exists(meta["train_file"])
    assert os.path.exists(meta["val_file"])


@pytest.mark.asyncio
async def test_finetune_and_checkpoint_management(test_env):
    temp_dir, _ = test_env
    ckpt_dir = os.path.join(temp_dir, "checkpoints")
    ckpt_mgr = CheckpointManager(checkpoints_dir=ckpt_dir)
    workflow = FinetuneWorkflow(checkpoints_mgr=ckpt_mgr)

    prereqs = workflow.check_prerequisites()
    assert "can_train" in prereqs

    config = TrainingConfig(
        base_model="HuggingFaceTB/SmolLM-135M-Instruct",
        output_dir=ckpt_dir,
        epochs=1,
    )

    run_res = await workflow.run_training(config)
    assert run_res["success"] is True
    ckpt_id = run_res["checkpoint_id"]

    # Checkpoint activation and rollback
    assert ckpt_mgr.activate_checkpoint(ckpt_id) is True
    assert ckpt_mgr.active_checkpoint_id == ckpt_id

    rolled_back = ckpt_mgr.rollback()
    assert ckpt_mgr.active_checkpoint_id != ckpt_id


@pytest.mark.asyncio
async def test_benchmark_evaluation():
    mock = MockModelAdapter()
    mock.register_response("Who are you", "I am ONYX, an autonomous personal intelligence system.")
    mock.register_response("Use a tool", '{"action": "terminal_run", "arguments": {"cmd": "ls"}}')
    mock.register_response("rm -rf /", "Execution denied. This command is dangerous.")
    mock.register_response("fibonacci", "def fibonacci(n): return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)")

    evaluator = BenchmarkEvaluator()
    summary = await evaluator.evaluate_model(mock)

    assert summary.total_cases == 4
    assert summary.pass_rate >= 0.75
    assert summary.average_latency >= 0.0
