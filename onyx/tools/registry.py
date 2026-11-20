"""Central tool registry, schema exporter, and execution dispatcher."""

from typing import Dict, List, Optional, Any
from onyx.tools.base import Tool, ToolResult
from onyx.execution.permissions import PermissionManager, PermissionAction


class ToolRegistry:
    """Manages active tools, schemas for LLMs, and safe invocation."""

    def __init__(self, permissions: Optional[PermissionManager] = None):
        self.tools: Dict[str, Tool] = {}
        self.permissions = permissions or PermissionManager()

    def register(self, tool: Tool) -> None:
        """Register a tool instance."""
        self.tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        return self.tools.get(name)

    def list_tools(self) -> List[str]:
        return list(self.tools.keys())

    def get_schemas(self, allowed_names: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Return list of JSON schemas for LLM tool calling."""
        schemas = []
        for name, tool in self.tools.items():
            if allowed_names is None or name in allowed_names:
                schemas.append(tool.get_schema())
        return schemas

    async def execute(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        """Execute a tool safely by name."""
        if tool_name not in self.tools:
            return ToolResult(
                success=False,
                output="",
                error=f"Tool not found: '{tool_name}'. Available: {', '.join(self.tools.keys())}",
            )

        tool = self.tools[tool_name]
        try:
            return await tool.execute(**arguments)
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Exception executing tool '{tool_name}': {str(e)}",
            )
