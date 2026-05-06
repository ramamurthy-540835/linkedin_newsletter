from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.models.schemas import PublishRequest
from app.services.linkedin_service import LinkedInService
from app.services.local_store import get_draft, save_post

router = APIRouter()
linkedin = LinkedInService()


@router.post("")
async def publish(req: PublishRequest) -> dict:
    draft = get_draft(req.draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    if not settings.linkedin_author_urn:
        raise HTTPException(status_code=400, detail="Missing LINKEDIN_AUTHOR_URN in backend .env")
    if not settings.linkedin_access_token:
        raise HTTPException(status_code=400, detail="Missing LINKEDIN_ACCESS_TOKEN in backend .env")

    content = draft.get("content", "")
    hashtags = draft.get("hashtags", [])
    cta = draft.get("cta", "")
    full_text = f"{content}\n\n{' '.join(hashtags)}\n\n{cta}".strip()

    linkedin_resp = await linkedin.publish_post(
        access_token=settings.linkedin_access_token,
        author_urn=settings.linkedin_author_urn,
        text=full_text,
    )

    record = {
        "draft_id": req.draft_id,
        "status": "published",
        "content": content,
        "linkedin_post_id": linkedin_resp.get("location", ""),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return save_post(record)


@router.post("/from-scheduler")
async def publish_from_scheduler(req: PublishRequest) -> dict:
    return await publish(req)
