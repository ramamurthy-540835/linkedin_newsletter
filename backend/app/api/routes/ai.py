from fastapi import APIRouter, HTTPException
import httpx
from pydantic import BaseModel

from app.core.config import settings
from app.services.xai_usage_service import XAIBudgetError, assert_budget_allows_request, record_xai_usage

router = APIRouter()


class GenerateBody(BaseModel):
    model: str = ""
    prompt: str
    system: str = ""


async def _generate_via_openai(body: GenerateBody) -> dict:
    key = (settings.openai_api_key or "").strip()
    if not key:
        raise RuntimeError("OPENAI_API_KEY not configured")
    base = "https://api.openai.com/v1"
    model = (body.model or "gpt-4o-mini").removeprefix("models/").strip()
    prompt = f"System: {body.system}\n\nUser: {body.prompt}" if body.system else body.prompt
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.2}
    async with httpx.AsyncClient(timeout=40) as client:
        resp = await client.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json=payload,
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"OpenAI generation failed: {resp.text}")
        data = resp.json()
        text = (((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
        return {"text": text, "usage": data.get("usage") or {}, "provider": "openai"}


@router.post("/generate")
async def ai_generate(body: GenerateBody) -> dict:
    ai_provider = (settings.ai_provider or "auto").strip().lower()
    if ai_provider == "xai" or settings.local_dev_mode or settings.disable_gcp or settings.disable_vertex_ai:
        try:
            budget = assert_budget_allows_request()
            base = (settings.xai_base_url or "").rstrip("/")
            key = (settings.xai_api_key or "").strip()
            model = (body.model or settings.xai_model or "").removeprefix("models/").strip()
            if not key:
                raise HTTPException(status_code=400, detail="XAI_API_KEY not configured")
            if not base:
                raise HTTPException(status_code=400, detail="XAI_BASE_URL not configured in environment")
            if not model:
                raise HTTPException(status_code=400, detail="AI model not configured in environment")
            prompt = f"System: {body.system}\n\nUser: {body.prompt}" if body.system else body.prompt
            payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.2}
            async with httpx.AsyncClient(timeout=40) as client:
                resp = await client.post(
                    f"{base}/chat/completions",
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json=payload,
                )
                if resp.status_code >= 400:
                    raise HTTPException(status_code=502, detail=f"xAI generation failed: {resp.text}")
                data = resp.json()
                text = (((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
            usage = record_xai_usage(feature="ai_generate", model=model, usage=data.get("usage") or {})
            soft = float(settings.xai_soft_stop_usd or 0)
            used = float(budget.get("used_usd") or 0)
            warning = None
            if soft > 0 and used >= soft:
                warning = f"xAI soft budget reached (${used:.4f}/${soft:.4f})."
            hard = float(settings.xai_hard_stop_usd or 0)
            if bool(settings.xai_auto_reload_enabled) and hard > 0 and used >= hard:
                warning = "Local budget exceeded, but xAI auto-reload is enabled."
            return {"text": text, "usage": usage, "budget_warning": warning}
        except XAIBudgetError as e:
            if (settings.openai_api_key or "").strip():
                try:
                    out = await _generate_via_openai(body)
                    out["fallback_from"] = "xai"
                    out["xai_error"] = str(e)
                    return out
                except Exception as openai_exc:
                    raise HTTPException(status_code=502, detail=f"xAI failed: {str(e)}; OpenAI fallback failed: {str(openai_exc)}")
            raise HTTPException(status_code=429, detail=str(e))
        except HTTPException as e:
            if (settings.openai_api_key or "").strip():
                try:
                    out = await _generate_via_openai(body)
                    out["fallback_from"] = "xai"
                    out["xai_error"] = str(e.detail)
                    return out
                except Exception as openai_exc:
                    raise HTTPException(status_code=502, detail=f"xAI failed: {e.detail}; OpenAI fallback failed: {str(openai_exc)}")
            raise
        except Exception as e:
            if (settings.openai_api_key or "").strip():
                try:
                    out = await _generate_via_openai(body)
                    out["fallback_from"] = "xai"
                    out["xai_error"] = str(e)
                    return out
                except Exception as openai_exc:
                    raise HTTPException(status_code=502, detail=f"xAI failed: {str(e)}; OpenAI fallback failed: {str(openai_exc)}")
            raise HTTPException(status_code=502, detail=f"xAI generation failed: {str(e)}")
    raise HTTPException(status_code=400, detail="AI_PROVIDER must be xai for local mode")
