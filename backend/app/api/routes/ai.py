import os

from fastapi import APIRouter, HTTPException
from google import genai
from pydantic import BaseModel

from app.api.routes.config import get_runtime_key
from app.core.config import settings

router = APIRouter()


class GenerateBody(BaseModel):
    model: str = "models/gemini-2.5-flash"
    prompt: str
    system: str = ""


@router.post("/generate")
async def ai_generate(body: GenerateBody) -> dict:
    try:
        client = genai.Client(vertexai=True, project=settings.gcp_project_id, location=settings.gcp_region)
    except Exception:
        api_key = os.getenv("GEMINI_API_KEY") or get_runtime_key("gemini_api_key")
        if not api_key:
            raise HTTPException(status_code=400, detail="GEMINI_API_KEY not configured")
        client = genai.Client(api_key=api_key)

    try:
        model_name = body.model.removeprefix("models/") if body.model else "gemini-2.5-flash"
        prompt = f"System: {body.system}\n\nUser: {body.prompt}" if body.system else body.prompt
        response = client.models.generate_content(model=model_name, contents=prompt)
        return {"text": (response.text or "").strip()}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Gemini generation failed: {exc}") from exc
