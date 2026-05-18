import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from app.core.config import settings


def _db_path() -> Path:
    raw = settings.local_db_path
    p = Path(raw)
    if p.is_absolute():
        return p
    root = Path(__file__).resolve().parents[2]
    return root / raw.replace("backend/", "", 1)


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    db = _db_path()
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_local_db() -> None:
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS profiles (
                id TEXT PRIMARY KEY,
                handle TEXT UNIQUE NOT NULL,
                name TEXT,
                headline TEXT,
                company TEXT,
                profile_url TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS topics (
                id TEXT PRIMARY KEY,
                profile_handle TEXT,
                topic TEXT NOT NULL,
                source TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS feed_items (
                id TEXT PRIMARY KEY,
                topic TEXT NOT NULL,
                title TEXT NOT NULL,
                snippet TEXT,
                source TEXT,
                source_url TEXT,
                published_at TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS connections (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                title TEXT,
                company TEXT,
                profile_url TEXT,
                source TEXT,
                relationship_type TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS network_events (
                id TEXT PRIMARY KEY,
                person_name TEXT NOT NULL,
                profile_url TEXT,
                event_type TEXT NOT NULL,
                context TEXT,
                event_date TEXT,
                suggested_message TEXT,
                status TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS drafts (
                id TEXT PRIMARY KEY,
                type TEXT,
                title TEXT,
                content TEXT,
                hashtags TEXT,
                cta TEXT,
                media_json TEXT,
                status TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS publish_queue (
                id TEXT PRIMARY KEY,
                draft_id TEXT NOT NULL,
                scheduled_at TEXT,
                status TEXT,
                error_message TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS xai_usage (
                id TEXT PRIMARY KEY,
                feature TEXT NOT NULL,
                model TEXT NOT NULL,
                prompt_tokens INTEGER NOT NULL DEFAULT 0,
                completion_tokens INTEGER NOT NULL DEFAULT 0,
                total_tokens INTEGER NOT NULL DEFAULT 0,
                cost_usd REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            """
        )
    seed_if_empty()


def seed_if_empty() -> None:
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        if conn.execute("SELECT COUNT(1) FROM profiles").fetchone()[0] == 0:
            conn.execute(
                "INSERT INTO profiles (id, handle, name, headline, company, profile_url, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("profile-1", "contentstudio", "Content Studio", "AI Content Creator", "Content Studio", "https://www.linkedin.com/in/contentstudio", now, now),
            )
        if conn.execute("SELECT COUNT(1) FROM topics").fetchone()[0] == 0:
            conn.execute(
                "INSERT INTO topics (id, profile_handle, topic, source, created_at) VALUES (?, ?, ?, ?, ?)",
                ("topic-1", "contentstudio", "AI for LinkedIn growth", "seed", now),
            )
        if conn.execute("SELECT COUNT(1) FROM feed_items").fetchone()[0] == 0:
            conn.execute(
                "INSERT INTO feed_items (id, topic, title, snippet, source, source_url, published_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("feed-1", "AI for LinkedIn growth", "How teams scale thought leadership", "A practical content ops playbook.", "seed", "https://example.com/content-ops", now, now),
            )
        if conn.execute("SELECT COUNT(1) FROM connections").fetchone()[0] == 0:
            conn.execute(
                "INSERT INTO connections (id, name, title, company, profile_url, source, relationship_type, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("conn-1", "Avery Stone", "Head of Marketing", "Acme Co", "https://www.linkedin.com/in/avery-stone", "seed", "1st-degree", now),
            )
        if conn.execute("SELECT COUNT(1) FROM network_events").fetchone()[0] == 0:
            conn.execute(
                "INSERT INTO network_events (id, person_name, profile_url, event_type, context, event_date, suggested_message, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("event-1", "Avery Stone", "https://www.linkedin.com/in/avery-stone", "job_change", "Started new role at Acme Co", now[:10], "Congrats on the new role, Avery.", "new", now),
            )


def list_drafts() -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM drafts ORDER BY created_at DESC").fetchall()
    out: list[dict[str, Any]] = []
    for r in rows:
        d = dict(r)
        d["hashtags"] = json.loads(d["hashtags"] or "[]")
        d["media_json"] = json.loads(d["media_json"] or "{}")
        out.append(d)
    return out


def get_draft(draft_id: str) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM drafts WHERE id = ?", (draft_id,)).fetchone()
    if not row:
        return None
    d = dict(row)
    d["hashtags"] = json.loads(d["hashtags"] or "[]")
    d["media_json"] = json.loads(d["media_json"] or "{}")
    return d


def save_draft(payload: dict[str, Any]) -> dict[str, Any]:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO drafts (id, type, title, content, hashtags, cta, media_json, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["id"],
                payload.get("type", "post"),
                payload.get("title", ""),
                payload.get("content", ""),
                json.dumps(payload.get("hashtags", [])),
                payload.get("cta", ""),
                json.dumps(payload.get("media_json", {})),
                payload.get("status", "draft"),
                payload["created_at"],
                payload["updated_at"],
            ),
        )
    return payload


def add_xai_usage(
    usage_id: str,
    feature: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    cost_usd: float,
    created_at: str,
) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO xai_usage (
                id, feature, model, prompt_tokens, completion_tokens, total_tokens, cost_usd, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                usage_id,
                feature,
                model,
                int(prompt_tokens or 0),
                int(completion_tokens or 0),
                int(total_tokens or 0),
                float(cost_usd or 0),
                created_at,
            ),
        )


def xai_usage_summary_month(month_prefix: str) -> dict[str, Any]:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT
                COALESCE(SUM(cost_usd), 0) AS used_usd,
                COALESCE(SUM(total_tokens), 0) AS total_tokens,
                COALESCE(COUNT(1), 0) AS request_count
            FROM xai_usage
            WHERE created_at LIKE ?
            """,
            (f"{month_prefix}%",),
        ).fetchone()
        last = conn.execute(
            """
            SELECT cost_usd, total_tokens, created_at, model, feature
            FROM xai_usage
            ORDER BY created_at DESC
            LIMIT 1
            """
        ).fetchone()
    out = {
        "used_usd": float(row["used_usd"] or 0),
        "total_tokens": int(row["total_tokens"] or 0),
        "request_count": int(row["request_count"] or 0),
        "last_request": None,
    }
    if last:
        out["last_request"] = {
            "cost_usd": float(last["cost_usd"] or 0),
            "total_tokens": int(last["total_tokens"] or 0),
            "created_at": last["created_at"],
            "model": last["model"],
            "feature": last["feature"],
        }
    return out
