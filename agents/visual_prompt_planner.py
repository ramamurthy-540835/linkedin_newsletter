import json
import re
from typing import Dict, Any
import requests


def _call_llm(prompt: str, model: str, api_key: str) -> str:
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set")
    resp = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        headers={"x-goog-api-key": api_key},
        json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"maxOutputTokens": 2500, "temperature": 0.2, "topP": 0.8}},
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()


def build_factual_visual_context(stats: Dict[str, Any]) -> Dict[str, Any]:
    top_categories = []
    for k, models in stats.get("categorized_models", {}).items():
        if not models:
            continue
        best = stats.get("latest_per_usecase", {}).get(k) or {}
        top_categories.append({"key": k, "name": k.replace("_", " ").title(), "count": len(models), "best": best.get("model_id", "N/A")})
    top_categories.sort(key=lambda x: x["count"], reverse=True)

    return {
        "provider": stats.get("provider", "OPENAI").lower(),
        "provider_display_name": stats.get("provider", "OPENAI"),
        "total_models": stats.get("total", 0),
        "total_families": stats.get("family_count", 0),
        "high_confidence": len(stats.get("conf_buckets", {}).get("high", [])),
        "medium_confidence": len(stats.get("conf_buckets", {}).get("medium", [])),
        "low_confidence": len(stats.get("conf_buckets", {}).get("low", [])),
        "enriched_coverage": f"{stats.get('enriched_coverage_count', 0)}/{stats.get('total', 0)}",
        "top_categories": top_categories[:8],
        "best_models": {k: (v.get("model_id") if v else None) for k, v in stats.get("latest_per_usecase", {}).items()},
        "discovery_method": "LangGraph orchestration + semantic enrichment + BigQuery registry",
        "pipeline_steps": [
            "Official API discovery",
            "LangGraph orchestration",
            "Semantic enrichment",
            "BigQuery registry",
            "Publishing pipeline",
        ],
    }


def generate_visual_prompt(context: Dict[str, Any], image_type: str, planner_model: str, api_key: str) -> Dict[str, Any]:
    planner_prompt = f"""You are an enterprise design strategist.

Create a production-quality image generation prompt.

Facts:
{json.dumps(context, indent=2)}

Rules:
- NEVER invent facts
- Use exact numbers only from context
- Never recalculate
- No fake UI screenshots
- No lorem ipsum
- No placeholder text
- Large readable typography
- Enterprise light theme
- Premium SaaS visual style
- Clean layout
- Minimal text
- No brand contamination

For DASHBOARD:
Use only high-level cards/charts conceptually.
Avoid tiny labels.

For ARCHITECTURE:
Use pipeline blocks with arrows.
No paragraph text.

image_type: {image_type}

Return JSON:
{{
  "title": "...",
  "visual_strategy": "...",
  "prompt": "...",
  "validation_rules": ["..."]
}}
"""
    txt = _call_llm(planner_prompt, planner_model, api_key)
    return json.loads(txt)


def review_prompt(prompt_json: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    prompt = prompt_json.get("prompt", "")
    issues = []
    must_not = ["ibm", "carbon", "microsoft", "lorem ipsum"]
    p = prompt.lower()
    for t in must_not:
        if t in p:
            issues.append(f"forbidden_term:{t}")
            prompt = re.sub(t, "", prompt, flags=re.IGNORECASE)
    provider = context.get("provider", "")
    if provider and provider not in p:
        issues.append("missing_provider")
        prompt += f" Include provider label: {context.get('provider_display_name')}"
    if str(context.get("total_models", "")) not in prompt:
        issues.append("missing_total_models")
        prompt += f" Use exact total models: {context.get('total_models')}"

    prompt += " Do not render brand/style-system names."
    out = dict(prompt_json)
    out["prompt"] = prompt.strip()
    out["issues"] = issues
    out["approved"] = len(issues) == 0
    return out
