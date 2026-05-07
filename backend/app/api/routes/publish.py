from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.models.schemas import PublishRequest
from app.services.linkedin_service import LinkedInService
from app.services.local_store import get_draft, save_post

router = APIRouter()
linkedin = LinkedInService()

MEDIA_DIR = Path(__file__).resolve().parents[3] / "data" / "media"


def _resolve_token_and_urn() -> tuple[str, str]:
    token = settings.linkedin_access_token
    urn = settings.linkedin_author_urn
    if not urn:
        raise HTTPException(status_code=400, detail="Missing LINKEDIN_AUTHOR_URN in backend .env")
    if not token:
        raise HTTPException(status_code=400, detail="Missing LINKEDIN_ACCESS_TOKEN in backend .env")
    return token, urn


def _build_full_text(draft: dict) -> str:
    content = draft.get("content", "")
    hashtags = draft.get("hashtags", [])
    cta = draft.get("cta", "")
    return f"{content}\n\n{' '.join(hashtags)}\n\n{cta}".strip()


@router.post("")
async def publish(req: PublishRequest) -> dict:
    draft = get_draft(req.draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    token, urn = _resolve_token_and_urn()
    full_text = _build_full_text(draft)

    linkedin_resp = await linkedin.publish_post(
        access_token=token,
        author_urn=urn,
        text=full_text,
    )

    record = {
        "draft_id": req.draft_id,
        "status": "published",
        "content": draft.get("content", ""),
        "linkedin_post_id": linkedin_resp.get("location", ""),
        "has_images": False,
        "image_count": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return save_post(record)


class PublishWithMediaRequest(BaseModel):
    draft_id: str
    image_filenames: list[str] = []


@router.post("/with-media")
async def publish_with_media(req: PublishWithMediaRequest) -> dict:
    """Publish a draft to LinkedIn, optionally attaching generated images."""
    draft = get_draft(req.draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    token, urn = _resolve_token_and_urn()
    full_text = _build_full_text(draft)

    if req.image_filenames:
        try:
            linkedin_resp = await linkedin.publish_post_with_images(
                access_token=token,
                author_urn=urn,
                text=full_text,
                image_filenames=req.image_filenames,
                media_dir=MEDIA_DIR,
            )
        except Exception as exc:
            # Fallback: publish text-only if image upload fails
            linkedin_resp = await linkedin.publish_post(
                access_token=token,
                author_urn=urn,
                text=full_text,
            )
            linkedin_resp["warning"] = f"Images failed to upload, published text-only: {exc}"
    else:
        linkedin_resp = await linkedin.publish_post(
            access_token=token,
            author_urn=urn,
            text=full_text,
        )

    record = {
        "draft_id": req.draft_id,
        "status": "published",
        "content": draft.get("content", ""),
        "linkedin_post_id": linkedin_resp.get("location", ""),
        "has_images": linkedin_resp.get("has_images", False),
        "image_count": linkedin_resp.get("image_count", 0),
        "warning": linkedin_resp.get("warning"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return save_post(record)


@router.post("/from-scheduler")
async def publish_from_scheduler(req: PublishRequest) -> dict:
    return await publish(req)
