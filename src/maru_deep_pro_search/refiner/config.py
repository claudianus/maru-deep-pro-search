from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .hardware import select_model_for_hardware

GITHUB_REPO: str = "claudianus/maru-deep-pro-search"
GITHUB_RELEASE_TAG: str = "models-v1"

MODEL_REGISTRY: dict[str, dict[str, Any]] = {
    "Qwen3.5-0.8B-Q4_K_M": {
        "repo_id": "unsloth/Qwen3.5-0.8B-GGUF",
        "filename": "Qwen3.5-0.8B-Q4_K_M.gguf",
        "github_url": (
            f"https://github.com/{GITHUB_REPO}"
            f"/releases/download/{GITHUB_RELEASE_TAG}"
            f"/Qwen3.5-0.8B-Q4_K_M.gguf"
        ),
        "min_ram_mb": 2048,
        "min_vram_mb": 512,
        "size_mb": 500,
        "context_length": 32768,
    },
    "Qwen3.5-2B-Q4_K_M": {
        "repo_id": "unsloth/Qwen3.5-2B-GGUF",
        "filename": "Qwen3.5-2B-Q4_K_M.gguf",
        "github_url": (
            f"https://github.com/{GITHUB_REPO}"
            f"/releases/download/{GITHUB_RELEASE_TAG}"
            f"/Qwen3.5-2B-Q4_K_M.gguf"
        ),
        "min_ram_mb": 5120,
        "min_vram_mb": 1536,
        "size_mb": 1200,
        "context_length": 32768,
    },
    "Qwen3.5-4B-Q4_K_M": {
        "repo_id": "unsloth/Qwen3.5-4B-GGUF",
        "filename": "Qwen3.5-4B-Q4_K_M.gguf",
        "github_url": (
            f"https://github.com/{GITHUB_REPO}"
            f"/releases/download/{GITHUB_RELEASE_TAG}"
            f"/Qwen3.5-4B-Q4_K_M.gguf"
        ),
        "min_ram_mb": 8192,
        "min_vram_mb": 2560,
        "size_mb": 2400,
        "context_length": 32768,
    },
}


@dataclass
class RefinerConfig:
    """Configuration for the built-in refiner engine.

    Attributes:
        model_name: Name of the GGUF model to load. None triggers auto-selection.
        n_ctx: Context window size in tokens.
        n_threads: Number of CPU threads for inference. None uses all CPUs.
        n_gpu_layers: Number of layers to offload to GPU. -1 means all layers.
        max_tokens: Maximum new tokens to generate per refinement pass.
        temperature: Sampling temperature.
        top_p: Nucleus sampling cutoff.
        cache_dir: Directory to cache downloaded models.
        enabled: Whether the refiner engine is active.
        timeout_seconds: Maximum time allowed for a single refinement call.
    """

    model_name: str | None = None
    n_ctx: int = 4096
    n_threads: int | None = None
    n_gpu_layers: int = -1
    max_tokens: int = 1500
    temperature: float = 0.1
    top_p: float = 0.9
    cache_dir: Path = field(
        default_factory=lambda: Path.home() / ".cache" / "maru" / "models"
    )
    enabled: bool = True
    timeout_seconds: float = 30.0

    @classmethod
    def from_env(cls) -> RefinerConfig:
        """Create a RefinerConfig from environment variables.

        Recognised variables (all prefixed with ``MARU_REFINER_``):

        - ``MODEL`` -> ``model_name`` (str)
        - ``CTX`` -> ``n_ctx`` (int)
        - ``THREADS`` -> ``n_threads`` (int)
        - ``GPU_LAYERS`` -> ``n_gpu_layers`` (int)
        - ``MAX_TOKENS`` -> ``max_tokens`` (int)
        - ``TEMP`` -> ``temperature`` (float)
        - ``ENABLED`` -> ``enabled`` (bool)
        - ``TIMEOUT`` -> ``timeout_seconds`` (float)

        Returns:
            A fully populated ``RefinerConfig`` instance.
        """
        model_name = os.getenv("MARU_REFINER_MODEL")
        model_name = model_name if model_name else None

        n_ctx_raw = os.getenv("MARU_REFINER_CTX")
        n_ctx = int(n_ctx_raw) if n_ctx_raw is not None else 4096

        n_threads_raw = os.getenv("MARU_REFINER_THREADS")
        n_threads = int(n_threads_raw) if n_threads_raw is not None else None

        n_gpu_layers_raw = os.getenv("MARU_REFINER_GPU_LAYERS")
        n_gpu_layers = int(n_gpu_layers_raw) if n_gpu_layers_raw is not None else -1

        max_tokens_raw = os.getenv("MARU_REFINER_MAX_TOKENS")
        max_tokens = int(max_tokens_raw) if max_tokens_raw is not None else 1500

        temp_raw = os.getenv("MARU_REFINER_TEMP")
        temperature = float(temp_raw) if temp_raw is not None else 0.1

        enabled_raw = os.getenv("MARU_REFINER_ENABLED")
        if enabled_raw is not None:
            enabled = enabled_raw.lower() in ("1", "true", "yes", "on")
        else:
            enabled = True

        timeout_raw = os.getenv("MARU_REFINER_TIMEOUT")
        timeout_seconds = float(timeout_raw) if timeout_raw is not None else 30.0

        cache_dir_raw = os.getenv("MARU_REFINER_CACHE_DIR")
        cache_dir = (
            Path(cache_dir_raw)
            if cache_dir_raw
            else Path.home() / ".cache" / "maru" / "models"
        )

        return cls(
            model_name=model_name,
            n_ctx=n_ctx,
            n_threads=n_threads,
            n_gpu_layers=n_gpu_layers,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=0.9,
            cache_dir=cache_dir,
            enabled=enabled,
            timeout_seconds=timeout_seconds,
        )

    def get_model_config(self, model_name: str) -> dict[str, Any]:
        """Retrieve the registered configuration for a given model.

        Args:
            model_name: Key used in ``MODEL_REGISTRY``.

        Returns:
            A dictionary describing the model's Hugging Face Hub details,
            hardware requirements, and capabilities.

        Raises:
            KeyError: If *model_name* is not present in ``MODEL_REGISTRY``.
        """
        return MODEL_REGISTRY[model_name]

    def select_model_for_hardware(self, hardware_profile: Any) -> str:
        """Select the most appropriate model based on available hardware.

        Delegates to :func:`.hardware.select_model_for_hardware`.

        Args:
            hardware_profile: Opaque hardware descriptor consumed by the
                hardware selection logic.

        Returns:
            The name of the recommended model from ``MODEL_REGISTRY``.
        """
        return select_model_for_hardware(hardware_profile)
