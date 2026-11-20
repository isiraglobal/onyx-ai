"""llama.cpp direct GGUF model adapter."""

import asyncio
import time
from typing import AsyncIterator, Dict, List, Optional, Any
from onyx.models.base import ModelAdapter, ModelCapabilities, ModelResponse, GenerationChunk


class LlamaCppModelAdapter(ModelAdapter):
    """Adapter for running quantized GGUF models directly via llama-cpp-python or binary."""

    def __init__(
        self,
        model_name: str = "custom.gguf",
        config: Optional[Dict[str, Any]] = None,
        model_path: Optional[str] = None,
    ):
        super().__init__(model_name, config)
        self.model_path = model_path or (config.get("model_path") if config else None)
        self.llm = None
        self.n_gpu_layers = (config.get("n_gpu_layers", -1) if config else -1)
        self.n_ctx = (config.get("context_window", 4096) if config else 4096)

    async def load(self) -> bool:
        if not self.model_path:
            return False

        try:
            from llama_cpp import Llama
            self.llm = Llama(
                model_path=self.model_path,
                n_gpu_layers=self.n_gpu_layers,
                n_ctx=self.n_ctx,
                verbose=False,
            )
            self.is_loaded = True
            return True
        except ImportError:
            # llama-cpp-python not installed
            self.is_loaded = False
            return False
        except Exception:
            self.is_loaded = False
            return False

    async def health_check(self) -> bool:
        return self.is_loaded and (self.llm is not None)

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stop: Optional[List[str]] = None,
    ) -> ModelResponse:
        if not self.llm:
            raise RuntimeError("llama.cpp model is not loaded or llama-cpp-python is not installed.")

        start = time.perf_counter()
        full_prompt = f"System: {system_prompt}\nUser: {prompt}\nAssistant:" if system_prompt else prompt

        # Run inference in worker thread to avoid blocking async event loop
        loop = asyncio.get_running_loop()
        output = await loop.run_in_executor(
            None,
            lambda: self.llm(
                full_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=stop or [],
            ),
        )

        elapsed = time.perf_counter() - start
        content = output["choices"][0]["text"]
        usage = output.get("usage", {})

        return ModelResponse(
            content=content,
            model_name=self.model_name,
            tokens_prompt=usage.get("prompt_tokens", len(prompt) // 4),
            tokens_completion=usage.get("completion_tokens", len(content) // 4),
            total_latency_seconds=elapsed,
            finish_reason=output["choices"][0].get("finish_reason", "stop"),
            raw_response=output,
        )

    async def stream_generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stop: Optional[List[str]] = None,
    ) -> AsyncIterator[GenerationChunk]:
        if not self.llm:
            raise RuntimeError("llama.cpp model is not loaded.")

        full_prompt = f"System: {system_prompt}\nUser: {prompt}\nAssistant:" if system_prompt else prompt
        stream = self.llm(
            full_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=stop or [],
            stream=True,
        )

        for chunk in stream:
            delta = chunk["choices"][0]["text"]
            finish = chunk["choices"][0].get("finish_reason")
            yield GenerationChunk(delta=delta, is_finished=finish is not None, finish_reason=finish)

    async def embed(self, texts: List[str]) -> List[List[float]]:
        if not self.llm:
            raise RuntimeError("llama.cpp model is not loaded.")
        embeddings = []
        for text in texts:
            emb = self.llm.create_embedding(text)
            embeddings.append(emb["data"][0]["embedding"])
        return embeddings

    async def unload(self) -> None:
        self.llm = None
        self.is_loaded = False

    def get_capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            streaming=True,
            embeddings=True,
            context_window=self.n_ctx,
            supports_system_prompt=True,
            quantization_supported=True,
            multimodal=False,
            json_mode=True,
        )
