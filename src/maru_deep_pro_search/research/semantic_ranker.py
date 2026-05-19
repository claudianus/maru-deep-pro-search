"""Semantic ranking using local sentence embeddings (always enabled).

Combines dense vector similarity with BM25 and metadata signals.
Model: ``ibm-granite/granite-embedding-97m-multilingual-r2`` by default (see ``embeddings``).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ..embeddings import encode_passages, encode_queries, get_encoder

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..engines.base import SearchResult


class SemanticRanker:
    """Hybrid semantic ranking utilities (requires sentence-transformers)."""

    @staticmethod
    def available() -> bool:
        """Semantic ranking is always required; probes model load."""
        get_encoder()
        return True

    @staticmethod
    def score_results(query: str, results: list[SearchResult]) -> list[float]:
        """Return cosine similarity scores between query and each result.

        Scores are in [0, 1]. Higher = more semantically relevant.
        """
        if not results:
            return []

        try:
            from sentence_transformers.util import cos_sim

            query_emb = encode_queries([query])
            docs = [f"{r.title} {r.snippet}" for r in results]
            doc_embs = encode_passages(docs)
            sims = cos_sim(query_emb, doc_embs)[0]
            return [float(s) for s in sims]
        except Exception as exc:
            logger.warning("Semantic scoring failed: %s", exc)
            return [0.0] * len(results)

    @staticmethod
    def sentence_similarity(sentences: list[str]) -> list[list[float]]:
        """Return pairwise cosine similarity matrix for sentences."""
        if len(sentences) < 2:
            return []

        try:
            from sentence_transformers.util import cos_sim

            embs = encode_passages(sentences)
            return cos_sim(embs, embs).tolist()  # type: ignore[no-any-return]
        except Exception as exc:
            logger.warning("Sentence similarity failed: %s", exc)
            return []

    @staticmethod
    def query_sentence_similarity_batch(query: str, sentences: list[str]) -> list[float]:
        """Return cosine similarity between query and each sentence."""
        if not sentences:
            return []

        try:
            from sentence_transformers.util import cos_sim

            query_emb = encode_queries([query])
            sent_embs = encode_passages(sentences)
            sims = cos_sim(query_emb, sent_embs)[0]
            return [float(s) for s in sims]
        except Exception as exc:
            logger.warning("Batch sentence similarity failed: %s", exc)
            return [0.0] * len(sentences)

    @staticmethod
    def semantic_dedupe(sentences: list[str], threshold: float = 0.82) -> list[str]:
        """Remove semantically duplicate sentences using embeddings."""
        if len(sentences) < 2:
            return sentences

        try:
            from sentence_transformers.util import cos_sim

            embs = encode_passages(sentences)
            sim_matrix = cos_sim(embs, embs)

            unique: list[str] = []
            for i, sent in enumerate(sentences):
                is_dup = False
                for j, _existing in enumerate(unique):
                    if sim_matrix[i][j] > threshold:
                        is_dup = True
                        break
                if not is_dup:
                    unique.append(sent)
            return unique
        except Exception as exc:
            logger.warning("Semantic dedupe failed: %s", exc)
            return sentences
