"""Deterministic mock adapter for automated testing, offline runs, and fast CI."""

import asyncio
import time
from typing import AsyncIterator, Dict, List, Optional, Any
from onyx.models.base import ModelAdapter, ModelCapabilities, ModelResponse, GenerationChunk


class MockModelAdapter(ModelAdapter):
    """Deterministic in-memory model adapter that generates simulated completions and embeddings."""

    def __init__(self, model_name: str = "mock-onyx-model", config: Optional[Dict[str, Any]] = None):
        super().__init__(model_name, config)
        self.preset_responses: Dict[str, str] = {}
        self.default_response: str = "ONYX Mock Response: Execution confirmed."

    async def load(self) -> bool:
        self.is_loaded = True
        return True

    def register_response(self, prompt_substring: str, response: str) -> None:
        """Register a canned response triggered when prompt contains a substring."""
        self.preset_responses[prompt_substring] = response

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stop: Optional[List[str]] = None,
    ) -> ModelResponse:
        start = time.perf_counter()
        selected_text = self.default_response
        for trigger, canned in self.preset_responses.items():
            if trigger in prompt:
                selected_text = canned
                break

        # If prompt contains JSON instructions, attempt structured response
        if "JSON" in prompt and selected_text == self.default_response:
            selected_text = '{"status": "success", "result": "mock_execution_complete"}'

        elapsed = time.perf_counter() - start
        tokens_est = max(1, len(selected_text) // 4)

        return ModelResponse(
            content=selected_text,
            model_name=self.model_name,
            tokens_prompt=max(1, len(prompt) // 4),
            tokens_completion=tokens_est,
            total_latency_seconds=elapsed,
            finish_reason="stop",
            raw_response={"mock": True},
        )

    async def stream_generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stop: Optional[List[str]] = None,
    ) -> AsyncIterator[GenerationChunk]:
        resp = await self.generate(prompt, system_prompt, temperature, max_tokens, stop)
        words = resp.content.split(" ")
        for i, word in enumerate(words):
            chunk = word + (" " if i < len(words) - 1 else "")
            await asyncio.sleep(0.005)
            yield GenerationChunk(delta=chunk, is_finished=(i == len(words) - 1))

    async def embed(self, texts: List[str]) -> List[List[float]]:
        # Deterministic 384-dim pseudo-embeddings based on character hashing
        embeddings: List[List[float]] = []
        for text in texts:
            vec = [0.0] * 384
            for i, char in enumerate(text):
                idx = (ord(char) * 17 + i * 31) % 384
                vec[idx] += 1.0
            # Normalize vector
            norm = sum(x * x for x in vec) ** 0.5 or 1.0
            embeddings.append([round(x / norm, 5) for x in vec])
        return embeddings

    async def health_check(self) -> bool:
        return True

    async def unload(self) -> None:
        self.is_loaded = False

    def get_capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            streaming=True,
            embeddings=True,
            context_window=8192,
            supports_system_prompt=True,
            quantization_supported=False,
            multimodal=False,
            json_mode=True,
        )
