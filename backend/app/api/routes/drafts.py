from datetime import datetime, timezone
from uuid import uuid4
from fastapi import APIRouter

from app.models.schemas import DraftCreateRequest
from app.services.local_store import save_draft

router = APIRouter()


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
