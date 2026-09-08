"""
Interest discovery and topic recommendation using SerpAPI + Gemini 2.5 Pro.
Scrapes the author's LinkedIn profile, fetches trending content, then
generates personalised post topic recommendations.
"""

from datetime import date
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx
import os

from app.core.config import settings

router = APIRouter()

AUTHOR_PROFILE = "https://www.linkedin.com/in/arunkumargofficial"
AUTHOR_HANDLE  = "arunkumargofficial"

# Core expertise pillars inferred from profile
EXPERTISE_PILLARS = [
    "Google Cloud Platform data architecture",
    "AI agents and agentic systems",
    "Enterprise data engineering",
    "Vertex AI and Gemini",
    "Cloud Run and serverless",
    "BigQuery analytics",
    "Digital transformation",
]


def _serp_key() -> str:
    key = settings.serp_api_key or os.getenv("SERPAPI_KEY", "") or os.getenv("SERP_API_KEY", "")
    if not key:
        raise HTTPException(400, "SERP_API_KEY not configured")
    return key.strip()


async def _serp_search(query: str, num: int = 5) -> list[dict]:
    async with httpx.AsyncClient(timeout=12) as client:
        r = await client.get("https://serpapi.com/search.json", params={
            "engine": "google",
            "q": query,
            "api_key": _serp_key(),
            "num": num,
            "tbs": "qdr:w",  # past week
        })
        if r.status_code != 200:
            return []
        return r.json().get("organic_results", [])


def _snippet(results: list[dict]) -> str:
    return "\n".join(
        f"- {r.get('title','')}: {r.get('snippet','')}"
        for r in results[:5]
    )


async def _gemini_generate(prompt: str) -> str:
    import vertexai
    from vertexai.generative_models import GenerativeModel
    vertexai.init(project=settings.gcp_project_id or "ctoteam",
                  location=settings.gcp_region or "us-central1")
    model = GenerativeModel("gemini-2.5-pro")
    response = model.generate_content(prompt)
    return (response.text or "").strip()


class RecommendRequest(BaseModel):
    extra_interests: list[str] = []
    count: int = 5


class TopicRecommendation(BaseModel):
    title: str
    hook: str
    why_relevant: str
    trending_angle: str
    engagement_estimate: str
    suggested_hashtags: list[str]


class RecommendResponse(BaseModel):
    profile_summary: str
    recommendations: list[TopicRecommendation]
    search_signals: list[str]


@router.post("/recommend", response_model=RecommendResponse)
async def recommend_topics(req: RecommendRequest) -> RecommendResponse:
    """
    Discover Arun's interests via SerpAPI and recommend personalised
    LinkedIn post topics using Gemini 2.5 Pro.
    """
    today = date.today().strftime("%B %d, %Y")
    pillars = EXPERTISE_PILLARS + req.extra_interests
    signals = []

    # Parallel SerpAPI searches for trending content
    search_queries = [
        f"Google Cloud GCP news announcements {today[:7]}",
        f"AI agents enterprise 2026 trends",
        f"Vertex AI Gemini new features",
        f"BigQuery data engineering best practices 2026",
        f"Cloud Run serverless AI workloads",
    ]

    all_snippets = []
    async with httpx.AsyncClient(timeout=15) as client:
        for q in search_queries:
            try:
                r = await client.get("https://serpapi.com/search.json", params={
                    "engine": "google", "q": q,
                    "api_key": _serp_key(), "num": 4, "tbs": "qdr:m",
                })
                if r.status_code == 200:
                    results = r.json().get("organic_results", [])
                    for item in results[:3]:
                        snippet = f"{item.get('title','')}: {item.get('snippet','')}"
                        all_snippets.append(snippet)
                        signals.append(item.get("title", ""))
            except Exception:
                continue

    context = "\n".join(f"- {s}" for s in all_snippets[:20])

    prompt = f"""You are a LinkedIn content strategist for Arun Kumar G — Director & Practice Leader with 15+ years in Data, AI, and Cloud (GCP).
Today is {today}.

His expertise pillars: {", ".join(pillars)}

Recent trending signals from the web:
{context}

Generate exactly {req.count} highly personalised LinkedIn post topic recommendations.
Each topic must:
1. Align with Arun's GCP/AI/data expertise
2. Reference a real current trend from the signals above
3. Have a strong hook that challenges conventional thinking
4. Be actionable and technical enough to establish thought leadership

Return ONLY this JSON (no markdown fences):
{{
  "profile_summary": "2-sentence summary of Arun's positioning",
  "recommendations": [
    {{
      "title": "Post topic title",
      "hook": "First sentence that grabs attention (max 20 words)",
      "why_relevant": "Why this topic fits Arun's brand (1 sentence)",
      "trending_angle": "The current trend this taps into",
      "engagement_estimate": "high|medium",
      "suggested_hashtags": ["#Tag1", "#Tag2", "#Tag3"]
    }}
  ]
}}"""

    import json
    try:
        raw = await _gemini_generate(prompt)
        # Strip markdown fences if present
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw.strip())
        return RecommendResponse(
            profile_summary=data.get("profile_summary", ""),
            recommendations=[TopicRecommendation(**r) for r in data.get("recommendations", [])],
            search_signals=signals[:10],
        )
    except Exception as e:
        raise HTTPException(500, f"Recommendation failed: {e}")


@router.get("/trending")
async def get_trending(pillar: str = "GCP AI") -> dict:
    """Quick trending search for a given pillar topic."""
    results = await _serp_search(f"{pillar} site:cloud.google.com OR site:techcrunch.com OR site:venturebeat.com 2026")
    return {
        "pillar": pillar,
        "results": [{"title": r.get("title"), "snippet": r.get("snippet"), "link": r.get("link")} for r in results],
    }
