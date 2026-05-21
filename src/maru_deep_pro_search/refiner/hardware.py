from __future__ import annotations

import logging
import os
import platform
import subprocess
import sys
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class HardwareProfile:
    """System hardware capabilities profile.

    Attributes:
        total_ram_mb: Total system RAM in megabytes.
        available_ram_mb: Currently available RAM in megabytes.
        cpu_count: Number of logical CPU cores.
        cpu_features: List of detected CPU feature strings (e.g., AVX2, AVX512).
        has_gpu: Whether a GPU is detected.
        gpu_name: GPU model name, if detected.
        gpu_vram_mb: GPU video RAM in megabytes, if detected.
        gpu_backend: GPU compute backend (cuda, metal, rocm, none).
        platform: Operating system platform (Windows, Darwin, Linux).
        is_apple_silicon: Whether running on Apple Silicon.
    """

    total_ram_mb: int
    available_ram_mb: int
    cpu_count: int
    cpu_features: list[str]
    has_gpu: bool
    gpu_name: str | None
    gpu_vram_mb: int | None
    gpu_backend: str | None
    platform: str
    is_apple_silicon: bool


def _get_linux_cpu_features() -> list[str]:
    """Read CPU features from /proc/cpuinfo on Linux."""
    features = []
    try:
        with open("/proc/cpuinfo", encoding="utf-8") as f:
            for line in f:
                if line.startswith("flags\t") or line.startswith("Features\t"):
                    if ":" in line:
                        flags = line.split(":", 1)[1].strip().split()
                        feature_map = {
                            "sse2": "SSE2",
                            "avx": "AVX",
                            "avx2": "AVX2",
                            "avx512f": "AVX512F",
                            "avx512dq": "AVX512DQ",
                            "avx512bw": "AVX512BW",
                            "avx512vl": "AVX512VL",
                            "neon": "NEON",
                        }
                        for flag in flags:
                            flag_lower = flag.lower()
                            if flag_lower in feature_map:
                                feat = feature_map[flag_lower]
                                if feat not in features:
                                    features.append(feat)
                    break
    except Exception:
        pass
    return features


