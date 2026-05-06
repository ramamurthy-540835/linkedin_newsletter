import json
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DRAFTS_FILE = DATA_DIR / "drafts.json"
POSTS_FILE = DATA_DIR / "posts.json"


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
