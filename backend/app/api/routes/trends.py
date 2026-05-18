import os
from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx

from app.core.config import settings

router = APIRouter()


class TrendDiscoverRequest(BaseModel):
    topics: list[str] = []
    industries: list[str] = []
    keywords: list[str] = []


class TrendSearchRequest(BaseModel):
    query: str
    time_range: str = "7d"
    sources: list[str] = []
    sort: str = "trending"


def _get_serp_key() -> str:
    if settings.serp_api_key:
        return settings.serp_api_key
    env_key = os.getenv("SERP_API_KEY", "").strip()
    if env_key:
        return env_key
    return ""


@router.post("/discover")
async def discover_trends(req: TrendDiscoverRequest) -> dict:
    """AI-powered trend discovery based on topics, industries, and keywords."""
    all_inputs = req.topics + req.industries + req.keywords
    if not all_inputs:
        raise HTTPException(status_code=400, detail="Provide at least one topic, industry, or keyword")

    topics_str = ", ".join(all_inputs)

    from google import genai
    client = genai.Client(
        vertexai=True,
        project=settings.gcp_project_id,
        location="us-central1",
    )

    today = date.today().strftime("%B %d, %Y")

    prompt = f"""You are a LinkedIn content trend analyst. Today is {today}. Analyze current trends for these topics: {topics_str}

Return valid JSON only (no markdown fences):
{{
  "trending_ideas": [
    {{"title": "post idea title", "hook": "engaging first line", "why_trending": "reason", "engagement_estimate": "high|medium|low"}}
  ],
  "viral_hooks": [
    {{"hook": "attention-grabbing opening line", "format": "question|statistic|story|contrarian", "topic": "related topic"}}
  ],
  "discussion_opportunities": [
    {{"topic": "discussion topic", "angle": "your unique angle", "trending_because": "reason"}}
  ],
  "breaking_news": [
    {{"headline": "news headline", "relevance": "why it matters for your audience", "post_angle": "how to cover it"}}
  ],
  "debate_topics": [
    {{"question": "debatable question", "side_a": "one perspective", "side_b": "other perspective", "engagement_potential": "high|medium"}}
  ]
}}

Rules:
- 3-5 items per category
- Today is {today} — all content must reference current events and trends from {date.today().year}
- Make hooks specific and actionable, not generic
- Trending ideas should feel timely and relevant to this week"""

    try:
        if not (settings.vertex_ai_model or "").strip():
            raise HTTPException(status_code=400, detail="AI model not configured in environment")
        response = client.models.generate_content(
            model=settings.vertex_ai_model,
            contents=["Return valid JSON only. No markdown fences.", prompt],
        )
        raw = (response.text or "{}").strip()
        if raw.startswith("```"):
            raw = raw.split("```json")[-1].split("```")[0].strip() if "```json" in raw else raw.replace("```", "").strip()

        import json
        result = json.loads(raw)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Trend discovery failed: {str(exc)}") from exc


@router.post("/search")
async def search_trends(req: TrendSearchRequest) -> dict:
    """Search for trending content with freshness and source filters."""
    api_key = _get_serp_key()
    if not api_key:
        raise HTTPException(status_code=400, detail="SerpAPI key not configured")

    time_filter_map = {
        "24h": "qdr:d",
        "7d": "qdr:w",
        "30d": "qdr:m",
    }
    tbs = time_filter_map.get(req.time_range, "qdr:w")

    source_queries = {
        "linkedin": "site:linkedin.com",
        "news": "",
        "reddit": "site:reddit.com",
        "x": "site:x.com OR site:twitter.com",
        "blogs": "blog",
        "research": "research OR whitepaper OR arxiv",
        "company_news": "press release OR announcement",
    }

    query = req.query
    if req.sources:
        source_parts = [source_queries.get(s, "") for s in req.sources if source_queries.get(s)]
        if source_parts:
            query += " " + " OR ".join(source_parts)

    sort_map = {
        "trending": "",
        "most_recent": "&sort=date",
        "most_shared": "",
        "high_engagement": "",
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            params = {
                "q": query,
                "api_key": api_key,
                "engine": "google",
                "num": 15,
                "tbs": tbs,
            }
            resp = await client.get("https://serpapi.com/search", params=params)
            if resp.status_code != 200:
                raise HTTPException(502, f"SerpAPI error: {resp.text}")

            data = resp.json()
            results = []
            for item in data.get("organic_results", []):
                source = item.get("source", "")
                displayed_link = item.get("displayed_link", "")

                source_type = "web"
                if "linkedin.com" in displayed_link:
                    source_type = "linkedin"
                elif "reddit.com" in displayed_link:
                    source_type = "reddit"
                elif "twitter.com" in displayed_link or "x.com" in displayed_link:
                    source_type = "x"
                elif any(w in displayed_link for w in ["arxiv", "scholar", "research"]):
                    source_type = "research"

                results.append({
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "link": item.get("link", ""),
                    "source": source,
                    "source_type": source_type,
                    "published_date": item.get("date", ""),
                    "position": item.get("position", 0),
                })

            return {
                "results": results,
                "time_range": req.time_range,
                "total": len(results),
            }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(502, f"Search error: {str(exc)}") from exc
    if settings.local_dev_mode or settings.disable_gcp or settings.disable_vertex_ai or (settings.ai_provider or "").lower() == "xai":
        raise HTTPException(status_code=400, detail="Trend discovery via Vertex is disabled in local xAI mode")
