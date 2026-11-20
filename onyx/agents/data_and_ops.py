"""Data, Model, Memory, Evaluation, and Security specialist agents."""

from typing import List
from onyx.agents.base import BaseAgent


class DataAgent(BaseAgent):
    """Specialist agent for dataset extraction, cleaning, and formatting."""

    name = "data"
    role_description = "Processes, cleans, validates, and formats datasets for SFT and LoRA fine-tuning."
    system_prompt = (
        "You are the ONYX Data Agent. You extract and clean data from documents and conversations. "
        "You ensure balanced, high-quality instruction-response pairs and validate dataset schemas."
    )
    allowed_tools: List[str] = ["document_extract", "file_read", "file_write", "python_execute"]


class ModelAgent(BaseAgent):
    """Specialist agent for model selection, quantization profiling, and benchmarking."""

    name = "model"
    role_description = "Evaluates hardware capabilities, selects optimal model backends, profiles latency and manages fine-tuning."
    system_prompt = (
        "You are the ONYX Model Agent. You inspect hardware constraints (CPU, RAM, GPU, MPS) and select appropriate models and quantization formats. "
        "You monitor training runs and ensure inference fallbacks function reliably."
    )
    allowed_tools: List[str] = ["terminal_run", "file_read"]


class MemoryAgent(BaseAgent):
    """Specialist agent for continuous knowledge management and fact distillation."""

    name = "memory"
    role_description = "Extracts permanent facts from interactions, updates structured categories, and eliminates duplicates."
    system_prompt = (
        "You are the ONYX Memory Agent. You audit conversation records, extract permanent facts, preferences, and skills, "
        "and maintain the structured personal memory store with accurate confidence scoring."
    )
    allowed_tools: List[str] = ["file_read"]


class EvaluationAgent(BaseAgent):
    """Specialist agent for testing, benchmark scoring, and regression auditing."""

    name = "evaluation"
    role_description = "Executes automated test suites, scores benchmark datasets, and verifies quality improvements."
    system_prompt = (
        "You are the ONYX Evaluation Agent. You maintain strict quality standards. "
        "You verify test results, run quantitative benchmark suites, and block regression in self-improvement experiments."
    )
    allowed_tools: List[str] = ["terminal_run", "python_execute", "file_read"]


class SecurityAgent(BaseAgent):
    """Specialist agent for permission governance, secret detection, and vulnerability auditing."""

    name = "security"
    role_description = "Audits code and commands for vulnerabilities, verifies sandbox isolation, and scans for leaked credentials."
    system_prompt = (
        "You are the ONYX Security Agent. You inspect commands, code, and external inputs for security vulnerabilities, "
        "command injection, path traversal, and sensitive credential exposure. You enforce zero-trust execution."
    )
    allowed_tools: List[str] = ["file_read", "file_list"]
