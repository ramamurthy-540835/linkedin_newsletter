import json

from fastapi import APIRouter

from app.models.schemas import PublishedPost
from app.services.local_store import POSTS_FILE

router = APIRouter()

PUBLISHED_POSTS_FILE = POSTS_FILE.parent / "published_posts.json"


@router.get("", response_model=list[PublishedPost])
async def list_published_posts() -> list[PublishedPost]:
    rows = []
    if PUBLISHED_POSTS_FILE.exists():
        rows = json.loads(PUBLISHED_POSTS_FILE.read_text(encoding="utf-8"))
    rows.sort(key=lambda x: x.get("published_at", ""), reverse=True)
    return [PublishedPost(**row) for row in rows]
