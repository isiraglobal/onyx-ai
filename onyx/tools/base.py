"""Base interface and metadata schemas for ONYX tools."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class ToolResult:
    success: bool
    output: str
    error: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "data": self.data,
        }


class Tool(ABC):
    """Abstract base class for all ONYX executable tools."""

    name: str = "base_tool"
    description: str = "Base tool description"
    parameters: Dict[str, Any] = {}  # JSON Schema parameter definition

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters."""
        pass

    def get_schema(self) -> Dict[str, Any]:
        """Return OpenAI / Ollama compatible tool definition."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
