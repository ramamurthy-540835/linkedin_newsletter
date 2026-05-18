from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.services.xai_usage_service import get_month_usage_summary

router = APIRouter()


def _infer_type(model_id: str) -> str:
    m = (model_id or "").lower()
    if "imagine-video" in m:
        return "video"
    if "imagine-image" in m:
        return "image"
    return "text"


@router.get("/models")
async def list_xai_models() -> dict:
    base = (settings.xai_base_url or "").rstrip("/")
    key = (settings.xai_api_key or "").strip()
    if not key:
        raise HTTPException(status_code=400, detail="XAI_API_KEY missing")
    if not base:
        raise HTTPException(status_code=400, detail="XAI_BASE_URL missing")

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{base}/models",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        )
        if resp.status_code >= 400:
            raise HTTPException(status_code=502, detail=f"xAI /models failed: {resp.text}")
        data = resp.json()

    raw = data.get("data") or []
    models = []
    for item in raw:
        model_id = item.get("id") or ""
        created = item.get("created")
        created_iso = None
        if isinstance(created, (int, float)):
            created_iso = datetime.fromtimestamp(created, tz=timezone.utc).isoformat()
        models.append(
            {
                "id": model_id,
                "object": item.get("object"),
                "owned_by": item.get("owned_by"),
                "created": created,
                "created_at": created_iso,
                "type": _infer_type(model_id),
                "source": "xAI API",
            }
        )
    return {"models": models}


@router.get("/usage")
async def xai_usage() -> dict:
    summary = get_month_usage_summary()
    return summary
