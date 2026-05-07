import json
from pathlib import Path
from typing import Any

import threading

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DRAFTS_FILE = DATA_DIR / "drafts.json"
POSTS_FILE = DATA_DIR / "posts.json"
WHITEPAPERS_FILE = DATA_DIR / "whitepapers.json"
MEDIA_JOBS_FILE = DATA_DIR / "media_jobs.json"

_media_lock = threading.Lock()


def _ensure_file(path: Path) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("[]", encoding="utf-8")


def _read(path: Path) -> list[dict[str, Any]]:
    _ensure_file(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, rows: list[dict[str, Any]]) -> None:
    _ensure_file(path)
    path.write_text(json.dumps(rows, indent=2, default=str), encoding="utf-8")


def save_draft(payload: dict[str, Any]) -> dict[str, Any]:
    rows = _read(DRAFTS_FILE)
    rows.append(payload)
    _write(DRAFTS_FILE, rows)
    return payload


def get_draft(draft_id: str) -> dict[str, Any] | None:
    rows = _read(DRAFTS_FILE)
    for row in rows:
        if row.get("id") == draft_id:
            return row
    return None


def save_post(payload: dict[str, Any]) -> dict[str, Any]:
    rows = _read(POSTS_FILE)
    rows.append(payload)
    _write(POSTS_FILE, rows)
    return payload


def list_drafts() -> list[dict[str, Any]]:
    return _read(DRAFTS_FILE)


def save_whitepaper(payload: dict[str, Any]) -> dict[str, Any]:
    rows = _read(WHITEPAPERS_FILE)
    rows.append(payload)
    _write(WHITEPAPERS_FILE, rows)
    return payload


def read_whitepapers() -> list[dict[str, Any]]:
    return _read(WHITEPAPERS_FILE)


def get_whitepaper(wp_id: str) -> dict[str, Any] | None:
    for row in _read(WHITEPAPERS_FILE):
        if row.get("id") == wp_id:
            return row
    return None


# ── Media job store (thread-safe for background video generation) ──────────────

def save_media_job(payload: dict[str, Any]) -> dict[str, Any]:
    with _media_lock:
        rows = _read(MEDIA_JOBS_FILE)
        rows.append(payload)
        _write(MEDIA_JOBS_FILE, rows)
    return payload


def get_media_job(job_id: str) -> dict[str, Any] | None:
    with _media_lock:
        for row in _read(MEDIA_JOBS_FILE):
            if row.get("id") == job_id:
                return row
    return None


def update_media_job(job_id: str, updates: dict[str, Any]) -> None:
    from datetime import datetime, timezone
    with _media_lock:
        rows = _read(MEDIA_JOBS_FILE)
        for row in rows:
            if row.get("id") == job_id:
                row.update(updates)
                row["updated_at"] = datetime.now(timezone.utc).isoformat()
                break
        _write(MEDIA_JOBS_FILE, rows)
