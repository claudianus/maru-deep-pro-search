"""Model download and cache management for local GGUF models.

Uses a hybrid approach: HuggingFace Hub's built-in cache plus maru-specific
metadata files under ``~/.cache/maru/models/``.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

try:
    from huggingface_hub import hf_hub_download, try_to_load_from_cache

    _HF_AVAILABLE = True
except ImportError:
    _HF_AVAILABLE = False
    hf_hub_download = None  # type: ignore[assignment,misc]
    try_to_load_from_cache = None  # type: ignore[assignment,misc]

# Registry of known models — maps friendly name → (repo_id, filename)
_MODEL_REGISTRY: dict[str, tuple[str, str]] = {
    "Qwen3.5-0.8B-Q4_K_M": (
        "unsloth/Qwen3.5-0.8B-GGUF",
        "Qwen3.5-0.8B-Q4_K_M.gguf",
    ),
    "Qwen3.5-2B-Q4_K_M": (
        "unsloth/Qwen3.5-2B-GGUF",
        "Qwen3.5-2B-Q4_K_M.gguf",
    ),
    "Qwen3.5-4B-Q4_K_M": (
        "unsloth/Qwen3.5-4B-GGUF",
        "Qwen3.5-4B-Q4_K_M.gguf",
    ),
}

# GitHub release mirror URLs — primary download source
_GITHUB_RELEASE_BASE: str = (
    "https://github.com/claudianus/maru-deep-pro-search/releases/download/models-v1"
)
_GITHUB_URLS: dict[str, str] = {
    "Qwen3.5-0.8B-Q4_K_M": f"{_GITHUB_RELEASE_BASE}/Qwen3.5-0.8B-Q4_K_M.gguf",
    "Qwen3.5-2B-Q4_K_M": f"{_GITHUB_RELEASE_BASE}/Qwen3.5-2B-Q4_K_M.gguf",
    "Qwen3.5-4B-Q4_K_M": f"{_GITHUB_RELEASE_BASE}/Qwen3.5-4B-Q4_K_M.gguf",
}


def default_progress_callback(current: int, total: int, speed: float, eta: float) -> None:
    """Default progress printer using tqdm-style output."""
    pct = current / total * 100 if total else 0
    bar = "█" * int(pct // 5) + "░" * (20 - int(pct // 5))
    print(
        f"\rDownloading [{bar}] {pct:.1f}% {speed / 1024 / 1024:.1f}MB/s ETA {eta:.0f}s",
        end="",
    )
    if current >= total and total > 0:
        print()


def _resolve_model(model_name: str, cache_dir: Path) -> tuple[str, str]:
    """Resolve a friendly model name to (repo_id, filename).

    Looks up the hard-coded registry first, then falls back to cached metadata.

    Args:
        model_name: Friendly name of the model.
        cache_dir: Maru cache directory root.

    Returns:
        Tuple of (repo_id, filename).

    Raises:
        ValueError: If the model cannot be resolved.
    """
    if model_name in _MODEL_REGISTRY:
        return _MODEL_REGISTRY[model_name]
    meta = _read_metadata(model_name, cache_dir)
    if meta is not None:
        return meta["repo_id"], meta["filename"]
    raise ValueError(f"Unknown model '{model_name}'. No registry entry or cached metadata found.")


def _get_hf_cache_path(repo_id: str, filename: str) -> Path | None:
    """Return the HF Hub cache path for a file if it already exists.

    Args:
        repo_id: HuggingFace repository identifier.
        filename: Name of the file in the repository.

    Returns:
        Path to the cached file, or ``None`` if not cached.
    """
    if not _HF_AVAILABLE or try_to_load_from_cache is None:
        return None
    result = try_to_load_from_cache(repo_id, filename)
    if result is None:
        return None
    path = Path(result)
    # Defensive: ignore stale ``.noexist`` sentinel files from older HF Hub versions
    if ".noexist" in path.name or not path.exists():
        return None
    return path


def _write_metadata(model_name: str, metadata: dict[str, Any], cache_dir: Path) -> None:
    """Persist metadata JSON for a model.

    Args:
        model_name: Friendly name of the model.
        metadata: Dictionary to serialize.
        cache_dir: Maru cache directory root.
    """
    meta_path = cache_dir / model_name / "metadata.json"
    meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def _read_metadata(model_name: str, cache_dir: Path) -> dict[str, Any] | None:
    """Load metadata JSON for a model.

    Args:
        model_name: Friendly name of the model.
        cache_dir: Maru cache directory root.

    Returns:
        Parsed metadata dictionary, or ``None`` if missing.
    """
    meta_path = cache_dir / model_name / "metadata.json"
    if not meta_path.exists():
        return None
    data: dict[str, Any] = json.loads(meta_path.read_text(encoding="utf-8"))
    return data


def _compute_sha256(file_path: Path) -> str:
    """Compute SHA-256 hex digest for a file.

    Args:
        file_path: Path to the file.

    Returns:
        Lower-case hex digest string.
    """
    h = hashlib.sha256()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


_CHUNK_SIZE_BYTES: int = 400 * 1024 * 1024  # 400 MB per chunk


class ModelManager:
    """Manages GGUF model downloads from HuggingFace Hub and local caching.

    Uses HF Hub's built-in cache for the actual blob storage and maintains
    maru-specific metadata + symlinks under ``~/.cache/maru/models/``.

    Supports GitHub Release split-download for large models (>1GB).

    Args:
        cache_dir: Root dir for maru model metadata and symlinks.
            Defaults to ``~/.cache/maru/models/``.
    """

    def __init__(self, cache_dir: Path | None = None):
        self._cache_dir = cache_dir

    def _split_file(self, file_path: Path, chunk_size: int = _CHUNK_SIZE_BYTES) -> list[Path]:
        """Split a large file into chunks.

        Args:
            file_path: Path to the file to split.
            chunk_size: Size of each chunk in bytes.

        Returns:
            List of chunk file paths.
        """
        chunks: list[Path] = []
        file_size = file_path.stat().st_size
        if file_size <= chunk_size:
            return [file_path]

        with file_path.open("rb") as f:
            chunk_idx = 0
            while True:
                chunk_data = f.read(chunk_size)
                if not chunk_data:
                    break
                chunk_path = file_path.parent / f"{file_path.name}.part-{chunk_idx:03d}"
                chunk_path.write_bytes(chunk_data)
                chunks.append(chunk_path)
                chunk_idx += 1

        return chunks

    def _merge_chunks(self, chunks: list[Path], dest: Path) -> None:
        """Merge chunk files into a single file.

        Args:
            chunks: List of chunk file paths (must be in order).
            dest: Destination path for the merged file.
        """
        with dest.open("wb") as out_f:
            for chunk in chunks:
                with chunk.open("rb") as in_f:
                    shutil.copyfileobj(in_f, out_f)

    def _download_chunks(
        self,
        model_name: str,
        dest: Path,
        progress_callback: Callable[[int, int, float, float], None] | None = None,
    ) -> bool:
        """Download split chunks from GitHub Release and merge.

        Args:
            model_name: Friendly name of the model.
            dest: Destination path for the merged file.
            progress_callback: Optional progress callback.

        Returns:
            True if download and merge succeeded, False otherwise.
        """
        base_url = _GITHUB_URLS.get(model_name)
        if base_url is None:
            return False

        chunks: list[Path] = []
        chunk_idx = 0
        total_downloaded = 0

        try:
            while True:
                chunk_url = f"{base_url}.part-{chunk_idx:03d}"
                chunk_path = dest.parent / f"{dest.name}.part-{chunk_idx:03d}"

                # Test if chunk exists (HEAD request)
                try:
                    response = httpx.head(chunk_url, follow_redirects=True, timeout=10.0)
                    if response.status_code == 404:
                        break
                    if response.status_code != 200:
                        # Transient error — retry a few times before giving up
                        if chunk_idx == 0:
                            return False
                        break
                except Exception:
                    # Network/transient error on first chunk — abort
                    if chunk_idx == 0:
                        return False
                    break

                # Download chunk — clean up partial file on failure
                try:
                    self._download_with_progress(chunk_url, chunk_path, None)
                except Exception:
                    if chunk_path.exists():
                        chunk_path.unlink()
                    raise
                chunks.append(chunk_path)
                total_downloaded += chunk_path.stat().st_size
                chunk_idx += 1

            if not chunks:
                return False

            # Merge chunks
            if progress_callback is not None:
                progress_callback(total_downloaded, total_downloaded, 0.0, 0.0)

            self._merge_chunks(chunks, dest)

            # Clean up chunks after merge
            for chunk in chunks:
                chunk.unlink()

            return True

        except Exception:
            # Clean up on failure
            for chunk in chunks:
                if chunk.exists():
                    chunk.unlink()
            if dest.exists():
                dest.unlink()
            return False

    def get_cache_dir(self) -> Path:
        """Return the maru cache directory, creating it if necessary.

        Returns:
            Absolute path to ``~/.cache/maru/models/`` (or the overridden path).
        """
        if self._cache_dir is not None:
            path = self._cache_dir.expanduser().resolve()
        else:
            path = Path.home() / ".cache" / "maru" / "models"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_model_path(self, model_name: str) -> Path | None:
        """Check whether a model is available locally.

        Checks the maru cache symlink first, then falls back to the HF Hub
        internal cache.

        Args:
            model_name: Friendly name of the model.

        Returns:
            Path to the local GGUF file, or ``None`` if not found.
        """
        cache_dir = self.get_cache_dir()
        model_dir = cache_dir / model_name

        # 1. Maru cache (symlink or actual file)
        meta = _read_metadata(model_name, cache_dir)
        filename: str | None = meta["filename"] if meta is not None else None
        if filename is not None:
            candidate = model_dir / filename
            if candidate.exists() or candidate.is_symlink():
                return candidate

        # 2. HF Hub cache
        try:
            repo_id, filename = _resolve_model(model_name, cache_dir)
        except ValueError:
            return None
        hf_path = _get_hf_cache_path(repo_id, filename)
        return hf_path

    def download_model(
        self,
        model_name: str,
        progress_callback: Callable[[int, int, float, float], None] | None = None,
    ) -> Path:
        """Download a model from GitHub releases (primary) or HuggingFace Hub (fallback).

        Supports split-file download for large models (>1GB) from GitHub Release.
        Automatically detects and merges split chunks.

        Args:
            model_name: Friendly name of the model.
            progress_callback: opt callback invoked at the start and end of
                the download with ``(cur, total, speed, eta)``.
        Returns:
            Path to the locally cached GGUF file.
        Raises:
            RuntimeError: If the model cannot be downloaded from any source.
            ValueError: If the model name cannot be resolved.
        """
        cache_dir = self.get_cache_dir()
        repo_id, filename = _resolve_model(model_name, cache_dir)
        model_dir = cache_dir / model_name
        model_dir.mkdir(parents=True, exist_ok=True)
        local_path = model_dir / filename
        if progress_callback is not None:
            progress_callback(0, 0, 0.0, 0.0)

        # Primary: GitHub Release (single file or split chunks)
        github_url = _GITHUB_URLS.get(model_name)
        if github_url is not None:
            # Try single-file download first
            try:
                self._download_with_progress(github_url, local_path, progress_callback)
                file_size = local_path.stat().st_size
                size_mb = round(file_size / (1024 * 1024), 2)
                sha256 = _compute_sha256(local_path)
                if progress_callback is not None:
                    progress_callback(file_size, file_size, 0.0, 0.0)
                metadata: dict[str, Any] = {
                    "model_name": model_name,
                    "repo_id": repo_id,
                    "filename": filename,
                    "download_date": datetime.now(timezone.utc).isoformat(),
                    "size_mb": size_mb,
                    "sha256": sha256,
                    "source": "github",
                    "url": github_url,
                    "selected_for": {
                        "hardware_profile": {},
                    },
                }
                _write_metadata(model_name, metadata, cache_dir)
                return local_path
            except Exception:
                # Single file failed, try split chunks
                if local_path.exists():
                    local_path.unlink()
                if self._download_chunks(model_name, local_path, progress_callback):
                    file_size = local_path.stat().st_size
                    size_mb = round(file_size / (1024 * 1024), 2)
                    sha256 = _compute_sha256(local_path)
                    metadata = {
                        "model_name": model_name,
                        "repo_id": repo_id,
                        "filename": filename,
                        "download_date": datetime.now(timezone.utc).isoformat(),
                        "size_mb": size_mb,
                        "sha256": sha256,
                        "source": "github_split",
                        "url": github_url,
                        "selected_for": {
                            "hardware_profile": {},
                        },
                    }
                    _write_metadata(model_name, metadata, cache_dir)
                    return local_path
                # Both single and split failed, fall through to HF Hub

        # Fallback: HuggingFace Hub
        if not _HF_AVAILABLE:
            raise RuntimeError(
                f"Failed to download {model_name} from GitHub and "
                "huggingface_hub is not installed for fallback."
            )
        hf_path_str = hf_hub_download(repo_id, filename)  # type: ignore[arg-type]
        hf_path = Path(hf_path_str)
        # Ensure symlink points to the latest cached blob
        if local_path.exists() or local_path.is_symlink():
            local_path.unlink()
        try:
            local_path.symlink_to(hf_path)
        except OSError:
            # Fallback for Windows without symlink privileges: copy the file
            shutil.copy2(hf_path, local_path)
        file_size = hf_path.stat().st_size
        size_mb = round(file_size / (1024 * 1024), 2)
        sha256 = _compute_sha256(hf_path)
        if progress_callback is not None:
            progress_callback(file_size, file_size, 0.0, 0.0)
        metadata = {
            "model_name": model_name,
            "repo_id": repo_id,
            "filename": filename,
            "download_date": datetime.now(timezone.utc).isoformat(),
            "size_mb": size_mb,
            "sha256": sha256,
            "source": "huggingface_hub",
            "selected_for": {
                "hardware_profile": {},
            },
        }
        _write_metadata(model_name, metadata, cache_dir)
        return local_path

    def ensure_model(self, model_name: str) -> Path:
        """Return the local path for a model, downloading it if necessary.

        Args:
            model_name: Friendly name of the model.

        Returns:
            Path to the local GGUF file.

        Raises:
            RuntimeError: If ``huggingface_hub`` is not installed and the model
                is not already cached.
            ValueError: If the model name cannot be resolved.
        """
        existing = self.get_model_path(model_name)
        if existing is not None:
            return existing
        return self.download_model(model_name)

    def list_cached_models(self) -> list[dict[str, Any]]:
        """List all models present in the maru cache with their metadata.

        Returns:
            List of metadata dictionaries (one per cached model).
        """
        cache_dir = self.get_cache_dir()
        models: list[dict[str, Any]] = []
        for item in cache_dir.iterdir():
            if item.is_dir():
                meta = _read_metadata(item.name, cache_dir)
                if meta is not None:
                    models.append(meta)
        return models

    def _download_with_progress(
        self,
        url: str,
        dest: Path,
        progress_callback: Callable[[int, int, float, float], None] | None = None,
    ) -> None:
        """Download a file from a URL with progress reporting.
        Args:
            url: Direct download URL.
            dest: Destination path.
            progress_callback: Optional callback ``(cur, total, speed, eta)``.
        """
        start_time = datetime.now(timezone.utc)
        with httpx.stream("GET", url, follow_redirects=True, timeout=300.0) as response:
            response.raise_for_status()
            total = int(response.headers.get("content-length", 0))
            downloaded = 0
            with dest.open("wb") as f:
                for chunk in response.iter_bytes(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback is not None and total > 0:
                        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
                        speed = downloaded / elapsed if elapsed > 0 else 0.0
                        eta = (total - downloaded) / speed if speed > 0 else 0.0
                        progress_callback(downloaded, total, speed, eta)

    def remove_model(self, model_name: str) -> bool:
        """Remove a model and its metadata from the maru cache.

        Args:
            model_name: Friendly name of the model.

        Returns:
            ``True`` if the model was removed, ``False`` if it did not exist.
        """
        model_dir = self.get_cache_dir() / model_name
        if not model_dir.exists():
            return False
        shutil.rmtree(model_dir)
        return True

    def get_metadata(self, model_name: str) -> dict[str, Any] | None:
        """Read metadata for a cached model.

        Args:
            model_name: Friendly name of the model.

        Returns:
            Metadata dictionary, or ``None`` if not cached.
        """
        return _read_metadata(model_name, self.get_cache_dir())
