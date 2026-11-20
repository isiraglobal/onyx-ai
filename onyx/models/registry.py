"""Model registry, lifecycle management, and intelligent fallback router."""

from typing import Dict, List, Optional, Any
from onyx.models.base import ModelAdapter
from onyx.models.detector import detect_hardware, HardwareProfile
from onyx.models.mock import MockModelAdapter
from onyx.models.ollama import OllamaModelAdapter
from onyx.models.llamacpp import LlamaCppModelAdapter
from onyx.models.transformers import TransformersModelAdapter
from onyx.models.vllm import VLLMModelAdapter


class ModelRegistry:
    """Manages active inference backends, model discovery, and fallback routing."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.adapters: Dict[str, ModelAdapter] = {}
        self.active_adapter_name: Optional[str] = None
        self.hardware: HardwareProfile = detect_hardware()
        self.fallback_order = self.config.get("fallback_order", ["ollama", "llamacpp", "transformers", "mock"])

    def register(self, name: str, adapter: ModelAdapter) -> None:
        """Register a model adapter under a unique identifier."""
        self.adapters[name] = adapter
        if self.active_adapter_name is None:
            self.active_adapter_name = name

    def get(self, name: Optional[str] = None) -> Optional[ModelAdapter]:
        """Get an adapter by name or the active default."""
        if name and name in self.adapters:
            return self.adapters[name]
        if self.active_adapter_name and self.active_adapter_name in self.adapters:
            return self.adapters[self.active_adapter_name]
        return None

    async def get_or_fallback(self) -> ModelAdapter:
        """Return the active model adapter, or systematically walk down the fallback chain."""
        # Check if active adapter is healthy
        if self.active_adapter_name and self.active_adapter_name in self.adapters:
            current = self.adapters[self.active_adapter_name]
            if await current.health_check():
                return current

        # Walk fallback list
        for backend_name in self.fallback_order:
            if backend_name in self.adapters:
                adapter = self.adapters[backend_name]
                if await adapter.health_check() or await adapter.load():
                    self.active_adapter_name = backend_name
                    return adapter

        # If nothing else works, ensure Mock is available
        if "mock" not in self.adapters:
            mock = MockModelAdapter()
            await mock.load()
            self.register("mock", mock)
        self.active_adapter_name = "mock"
        return self.adapters["mock"]

    async def auto_configure(self) -> ModelAdapter:
        """Automatically initialize model adapters based on environment and hardware."""
        # 1. Register Mock adapter (always available for safety and testing)
        mock = MockModelAdapter()
        await mock.load()
        self.register("mock", mock)

        # If explicit default backend is configured (e.g. "mock" for deterministic tests)
        preferred = self.config.get("default_backend", "auto")
        if preferred == "mock":
            self.active_adapter_name = "mock"
            return mock

        # 2. Check Ollama
        ollama_url = self.config.get("ollama_base_url", "http://localhost:11434")
        ollama_model = self.config.get("ollama_default_model", "llama3.2:latest")
        ollama = OllamaModelAdapter(model_name=ollama_model, base_url=ollama_url)
        if await ollama.load():
            self.register("ollama", ollama)
            self.active_adapter_name = "ollama"

        # 3. Check Transformers (Local Apple Silicon MPS / CPU)
        try:
            from onyx.models.transformers import TransformersModelAdapter
            tf_adapter = TransformersModelAdapter(model_name="Qwen/Qwen2.5-0.5B-Instruct")
            if await tf_adapter.load():
                self.register("transformers", tf_adapter)
                self.active_adapter_name = "transformers"
                return tf_adapter
        except Exception:
            pass

        # 4. Check llama.cpp if configured
        llamacpp_path = self.config.get("llamacpp_model_path")
        if llamacpp_path:
            llamacpp = LlamaCppModelAdapter(model_path=llamacpp_path)
            if await llamacpp.load():
                self.register("llamacpp", llamacpp)

        return await self.get_or_fallback()

    def list_models(self) -> List[Dict[str, Any]]:
        """List all registered models and their status."""
        items = []
        for name, adapter in self.adapters.items():
            caps = adapter.get_capabilities()
            items.append({
                "name": name,
                "model_name": adapter.model_name,
                "is_loaded": adapter.is_loaded,
                "is_active": (name == self.active_adapter_name),
                "capabilities": {
                    "streaming": caps.streaming,
                    "embeddings": caps.embeddings,
                    "context_window": caps.context_window,
                },
            })
        return items
