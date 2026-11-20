"""Base adapter interfaces and data structures for interchangeable model engines."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator, Dict, List, Optional, Any


@dataclass
class ModelCapabilities:
    streaming: bool = True
    embeddings: bool = False
    context_window: int = 8192
    supports_system_prompt: bool = True
    quantization_supported: bool = True
    multimodal: bool = False
    json_mode: bool = True


@dataclass
class GenerationChunk:
    delta: str
    is_finished: bool = False
    finish_reason: Optional[str] = None


@dataclass
class ModelResponse:
    content: str
    model_name: str
    tokens_prompt: int = 0
    tokens_completion: int = 0
    total_latency_seconds: float = 0.0
    finish_reason: str = "stop"
    raw_response: Optional[Dict[str, Any]] = None


class ModelAdapter(ABC):
    """Abstract base class for all ONYX model engines (Ollama, llama.cpp, HF, vLLM, Mock)."""

    def __init__(self, model_name: str, config: Optional[Dict[str, Any]] = None):
        self.model_name = model_name
        self.config = config or {}
        self.is_loaded = False

    @abstractmethod
    async def load(self) -> bool:
        """Initialize or verify the model backend is accessible."""
        pass

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stop: Optional[List[str]] = None,
    ) -> ModelResponse:
        """Generate a complete text response."""
        pass

    @abstractmethod
    async def stream_generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stop: Optional[List[str]] = None,
    ) -> AsyncIterator[GenerationChunk]:
        """Stream response tokens asynchronously."""
        pass

    @abstractmethod
    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Compute dense vector embeddings for input texts."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the model backend is responsive."""
        pass

    @abstractmethod
    async def unload(self) -> None:
        """Release allocated weights or connection resources."""
        pass

    @abstractmethod
    def get_capabilities(self) -> ModelCapabilities:
        """Return the functional capabilities supported by this adapter."""
        pass