def _get_darwin_cpu_features() -> list[str]:
    """Get CPU features on macOS using sysctl."""
    features = []
    try:
        result = subprocess.run(
            ["sysctl", "-a", "machdep.cpu.features"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0 and ":" in result.stdout:
            flags = result.stdout.split(":", 1)[1].strip().split()
            feature_map = {
                "SSE2": "SSE2",
                "AVX1.0": "AVX",
                "AVX2": "AVX2",
                "AVX512F": "AVX512F",
                "AVX512DQ": "AVX512DQ",
                "AVX512BW": "AVX512BW",
                "AVX512VL": "AVX512VL",
            }
            for flag in flags:
                if flag in feature_map:
                    feat = feature_map[flag]
                    if feat not in features:
                        features.append(feat)
    except Exception:
        pass

    # Check for Apple Silicon NEON
    try:
        result = subprocess.run(
            ["sysctl", "-n", "hw.optional.AdvSIMD"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip() == "1" and "NEON" not in features:
            features.append("NEON")
    except Exception:
        pass

    return features


def _get_windows_cpu_features() -> list[str]:
    """Get CPU features on Windows via IsProcessorFeaturePresent."""
    features = []
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]

        PF_AVX_INSTRUCTIONS_AVAILABLE = 13
        PF_AVX2_INSTRUCTIONS_AVAILABLE = 14
        PF_AVX512F_INSTRUCTIONS_AVAILABLE = 15

        if kernel32.IsProcessorFeaturePresent(PF_AVX_INSTRUCTIONS_AVAILABLE):
            features.append("AVX")
        if kernel32.IsProcessorFeaturePresent(PF_AVX2_INSTRUCTIONS_AVAILABLE):
            features.append("AVX2")
        if kernel32.IsProcessorFeaturePresent(PF_AVX512F_INSTRUCTIONS_AVAILABLE):
            features.append("AVX512F")
    except Exception:
        pass
    return features


def _get_cpuid_features() -> list[str]:
    """Detect CPU features using available platform-specific methods."""
    features = []

    if sys.platform == "linux":
        features = _get_linux_cpu_features()
    elif sys.platform == "darwin":
        features = _get_darwin_cpu_features()
    elif sys.platform == "win32":
        features = _get_windows_cpu_features()

    return features


def _fallback_total_ram() -> int:
    """Fallback RAM detection when psutil is not available."""
    try:
        if sys.platform == "darwin":
            result = subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                capture_output=True,
                text=True,
                check=True,
            )
            return int(result.stdout.strip()) // (1024 * 1024)
        elif sys.platform == "linux":
            with open("/proc/meminfo", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        kb = int(line.split()[1])
                        return kb // 1024
        elif sys.platform == "win32":
            import ctypes
            from ctypes import wintypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", wintypes.DWORD),
                    ("dwMemoryLoad", wintypes.DWORD),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
            mem_status = MEMORYSTATUSEX()
            mem_status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            if kernel32.GlobalMemoryStatusEx(ctypes.byref(mem_status)):
                return mem_status.ullTotalPhys // (1024 * 1024)
    except Exception as e:
        logger.warning(f"Fallback RAM detection failed: {e}")

    return 4096  # Conservative default: 4GB


def detect_hardware() -> HardwareProfile:
    """Detect system hardware capabilities.

    Detects RAM, CPU, GPU, and platform information using psutil, pynvml,
    and platform-specific system calls. Handles missing optional dependencies
    gracefully with fallback detection methods.

    Returns:
        HardwareProfile with detected system capabilities.
    """
    # RAM detection
    try:
        import psutil

        mem = psutil.virtual_memory()
        total_ram_mb = mem.total // (1024 * 1024)
        available_ram_mb = mem.available // (1024 * 1024)
    except ImportError:
        logger.warning("psutil not installed, using fallback RAM detection")
        total_ram_mb = _fallback_total_ram()
        available_ram_mb = total_ram_mb // 2
    except Exception as e:
        logger.warning(f"psutil failed: {e}, using fallback")
        total_ram_mb = _fallback_total_ram()
        available_ram_mb = total_ram_mb // 2

    # CPU detection
    cpu_count = os.cpu_count() or 1
    cpu_features = _get_cpuid_features()

    # Platform detection
    plat = platform.system()
    is_apple_silicon = False

    if plat == "Darwin":
        processor = platform.processor()
        if processor == "arm" or "Apple" in processor:
            is_apple_silicon = True
        try:
            machine = platform.machine()
            if machine == "arm64":
                is_apple_silicon = True
        except Exception:
            pass

    # GPU detection
    has_gpu = False
    gpu_name = None
    gpu_vram_mb = None
    gpu_backend = "none"

    # Try NVIDIA first
    try:
        import pynvml

        pynvml.nvmlInit()
        try:
            device_count = pynvml.nvmlDeviceGetCount()
            if device_count > 0:
                has_gpu = True
                gpu_backend = "cuda"
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                gpu_vram_mb = info.total // (1024 * 1024)

                try:
                    name = pynvml.nvmlDeviceGetName(handle)
                    gpu_name = name.decode("utf-8") if isinstance(name, bytes) else str(name)
                except Exception:
                    gpu_name = "NVIDIA GPU"
        finally:
            pynvml.nvmlShutdown()
    except ImportError:
        logger.debug("pynvml not installed, skipping NVIDIA GPU detection")
    except Exception as e:
        logger.debug(f"NVIDIA GPU detection failed: {e}")

    # Try Metal on macOS
    if not has_gpu and plat == "Darwin" and is_apple_silicon:
        has_gpu = True
        gpu_backend = "metal"
        gpu_vram_mb = total_ram_mb // 2
        gpu_name = "Apple Silicon GPU"

    # Try ROCm on Linux
    if not has_gpu and plat == "Linux":
        try:
            if os.path.exists("/opt/rocm"):
                has_gpu = True
                gpu_backend = "rocm"
                gpu_name = "AMD GPU (ROCm)"
                gpu_vram_mb = None
        except Exception:
            pass

    return HardwareProfile(
        total_ram_mb=total_ram_mb,
        available_ram_mb=available_ram_mb,
        cpu_count=cpu_count,
        cpu_features=cpu_features,
        has_gpu=has_gpu,
        gpu_name=gpu_name,
        gpu_vram_mb=gpu_vram_mb,
        gpu_backend=gpu_backend if has_gpu else "none",
        platform=plat,
        is_apple_silicon=is_apple_silicon,
    )


MODEL_CONFIGS: dict[str, dict[str, object]] = {
    "Qwen3.5-0.8B-Q4_K_M": {
        "repo_id": "Qwen/Qwen3.5-0.8B-Instruct-GGUF",
        "filename": "qwen3.5-0.8b-instruct-q4_k_m.gguf",
        "min_ram_mb": 2048,
        "min_vram_mb": 512,
        "size_mb": 500,
    },
    "Qwen3.5-2B-Q4_K_M": {
        "repo_id": "Qwen/Qwen3.5-2B-Instruct-GGUF",
        "filename": "qwen3.5-2b-instruct-q4_k_m.gguf",
        "min_ram_mb": 5120,
        "min_vram_mb": 1536,
        "size_mb": 1200,
    },
    "Qwen3.5-4B-Q4_K_M": {
        "repo_id": "Qwen/Qwen3.5-4B-Instruct-GGUF",
        "filename": "qwen3.5-4b-instruct-q4_k_m.gguf",
        "min_ram_mb": 8192,
        "min_vram_mb": 2560,
        "size_mb": 2400,
    },
}


def get_optimal_model(profile: HardwareProfile) -> str:
    """Select optimal model based on hardware profile.

    Selection logic:
        - VRAM > 6000 MB: Qwen3.5-4B-Q4_K_M
        - VRAM > 2000 MB: Qwen3.5-2B-Q4_K_M
        - RAM > 8000 MB: Qwen3.5-2B-Q4_K_M (CPU fallback)
        - Otherwise: Qwen3.5-0.8B-Q4_K_M

    Args:
        profile: Detected hardware profile.

    Returns:
        Model identifier string.
    """
    if profile.gpu_vram_mb is not None and profile.gpu_vram_mb > 6000:
        return "Qwen3.5-4B-Q4_K_M"
    elif (
        profile.gpu_vram_mb is not None and profile.gpu_vram_mb > 2000
    ) or profile.total_ram_mb > 8000:
        return "Qwen3.5-2B-Q4_K_M"
    else:
        return "Qwen3.5-0.8B-Q4_K_M"


def can_run_refiner(profile: HardwareProfile) -> bool:
    """Check if refiner can run on this hardware.

    The minimum requirement is 2000 MB of total RAM for the 0.8B model.

    Args:
        profile: Detected hardware profile.

    Returns:
        True if refiner is feasible, False otherwise.
    """
    return profile.total_ram_mb >= 2000


def select_model_for_hardware(hardware_profile: HardwareProfile) -> str:
    """Compatibility wrapper for model selection.

    Delegates to :func:`get_optimal_model`.

    Args:
        hardware_profile: Detected hardware profile.

    Returns:
        Model identifier string.
    """
    return get_optimal_model(hardware_profile)
