"""Inference benchmarking suite for measuring latency, throughput, and memory footprint."""

from dataclasses import dataclass, asdict
import time
from typing import Dict, List, Optional, Any
from onyx.models.base import ModelAdapter


@dataclass
class BenchmarkResult:
    model_name: str
    prompt_tokens: int
    completion_tokens: int
    ttft_seconds: float
    total_seconds: float
    tokens_per_second: float
    success: bool
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


async def benchmark_model(
    adapter: ModelAdapter,
    prompt: str = "Explain the fundamental principles of portable artificial intelligence in two concise paragraphs.",
    max_tokens: int = 150,
) -> BenchmarkResult:
    """Benchmark a model adapter for time-to-first-token, throughput, and total latency."""
    start_time = time.perf_counter()
    first_token_time = None
    accumulated_content = []

    try:
        if not adapter.is_loaded:
            loaded = await adapter.load()
            if not loaded:
                return BenchmarkResult(
                    model_name=adapter.model_name,
                    prompt_tokens=0,
                    completion_tokens=0,
                    ttft_seconds=0.0,
                    total_seconds=0.0,
                    tokens_per_second=0.0,
                    success=False,
                    error="Failed to load model adapter",
                )

        # Stream to measure TTFT
        stream = adapter.stream_generate(prompt=prompt, max_tokens=max_tokens)
        async for chunk in stream:
            if first_token_time is None and chunk.delta:
                first_token_time = time.perf_counter()
            accumulated_content.append(chunk.delta)

        end_time = time.perf_counter()
        total_time = max(0.001, end_time - start_time)
        ttft = (first_token_time - start_time) if first_token_time else total_time

        full_text = "".join(accumulated_content)
        # Approximate tokens (4 chars per token)
        completion_tokens = max(1, len(full_text) // 4)
        prompt_tokens = max(1, len(prompt) // 4)
        tokens_per_second = round(completion_tokens / total_time, 2)

        return BenchmarkResult(
            model_name=adapter.model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            ttft_seconds=round(ttft, 4),
            total_seconds=round(total_time, 4),
            tokens_per_second=tokens_per_second,
            success=True,
        )
    except Exception as e:
        return BenchmarkResult(
            model_name=adapter.model_name,
            prompt_tokens=0,
            completion_tokens=0,
            ttft_seconds=0.0,
            total_seconds=0.0,
            tokens_per_second=0.0,
            success=False,
            error=str(e),
        )
