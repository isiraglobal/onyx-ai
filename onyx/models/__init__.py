"""ONYX interchangeable model engine."""

from onyx.models.base import ModelAdapter, ModelCapabilities, ModelResponse, GenerationChunk
from onyx.models.detector import detect_hardware, HardwareProfile
from onyx.models.mock import MockModelAdapter
from onyx.models.ollama import OllamaModelAdapter
from onyx.models.llamacpp import LlamaCppModelAdapter
from onyx.models.transformers import TransformersModelAdapter
from onyx.models.vllm import VLLMModelAdapter
from onyx.models.registry import ModelRegistry
from onyx.models.benchmark import benchmark_model, BenchmarkResult

__all__ = [
    "ModelAdapter",
    "ModelCapabilities",
    "ModelResponse",
    "GenerationChunk",
    "detect_hardware",
    "HardwareProfile",
    "MockModelAdapter",
    "OllamaModelAdapter",
    "LlamaCppModelAdapter",
    "TransformersModelAdapter",
    "VLLMModelAdapter",
    "ModelRegistry",
    "benchmark_model",
    "BenchmarkResult",
]
