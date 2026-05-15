"""Knowledge persistence layer — SQLite-backed cache with semantic similarity."""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("maru_deep_pro_search.harness.persistence")


@dataclass(frozen=True)
class KnowledgeEntry:
    """A single piece of persisted knowledge."""

    query: str
    answer: str
    sources: list[dict[str, Any]]
    created_at: str = ""
    embedding: list[float] | None = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def from_json(cls, raw: str) -> KnowledgeEntry:
        data = json.loads(raw)
        return cls(**data)


class KnowledgeStore:
    """SQLite-backed knowledge store with optional semantic search.

    Falls back to exact + substring match when sentence-transformers
    is not available (keeping the zero-API-key promise).
    """

    _instances: dict[str, KnowledgeStore] = {}
    _lock = threading.Lock()

    _db_path: str
    _conn: sqlite3.Connection | None
    _encoder: Any
    _initialized: bool

    def __new__(cls, db_path: str | Path | None = None) -> KnowledgeStore:
        path = str(db_path or cls._default_db_path())
        with cls._lock:
            if path not in cls._instances:
                instance = super().__new__(cls)
                instance._db_path = path
                instance._conn = None
                instance._encoder = None
                instance._initialized = False
                cls._instances[path] = instance
            return cls._instances[path]

    # ── lifecycle ───────────────────────────────────────────────

    def _connect(self) -> sqlite3.Connection:
        if self._conn is None:
            Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._ensure_schema()
        return self._conn

    def _ensure_schema(self) -> None:
        conn = self._conn
        assert conn is not None
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_hash TEXT UNIQUE NOT NULL,
                query TEXT NOT NULL,
                answer TEXT NOT NULL,
                sources TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                embedding TEXT,
                access_count INTEGER DEFAULT 1,
                last_accessed TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_query_hash ON knowledge(query_hash);
            CREATE INDEX IF NOT EXISTS idx_created ON knowledge(created_at);
            CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts
                USING fts5(query, answer, sources, content='knowledge', content_rowid='id');

            CREATE TABLE IF NOT EXISTS domain_stats (
                domain TEXT PRIMARY KEY,
                avg_duration_ms REAL DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                last_accessed TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_domain_last ON domain_stats(last_accessed);
            """
        )
        conn.commit()

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    # ── public API ──────────────────────────────────────────────

    def save(
        self,
        query: str,
        answer: str,
        sources: list[dict[str, Any]] | None = None,
    ) -> None:
        """Persist a research result."""
        conn = self._connect()
        now = datetime.now(timezone.utc).isoformat()
        q_hash = self._hash_query(query)
        sources_json = json.dumps(sources or [], ensure_ascii=False)

        # Try to compute embedding if model available
        embedding_json: str | None = None
        emb = self._compute_embedding(query + " " + answer[:500])
        if emb is not None:
            embedding_json = json.dumps(emb)

        conn.execute(
            """
            INSERT INTO knowledge (query_hash, query, answer, sources, created_at, embedding)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(query_hash) DO UPDATE SET
                answer=excluded.answer,
                sources=excluded.sources,
                created_at=excluded.created_at,
                embedding=excluded.embedding,
                access_count=access_count+1,
                last_accessed=?
            """,
            (q_hash, query, answer, sources_json, now, embedding_json, now),
        )
        conn.commit()
        logger.debug("Knowledge saved: %s", query[:60])

    def query(
        self,
        query: str,
        semantic_threshold: float = 0.82,
        max_results: int = 3,
        max_age_days: int = 30,
    ) -> list[KnowledgeEntry]:
        """Search knowledge base: exact → substring → semantic fallback."""
        conn = self._connect()
        now = datetime.now(timezone.utc)

        # 1. Exact match
        row = conn.execute(
            "SELECT * FROM knowledge WHERE query_hash = ?",
            (self._hash_query(query),),
        ).fetchone()
        if row:
            self._bump_access(row["id"], now.isoformat())
            return [self._row_to_entry(row)]

        # 2. Substring / FTS match
        fts_rows = conn.execute(
            """
            SELECT k.* FROM knowledge k
            JOIN knowledge_fts fts ON k.id = fts.rowid
            WHERE knowledge_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (query, max_results),
        ).fetchall()
        if fts_rows:
            for r in fts_rows:
                self._bump_access(r["id"], now.isoformat())
            return [self._row_to_entry(r) for r in fts_rows]

        # 3. Semantic match (if encoder available)
        semantic = self._semantic_search(query, threshold=semantic_threshold, limit=max_results)
        if semantic:
            for e in semantic:
                self._bump_access_by_query(e.query, now.isoformat())
            return semantic

        return []

    def get_stats(self) -> dict[str, Any]:
        """Return store statistics."""
        conn = self._connect()
        total = conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]
        recent = conn.execute(
            "SELECT COUNT(*) FROM knowledge WHERE created_at > datetime('now', '-7 days')"
        ).fetchone()[0]
        top = conn.execute(
            "SELECT query, access_count FROM knowledge ORDER BY access_count DESC LIMIT 5"
        ).fetchall()
        return {
            "total_entries": total,
            "last_7_days": recent,
            "top_queries": [{"query": r["query"], "access_count": r["access_count"]} for r in top],
        }

    def prune(self, max_age_days: int = 30) -> int:
        """Remove entries older than max_age_days. Returns count deleted."""
        conn = self._connect()
        cursor = conn.execute(
            "DELETE FROM knowledge WHERE created_at < datetime('now', ?)",
            (f"-{max_age_days} days",),
        )
        conn.commit()
        deleted = cursor.rowcount
        logger.info("Pruned %d old knowledge entries", deleted)
        return deleted

    def record_domain_fetch(self, domain: str, duration_ms: float, success: bool) -> None:
        """Record fetch performance for a domain."""
        conn = self._connect()
        now = datetime.now(timezone.utc).isoformat()
        row = conn.execute(
            "SELECT avg_duration_ms, success_count, failure_count FROM domain_stats WHERE domain = ?",
            (domain,),
        ).fetchone()
        if row:
            old_avg = row["avg_duration_ms"] or 0
            old_succ = row["success_count"] or 0
            old_fail = row["failure_count"] or 0
            total = old_succ + old_fail + 1
            new_avg = (old_avg * (total - 1) + duration_ms) / total
            conn.execute(
                """UPDATE domain_stats
                   SET avg_duration_ms = ?, success_count = ?, failure_count = ?, last_accessed = ?
                   WHERE domain = ?""",
                (
                    new_avg,
                    old_succ + (1 if success else 0),
                    old_fail + (0 if success else 1),
                    now,
                    domain,
                ),
            )
        else:
            conn.execute(
                """INSERT INTO domain_stats (domain, avg_duration_ms, success_count, failure_count, last_accessed)
                   VALUES (?, ?, ?, ?, ?)""",
                (domain, duration_ms, 1 if success else 0, 0 if success else 1, now),
            )
        conn.commit()

    def export_bundle(self, path: Path | str, max_entries: int = 500) -> int:
        """Export knowledge rows to a portable JSON bundle (no embeddings)."""
        out = Path(path)
        conn = self._connect()
        rows = conn.execute(
            """
            SELECT query, answer, sources, created_at
            FROM knowledge
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (max_entries,),
        ).fetchall()
        entries = [
            {
                "query": row["query"],
                "answer": row["answer"],
                "sources": json.loads(row["sources"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]
        payload = {"format": "maru-knowledge-v1", "count": len(entries), "entries": entries}
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return len(entries)

    def import_bundle(self, path: Path | str) -> int:
        """Import entries from a maru-knowledge-v1 JSON bundle."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        entries = data.get("entries", [])
        if not isinstance(entries, list):
            return 0
        count = 0
        for item in entries:
            if not isinstance(item, dict):
                continue
            query = item.get("query")
            answer = item.get("answer")
            if not isinstance(query, str) or not isinstance(answer, str):
                continue
            sources = item.get("sources")
            if not isinstance(sources, list):
                sources = []
            self.save(query, answer, sources)
            count += 1
        return count

    def get_domain_stats(self, domain: str) -> dict | None:
        """Get performance stats for a domain."""
        conn = self._connect()
        row = conn.execute(
            "SELECT avg_duration_ms, success_count, failure_count, last_accessed FROM domain_stats WHERE domain = ?",
            (domain,),
        ).fetchone()
        if not row:
            return None
        total = row["success_count"] + row["failure_count"]
        return {
            "avg_duration_ms": row["avg_duration_ms"],
            "success_rate": row["success_count"] / total if total > 0 else 0.0,
            "failure_count": row["failure_count"],
            "total": total,
        }

    # ── helpers ─────────────────────────────────────────────────

    @staticmethod
    def _default_db_path() -> Path:
        return Path.cwd() / ".maru" / "knowledge.db"

    @staticmethod
    def _hash_query(query: str) -> str:
        return hashlib.sha256(query.lower().strip().encode()).hexdigest()[:32]

    def _row_to_entry(self, row: sqlite3.Row) -> KnowledgeEntry:
        emb = None
        if row["embedding"]:
            emb = json.loads(row["embedding"])
        return KnowledgeEntry(
            query=row["query"],
            answer=row["answer"],
            sources=json.loads(row["sources"]),
            created_at=row["created_at"],
            embedding=emb,
        )

    def _bump_access(self, row_id: int, now: str) -> None:
        if self._conn:
            self._conn.execute(
                "UPDATE knowledge SET access_count = access_count + 1, last_accessed = ? WHERE id = ?",
                (now, row_id),
            )
            self._conn.commit()

    def _bump_access_by_query(self, query: str, now: str) -> None:
        if self._conn:
            self._conn.execute(
                "UPDATE knowledge SET access_count = access_count + 1, last_accessed = ? WHERE query_hash = ?",
                (now, self._hash_query(query)),
            )
            self._conn.commit()

    # ── semantic search (optional) ──────────────────────────────

    def _compute_embedding(self, text: str) -> list[float] | None:
        if self._encoder is None:
            try:
                from sentence_transformers import SentenceTransformer

                self._encoder = SentenceTransformer("intfloat/multilingual-e5-small")
            except Exception:
                return None
        try:
            import numpy as np

            emb = self._encoder.encode([text], convert_to_numpy=True)
            emb = emb / (np.linalg.norm(emb, axis=1, keepdims=True) + 1e-8)
            return emb[0].tolist()  # type: ignore[no-any-return]
        except Exception:
            return None

    def _semantic_search(self, query: str, threshold: float, limit: int) -> list[KnowledgeEntry]:
        q_emb = self._compute_embedding(query)
        if q_emb is None:
            return []

        conn = self._connect()
        rows = conn.execute("SELECT * FROM knowledge WHERE embedding IS NOT NULL").fetchall()
        if not rows:
            return []

        import numpy as np

        q_vec = np.array(q_emb)
        scored: list[tuple[float, sqlite3.Row]] = []
        for row in rows:
            emb = json.loads(row["embedding"])
            vec = np.array(emb)
            sim = float(np.dot(q_vec, vec))
            if sim >= threshold:
                scored.append((sim, row))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [self._row_to_entry(r) for _, r in scored[:limit]]
