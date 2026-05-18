import json
import os
from urllib.parse import quote_plus

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from google import genai
from app.core.config import ROOT_ENV_LOCAL, settings

router = APIRouter()

_RUNTIME_KEYS: dict[str, str] = {}


def get_runtime_key(name: str) -> str:
    return (_RUNTIME_KEYS.get(name) or "").strip()


class AutocompleteRequest(BaseModel):
    partial: str


class ConfigKeysRequest(BaseModel):
    gemini_api_key: str | None = None
    openai_api_key: str | None = None


@router.get("/status")
async def config_status() -> dict:
    serp_key = settings.serp_api_key or os.getenv("SERP_API_KEY", "").strip()
    linkedin_client_id = settings.linkedin_client_id or os.getenv("LINKEDIN_CLIENT_ID", "").strip()
    linkedin_client_secret = settings.linkedin_client_secret or os.getenv("LINKEDIN_CLIENT_SECRET", "").strip()
    gemini_env = os.getenv("GEMINI_API_KEY", "").strip()
    gemini_runtime = get_runtime_key("gemini_api_key")
    ai_provider = (settings.ai_provider or "auto").strip().lower()
    xai_key = (settings.xai_api_key or "").strip()
    xai_base = (settings.xai_base_url or "").strip()
    xai_model = (settings.xai_model or "").strip()
    xai_image_model = (settings.xai_image_model or "").strip()
    xai_video_model = (settings.xai_video_model or "").strip()
    vertex_model = (settings.vertex_ai_model or "").strip()
    gcp_disabled = settings.local_dev_mode or settings.disable_gcp
    bq_disabled = gcp_disabled or settings.disable_bigquery
    vertex_disabled = gcp_disabled or settings.disable_vertex_ai or ai_provider == "xai"
    vertex_enabled = not vertex_disabled and ai_provider in ("google", "vertex", "auto")

    return {
        "serp_configured": bool(serp_key),
        "linkedin_configured": bool(linkedin_client_id and linkedin_client_secret),
        "linkedin_client_id": (linkedin_client_id[:8] + "...") if linkedin_client_id else "",
        "gemini_configured": bool(gemini_env or gemini_runtime),
        "gemini_source": "env" if gemini_env else ("runtime" if gemini_runtime else "none"),
        "ai_provider": ai_provider,
        "gcp": "disabled" if gcp_disabled else "enabled",
        "bigquery": "disabled" if bq_disabled else "enabled",
        "vertex": "disabled" if vertex_disabled else "enabled",
        "google_vertex": "enabled" if vertex_enabled else "disabled",
        "xai": "connected" if bool(xai_key) else "missing",
        "xai_base_url": xai_base,
        "xai_model": xai_model,
        "xai_image_model": xai_image_model,
        "xai_video_model": xai_video_model,
        "active_provider": "xai" if (ai_provider == "xai" or gcp_disabled) else ai_provider,
        "active_model": xai_model if (ai_provider == "xai" or gcp_disabled) else vertex_model,
        "active_base_url": xai_base if ai_provider == "xai" else "",
        "env_file_loaded": ROOT_ENV_LOCAL.exists(),
        "env_file_path": str(ROOT_ENV_LOCAL),
        "xai_key_present": bool(xai_key),
    }


@router.post("/keys")
async def config_keys(body: ConfigKeysRequest) -> dict:
    if body.gemini_api_key is not None:
        _RUNTIME_KEYS["gemini_api_key"] = body.gemini_api_key.strip()
    if body.openai_api_key is not None:
        _RUNTIME_KEYS["openai_api_key"] = body.openai_api_key.strip()
    return {"success": True}


async def _google_suggest(query: str) -> list[str]:
    """Google Search-style instant suggestions (~50ms, no API key needed)."""
    url = f"https://suggestqueries.google.com/complete/search?client=firefox&q={quote_plus(query)}"
    async with httpx.AsyncClient(timeout=3) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()
        # Response format: ["query", ["suggestion1", "suggestion2", ...]]
        return data[1] if len(data) > 1 and isinstance(data[1], list) else []


@router.post("/autocomplete")
async def autocomplete_topics(req: AutocompleteRequest) -> dict:
    if not req.partial or len(req.partial) < 2:
        return {"suggestions": []}

    # Primary: Google Suggest (instant, like Google Search)
    try:
        results = await _google_suggest(req.partial)
        if results:
            return {"suggestions": [str(s) for s in results[:8]], "source": "google"}
    except Exception:
        pass

    # Fallback: Gemini AI for LinkedIn-specific suggestions
    if settings.local_dev_mode or settings.disable_gcp or settings.disable_vertex_ai:
        return {"suggestions": []}

    try:
        try:
            client = genai.Client(vertexai=True, project=settings.gcp_project_id, location=settings.gcp_region)
            model = settings.vertex_ai_model
            if not model:
                return {"suggestions": []}
        except Exception:
            api_key = os.getenv("GOOGLE_API_KEY", "").strip() or os.getenv("GEMINI_API_KEY", "").strip() or get_runtime_key("gemini_api_key")
            if not api_key:
                return {"suggestions": []}
            client = genai.Client(api_key=api_key)
            model = settings.vertex_ai_model
            if not model:
                return {"suggestions": []}

        response = client.models.generate_content(
            model=model,
            contents=f"""The user is typing a LinkedIn topic: \"{req.partial}\"
Give 5 autocomplete suggestions starting with or related to this.
Return ONLY a JSON array of strings, no markdown.
Example: [\"Generative AI in HR\", \"Agentic AI workflows\"]"""
        )

        text = (response.text or "").strip()
        for fence in ("```json", "```"):
            text = text.replace(fence, "")
        text = text.strip()
        try:
            suggestions = json.loads(text)
            result = suggestions if isinstance(suggestions, list) else []
            return {"suggestions": [str(s) for s in result[:8]], "source": "gemini"}
        except (json.JSONDecodeError, ValueError):
            return {"suggestions": []}

    except Exception:
        return {"suggestions": []}
