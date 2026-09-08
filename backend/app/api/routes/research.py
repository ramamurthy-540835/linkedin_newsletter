"""
AI Research Pipeline — SerpAPI + Gemini 2.5 Pro

Flow:
  1. SerpAPI: 3 batched queries (GCP news, AI agents, data engineering)
  2. Gemini 2.5 Pro: analyze signals, pick top topics, score viral potential
  3. Gemini 2.5 Pro: generate full LinkedIn post draft per topic
  4. Save drafts to data/drafts.json — ready to review and publish anytime

SerpAPI quota is protected: results are cached for 24h to avoid wasting credits.
"""

import json
import hashlib
import os
from datetime import date, datetime, timezone
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter()

CACHE_DIR  = Path(__file__).resolve().parents[3] / "data" / "research_cache"
DRAFTS_FILE = Path(__file__).resolve().parents[3] / "data" / "drafts.json"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

AUTHOR = "Arun Kumar G"
HANDLE = "arunkumargofficial"
BIO    = (
    "Director & Practice Leader | 15+ years in Data, AI & Cloud | GCP specialist | "
    "Helps enterprises build scalable data platforms, agentic AI systems, and "
    "cloud-native architectures. Generates $5M annual revenue impact."
)

SEARCH_QUERIES = [
    "Google Cloud Platform GCP AI announcements September 2026",
    "enterprise AI agents agentic workflows 2026 trends production",
    "BigQuery Vertex AI Gemini new features data engineering 2026",
]


# ── helpers ──────────────────────────────────────────────────────────────────

def _serp_key() -> str:
    key = (settings.serp_api_key or os.getenv("SERPAPI_KEY","") or os.getenv("SERP_API_KEY","")).strip()
    if not key:
        raise HTTPException(400, "SERP_API_KEY not configured")
    return key


def _cache_path(query: str) -> Path:
    h = hashlib.md5(query.encode()).hexdigest()[:12]
    return CACHE_DIR / f"{h}.json"


def _load_cache(query: str) -> list[dict] | None:
    p = _cache_path(query)
    if not p.exists():
        return None
    data = json.loads(p.read_text())
    # cache valid for 24 hours
    age = datetime.now(timezone.utc).timestamp() - data.get("ts", 0)
    if age > 86400:
        return None
    return data.get("results", [])


def _save_cache(query: str, results: list[dict]) -> None:
    _cache_path(query).write_text(json.dumps({
        "ts": datetime.now(timezone.utc).timestamp(),
        "results": results,
    }))


async def _serp_fetch(query: str) -> list[dict]:
    cached = _load_cache(query)
    if cached is not None:
        return cached
    async with httpx.AsyncClient(timeout=12) as client:
        r = await client.get("https://serpapi.com/search.json", params={
            "engine": "google", "q": query,
            "api_key": _serp_key(), "num": 6, "tbs": "qdr:m",
        })
        if r.status_code != 200:
            return []
        results = [
            {"title": x.get("title",""), "snippet": x.get("snippet",""), "link": x.get("link","")}
            for x in r.json().get("organic_results", [])[:6]
        ]
        _save_cache(query, results)
        return results


async def _gemini(prompt: str) -> str:
    import vertexai
    from vertexai.generative_models import GenerativeModel
    vertexai.init(project=settings.gcp_project_id or "ctoteam",
                  location=settings.gcp_region or "us-central1")
    model = GenerativeModel("gemini-2.5-pro")
    r = model.generate_content(prompt)
    return (r.text or "").strip()


def _strip_fences(raw: str) -> str:
    if "```" in raw:
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:]
    return raw.strip()


def _load_drafts() -> list[dict]:
    if DRAFTS_FILE.exists():
        try:
            return json.loads(DRAFTS_FILE.read_text())
        except Exception:
            return []
    return []


def _save_drafts(drafts: list[dict]) -> None:
    DRAFTS_FILE.write_text(json.dumps(drafts, indent=2, ensure_ascii=False))


# ── endpoints ─────────────────────────────────────────────────────────────────

class ResearchRequest(BaseModel):
    extra_queries: list[str] = []
    post_count: int = 3          # how many full posts to generate
    use_cache: bool = True       # set False to force fresh SerpAPI calls


class ResearchResponse(BaseModel):
    searches_used: int
    signals_collected: int
    topics_analysed: list[dict]
    drafts_saved: int
    draft_ids: list[str]


