import json
import re
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
        return self._parse_json(raw)

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
