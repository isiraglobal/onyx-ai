"""Unit tests for ONYX Core, Context, Workflow, Audit, and API Gateway."""

import os
import shutil
import tempfile
import pytest
from httpx import AsyncClient, ASGITransport

from onyx.config import OnyxConfig
from onyx.core.context import ContextManager
from onyx.core.router import TaskRouter
from onyx.core.workflow import WorkflowEngine, WorkflowPlan, WorkflowStep, StepStatus
from onyx.core.orchestrator import OnyxCore
from onyx.security.audit import AuditLogger
from onyx.api.server import create_app
from onyx.agents.pool import AgentPool
from onyx.models.mock import MockModelAdapter


@pytest.fixture
def core_test_env():
    temp_dir = tempfile.mkdtemp(prefix="onyx_core_test_")
    db_path = os.path.join(temp_dir, "core_mem.db")
    ws_dir = os.path.join(temp_dir, "ws")
    audit_file = os.path.join(temp_dir, "audit.log")

    cfg = OnyxConfig(project_root=temp_dir)
    cfg.memory.sqlite_path = db_path
    cfg.execution.sandbox_root = ws_dir
    cfg.models.default_backend = "mock"
    cfg.models.fallback_order = ["mock"]

    core = OnyxCore(config=cfg)

    yield temp_dir, core, audit_file
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_context_manager_pruning():
    mgr = ContextManager(max_context_tokens=100, reserve_completion_tokens=20)
    for i in range(10):
        mgr.add_turn("user", f"Message number {i} with some additional filler text.")
        mgr.add_turn("assistant", f"Response number {i} confirming message.")

    dialogue = mgr.get_pruned_dialogue("System instructions")
    assert "Message number 9" in dialogue  # Most recent turn must be retained
    assert "Message number 0" not in dialogue  # Oldest turns pruned to respect budget


def test_task_router_classification():
    router = TaskRouter()

    dec1 = router.route_task("Can you research the latest advancements in quantizing open models?")
    assert dec1.target_agent == "research"
    assert dec1.needs_tools is True

    dec2 = router.route_task("Write code for a Python HTTP client function.")
    assert dec2.target_agent == "developer"

    dec3 = router.route_task("Design the system architecture for a distributed cache.")
    assert dec3.target_agent == "architect"

    dec4 = router.route_task("Hello, who are you?")
    assert dec4.target_agent == "supervisor"


@pytest.mark.asyncio
async def test_workflow_engine():
    mock = MockModelAdapter()
    pool = AgentPool(model=mock)
    engine = WorkflowEngine(agents_map=pool.agents)

    plan = WorkflowPlan(
        workflow_id="wf_1",
        title="Test Multi-Agent Pipeline",
        steps=[
            WorkflowStep(id="s1", agent_name="research", instruction="Research database requirements"),
            WorkflowStep(id="s2", agent_name="architect", instruction="Design schema", depends_on=["s1"]),
            WorkflowStep(id="s3", agent_name="developer", instruction="Implement schema", depends_on=["s2"]),
        ],
    )

    res_plan = await engine.execute_plan(plan)
    assert res_plan.status == StepStatus.COMPLETED
    assert all(s.status == StepStatus.COMPLETED for s in res_plan.steps)


def test_audit_logger_integrity(core_test_env):
    _, _, audit_file = core_test_env
    logger = AuditLogger(log_path=audit_file)

    logger.log("user", "LOGIN", "system", "SUCCESS")
    logger.log("agent:developer", "FILE_WRITE", "data/test.py", "SUCCESS", {"bytes": 42})
    logger.log("agent:security", "PERMISSION_CHECK", "terminal_run", "DENIED")

    assert logger.verify_integrity() is True

    # Tamper with file
    with open(audit_file, "a", encoding="utf-8") as f:
        f.write('{"timestamp": 0, "actor": "hacker", "action": "TAMPER", "target": "root", "status": "FAIL", "details": {}, "entry_hash": "bad"}\n')

    assert logger.verify_integrity() is False


@pytest.mark.asyncio
async def test_onyx_core_end_to_end(core_test_env):
    _, core, _ = core_test_env
    await core.initialize()

    reply = await core.process_message("What is ONYX and what do you do?")
    assert reply is not None
    assert len(reply) > 0

    # Verify episodic memory was recorded
    records = await core.memory.store.export_all()
    episodic = [r for r in records if r.category.value == "episodic"]
    assert len(episodic) >= 1


@pytest.mark.asyncio
async def test_fastapi_rest_endpoints(core_test_env):
    _, core, _ = core_test_env
    await core.initialize()
    app = create_app(core=core)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Health
        resp = await client.get("/api/v1/system/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "hardware" in data

        # Chat
        chat_resp = await client.post("/api/v1/chat", json={"message": "System status check"})
        assert chat_resp.status_code == 200
        assert "response" in chat_resp.json()

        # Models
        models_resp = await client.get("/api/v1/models")
        assert models_resp.status_code == 200
        assert len(models_resp.json()["models"]) >= 1

        # Memory Add & Get
        add_resp = await client.post("/api/v1/memory", json={"content": "Important test fact", "category": "knowledge"})
        assert add_resp.status_code == 200
        rec_id = add_resp.json()["record"]["id"]

        get_resp = await client.get("/api/v1/memory?query=Important")
        assert get_resp.status_code == 200
        assert len(get_resp.json()) >= 1

        # Memory Delete
        del_resp = await client.delete(f"/api/v1/memory/{rec_id}")
        assert del_resp.status_code == 200
