"""Isolated workspace environments and sandboxed process execution."""

import asyncio
from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import uuid
from typing import Dict, List, Optional, Any
from onyx.execution.permissions import PermissionManager, PermissionAction


@dataclass
class ExecutionResult:
    command: str
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False
    duration_seconds: float = 0.0

    @property
    def success(self) -> bool:
        return self.exit_code == 0 and not self.timed_out


class WorkspaceSandbox:
    """Manages an isolated workspace directory with strict boundary checks."""

    def __init__(
        self,
        workspace_id: Optional[str] = None,
        base_dir: str = "data/workspaces",
        permissions: Optional[PermissionManager] = None,
        default_timeout: int = 60,
        max_output_bytes: int = 1048576,
    ):
        self.workspace_id = workspace_id or str(uuid.uuid4())[:8]
        self.root = Path(base_dir).resolve() / self.workspace_id
        self.permissions = permissions or PermissionManager()
        self.default_timeout = default_timeout
        self.max_output_bytes = max_output_bytes
        self.root.mkdir(parents=True, exist_ok=True)

    def resolve_path(self, relative_or_absolute: str) -> Path:
        """Resolve a path safely inside the workspace, preventing directory traversal."""
        p = Path(relative_or_absolute)
        if not p.is_absolute():
            resolved = (self.root / p).resolve()
        else:
            resolved = p.resolve()

        # Enforce workspace root boundary
        if not str(resolved).startswith(str(self.root)):
            raise PermissionError(f"Path traversal detected: {relative_or_absolute} outside workspace {self.root}")

        return resolved

    async def execute_command(self, cmd: str, timeout: Optional[int] = None) -> ExecutionResult:
        """Execute a shell command inside the workspace directory."""
        action = self.permissions.evaluate_command(cmd)
        if action == PermissionAction.DENY:
            return ExecutionResult(
                command=cmd,
                exit_code=126,
                stdout="",
                stderr="Permission Denied: Command violates safety policy.",
                duration_seconds=0.0,
            )

        timeout = timeout or self.default_timeout
        start_time = asyncio.get_event_loop().time()

        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                cwd=str(self.root),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            duration = round(asyncio.get_event_loop().time() - start_time, 4)

            # Truncate if exceeding max output bytes
            stdout_str = stdout_b[:self.max_output_bytes].decode("utf-8", errors="replace")
            stderr_str = stderr_b[:self.max_output_bytes].decode("utf-8", errors="replace")

            return ExecutionResult(
                command=cmd,
                exit_code=proc.returncode if proc.returncode is not None else 1,
                stdout=stdout_str,
                stderr=stderr_str,
                timed_out=False,
                duration_seconds=duration,
            )
        except asyncio.TimeoutError:
            try:
                proc.kill()
                await proc.wait()
            except Exception:
                pass
            return ExecutionResult(
                command=cmd,
                exit_code=-1,
                stdout="",
                stderr=f"Execution timed out after {timeout} seconds.",
                timed_out=True,
                duration_seconds=timeout,
            )
        except Exception as e:
            return ExecutionResult(
                command=cmd,
                exit_code=1,
                stdout="",
                stderr=str(e),
                duration_seconds=round(asyncio.get_event_loop().time() - start_time, 4),
            )

    def write_file(self, file_path: str, content: str) -> Path:
        """Safely write text content to a file inside the workspace."""
        target = self.resolve_path(file_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    def read_file(self, file_path: str) -> str:
        """Safely read text content from a file inside the workspace."""
        target = self.resolve_path(file_path)
        if not target.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        return target.read_text(encoding="utf-8")

    def cleanup(self) -> None:
        """Erase workspace files."""
        if self.root.exists():
            shutil.rmtree(self.root, ignore_errors=True)