@router.post("/run", response_model=ResearchResponse)
async def run_research(req: ResearchRequest) -> ResearchResponse:
    """
    Full pipeline:
    1. SerpAPI research (cached → saves quota)
    2. Gemini topic analysis + viral scoring
    3. Gemini full post generation
    4. Save to drafts.json
    """
    today = date.today().isoformat()
    queries = SEARCH_QUERIES + req.extra_queries
    searches_used = 0
    all_signals = []

    # Step 1 — collect search signals
    for q in queries:
        cached = _load_cache(q) if req.use_cache else None
        if cached is None:
            results = await _serp_fetch(q)
            searches_used += 1
        else:
            results = cached
        for r in results:
            all_signals.append(f"[{r['title']}] {r['snippet']}")

    signals_text = "\n".join(f"- {s}" for s in all_signals[:25])

    # Step 2 — AI topic analysis + scoring
    topic_prompt = f"""You are a LinkedIn growth strategist for {AUTHOR}.
Profile: {BIO}

Today: {today}

Trending signals from the web this month:
{signals_text}

Analyse these signals and identify the {req.post_count} best LinkedIn post topics for Arun.
Score each on viral potential (1-10) based on:
- Relevance to his GCP/AI/data expertise
- Controversy or contrarian angle
- Practical value for CTOs and data leaders
- Timeliness to current news

Return ONLY this JSON (no markdown):
{{
  "topics": [
    {{
      "id": "slug-id",
      "title": "Post title",
      "viral_score": 8,
      "hook": "Opening line that grabs a CTO's attention (max 15 words)",
      "angle": "contrarian|educational|news-reaction|case-study|prediction",
      "key_points": ["point 1", "point 2", "point 3"],
      "trending_signal": "The specific news item this references",
      "hashtags": ["#Tag1","#Tag2","#Tag3","#Tag4","#Tag5"]
    }}
  ]
}}"""

    raw_topics = await _gemini(topic_prompt)
    topics_data = json.loads(_strip_fences(raw_topics)).get("topics", [])

    # Step 3 — generate full post for each topic
    drafts = _load_drafts()
    existing_ids = {d.get("id") for d in drafts}
    new_draft_ids = []

    for topic in topics_data[:req.post_count]:
        post_prompt = f"""Write a high-engagement LinkedIn post for {AUTHOR}.

Topic: {topic['title']}
Hook: {topic['hook']}
Angle: {topic['angle']}
Key points to cover: {', '.join(topic['key_points'])}
Trending signal to reference: {topic['trending_signal']}

Guidelines:
- Start with the hook (no "I" as first word)
- 150-250 words total
- Short punchy paragraphs (1-3 lines max)
- Use line breaks generously for readability
- End with a thought-provoking question to drive comments
- Add hashtags on the last line: {' '.join(topic['hashtags'])}
- Write as Arun — authoritative, direct, practitioner voice
- DO NOT use emojis
- NO generic intros like "In today's world..."

Return ONLY the post text, nothing else."""

        post_body = await _gemini(post_prompt)

        draft_id = f"{today}-{topic['id']}"
        if draft_id in existing_ids:
            draft_id = f"{today}-{topic['id']}-v2"

        draft = {
            "id": draft_id,
            "created": today,
            "status": "draft",
            "title": topic["title"],
            "hook": topic["hook"],
            "angle": topic["angle"],
            "viral_score": topic["viral_score"],
            "hashtags": topic["hashtags"],
            "trending_signal": topic["trending_signal"],
            "body": post_body,
            "author": HANDLE,
        }
        drafts.append(draft)
        new_draft_ids.append(draft_id)
        existing_ids.add(draft_id)

    _save_drafts(drafts)

    return ResearchResponse(
        searches_used=searches_used,
        signals_collected=len(all_signals),
        topics_analysed=topics_data,
        drafts_saved=len(new_draft_ids),
        draft_ids=new_draft_ids,
    )


@router.get("/drafts")
async def list_drafts(status: str = "draft") -> dict:
    """List all saved research drafts."""
    drafts = _load_drafts()
    filtered = [d for d in drafts if d.get("status") == status] if status != "all" else drafts
    return {"total": len(filtered), "drafts": filtered}


@router.get("/drafts/{draft_id}")
async def get_draft(draft_id: str) -> dict:
    """Get a single draft by ID."""
    drafts = _load_drafts()
    for d in drafts:
        if d.get("id") == draft_id:
            return d
    raise HTTPException(404, f"Draft {draft_id!r} not found")


@router.patch("/drafts/{draft_id}")
async def update_draft(draft_id: str, body: dict) -> dict:
    """Update a draft (edit body, change status, etc.)."""
    drafts = _load_drafts()
    for d in drafts:
        if d.get("id") == draft_id:
            d.update({k: v for k, v in body.items() if k != "id"})
            _save_drafts(drafts)
            return d
    raise HTTPException(404, f"Draft {draft_id!r} not found")


@router.get("/cache/status")
async def cache_status() -> dict:
    """Show what's cached to protect SerpAPI quota."""
    files = list(CACHE_DIR.glob("*.json"))
    entries = []
    for f in files:
        data = json.loads(f.read_text())
        age_h = (datetime.now(timezone.utc).timestamp() - data.get("ts", 0)) / 3600
        entries.append({
            "file": f.name,
            "results": len(data.get("results", [])),
            "age_hours": round(age_h, 1),
            "valid": age_h < 24,
        })
    return {"cached_queries": len(entries), "entries": entries}
