"""Ollama REST API model adapter."""

import json
import time
from typing import AsyncIterator, Dict, List, Optional, Any
import httpx
from onyx.models.base import ModelAdapter, ModelCapabilities, ModelResponse, GenerationChunk


class OllamaModelAdapter(ModelAdapter):
    """Adapter for interacting with locally running Ollama instance."""

    def __init__(
        self,
        model_name: str = "llama3.2:latest",
        config: Optional[Dict[str, Any]] = None,
        base_url: str = "http://localhost:11434",
    ):
        super().__init__(model_name, config)
        self.base_url = (config.get("base_url") if config else None) or base_url
        self.timeout = (config.get("timeout_seconds") if config else 120) or 120

    async def load(self) -> bool:
        """Verify Ollama is reachable and check if model is available."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    self.is_loaded = True
                    return True
        except Exception:
            self.is_loaded = False
        return self.is_loaded

    async def health_check(self) -> bool:
        """Check if Ollama server is alive."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/api/version")
                return res.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> List[str]:
        """Fetch list of pulled models from Ollama."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    return [m.get("name", "") for m in data.get("models", [])]
        except Exception:
            pass
        return []

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stop: Optional[List[str]] = None,
    ) -> ModelResponse:
        start = time.perf_counter()
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt
        if stop:
            payload["options"]["stop"] = stop

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            res = await client.post(f"{self.base_url}/api/generate", json=payload)
            res.raise_for_status()
            data = res.json()

        elapsed = time.perf_counter() - start
        content = data.get("response", "")
        prompt_eval_count = data.get("prompt_eval_count", len(prompt) // 4)
        eval_count = data.get("eval_count", len(content) // 4)

        return ModelResponse(
            content=content,
            model_name=self.model_name,
            tokens_prompt=prompt_eval_count,
            tokens_completion=eval_count,
            total_latency_seconds=elapsed,
            finish_reason=data.get("done_reason", "stop"),
            raw_response=data,
        )

    async def stream_generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stop: Optional[List[str]] = None,
    ) -> AsyncIterator[GenerationChunk]:
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt
        if stop:
            payload["options"]["stop"] = stop

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", f"{self.base_url}/api/generate", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        chunk_json = json.loads(line)
                        delta = chunk_json.get("response", "")
                        done = chunk_json.get("done", False)
                        yield GenerationChunk(
                            delta=delta,
                            is_finished=done,
                            finish_reason=chunk_json.get("done_reason") if done else None,
                        )
                        if done:
                            break
                    except json.JSONDecodeError:
                        continue

    async def embed(self, texts: List[str]) -> List[List[float]]:
        embeddings: List[List[float]] = []
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for text in texts:
                res = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.model_name, "prompt": text},
                )
                if res.status_code == 200:
                    embeddings.append(res.json().get("embedding", []))
                else:
                    embeddings.append([0.0] * 384)
        return embeddings

    async def unload(self) -> None:
        """Tell Ollama to evict model from memory (keep_alive: 0)."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"{self.base_url}/api/generate",
                    json={"model": self.model_name, "keep_alive": 0},
                )
        except Exception:
            pass
        self.is_loaded = False

    def get_capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            streaming=True,
            embeddings=True,
            context_window=self.config.get("context_window", 8192),
            supports_system_prompt=True,
            quantization_supported=True,
            multimodal=True,
            json_mode=True,
        )
