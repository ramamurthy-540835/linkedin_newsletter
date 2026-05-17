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
    """Resolve SerpAPI key: query param > settings (.env) > os env > error"""
    if key_param and key_param.strip():
        return key_param.strip()
    if settings.serp_api_key:
        return settings.serp_api_key
    env_key = os.getenv("SERP_API_KEY", "").strip()
    if env_key:
        return env_key
    raise HTTPException(400, {"error": "SerpAPI key not configured. Set SERP_API_KEY in backend .env or provide it in settings."})


@router.get("/search", response_model=SearchResponse)
async def search_serp(q: str = Query(...), key: str = Query(""), freshness: str = Query("")) -> SearchResponse:
    """Proxy SerpAPI search request. freshness: 24h, 7d, 30d or empty."""
    api_key = _get_serp_key(key)

    freshness_map = {"24h": "qdr:d", "7d": "qdr:w", "30d": "qdr:m"}
    params = {
        "q": q,
        "api_key": api_key,
        "engine": "google",
        "num": 5,
    }
    if freshness and freshness in freshness_map:
        params["tbs"] = freshness_map[freshness]

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get("https://serpapi.com/search", params=params)
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


class ConnectionItem(BaseModel):
    name: str
    headline: str = ""
    profile_url: str = ""
    avatar: str = ""
    event: str = ""
    details: str = ""


class ConnectionsResponse(BaseModel):
    connections: list[ConnectionItem]
    total: int = 0
    page: int = 1


@router.get("/connections", response_model=ConnectionsResponse)
async def get_connections(
    key: str = Query(""),
    page: int = Query(1),
    per_page: int = Query(10),
    profile: str = Query(""),
) -> ConnectionsResponse:
    """Fetch real LinkedIn connections via SerpAPI Google search."""
    api_key = _get_serp_key(key)

    handle = ""
    if profile:
        handle = profile.rstrip("/").split("/")[-1].split("?")[0]
    if not handle:
        purl = getattr(settings, "linkedin_profile_url", "") or ""
        if purl:
            handle = purl.rstrip("/").split("/")[-1]

    start = (page - 1) * per_page
    own_url_fragments = [f"/in/{handle}"] if handle else []

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            user_name = ""
            user_company = ""
            user_title = ""
            if handle:
                pr = await client.get("https://serpapi.com/search.json", params={
                    "engine": "google", "q": f"site:linkedin.com/in/{handle}", "api_key": api_key, "num": 1,
                })
                if pr.status_code == 200:
                    items = pr.json().get("organic_results", [])
                    if items:
                        t = items[0].get("title", "")
                        parts = t.split(" - ")
                        user_name = parts[0].strip() if parts else handle
                        if len(parts) > 1:
                            role_company = parts[1].strip()
                            cp = role_company.split(" @ ")
                            if len(cp) > 1:
                                user_title = cp[0].strip()
                                user_company = cp[1].strip()
                            elif " at " in role_company.lower():
                                cp2 = role_company.split(" at ")
                                user_company = cp2[-1].strip()

            queries = []
            if user_company:
                queries.append(f'site:linkedin.com/in "{user_company}"')
            if user_name:
                queries.append(f'site:linkedin.com/in "{user_name}"')
            if user_title:
                queries.append(f'site:linkedin.com/in "{user_title}"')
            if not queries:
                queries = ["site:linkedin.com/in professional network"]

            all_connections = []
            seen_urls = set()

            for q in queries:
                resp = await client.get("https://serpapi.com/search.json", params={
                    "engine": "google",
                    "q": q,
                    "api_key": api_key,
                    "num": per_page * 2,
                    "start": start,
                })
                if resp.status_code != 200:
                    continue

                data = resp.json()
                for item in data.get("organic_results", []):
                    link = item.get("link", "")
                    if "/in/" not in link or link in seen_urls:
                        continue
                    if any(frag in link for frag in own_url_fragments):
                        continue
                    seen_urls.add(link)

                    title = item.get("title", "")
                    snippet = item.get("snippet", "")

                    name_part = title.split(" - ")[0].split(" | ")[0].strip() if " - " in title or " | " in title else title
                    headline_part = title.split(" - ")[1].strip() if " - " in title and len(title.split(" - ")) > 1 else snippet.split(".")[0] if snippet else ""

                    initials = "".join(w[0].upper() for w in name_part.split()[:2] if w) if name_part else "?"

                    all_connections.append(ConnectionItem(
                        name=name_part[:60],
                        headline=headline_part[:120],
                        profile_url=link,
                        avatar=initials,
                        event="connection",
                        details=headline_part[:80],
                    ))

            return ConnectionsResponse(
                connections=all_connections[:per_page],
                total=len(all_connections),
                page=page,
            )

    except HTTPException:
        raise
    except Exception as e:
        return ConnectionsResponse(connections=[], total=0, page=page)


@router.get("/people", response_model=ConnectionsResponse)
async def search_people(
    key: str = Query(""),
    name: str = Query(""),
    handle: str = Query(""),
    company: str = Query(""),
    title: str = Query(""),
    event_type: str = Query(""),
    page: int = Query(1),
    per_page: int = Query(10),
) -> ConnectionsResponse:
    """Search LinkedIn people by name, handle, company, or title."""
    api_key = _get_serp_key(key)

    if handle:
        clean = handle.strip().rstrip("/")
        if "/in/" in clean:
            clean = clean.split("/in/")[-1]
        query = f"site:linkedin.com/in/{clean}"
    else:
        parts = ["site:linkedin.com/in"]
        if name:
            parts.append(f'"{name.strip()}"')
        if company:
            parts.append(f'"{company.strip()}"')
        if title:
            parts.append(f'"{title.strip()}"')
        if len(parts) == 1:
            return ConnectionsResponse(connections=[], total=0, page=page)
        query = " ".join(parts)

    start = (page - 1) * per_page

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get("https://serpapi.com/search.json", params={
                "engine": "google",
                "q": query,
                "api_key": api_key,
                "num": per_page,
                "start": start,
            })
            if resp.status_code != 200:
                raise HTTPException(502, f"SerpAPI error: {resp.text}")

            results = []
            seen = set()
            for item in resp.json().get("organic_results", []):
                link = item.get("link", "")
                if "/in/" not in link or link in seen:
                    continue
                seen.add(link)

                raw_title = item.get("title", "")
                snippet = item.get("snippet", "")
                name_part = raw_title.split(" - ")[0].split(" | ")[0].strip()
                headline_part = raw_title.split(" - ")[1].strip() if " - " in raw_title else snippet.split(".")[0] if snippet else ""
                initials = "".join(w[0].upper() for w in name_part.split()[:2] if w) if name_part else "?"

                results.append(ConnectionItem(
                    name=name_part[:60],
                    headline=headline_part[:120],
                    profile_url=link,
                    avatar=initials,
                    event=event_type or "connection",
                    details=headline_part[:80],
                ))

            return ConnectionsResponse(connections=results, total=len(results), page=page)

    except HTTPException:
        raise
    except Exception as e:
        return ConnectionsResponse(connections=[], total=0, page=page)
