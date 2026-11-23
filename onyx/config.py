"""ONYX configuration management."""

from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml


@dataclass
class IdentityConfig:
    role: str = "Autonomous Personal AI Intelligence System"
    owner: str = "ISIRA Automations"
    built_by: str = "ISIRA Automations"
    operating_principles: List[str] = field(default_factory=lambda: [
        "Operate with persistent memory and factual integrity.",
        "Prioritize local, private, and deterministic execution.",
        "Refuse fabricated capabilities, data, or verification states.",
        "Perform sandboxed tool operations with explicit permission controls.",
        "Continuously learn, evaluate, and safely improve workflows."
    ])


@dataclass
class ServerConfig:
    host: str = "127.0.0.1"
    port: int = 8080
    debug: bool = False
    require_auth: bool = False
    api_prefix: str = "/api/v1"
    auth_token: Optional[str] = None


@dataclass
class MemoryConfig:
    backend: str = "sqlite"  # sqlite | postgres
    sqlite_path: str = "data/memory/onyx_memory.db"
    pg_url: str = "postgresql://onyx:onyx@localhost:5432/onyx_memory"
    vector_dimension: int = 384
    embedding_model: str = "fast-embed-local"
    ttl_cleanup_minutes: int = 60
    obsidian_vault_path: str = "data/obsidian_vault"


@dataclass
class ModelConfig:
    default_backend: str = "auto"
    fallback_order: List[str] = field(default_factory=lambda: ["ollama", "llamacpp", "transformers", "mock"])
    ollama_base_url: str = "http://localhost:11434"
    ollama_default_model: str = "llama3.2:latest"
    llamacpp_model_path: Optional[str] = None
    transformers_device: str = "auto"
    transformers_quantization: str = "4bit"
    context_window: int = 8192
    temperature: float = 0.7


@dataclass
class ExecutionConfig:
    sandbox_root: str = "data/workspaces"
    command_timeout_seconds: int = 60
    max_output_bytes: int = 1048576
    allow_network: bool = True


@dataclass
class LearningConfig:
    datasets_dir: str = "data/learning/datasets"
    checkpoints_dir: str = "data/learning/checkpoints"
    experiments_dir: str = "data/learning/experiments"
    max_training_epochs: int = 3
    batch_size: int = 2


@dataclass
class SyncConfig:
    node_id: str = "onyx-node-primary"
    bundle_dir: str = "data/sync"
    allowed_categories: List[str] = field(default_factory=lambda: [
        "skills", "identity", "long_term_knowledge"
    ])


