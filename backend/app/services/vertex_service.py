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
        def _loads(s: str) -> dict[str, Any]:
            return json.loads(s)

        try:
            return _loads(raw)
        except json.JSONDecodeError:
            pass

        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = raw[start : end + 1]
            try:
                return _loads(candidate)
            except json.JSONDecodeError:
                # Remove non-printable control chars that often break model JSON output.
                cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", " ", candidate)
                return _loads(cleaned)

        raise json.JSONDecodeError("Invalid JSON from model", raw, 0)
