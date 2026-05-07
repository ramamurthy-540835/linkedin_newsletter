from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app.models.schemas import DraftCreateRequest
from app.services.local_store import get_draft, list_drafts, save_draft

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
    payload = {
        "id": draft_id,
        "title": req.title,
        "content": req.content,
        "hashtags": req.hashtags,
        "cta": req.cta,
        "created_at": now,
        "updated_at": now,
    }
    return save_draft(payload)
