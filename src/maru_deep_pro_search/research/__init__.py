"""Research pipeline for maru-search."""

from .deep import CitedSource, ResearchResult, deep_research, format_for_llm, research_quality_line
from .expander import expand_query, extract_keywords
from .fetch_planner import PlannedRead, plan_reads
from .pipeline import (
    PersistedResearch,
    answer_quality_suffix,
    append_research_footer,
    persist_research_artifacts,
)
from .ranker import RankedResult, merge_results, rank_pages
from .receipt import generate_research_id, write_receipt

__all__ = [
    "PersistedResearch",
    "answer_quality_suffix",
    "append_research_footer",
    "persist_research_artifacts",
    "CitedSource",
    "PlannedRead",
    "RankedResult",
    "ResearchResult",
    "deep_research",
    "expand_query",
    "extract_keywords",
    "format_for_llm",
    "generate_research_id",
    "merge_results",
    "plan_reads",
    "rank_pages",
    "research_quality_line",
    "write_receipt",
]
