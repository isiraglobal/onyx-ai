"""Isolated Python code execution tool."""

import sys
from typing import Optional
from onyx.tools.base import Tool, ToolResult
from onyx.execution.sandbox import WorkspaceSandbox


class PythonExecTool(Tool):
    """Executes Python code scripts inside an isolated workspace."""

    name = "python_execute"
    description = "Execute a snippet of Python code inside the workspace and capture stdout/stderr."
    parameters = {
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Python source code to execute"},
            "timeout_seconds": {"type": "integer", "description": "Timeout in seconds", "default": 30},
        },
        "required": ["code"],
    }

    def __init__(self, sandbox: Optional[WorkspaceSandbox] = None):
        self.sandbox = sandbox or WorkspaceSandbox()

    async def execute(self, code: str, timeout_seconds: int = 30, **kwargs) -> ToolResult:
        try:
            # Write script to temporary workspace file
            script_file = "exec_script.py"
            self.sandbox.write_file(script_file, code)

            cmd = f"{sys.executable} {script_file}"
            res = await self.sandbox.execute_command(cmd, timeout=timeout_seconds)

            if res.success:
                return ToolResult(
                    success=True,
                    output=res.stdout or "(Code executed with no output)",
                    data={"exit_code": res.exit_code, "duration_seconds": res.duration_seconds},
                )
            else:
                return ToolResult(
                    success=False,
                    output=res.stdout,
                    error=res.stderr or f"Execution failed with code {res.exit_code}",
                    data={"exit_code": res.exit_code, "timed_out": res.timed_out},
                )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
