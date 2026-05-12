import os
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import httpx
import json
from app.core.config import settings

router = APIRouter()


class SearchResult(BaseModel):
    title: str
    snippet: str
    link: str
    source: str = ""


class SearchResponse(BaseModel):
    results: list[SearchResult]


class ProfileData(BaseModel):
    name: str = "LinkedIn Member"
    headline: str = "LinkedIn Member"
    bio: str = "Profile data not available via search"
    skills: list[str] = []
    interests: list[str] = []
    summary: str = "Profile data not available via search"
    profile_url: str = ""


def _get_serp_key(key_param: str = "") -> str:
    """Resolve SerpAPI key: query param > env var > error"""
    if key_param and key_param.strip():
        return key_param.strip()
    env_key = os.getenv("SERP_API_KEY", "").strip()
    if env_key:
        return env_key
    raise HTTPException(400, {"error": "SerpAPI key not configured. Set SERP_API_KEY in backend .env or provide it in settings."})


@router.get("/search", response_model=SearchResponse)
async def search_serp(q: str = Query(...), key: str = Query("")) -> SearchResponse:
    """Proxy SerpAPI search request"""
    api_key = _get_serp_key(key)

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get("https://serpapi.com/search", params={
                "q": q,
                "api_key": api_key,
                "engine": "google",
                "num": 5,
            })
            if resp.status_code != 200:
                raise HTTPException(502, f"SerpAPI error: {resp.text}")

            data = resp.json()
            results = []
            for item in data.get("organic_results", []):
                results.append(SearchResult(
                    title=item.get("title", ""),
                    snippet=item.get("snippet", ""),
                    link=item.get("link", ""),
                    source=item.get("source", ""),
                ))
            return SearchResponse(results=results)
    except HTTPException:
        raise
    except httpx.TimeoutException:
        raise HTTPException(502, "SerpAPI request timeout")
    except Exception as e:
        raise HTTPException(502, f"SerpAPI error: {str(e)}")


@router.get("/profile/scrape", response_model=ProfileData)
async def scrape_profile(linkedin_url: str = Query(...), key: str = Query("")) -> ProfileData:
    """Scrape LinkedIn profile info via SerpAPI"""
    api_key = _get_serp_key(key)

    handle = linkedin_url.rstrip("/").split("/")[-1] if linkedin_url else "member"
    fallback = ProfileData(
        name=handle or "LinkedIn Member",
        headline="LinkedIn Member",
        bio="Profile data not available via search",
        skills=[],
        interests=[],
        summary="Profile data not available via search",
        profile_url=linkedin_url or f"https://www.linkedin.com/in/{handle}",
    )

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r1 = await client.get("https://serpapi.com/search.json", params={
                "engine": "google",
                "q": f"{handle} site:linkedin.com/in",
                "api_key": api_key,
                "num": 5,
            })
            r2 = await client.get("https://serpapi.com/search.json", params={
                "engine": "google",
                "q": f"linkedin {handle} profile skills",
                "api_key": api_key,
            })
            if r1.status_code != 200 and r2.status_code != 200:
                return fallback

            d1 = r1.json() if r1.status_code == 200 else {}
            d2 = r2.json() if r2.status_code == 200 else {}
            kg = d2.get("knowledge_graph") or d1.get("knowledge_graph") or {}
            organic = d1.get("organic_results") or d2.get("organic_results") or []
            top = organic[0] if organic else {}

            name = kg.get("title") or handle or "LinkedIn Member"
            headline = kg.get("description") or kg.get("subtitle") or top.get("snippet") or "LinkedIn Member"
            summary = top.get("snippet") or kg.get("description") or "Profile data not available via search"
            bio = kg.get("description") or summary

            skills = []
            interests = []
            combined_text = (bio + " " + summary + " " + " ".join([x.get("snippet", "") for x in organic[:3]])).lower()
            skill_keywords = [
                "python", "java", "javascript", "react", "fastapi", "sql",
                "machine learning", "ai", "data science", "leadership",
                "project management", "marketing", "sales", "design",
                "product", "engineering", "strategy", "analytics"
            ]
            for keyword in skill_keywords:
                if keyword in combined_text and keyword not in skills:
                    skills.append(keyword)

            profile = ProfileData(
                name=name,
                headline=headline,
                bio=bio,
                skills=skills[:10],
                interests=interests,
                summary=summary,
                profile_url=linkedin_url or f"https://www.linkedin.com/in/{handle}",
            )
            if not profile.name:
                return fallback
            return profile
    except HTTPException:
        raise
    except Exception as e:
        return fallback
