from datetime import datetime, timezone
from uuid import uuid4
from fastapi import APIRouter

from app.db.firestore_client import get_firestore_client
from app.core.config import settings
from app.models.schemas import DraftCreateRequest

router = APIRouter()


@router.post("")
async def create_draft(req: DraftCreateRequest) -> dict:
    db = get_firestore_client()
    draft_id = str(uuid4())
    now = datetime.now(timezone.utc)
    payload = {
        "id": draft_id,
        "title": req.title,
        "content": req.content,
        "hashtags": req.hashtags,
        "cta": req.cta,
        "created_at": now,
        "updated_at": now,
    }
    db.collection(settings.firestore_collection_drafts).document(draft_id).set(payload)
    return payload
