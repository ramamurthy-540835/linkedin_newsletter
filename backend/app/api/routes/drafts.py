from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app.models.schemas import DraftCreateRequest
from app.services.local_store import get_draft, list_drafts, save_draft
from app.services.content_sanitizer import sanitize_post_payload

router = APIRouter()


@router.get("")
async def get_drafts() -> list:
    return list_drafts()


@router.get("/{draft_id}")
async def get_draft_by_id(draft_id: str) -> dict:
    draft = get_draft(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


@router.post("")
async def create_draft(req: DraftCreateRequest) -> dict:
    draft_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    clean_content, clean_cta, clean_title = sanitize_post_payload(req.content, req.cta, req.title)
    payload = {
        "id": draft_id,
        "title": clean_title,
        "content": clean_content,
        "hashtags": req.hashtags,
        "cta": clean_cta,
        "created_at": now,
        "updated_at": now,
    }
    return save_draft(payload)
