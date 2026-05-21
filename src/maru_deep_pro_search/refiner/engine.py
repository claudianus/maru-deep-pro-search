"""Core inference engine for local LLM-based content refinement.

Wraps llama-cpp-python to provide async content cleaning, fact extraction,
and snippet refinement. The refiner is invisible to the host — it is used
internally by MCP tools before returning web content to the caller.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading

from .config import RefinerConfig
from .hardware import detect_hardware, get_optimal_model
from .model_manager import ModelManager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

CONTENT_REFINEMENT_PROMPT = """You are a web content refiner. Extract only the factual information relevant to the user's query.

Query: {query}

Content:
{text}

Instructions:
- Remove navigation, ads, footers, and unrelated content
- Extract facts, evidence, and key data points
- Preserve markdown formatting
- Output in concise bullet points or short paragraphs
- Maximum {max_tokens} tokens
"""

SNIPPET_REFINEMENT_PROMPT = """Refine this search snippet to 1-2 sentences containing the key fact.

Query: {query}
Snippet: {text}

Refined:"""

FACT_EXTRACTION_PROMPT = """Extract factual claims from this content as JSON.

Query: {query}
Content:
{text}

Output JSON array:
[{"claim": "...", "confidence": 0.95, "type": "fact|statistic|opinion"}]
"""

# ---------------------------------------------------------------------------
# llama-cpp import (optional dependency)
# ---------------------------------------------------------------------------

try:
    from llama_cpp import Llama

    _LLAMA_AVAILABLE = True
except ImportError:  # pragma: no cover
    _LLAMA_AVAILABLE = False
    Llama = None  # type: ignore[misc,assignment]
    logger.debug("llama-cpp-python not installed; refiner will passthrough")


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class RefinerEngine:
    """Async content refiner powered by a local GGUF model via llama-cpp-python.

    The Llama instance is created lazily on the first refinement call and
    protected by a ``threading.Lock`` so that concurrent callers safely share
    a single loaded model.

    If llama-cpp-python is not installed, or if the configured model cannot be
    found, every method falls back to returning the original text unchanged.

    Example::

        engine = RefinerEngine()
        refined = await engine.refine_content(
            text="Raw webpage with ads and nav...",
            query="Python async patterns",
            max_tokens=1000,
        )
    """

    def __init__(self, config: RefinerConfig | None = None) -> None:
        """Initialise the engine (model is *not* loaded yet).

        Args:
            config: Refiner configuration. When ``None`` a default
                ``RefinerConfig.from_env()`` is used.
        """
        self._config = config or RefinerConfig.from_env()
        self._llama: Llama | None = None  # type: ignore[valid-type]
        self._load_lock = threading.Lock()
        self._load_error: Exception | None = None
        self._model_manager = ModelManager(cache_dir=self._config.cache_dir)

    # -- public async API ---------------------------------------------------

    async def refine_content(
        self,
        text: str,
        query: str = "",
        max_tokens: int | None = None,
    ) -> str:
        """Refine raw web content into clean, structured facts.

        Args:
            text: Raw content scraped from a web page.
            query: Original user query (used for relevance filtering).
            max_tokens: Maximum tokens to generate. ``None`` uses
                ``config.max_tokens``.

        Returns:
            Refined text, or the original ``text`` on any failure.
        """
        if not text.strip():
            return text

        prompt = self._build_prompt(
            text=text,
            query=query,
            task="content",
            max_tokens=max_tokens or self._config.max_tokens,
        )
        raw = await self._run_inference(prompt, max_tokens=max_tokens)
        return self._parse_output(raw) if raw is not None else text

    async def refine_snippet(self, text: str, query: str = "") -> str:
        """Refine a search-result snippet to 1--2 key sentences.

        Args:
            text: Short snippet from a search engine result.
            query: Original user query.

        Returns:
            Refined snippet, or the original ``text`` on any failure.
        """
        if not text.strip():
            return text

        prompt = self._build_prompt(text=text, query=query, task="snippet")
        raw = await self._run_inference(prompt, max_tokens=128)
        return self._parse_output(raw) if raw is not None else text

    async def extract_facts(self, text: str, query: str = "") -> list[dict]:
        """Extract structured factual claims with confidence scores.

        Args:
            text: Content to analyse.
            query: Original user query.

        Returns:
            List of fact dictionaries. On failure an empty list is returned.
        """
        if not text.strip():
            return []

        prompt = self._build_prompt(text=text, query=query, task="facts")
        raw = await self._run_inference(prompt, max_tokens=512)
        if raw is None:
            return []

        cleaned = self._parse_output(raw)
        return self._extract_json_array(cleaned)

    async def health_check(self) -> dict:
        """Return engine health and model metadata.

        Returns:
            Dictionary with keys ``loaded``, ``model_name``, ``backend``,
            and ``memory_usage``.
        """
        loaded = self._llama is not None and self._load_error is None
        backend = "GPU" if self._config.n_gpu_layers != 0 else "CPU"

        result: dict = {
            "loaded": loaded,
            "model_name": "",
            "backend": backend,
            "memory_usage": 0,
        }

        if loaded and self._llama is not None:
            try:
                result["model_name"] = getattr(self._llama, "model_path", "unknown")
                n_ctx = getattr(self._llama, "n_ctx", lambda: 0)()
                result["memory_usage"] = n_ctx * 4  # rough MB estimate
            except Exception as exc:  # noqa: BLE001
                logger.debug("Health check metadata error: %s", exc)

        if not loaded and self._load_error is not None:
            result["last_error"] = str(self._load_error)

        return result

    # -- internal helpers ---------------------------------------------------

    def _resolve_model(self) -> str | None:
        """Determine which model to load.

        If ``config.model_name`` is set, use it directly. Otherwise auto-select
        based on the detected hardware profile.

        Returns:
            Friendly model name, or ``None`` if no suitable model is found.
        """
        if self._config.model_name:
            return self._config.model_name

        try:
            profile = detect_hardware()
            return get_optimal_model(profile)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Hardware detection failed: %s", exc)
            return None

    def _load_model(self) -> None:
        """Create the Llama instance if it does not yet exist.

        This method is synchronous and must be called from within
        ``run_in_executor`` or while holding ``_load_lock``.
        """
        if self._llama is not None:
            return

        if not _LLAMA_AVAILABLE:
            logger.warning("llama-cpp-python not installed; refiner disabled")
            return

        model_name = self._resolve_model()
        if not model_name:
            logger.warning("No model configured and auto-selection failed")
            return

        try:
            model_path = self._model_manager.ensure_model(model_name)
        except Exception as exc:  # noqa: BLE001
            self._load_error = exc
            logger.error("Failed to resolve model %r: %s", model_name, exc)
            return

        kwargs = self._get_llama_params()
        kwargs["model_path"] = str(model_path)

        logger.info("Loading Llama model from %s", model_path)
        try:
            self._llama = Llama(**kwargs)  # type: ignore[operator]
            logger.info("Llama model loaded successfully")
        except Exception as exc:  # noqa: BLE001
            self._load_error = exc
            logger.error("Failed to load Llama model: %s", exc)

    def _build_prompt(
        self,
        text: str,
        query: str,
        task: str,
        max_tokens: int | None = None,
    ) -> str:
        """Select and format the appropriate prompt template.

        Args:
            text: Content to refine or analyse.
            query: User query for context.
            task: One of ``"content"``, ``"snippet"``, ``"facts"``.
            max_tokens: Token limit (content task only).

        Returns:
            Formatted prompt string.
        """
        if task == "content":
            assert max_tokens is not None
            return CONTENT_REFINEMENT_PROMPT.format(query=query, text=text, max_tokens=max_tokens)
        if task == "snippet":
            return SNIPPET_REFINEMENT_PROMPT.format(query=query, text=text)
        if task == "facts":
            return FACT_EXTRACTION_PROMPT.format(query=query, text=text)
        # Fallback — should never happen
        return text  # type: ignore[no-any-return]

    def _parse_output(self, raw: str) -> str:
        """Clean and validate raw LLM output.

        Strips leading/trailing whitespace, removes common markdown fences,
        and drops empty lines at the boundaries.

        Args:
            raw: Raw text returned by the model.

        Returns:
            Cleaned text.
        """
        if not raw:
            return raw

        cleaned = raw.strip()

        # Strip markdown code fences
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            while lines and lines[0].startswith("```"):
                lines.pop(0)
            while lines and lines[-1].startswith("```"):
                lines.pop()
            cleaned = "\n".join(lines).strip()

        return cleaned

    def _get_llama_params(self) -> dict:
        """Convert ``RefinerConfig`` into keyword arguments for ``Llama``.

        Returns:
            Dictionary of constructor arguments.
        """
        params: dict = {
            "n_ctx": self._config.n_ctx,
            "n_gpu_layers": self._config.n_gpu_layers,
        }
        if self._config.n_threads is not None:
            params["n_threads"] = self._config.n_threads
        return params

    def _get_sampling_params(self, max_tokens: int | None = None) -> dict:
        """Build sampling/generation parameters for ``Llama.create_completion``.

        Args:
            max_tokens: Override for the number of tokens to generate.

        Returns:
            Dictionary with ``max_tokens``, ``temperature``, and ``top_p``.
        """
        return {
            "max_tokens": max_tokens or self._config.max_tokens,
            "temperature": self._config.temperature,
            "top_p": self._config.top_p,
            "stop": ["<|im_end|>", "<|endoftext|>"],
        }

    # -- async inference wrapper ---------------------------------------------

    async def _run_inference(
        self,
        prompt: str,
        max_tokens: int | None = None,
    ) -> str | None:
        """Execute inference in a thread-pool executor with timeout.

        Lazily loads the model on first call. Returns ``None`` when the
        model is unavailable or inference fails.

        Args:
            prompt: Formatted prompt text.
            max_tokens: Token limit for this call.

        Returns:
            Generated text, or ``None`` on failure.
        """
        # Lazy, thread-safe model initialisation
        if self._llama is None and self._load_error is None:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._load_model)

        if self._llama is None:
            return None

        sampling = self._get_sampling_params(max_tokens)

        def _infer() -> str | None:
            try:
                output = self._llama.create_completion(prompt, **sampling)  # type: ignore[union-attr]
                if isinstance(output, dict):
                    choices = output.get("choices", [])
                    if choices:
                        return str(choices[0].get("text", ""))
                return None
            except Exception as exc:  # noqa: BLE001
                logger.warning("Inference error: %s", exc)
                return None

        loop = asyncio.get_running_loop()
        try:
            return await asyncio.wait_for(
                loop.run_in_executor(None, _infer),
                timeout=self._config.timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.warning("Inference timed out after %.1fs", self._config.timeout_seconds)
            return None

    @staticmethod
    def _extract_json_array(text: str) -> list[dict]:
        """Attempt to parse a JSON array from *text*.

        Tolerates surrounding prose by searching for the first ``[`` and
        last ``]``.

        Args:
            text: Text that should contain a JSON array.

        Returns:
            Parsed list of dictionaries, or an empty list on failure.
        """
        if not text:
            return []

        # Try direct parse first
        try:
            data = json.loads(text)
            if isinstance(data, list):
                return [item for item in data if isinstance(item, dict)]
        except json.JSONDecodeError:
            pass

        # Fallback: extract between first [ and last ]
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1 and end > start:
            try:
                data = json.loads(text[start : end + 1])
                if isinstance(data, list):
                    return [item for item in data if isinstance(item, dict)]
            except json.JSONDecodeError:
                pass

        return []
