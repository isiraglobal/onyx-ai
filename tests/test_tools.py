"""Unit tests for ONYX tools and sandboxed execution."""

import os
import shutil
import tempfile
import pytest
from onyx.execution.permissions import PermissionManager, PermissionAction
from onyx.execution.sandbox import WorkspaceSandbox
from onyx.tools.filesystem import FileReadTool, FileWriteTool, FileListTool
from onyx.tools.terminal import TerminalTool
from onyx.tools.code_exec import PythonExecTool
from onyx.tools.document import DocumentExtractTool
from onyx.tools.scheduler import ScheduledTaskTool
from onyx.tools.registry import ToolRegistry


@pytest.fixture
def sandbox_fixture():
    temp_dir = tempfile.mkdtemp(prefix="onyx_test_ws_")
    sandbox = WorkspaceSandbox(workspace_id="test-ws", base_dir=temp_dir)
    yield sandbox
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_permission_manager_rules():
    pm = PermissionManager()
    # Allowed command
    assert pm.evaluate_command("ls -la") == PermissionAction.ALLOW
    assert pm.evaluate_command("echo 'hello'") == PermissionAction.ALLOW

    # Denied dangerous command
    assert pm.evaluate_command("rm -rf /") == PermissionAction.DENY
    assert pm.evaluate_command("sudo rm -rf /etc") == PermissionAction.DENY
    assert pm.evaluate_command(":(){ :|:& };:") == PermissionAction.DENY

    # Path boundaries
    assert pm.evaluate_path_access("/etc/passwd", is_write=True) == PermissionAction.DENY
    assert pm.evaluate_path_access("~/.ssh/id_rsa", is_write=False) == PermissionAction.DENY


@pytest.mark.asyncio
async def test_sandbox_path_traversal_prevention(sandbox_fixture):
    # Valid write inside workspace
    p = sandbox_fixture.write_file("test.txt", "hello inside")
    assert p.exists()
    assert sandbox_fixture.read_file("test.txt") == "hello inside"

    # Directory traversal attack should raise PermissionError
    with pytest.raises(PermissionError):
        sandbox_fixture.resolve_path("../../etc/passwd")


@pytest.mark.asyncio
async def test_terminal_and_python_exec(sandbox_fixture):
    term = TerminalTool(sandbox=sandbox_fixture)
    res = await term.execute("echo 'ONYX TERMINAL SUCCESS'")
    assert res.success is True
    assert "ONYX TERMINAL SUCCESS" in res.output

    # Denied command blocked
    res_denied = await term.execute("rm -rf /")
    assert res_denied.success is False
    assert "Permission Denied" in res_denied.error

    # Python Execution
    py_tool = PythonExecTool(sandbox=sandbox_fixture)
    res_py = await py_tool.execute("print(sum([1, 2, 3, 4, 5]))")
    assert res_py.success is True
    assert "15" in res_py.output.strip()


@pytest.mark.asyncio
async def test_filesystem_tools(sandbox_fixture):
    write_tool = FileWriteTool(sandbox=sandbox_fixture)
    read_tool = FileReadTool(sandbox=sandbox_fixture)
    list_tool = FileListTool(sandbox=sandbox_fixture)

    w_res = await write_tool.execute(path="notes.txt", content="Architectural note line 1\nLine 2")
    assert w_res.success is True

    r_res = await read_tool.execute(path="notes.txt")
    assert r_res.success is True
    assert "Architectural note line 1" in r_res.output

    l_res = await list_tool.execute()
    assert l_res.success is True
    assert "notes.txt" in l_res.output


@pytest.mark.asyncio
async def test_tool_registry_and_dispatch(sandbox_fixture):
    reg = ToolRegistry()
    term = TerminalTool(sandbox=sandbox_fixture)
    sched = ScheduledTaskTool()

    reg.register(term)
    reg.register(sched)

    schemas = reg.get_schemas()
    assert len(schemas) == 2
    assert any(s["function"]["name"] == "terminal_run" for s in schemas)

    # Dispatch tool
    dispatch_res = await reg.execute("task_scheduler", {"action": "schedule", "job_id": "job1", "interval_seconds": 60})
    assert dispatch_res.success is True
    assert "job1" in dispatch_res.output
