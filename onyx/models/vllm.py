"""vLLM high-throughput model adapter for GPU servers and clusters."""

import json
import time
from typing import AsyncIterator, Dict, List, Optional, Any
import httpx
from onyx.models.base import ModelAdapter, ModelCapabilities, ModelResponse, GenerationChunk


class VLLMModelAdapter(ModelAdapter):
    """Adapter for interacting with a vLLM server via OpenAI-compatible endpoints."""

    def __init__(
        self,
        model_name: str = "default",
        config: Optional[Dict[str, Any]] = None,
        base_url: str = "http://localhost:8000/v1",
    ):
        super().__init__(model_name, config)
        self.base_url = (config.get("base_url") if config else None) or base_url
        self.api_key = (config.get("api_key") if config else None) or "EMPTY"

    async def load(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(
                    f"{self.base_url}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                if res.status_code == 200:
                    self.is_loaded = True
                    return True
        except Exception:
            self.is_loaded = False
        return False

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/models")
                return res.status_code == 200
        except Exception:
            return False

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stop: Optional[List[str]] = None,
    ) -> ModelResponse:
        start = time.perf_counter()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stop": stop,
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            res = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            )
            res.raise_for_status()
            data = res.json()

        elapsed = time.perf_counter() - start
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})

        return ModelResponse(
            content=content,
            model_name=self.model_name,
            tokens_prompt=usage.get("prompt_tokens", len(prompt) // 4),
            tokens_completion=usage.get("completion_tokens", len(content) // 4),
            total_latency_seconds=elapsed,
            finish_reason=data["choices"][0].get("finish_reason", "stop"),
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
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stop": stop,
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk_json = json.loads(data_str)
                        choices = chunk_json.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {}).get("content", "")
                            finish = choices[0].get("finish_reason")
                            yield GenerationChunk(delta=delta, is_finished=finish is not None, finish_reason=finish)
                    except json.JSONDecodeError:
                        continue

    async def embed(self, texts: List[str]) -> List[List[float]]:
        # Using OpenAI compatible embeddings endpoint
        embeddings = []
        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(
                f"{self.base_url}/embeddings",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model_name, "input": texts},
            )
            if res.status_code == 200:
                data = res.json()
                for item in data.get("data", []):
                    embeddings.append(item.get("embedding", []))
            else:
                for text in texts:
                    embeddings.append([0.0] * 384)
        return embeddings

    async def unload(self) -> None:
        self.is_loaded = False

    def get_capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            streaming=True,
            embeddings=True,
            context_window=32768,
            supports_system_prompt=True,
            quantization_supported=True,
            multimodal=False,
            json_mode=True,
        )
