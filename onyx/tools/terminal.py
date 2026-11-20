"""Terminal execution tool with sandboxed workspace isolation."""

from typing import Dict, Any, Optional
from onyx.tools.base import Tool, ToolResult
from onyx.execution.sandbox import WorkspaceSandbox


class TerminalTool(Tool):
    """Executes safe terminal commands inside an isolated workspace."""

    name = "terminal_run"
    description = "Execute a shell command inside the current isolated workspace."
    parameters = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The shell command to execute.",
            },
            "timeout_seconds": {
                "type": "integer",
                "description": "Maximum seconds to wait before terminating process.",
                "default": 60,
            },
        },
        "required": ["command"],
    }

    def __init__(self, sandbox: Optional[WorkspaceSandbox] = None):
        self.sandbox = sandbox or WorkspaceSandbox()

    async def execute(self, command: str, timeout_seconds: int = 60, **kwargs) -> ToolResult:
        res = await self.sandbox.execute_command(command, timeout=timeout_seconds)
        if res.success:
            return ToolResult(
                success=True,
                output=res.stdout or "(Command completed with no output)",
                data={"exit_code": res.exit_code, "duration_seconds": res.duration_seconds},
            )
        else:
            return ToolResult(
                success=False,
                output=res.stdout,
                error=res.stderr or f"Command exited with code {res.exit_code}",
                data={"exit_code": res.exit_code, "timed_out": res.timed_out},
            )
