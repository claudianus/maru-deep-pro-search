"""Semantic ranking using lightweight sentence embeddings.

Optional enhancement that adds dense vector similarity on top of BM25
for significantly better relevance ranking. Falls back gracefully when
sentence-transformers is not installed.

Models used:
- Bi-Encoder: intfloat/multilingual-e5-small (33M params, ~100MB RAM, 0.6ms/sentence)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..engines.base import SearchResult


class _LazyModels:
    """Lazy-initialized sentence-transformers models."""

    _bi_encoder = None
    _available: bool | None = None
    _model_name: str = "intfloat/multilingual-e5-small"

    @classmethod
    def _init(cls) -> bool:
        if cls._available is not None:
            return cls._available
        try:
            from sentence_transformers import SentenceTransformer

            logger.info("Loading semantic ranking model...")
            cls._bi_encoder = SentenceTransformer(cls._model_name, device="cpu")
            cls._available = True
            logger.info("Semantic ranking ready (%s)", cls._model_name)
        except ImportError:
            cls._available = False
            logger.debug("sentence-transformers not installed; semantic ranking disabled")
        return cls._available

    @classmethod
    def available(cls) -> bool:
        return cls._init()

    @classmethod
    def bi_encoder(cls):
        cls._init()
        return cls._bi_encoder


class SemanticRanker:
    """Hybrid semantic ranking utilities.

    All methods are no-ops when sentence-transformers is not installed,
    ensuring zero breaking changes for minimal installs.
    """

    @staticmethod
    def available() -> bool:
        return _LazyModels.available()

    @staticmethod
    def score_results(query: str, results: list[SearchResult]) -> list[float]:
        """Return cosine similarity scores between query and each result.

        Scores are in [0, 1]. Higher = more semantically relevant.
        """
        bi = _LazyModels.bi_encoder()
        if bi is None or not results:
            return [0.0] * len(results)

        try:
            from sentence_transformers.util import cos_sim

            query_emb = bi.encode([query], convert_to_tensor=False, show_progress_bar=False)
            docs = [f"{r.title} {r.snippet}" for r in results]
            doc_embs = bi.encode(docs, convert_to_tensor=False, show_progress_bar=False)

            sims = cos_sim(query_emb, doc_embs)[0]
            return [float(s) for s in sims]
        except Exception as exc:
            logger.warning("Semantic scoring failed: %s", exc)
            return [0.0] * len(results)

    @staticmethod
    def sentence_similarity(sentences: list[str]) -> list[list[float]]:
        """Return pairwise cosine similarity matrix for sentences.

        Useful for deduplication and clustering.
        """
        bi = _LazyModels.bi_encoder()
        if bi is None or len(sentences) < 2:
            return []

        try:
            from sentence_transformers.util import cos_sim

            embs = bi.encode(sentences, convert_to_tensor=False, show_progress_bar=False)
            return cos_sim(embs, embs).tolist()
        except Exception as exc:
            logger.warning("Sentence similarity failed: %s", exc)
            return []

    @staticmethod
    def query_sentence_similarity_batch(query: str, sentences: list[str]) -> list[float]:
        """Return cosine similarity between query and each sentence."""
        bi = _LazyModels.bi_encoder()
        if bi is None or not sentences:
            return [0.0] * len(sentences)
        try:
            from sentence_transformers.util import cos_sim

            all_texts = [query] + sentences
            embs = bi.encode(all_texts, convert_to_tensor=False, show_progress_bar=False)
            query_emb = embs[0:1]
            sent_embs = embs[1:]
            sims = cos_sim(query_emb, sent_embs)[0]
            return [float(s) for s in sims]
        except Exception as exc:
            logger.warning("Batch sentence similarity failed: %s", exc)
            return [0.0] * len(sentences)

    @staticmethod
    def semantic_dedupe(sentences: list[str], threshold: float = 0.82) -> list[str]:
        """Remove semantically duplicate sentences using embeddings.

        More robust than Jaccard for paraphrased duplicates.
        """
        bi = _LazyModels.bi_encoder()
        if bi is None or len(sentences) < 2:
            return sentences

        try:
            from sentence_transformers.util import cos_sim

            embs = bi.encode(sentences, convert_to_tensor=False, show_progress_bar=False)
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
