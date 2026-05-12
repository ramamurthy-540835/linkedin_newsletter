import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from google import genai
from app.core.config import settings

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
    serp_key = os.getenv("SERP_API_KEY", "").strip()
    linkedin_client_id = os.getenv("LINKEDIN_CLIENT_ID", "").strip()
    linkedin_client_secret = os.getenv("LINKEDIN_CLIENT_SECRET", "").strip()
    gemini_env = os.getenv("GEMINI_API_KEY", "").strip()
    gemini_runtime = get_runtime_key("gemini_api_key")

    return {
        "serp_configured": bool(serp_key),
        "linkedin_configured": bool(linkedin_client_id and linkedin_client_secret),
        "linkedin_client_id": (linkedin_client_id[:8] + "...") if linkedin_client_id else "",
        "gemini_configured": bool(gemini_env or gemini_runtime),
        "gemini_source": "env" if gemini_env else ("runtime" if gemini_runtime else "none"),
    }


@router.post("/keys")
async def config_keys(body: ConfigKeysRequest) -> dict:
    if body.gemini_api_key is not None:
        _RUNTIME_KEYS["gemini_api_key"] = body.gemini_api_key.strip()
    if body.openai_api_key is not None:
        _RUNTIME_KEYS["openai_api_key"] = body.openai_api_key.strip()
    return {"success": True}


@router.post("/autocomplete")
async def autocomplete_topics(req: AutocompleteRequest) -> dict:
    if not req.partial or len(req.partial) < 2:
        return {"suggestions": []}

    try:
        try:
            client = genai.Client(vertexai=True, project=settings.gcp_project_id, location=settings.gcp_region)
            model = settings.vertex_model or "gemini-2.5-flash"
        except Exception:
            api_key = os.getenv("GOOGLE_API_KEY", "").strip() or os.getenv("GEMINI_API_KEY", "").strip() or get_runtime_key("gemini_api_key")
            if not api_key:
                raise HTTPException(400, "Neither ADC nor GEMINI/GOOGLE API key configured")
            client = genai.Client(api_key=api_key)
            model = "gemini-2.5-flash"

        response = client.models.generate_content(
            model=model,
            contents=f"""The user is typing a LinkedIn topic to track: \"{req.partial}\"
Give 5 autocomplete suggestions for LinkedIn post topics starting with or related to this.
Return ONLY a JSON array of strings, no markdown, no explanation.
Example: [\"Generative AI in HR\", \"AI tools 2025\", \"Tech trends\"]"""
        )

        text = (response.text or "").strip().replace("```json", "").replace("```", "")
        try:
            suggestions = eval(text) if isinstance(text, str) else text
            result = suggestions if isinstance(suggestions, list) else []
            return {"suggestions": result}
        except Exception:
            return {"suggestions": []}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"Autocomplete error: {str(e)}")
