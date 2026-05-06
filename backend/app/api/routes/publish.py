from fastapi import APIRouter, HTTPException

from app.db.firestore_client import get_firestore_client
from app.core.config import settings
from app.models.schemas import PublishRequest

router = APIRouter()


@router.post("")
async def publish(req: PublishRequest) -> dict:
    db = get_firestore_client()
    doc = db.collection(settings.firestore_collection_drafts).document(req.draft_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Draft not found")

    draft = doc.to_dict()
    # Placeholder: inject LinkedIn token and author_urn from user session/secrets.
    record = {
        "draft_id": req.draft_id,
        "status": "queued_for_linkedin_publish",
        "content": draft.get("content", ""),
    }
    db.collection(settings.firestore_collection_posts).document(req.draft_id).set(record)
    return record


@router.post("/from-scheduler")
async def publish_from_scheduler(req: PublishRequest) -> dict:
    return await publish(req)
