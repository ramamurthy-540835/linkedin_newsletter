import json
from typing import Any

import vertexai
from vertexai.generative_models import GenerativeModel

from app.core.config import settings


class VertexService:
    def __init__(self) -> None:
        self._initialized = False

    def _ensure_init(self) -> None:
        if self._initialized:
            return
        vertexai.init(project=settings.gcp_project_id, location=settings.gcp_region)
        self._initialized = True

    async def generate_json(self, prompt: str) -> dict[str, Any]:
        self._ensure_init()
        model = GenerativeModel(settings.vertex_model)
        response = model.generate_content(
            [
                "Return valid JSON only. No markdown fences.",
                prompt,
            ]
        )
        raw = (response.text or "{}").strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            start = raw.find("{")
            end = raw.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(raw[start : end + 1])
            raise
