"""Git operations tool for version control inside workspaces."""

from typing import Optional
from onyx.tools.base import Tool, ToolResult
from onyx.execution.sandbox import WorkspaceSandbox


class GitOperationsTool(Tool):
    """Executes safe git operations (status, diff, log, commit)."""

    name = "git_operations"
    description = "Execute safe git operations like status, diff, log, branch, or commit."
    parameters = {
        "type": "object",
        "properties": {
            "subcommand": {
                "type": "string",
                "enum": ["status", "diff", "log", "branch", "commit"],
                "description": "Git subcommand to execute",
            },
            "message": {
                "type": "string",
                "description": "Commit message if subcommand is 'commit'",
            },
            "args": {
                "type": "string",
                "description": "Additional safe arguments (e.g. branch name or log limit)",
            },
        },
        "required": ["subcommand"],
    }

    def __init__(self, sandbox: Optional[WorkspaceSandbox] = None):
        self.sandbox = sandbox or WorkspaceSandbox()

    async def execute(self, subcommand: str, message: Optional[str] = None, args: Optional[str] = None, **kwargs) -> ToolResult:
        if subcommand == "status":
            cmd = "git status --short"
        elif subcommand == "diff":
            cmd = f"git diff {args or ''}".strip()
        elif subcommand == "log":
            cmd = f"git log -n 5 --oneline {args or ''}".strip()
        elif subcommand == "branch":
            cmd = f"git branch {args or ''}".strip()
        elif subcommand == "commit":
            if not message:
                return ToolResult(success=False, output="", error="Commit message is required for commit subcommand.")
            safe_msg = message.replace('"', '\\"')
            cmd = f'git commit -m "{safe_msg}"'
        else:
            return ToolResult(success=False, output="", error=f"Unsupported git subcommand: {subcommand}")

        res = await self.sandbox.execute_command(cmd)
        if res.success:
            return ToolResult(
                success=True,
                output=res.stdout or "(No git output)",
                data={"command": cmd, "exit_code": res.exit_code},
            )
        else:
            return ToolResult(
                success=False,
                output=res.stdout,
                error=res.stderr or f"Git error with exit code {res.exit_code}",
                data={"command": cmd, "exit_code": res.exit_code},
            )
