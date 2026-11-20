"""Hardware and acceleration capability detection."""

from dataclasses import dataclass, asdict
import os
import platform
import shutil
import subprocess
from typing import Optional, Dict, Any


@dataclass
class HardwareProfile:
    os_name: str
    architecture: str
    cpu_cores: int
    ram_gb: float
    disk_free_gb: float
    apple_silicon: bool
    has_mps: bool
    has_cuda: bool
    has_rocm: bool
    cuda_device_name: Optional[str] = None
    cuda_vram_gb: Optional[float] = None
    recommended_quantization: str = "4bit"
    recommended_backend: str = "ollama"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def detect_hardware() -> HardwareProfile:
    """Inspect current host machine and determine inference hardware capabilities."""
    os_name = platform.system()
    arch = platform.machine()
    cpu_cores = os.cpu_count() or 4

    # Calculate RAM
    ram_gb = 8.0
    try:
        if os_name == "Darwin":
            out = subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True).strip()
            ram_gb = round(int(out) / (1024 ** 3), 2)
        elif os_name == "Linux":
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        kb = int(line.split()[1])
                        ram_gb = round(kb / (1024 ** 2), 2)
                        break
    except Exception:
        pass

    # Disk free space in current directory
    disk_free_gb = 50.0
    try:
        stat = shutil.disk_usage(".")
        disk_free_gb = round(stat.free / (1024 ** 3), 2)
    except Exception:
        pass

    apple_silicon = (os_name == "Darwin" and arch == "arm64")
    has_mps = False
    has_cuda = False
    has_rocm = False
    cuda_device_name = None
    cuda_vram_gb = None

    # Check torch capabilities if available
    try:
        import torch
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            has_mps = True
        if torch.cuda.is_available():
            has_cuda = True
            cuda_device_name = torch.cuda.get_device_name(0)
            cuda_vram_gb = round(torch.cuda.get_device_properties(0).total_memory / (1024 ** 3), 2)
    except ImportError:
        pass

    # Recommend quantization and backend
    recommended_quantization = "4bit"
    recommended_backend = "ollama"

    if has_cuda and cuda_vram_gb and cuda_vram_gb >= 16:
        recommended_quantization = "8bit"
        recommended_backend = "vllm"
    elif has_cuda or has_mps:
        recommended_quantization = "4bit"
        recommended_backend = "ollama"
    else:
        # CPU only
        recommended_quantization = "4bit"
        recommended_backend = "llamacpp"

    return HardwareProfile(
        os_name=os_name,
        architecture=arch,
        cpu_cores=cpu_cores,
        ram_gb=ram_gb,
        disk_free_gb=disk_free_gb,
        apple_silicon=apple_silicon,
        has_mps=has_mps,
        has_cuda=has_cuda,
        has_rocm=has_rocm,
        cuda_device_name=cuda_device_name,
        cuda_vram_gb=cuda_vram_gb,
        recommended_quantization=recommended_quantization,
        recommended_backend=recommended_backend,
    )
