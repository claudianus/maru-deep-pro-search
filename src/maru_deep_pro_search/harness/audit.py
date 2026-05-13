"""MCP audit logging — behavioral monitoring for tool invocations.

Addresses the security gap identified in 2026 MCP research:
"No behavioral monitoring: There is no detection of unusual file access
patterns, no logging of tool invocations for security review."

Reference: Huang et al., "Are AI-assisted Development Tools Immune to
Prompt Injection?" (arXiv:2603.21642v1, 2026)
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("maru_deep_pro_search.harness.audit")


@dataclass
class ToolInvocation:
    """A single MCP tool invocation record."""

    tool_name: str
    params: dict[str, Any]
    result_size: int
    duration_ms: float
    timestamp: str
    anomaly_flags: list[str]


class AuditLogger:
    """SQLite-backed audit logger for MCP tool invocations.

    Creates behavioral baselines and flags anomalies such as:
    - Rapid-fire tool invocation (possible loop / poisoning)
    - Unusual parameter patterns
    - High result sizes (possible data exfiltration)
    """

    _instances: dict[str, AuditLogger] = {}
    _lock = threading.Lock()

    def __new__(cls, db_path: str | Path | None = None) -> AuditLogger:
        path = str(db_path or cls._default_db_path())
        with cls._lock:
            if path not in cls._instances:
                instance = super().__new__(cls)
                instance._db_path = path
                instance._conn: sqlite3.Connection | None = None
                cls._instances[path] = instance
            return cls._instances[path]

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
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                tool_name TEXT NOT NULL,
                params TEXT NOT NULL DEFAULT '{}',
                result_size INTEGER DEFAULT 0,
                duration_ms REAL DEFAULT 0,
                anomaly_flags TEXT DEFAULT '[]'
            );
            CREATE INDEX IF NOT EXISTS idx_audit_tool ON audit_log(tool_name);
            CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_log(timestamp);

            CREATE TABLE IF NOT EXISTS audit_stats (
                tool_name TEXT PRIMARY KEY,
                invocation_count INTEGER DEFAULT 0,
                avg_result_size REAL DEFAULT 0,
                avg_duration_ms REAL DEFAULT 0,
                last_invoked TEXT
            );
            """
        )
        conn.commit()

    def log(
        self,
        tool_name: str,
        params: dict[str, Any],
        result_size: int = 0,
        duration_ms: float = 0.0,
    ) -> ToolInvocation:
        """Log a tool invocation and return anomaly flags."""
        now = datetime.now(timezone.utc).isoformat()
        flags = self._detect_anomalies(tool_name, params, result_size, duration_ms)

        conn = self._connect()
        conn.execute(
            """
            INSERT INTO audit_log (timestamp, tool_name, params, result_size, duration_ms, anomaly_flags)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                now,
                tool_name,
                json.dumps(params, ensure_ascii=False),
                result_size,
                duration_ms,
                json.dumps(flags),
            ),
        )

        # Update rolling stats
        row = conn.execute(
            "SELECT invocation_count, avg_result_size, avg_duration_ms FROM audit_stats WHERE tool_name = ?",
            (tool_name,),
        ).fetchone()
        if row:
            n = row["invocation_count"] + 1
            new_avg_size = ((row["avg_result_size"] or 0) * (n - 1) + result_size) / n
            new_avg_dur = ((row["avg_duration_ms"] or 0) * (n - 1) + duration_ms) / n
            conn.execute(
                "UPDATE audit_stats SET invocation_count = ?, avg_result_size = ?, avg_duration_ms = ?, last_invoked = ? WHERE tool_name = ?",
                (n, new_avg_size, new_avg_dur, now, tool_name),
            )
        else:
            conn.execute(
                "INSERT INTO audit_stats (tool_name, invocation_count, avg_result_size, avg_duration_ms, last_invoked) VALUES (?, 1, ?, ?, ?)",
                (tool_name, result_size, duration_ms, now),
            )
        conn.commit()

        if flags:
            logger.warning("Anomaly detected in %s: %s", tool_name, flags)

        return ToolInvocation(
            tool_name=tool_name,
            params=params,
            result_size=result_size,
            duration_ms=duration_ms,
            timestamp=now,
            anomaly_flags=flags,
        )

    def _detect_anomalies(
        self,
        tool_name: str,
        params: dict[str, Any],
        result_size: int,
        duration_ms: float,
    ) -> list[str]:
        """Check for suspicious patterns."""
        flags: list[str] = []

        # 1. Rapid-fire detection
        conn = self._connect()
        recent = conn.execute(
            "SELECT COUNT(*) as cnt FROM audit_log WHERE tool_name = ? AND timestamp > datetime('now', '-5 seconds')",
            (tool_name,),
        ).fetchone()
        if recent and recent["cnt"] > 5:
            flags.append(f"rapid_fire:{recent['cnt']} in 5s")

        # 2. Unusually large result
        stats = conn.execute(
            "SELECT avg_result_size FROM audit_stats WHERE tool_name = ?",
            (tool_name,),
        ).fetchone()
        if stats and stats["avg_result_size"] and result_size > stats["avg_result_size"] * 5:
            flags.append(f"large_result:{result_size} vs avg {stats['avg_result_size']:.0f}")

        # 3. Suspicious parameter patterns
        params_str = json.dumps(params, ensure_ascii=False).lower()
        if any(k in params_str for k in ["ignore previous", "disregard", "forget"]):
            flags.append("suspicious_params")

        # 4. Very long duration
        if duration_ms > 30000:
            flags.append(f"slow_execution:{duration_ms:.0f}ms")

        return flags

    def get_stats(self) -> dict[str, Any]:
        """Return audit statistics."""
        conn = self._connect()
        total = conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
        recent = conn.execute(
            "SELECT COUNT(*) FROM audit_log WHERE timestamp > datetime('now', '-1 hour')"
        ).fetchone()[0]
        anomalies = conn.execute(
            "SELECT COUNT(*) FROM audit_log WHERE anomaly_flags != '[]'"
        ).fetchone()[0]
        top_tools = conn.execute(
            "SELECT tool_name, invocation_count FROM audit_stats ORDER BY invocation_count DESC LIMIT 5"
        ).fetchall()
        return {
            "total_invocations": total,
            "last_hour": recent,
            "anomalies_detected": anomalies,
            "top_tools": [
                {"tool": r["tool_name"], "count": r["invocation_count"]} for r in top_tools
            ],
        }

    @staticmethod
    def _default_db_path() -> Path:
        return Path.cwd() / ".maru" / "audit.db"
