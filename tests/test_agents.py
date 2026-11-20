"""Unit tests for ONYX autonomous agent system."""

import pytest
from onyx.agents.base import AgentTask, TaskStatus
from onyx.agents.pool import AgentPool
from onyx.models.mock import MockModelAdapter
from onyx.tools.registry import ToolRegistry
from onyx.tools.terminal import TerminalTool
from onyx.tools.filesystem import FileWriteTool, FileReadTool
from onyx.execution.sandbox import WorkspaceSandbox
import tempfile
import shutil


@pytest.fixture
def agent_system():
    temp_dir = tempfile.mkdtemp(prefix="onyx_agent_test_")
    sandbox = WorkspaceSandbox(workspace_id="test-agent-ws", base_dir=temp_dir)
    tools = ToolRegistry()
    tools.register(FileWriteTool(sandbox=sandbox))
    tools.register(FileReadTool(sandbox=sandbox))
    tools.register(TerminalTool(sandbox=sandbox))

    mock_model = MockModelAdapter(model_name="mock-agent-model")
    pool = AgentPool(model=mock_model, tools=tools)

    yield pool, sandbox, mock_model
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_agent_pool_initialization(agent_system):
    pool, _, _ = agent_system
    agents = pool.list_agents()
    agent_names = [a["name"] for a in agents]

    # Verify all mandatory specialist agents exist
    assert "supervisor" in agent_names
    assert "research" in agent_names
    assert "architect" in agent_names
    assert "developer" in agent_names
    assert "data" in agent_names
    assert "model" in agent_names
    assert "memory" in agent_names
    assert "evaluation" in agent_names
    assert "security" in agent_names


@pytest.mark.asyncio
async def test_supervisor_coordination_and_delegation(agent_system):
    pool, sandbox, mock_model = agent_system
    supervisor = pool.get_agent("supervisor")
    assert supervisor is not None

    # Test direct coordination
    task = await supervisor.coordinate("What is the capital of France?")
    assert task.status == TaskStatus.COMPLETED
    assert task.result is not None
    assert len(task.messages) >= 2


@pytest.mark.asyncio
async def test_developer_agent_tool_execution(agent_system):
    pool, sandbox, mock_model = agent_system
    developer = pool.get_agent("developer")
    assert developer is not None

    # Configure mock model to trigger a tool call
    mock_model.preset_responses["write code"] = (
        '```json\n{"action": "file_write", "arguments": {"path": "hello.py", "content": "print(42)"}}\n```'
    )

    task = AgentTask(goal="write code for a hello script", assigned_agent="developer")
    res_task = await developer.execute_task(task)

    assert res_task.status == TaskStatus.COMPLETED
    # Verify file was actually written to workspace
    assert sandbox.read_file("hello.py") == "print(42)"


@pytest.mark.asyncio
async def test_dynamic_specialist_agent_spawning(agent_system):
    pool, _, _ = agent_system

    custom_agent = pool.spawn_temporary_agent(
        name="crypto_auditor",
        role_description="Audits smart contract Solidity code for reentrancy bugs",
        instructions="Analyze solidity code contracts strictly.",
        allowed_tools=["file_read"],
    )

    assert custom_agent.name == "crypto_auditor"
    assert pool.get_agent("crypto_auditor") is not None

    task = AgentTask(goal="Audit contract Token.sol", assigned_agent="crypto_auditor")
    res = await custom_agent.execute_task(task)
    assert res.status == TaskStatus.COMPLETED