@dataclass
class OnyxConfig:
    project_root: Path
    identity: IdentityConfig = field(default_factory=IdentityConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    models: ModelConfig = field(default_factory=ModelConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    learning: LearningConfig = field(default_factory=LearningConfig)
    sync: SyncConfig = field(default_factory=SyncConfig)

    def ensure_directories(self) -> None:
        """Create required directories for data, workspaces, and models."""
        dirs = [
            self.project_root / "data" / "memory",
            self.project_root / "data" / "workspaces",
            self.project_root / "data" / "learning" / "datasets",
            self.project_root / "data" / "learning" / "checkpoints",
            self.project_root / "data" / "learning" / "experiments",
            self.project_root / "data" / "sync",
            self.project_root / "data" / "cache",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)


def load_config(config_path: Optional[str] = None) -> OnyxConfig:
    """Load configuration from YAML file and apply environment variable overrides."""
    # Find project root (directory containing pyproject.toml or configs/)
    current = Path(__file__).resolve().parent.parent
    root = current

    yaml_data: Dict[str, Any] = {}
    if config_path is None:
        default_file = root / "configs" / "onyx.yaml"
        if default_file.exists():
            config_path = str(default_file)

    if config_path and Path(config_path).exists():
        with open(config_path, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f) or {}

    # Parse sections
    sys_data = yaml_data.get("system", {})
    id_data = sys_data.get("identity", {})
    identity = IdentityConfig(
        role=id_data.get("role", "Autonomous Personal AI Intelligence System"),
        owner=id_data.get("owner", "ISIRA Automations"),
        built_by=id_data.get("built_by", "ISIRA Automations"),
        operating_principles=id_data.get("operating_principles", IdentityConfig().operating_principles),
    )

    srv_data = yaml_data.get("server", {})
    server = ServerConfig(
        host=os.getenv("ONYX_HOST", srv_data.get("host", "127.0.0.1")),
        port=int(os.getenv("ONYX_PORT", srv_data.get("port", 8080))),
        debug=bool(srv_data.get("debug", False)),
        require_auth=os.getenv("ONYX_REQUIRE_AUTH", "false").lower() == "true" or srv_data.get("require_auth", False),
        api_prefix=srv_data.get("api_prefix", "/api/v1"),
        auth_token=os.getenv("ONYX_AUTH_TOKEN"),
    )

    mem_data = yaml_data.get("memory", {})
    memory = MemoryConfig(
        backend=os.getenv("ONYX_MEMORY_BACKEND", mem_data.get("backend", "sqlite")),
        sqlite_path=mem_data.get("sqlite_path", "data/memory/onyx_memory.db"),
        pg_url=os.getenv("ONYX_PG_URL", mem_data.get("pg_url", "postgresql://onyx:onyx@localhost:5432/onyx_memory")),
        vector_dimension=int(mem_data.get("vector_dimension", 384)),
        embedding_model=mem_data.get("embedding_model", "fast-embed-local"),
        ttl_cleanup_minutes=int(mem_data.get("ttl_cleanup_minutes", 60)),
        obsidian_vault_path=mem_data.get("obsidian_vault_path", "data/obsidian_vault"),
    )

    mod_data = yaml_data.get("models", {})
    ollama_data = mod_data.get("ollama", {})
    tf_data = mod_data.get("transformers", {})
    models = ModelConfig(
        default_backend=os.getenv("ONYX_DEFAULT_MODEL_BACKEND", mod_data.get("default_backend", "auto")),
        fallback_order=mod_data.get("fallback_order", ["ollama", "llamacpp", "transformers", "mock"]),
        ollama_base_url=os.getenv("ONYX_OLLAMA_BASE_URL", ollama_data.get("base_url", "http://localhost:11434")),
        ollama_default_model=ollama_data.get("default_model", "llama3.2:latest"),
        llamacpp_model_path=os.getenv("ONYX_LLAMACPP_MODEL_PATH", mod_data.get("llamacpp", {}).get("model_path")),
        transformers_device=tf_data.get("device", "auto"),
        transformers_quantization=tf_data.get("quantization", "4bit"),
        context_window=int(mod_data.get("context_window", 8192)),
        temperature=float(mod_data.get("temperature", 0.7)),
    )

    exec_data = yaml_data.get("execution", {})
    execution = ExecutionConfig(
        sandbox_root=exec_data.get("sandbox_root", "data/workspaces"),
        command_timeout_seconds=int(exec_data.get("command_timeout_seconds", 60)),
        max_output_bytes=int(exec_data.get("max_output_bytes", 1048576)),
        allow_network=bool(exec_data.get("allow_network", True)),
    )

    lrn_data = yaml_data.get("learning", {})
    learning = LearningConfig(
        datasets_dir=lrn_data.get("datasets_dir", "data/learning/datasets"),
        checkpoints_dir=lrn_data.get("checkpoints_dir", "data/learning/checkpoints"),
        experiments_dir=lrn_data.get("experiments_dir", "data/learning/experiments"),
        max_training_epochs=int(lrn_data.get("max_training_epochs", 3)),
        batch_size=int(lrn_data.get("batch_size", 2)),
    )

    syn_data = yaml_data.get("sync", {})
    sync = SyncConfig(
        node_id=syn_data.get("node_id", "onyx-node-primary"),
        bundle_dir=syn_data.get("bundle_dir", "data/sync"),
        allowed_categories=syn_data.get("allowed_categories", ["skills", "identity", "long_term_knowledge"]),
    )

    config = OnyxConfig(
        project_root=root,
        identity=identity,
        server=server,
        memory=memory,
        models=models,
        execution=execution,
        learning=learning,
        sync=sync,
    )
    config.ensure_directories()
    return config
