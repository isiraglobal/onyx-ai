"""Filesystem manipulation tools with boundary validation."""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from onyx.tools.base import Tool, ToolResult
from onyx.execution.sandbox import WorkspaceSandbox


class FileReadTool(Tool):
    name = "file_read"
    description = "Read text content from a file in the workspace."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Relative path to file"},
            "max_lines": {"type": "integer", "description": "Maximum lines to read", "default": 500},
        },
        "required": ["path"],
    }

    def __init__(self, sandbox: Optional[WorkspaceSandbox] = None):
        self.sandbox = sandbox or WorkspaceSandbox()

    async def execute(self, path: str, max_lines: int = 500, **kwargs) -> ToolResult:
        try:
            target = self.sandbox.resolve_path(path)
            if not target.exists():
                return ToolResult(success=False, output="", error=f"File not found: {path}")
            lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
            content = "\n".join(lines[:max_lines])
            return ToolResult(
                success=True,
                output=content,
                data={"total_lines": len(lines), "truncated": len(lines) > max_lines},
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class FileWriteTool(Tool):
    name = "file_write"
    description = "Write or overwrite text content to a file in the workspace."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Relative path to file"},
            "content": {"type": "string", "description": "Text content to write"},
        },
        "required": ["path", "content"],
    }

    def __init__(self, sandbox: Optional[WorkspaceSandbox] = None):
        self.sandbox = sandbox or WorkspaceSandbox()

    async def execute(self, path: str, content: str, **kwargs) -> ToolResult:
        try:
            target = self.sandbox.write_file(path, content)
            return ToolResult(
                success=True,
                output=f"Successfully wrote {len(content)} characters to {path}",
                data={"path": str(target), "bytes": len(content.encode('utf-8'))},
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class FileListTool(Tool):
    name = "file_list"
    description = "List files and directories within a workspace directory."
    parameters = {
        "type": "object",
        "properties": {
            "directory": {"type": "string", "description": "Relative directory path", "default": "."},
        },
    }

    def __init__(self, sandbox: Optional[WorkspaceSandbox] = None):
        self.sandbox = sandbox or WorkspaceSandbox()

    async def execute(self, directory: str = ".", **kwargs) -> ToolResult:
        try:
            target = self.sandbox.resolve_path(directory)
            if not target.is_dir():
                return ToolResult(success=False, output="", error=f"Not a directory: {directory}")
            entries = []
            for item in sorted(target.iterdir()):
                kind = "DIR" if item.is_dir() else "FILE"
                entries.append(f"[{kind}] {item.name}")
            return ToolResult(
                success=True,
                output="\n".join(entries) if entries else "(Empty directory)",
                data={"count": len(entries)},
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
