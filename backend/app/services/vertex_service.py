import json
import re
from typing import Any

import httpx

from app.core.config import settings
from app.services.xai_usage_service import assert_budget_allows_request, record_xai_usage


class VertexService:
    def __init__(self) -> None:
        self._initialized = False

    def _ensure_init(self) -> None:
        if self._initialized:
            return
        if settings.local_dev_mode or settings.disable_gcp or settings.disable_vertex_ai:
            raise RuntimeError("Vertex AI disabled in local mode")
        import vertexai
        vertexai.init(project=settings.gcp_project_id, location=settings.gcp_region)
        self._initialized = True

    def _provider(self) -> str:
        return (settings.ai_provider or "auto").strip().lower()

    async def _generate_with_xai(self, prompt: str) -> dict[str, Any]:
        summary = assert_budget_allows_request()
        base = (settings.xai_base_url or "").rstrip("/")
        key = (settings.xai_api_key or "").strip()
        model = (settings.xai_model or "").strip()
        if not key:
            raise RuntimeError("XAI_API_KEY not configured")
        if not base:
            raise RuntimeError("XAI_BASE_URL not configured in environment")
        if not model:
            raise RuntimeError("AI model not configured in environment")

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "Return valid JSON only. No markdown fences."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=40) as client:
            resp = await client.post(f"{base}/chat/completions", headers=headers, json=payload)
            if resp.status_code >= 400:
                raise RuntimeError(f"xAI error {resp.status_code}: {resp.text}")
            data = resp.json()
            text = (((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "{}").strip()
            record_xai_usage(feature="content_plan", model=model, usage=data.get("usage") or {})
            soft = float(settings.xai_soft_stop_usd or 0)
            used = float(summary.get("used_usd") or 0)
            if soft > 0 and used >= soft:
                print(f"[xai-budget] soft stop reached before request: used=${used:.4f} soft=${soft:.4f}")
            return self._parse_json(text)

    async def generate_json(self, prompt: str) -> dict[str, Any]:
        provider = self._provider()
        if provider == "xai":
            return await self._generate_with_xai(prompt)
        if settings.local_dev_mode or settings.disable_gcp or settings.disable_vertex_ai:
            raise RuntimeError("AI_PROVIDER must be xai in local mode; Vertex is disabled")

        try:
            self._ensure_init()
            vertex_model = (settings.vertex_ai_model or "").strip()
            if not vertex_model:
                raise RuntimeError("AI model not configured in environment")
            from vertexai.generative_models import GenerativeModel
            model = GenerativeModel(vertex_model)
            response = model.generate_content(
                [
                    "Return valid JSON only. No markdown fences.",
                    prompt,
                ]
            )
            raw = (response.text or "{}").strip()
            return self._parse_json(raw)
        except Exception:
            raise

    def _parse_json(self, raw: str) -> dict[str, Any]:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            raw = raw[start : end + 1]

        # Replace unescaped newlines/tabs inside JSON string values with \\n/\\t,
        # and strip other control characters.
        cleaned = re.sub(r'(?<=": ")(.*?)(?=")', lambda m: m.group(0).replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t"), raw, flags=re.DOTALL)
        cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", " ", cleaned)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Last resort: replace ALL literal newlines with \\n
            fallback = re.sub(r"[\x00-\x1F]", lambda m: {"\n": "\\n", "\r": "\\r", "\t": "\\t"}.get(m.group(), " "), raw)
            return json.loads(fallback)
