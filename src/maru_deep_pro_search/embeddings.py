"""Shared local embedding model for ranking, knowledge store, and security.

Default: ``ibm-granite/granite-embedding-97m-multilingual-r2`` — 97M params, Apache 2.0,
~60.3 MTEB multilingual retrieval (IBM R2 report vs ~50.9 for multilingual-e5-small).
Override with ``MARU_EMBEDDING_MODEL`` (e.g. ``intfloat/multilingual-e5-small``).

E5-family models use ``query:`` / ``passage:`` prefixes; Granite needs no task prefix.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_EMBEDDING_MODEL = "ibm-granite/granite-embedding-97m-multilingual-r2"

_ENCODER: Any = None


class EmbeddingUnavailableError(RuntimeError):
    """Raised when sentence-transformers is missing or the model fails to load."""


def embedding_model_name() -> str:
    """Resolved Hugging Face model id for the active embedding backend."""
    raw = os.getenv("MARU_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL).strip()
    return raw or DEFAULT_EMBEDDING_MODEL


def _uses_e5_prefix(model_name: str) -> bool:
    return "e5" in model_name.lower()


def format_query(text: str) -> str:
    """Prefix text for query-side embedding (E5 convention)."""
    if _uses_e5_prefix(embedding_model_name()) and not text.lower().startswith("query:"):
        return f"query: {text}"
    return text


def format_passage(text: str) -> str:
    """Prefix text for document-side embedding (E5 convention)."""
    if _uses_e5_prefix(embedding_model_name()) and not text.lower().startswith("passage:"):
        return f"passage: {text}"
    return text


def get_encoder() -> Any:
    """Return a cached ``SentenceTransformer`` (loads on first use)."""
    global _ENCODER
    if _ENCODER is not None:
        return _ENCODER
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise EmbeddingUnavailableError(
            "sentence-transformers is required for maru-deep-pro-search. "
            "Install with: pip install maru-deep-pro-search"
        ) from exc
    model = embedding_model_name()
    logger.info("Loading embedding model %s...", model)
    try:
        _ENCODER = SentenceTransformer(model, device="cpu")
    except Exception as exc:
        raise EmbeddingUnavailableError(f"Failed to load embedding model {model!r}: {exc}") from exc
    logger.info("Embedding model ready (%s)", model)
    return _ENCODER


def encode_queries(texts: list[str]) -> Any:
    """Encode query strings (with model-specific prefixes)."""
    if not texts:
        return []
    encoder = get_encoder()
    return encoder.encode(
        [format_query(t) for t in texts],
        convert_to_tensor=False,
        show_progress_bar=False,
    )


def encode_passages(texts: list[str]) -> Any:
    """Encode document/passage strings (with model-specific prefixes)."""
    if not texts:
        return []
    encoder = get_encoder()
    return encoder.encode(
        [format_passage(t) for t in texts],
        convert_to_tensor=False,
        show_progress_bar=False,
    )


def warmup_embeddings() -> str:
    """Download (if needed), load, and run a probe encode to avoid first-search cold start.

    Returns:
        The model id that was warmed up.
    """
    model = embedding_model_name()
    logger.info("Warming up embedding model %s", model)
    encode_queries(["embedding warmup probe"])
    encode_passages(["embedding warmup passage"])
    logger.info("Embedding model warm (%s)", model)
    return model
