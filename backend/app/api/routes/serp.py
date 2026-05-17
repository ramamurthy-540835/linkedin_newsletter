import os
import io
import csv
import math
from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from pydantic import BaseModel
import httpx
from app.core.config import settings
from app.services.linkedin_session_service import LinkedInSessionService

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


def _simulated_mode_response(message: str = "Real LinkedIn session/API unavailable. Using public search simulation. For full My Network access use the official LinkedIn site.") -> dict:
    return {
        "simulated": True,
        "message": message,
        "my_network_url": "https://www.linkedin.com/mynetwork/",
        "notifications_url": "https://www.linkedin.com/notifications/?filter=all",
    }


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
    company: str = ""
    location: str = ""


class ConnectionsResponse(BaseModel):
    connections: list[ConnectionItem]
    total: int = 0
    page: int = 1
    pageSize: int = 10
    hasNext: bool = False
    hasPrev: bool = False
    selectedSource: str = "none"
    selectedMode: str = "connections"
    debugMessage: str = ""
    error: str = ""


class LinkedInSessionRequest(BaseModel):
    li_at: str


def _parse_linkedin_title(title: str, snippet: str = ""):
    """Parse a LinkedIn search result title into name and headline."""
    name_part = title.split(" - ")[0].split(" | ")[0].strip() if " - " in title or " | " in title else title
    headline_part = ""
    if " - " in title and len(title.split(" - ")) > 1:
        headline_part = title.split(" - ")[1].strip()
    elif snippet:
        headline_part = snippet.split(".")[0]
    initials = "".join(w[0].upper() for w in name_part.split()[:2] if w) if name_part else "?"
    return name_part[:60], headline_part[:120], initials

def _followers_relevance_ok(link: str, title: str, snippet: str, handle: str, user_name: str) -> bool:
    """Reduce false positives for followers mode by enforcing target relevance."""
    blob = f"{link} {title} {snippet}".lower()
    h = (handle or "").strip().lower()
    n = (user_name or "").strip().lower()
    if h and h in blob:
        return True
    if n:
        parts = [p for p in n.split() if len(p) > 2]
        if len(parts) >= 2 and all(p in blob for p in parts[:2]):
            return True
        if any(p in blob for p in parts):
            return True
    return False


def _paginate(items: list, page: int, page_size: int) -> dict:
    """Compute pagination metadata for a list of items."""
    total = len(items)
    total_pages = max(1, math.ceil(total / page_size))
    page = max(1, min(page, total_pages))
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "items": items[start:end],
        "total": total,
        "page": page,
        "pageSize": page_size,
        "hasNext": page < total_pages,
        "hasPrev": page > 1,
    }


@router.get("/linkedin/status")
async def linkedin_status():
    """Return configuration status for LinkedIn sources."""
    oauth = bool(getattr(settings, 'linkedin_access_token', None) or os.getenv('LINKEDIN_ACCESS_TOKEN'))
    session = bool(getattr(settings, 'linkedin_session_cookie', None) or os.getenv('LINKEDIN_SESSION_COOKIE'))
    serp = bool(_get_serp_key('') if True else False)  # will raise but we catch
    try:
        _get_serp_key('')
        serp = True
    except:
        serp = False
    csv_imported = False
    try:
        # simplistic check
        csv_imported = bool(os.path.exists('/tmp/linkedin_csv_imported'))
    except:
        pass
    active = 'oauth' if oauth else 'session' if session else 'serp' if serp else 'csv' if csv_imported else 'none'
    return {
        "linkedinOAuthConfigured": oauth,
        "linkedinSessionConfigured": session,
        "serpConfigured": serp,
        "csvImported": csv_imported,
        "activeSource": active,
        "profileHandle": getattr(settings, 'linkedin_profile_url', '').split('/')[-1] or 'ramavala'
    }


@router.post("/linkedin/session")
async def set_linkedin_session(body: LinkedInSessionRequest):
    li_at = (body.li_at or "").strip()
    if not li_at:
        raise HTTPException(status_code=400, detail="li_at cookie is required")
    setattr(settings, "linkedin_session_cookie", li_at)
    return {"ok": True, "linkedinSessionConfigured": True}

@router.get("/connections", response_model=ConnectionsResponse)
async def get_connections(
    key: str = Query(""),
    page: int = Query(1),
    per_page: int = Query(10),
    profile: str = Query(""),
    mode: str = Query("connections"),  # connections | followers | notifications
) -> ConnectionsResponse:
    """Fetch LinkedIn connections/followers/notifications via SerpAPI simulation.
    Real LinkedIn My Network requires login. Returns simulated flag when using public search.
    """
    oauth_configured = bool(getattr(settings, "linkedin_access_token", None) or os.getenv("LINKEDIN_ACCESS_TOKEN"))
    session_configured = bool(getattr(settings, "linkedin_session_cookie", None) or os.getenv("LINKEDIN_SESSION_COOKIE"))
    selected_source = "oauth" if oauth_configured else "session" if session_configured else "none"
    api_key = ""
    if mode in ("followers", "notifications"):
        if selected_source == "none":
            return ConnectionsResponse(
                connections=[],
                total=0,
                page=page,
                pageSize=per_page,
                hasNext=False,
                hasPrev=False,
                selectedSource="none",
                selectedMode=mode,
                debugMessage=f"Auth required for {mode}.",
                error="LinkedIn authentication required for real followers",
            )
        if selected_source == "session":
            svc = LinkedInSessionService(getattr(settings, "linkedin_session_cookie", "") or os.getenv("LINKEDIN_SESSION_COOKIE", ""))
            raw = await (svc.fetch_followers() if mode == "followers" else svc.fetch_notifications())
            paged = _paginate(raw, page, per_page)
            return ConnectionsResponse(
                connections=[ConnectionItem(**x) for x in paged["items"]],
                total=paged["total"],
                page=paged["page"],
                pageSize=paged["pageSize"],
                hasNext=paged["hasNext"],
                hasPrev=paged["hasPrev"],
                selectedSource="session",
                selectedMode=mode,
                debugMessage=f"Using source=session mode={mode}.",
            )
        # OAuth exists but follower extraction is not implemented yet.
        return ConnectionsResponse(
            connections=[],
            total=0,
            page=page,
            pageSize=per_page,
            hasNext=False,
            hasPrev=False,
            selectedSource="oauth",
            selectedMode=mode,
            debugMessage=f"OAuth configured, but {mode} fetcher is not implemented yet.",
            error="LinkedIn authentication required for real followers",
        )

    # SERP remains enabled for public discovery/search modes only.
    api_key = _get_serp_key(key)

    handle = ""
    if profile:
        handle = profile.rstrip("/").split("/")[-1].split("?")[0]
    if not handle:
        purl = getattr(settings, "linkedin_profile_url", "") or ""
        if purl:
            handle = purl.rstrip("/").split("/")[-1]

    own_url_fragments = [f"/in/{handle}"] if handle else []

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            user_name = ""
            user_company = ""
            user_title = ""
            user_location = ""
            if handle:
                pr = await client.get("https://serpapi.com/search.json", params={
                    "engine": "google", "q": f"site:linkedin.com/in/{handle}", "api_key": api_key, "num": 1,
                })
                if pr.status_code == 200:
                    items = pr.json().get("organic_results", [])
                    if items:
                        t = items[0].get("title", "")
                        snippet = items[0].get("snippet", "")
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
                        for loc_kw in ["Greater", "Area", "Metro"]:
                            if loc_kw in snippet:
                                for part in snippet.split("·"):
                                    part = part.strip()
                                    if loc_kw in part:
                                        user_location = part
                                        break

            queries = []
            if handle:
                queries.append(f'site:linkedin.com/in "{handle}" connections')
            if user_name:
                name_parts = user_name.split()
                if len(name_parts) >= 2:
                    queries.append(f'site:linkedin.com/in "{name_parts[0]}" network professional')
            if user_company:
                queries.append(f'site:linkedin.com/in "{user_company}"')
            if user_title:
                queries.append(f'site:linkedin.com/in "{user_title}"')
            if user_location:
                queries.append(f'site:linkedin.com/in "{user_location}" professional')
            if not queries:
                queries = ["site:linkedin.com/in professional network"]

            if mode == "followers":
                queries = [
                    f'site:linkedin.com/in "{handle}" "followers"',
                    f'site:linkedin.com/in "{user_name}" "LinkedIn"',
                    f'site:linkedin.com/in "{user_name}" "follower"',
                    f'site:linkedin.com/feed/followers/ "{handle}"'
                ] if handle or user_name else ["site:linkedin.com/in followers network"]
                print(f"[FOLLOWERS] mode=followers selected_source={selected_source} profile_handle={handle or 'unknown'}")
                print(f"[FOLLOWERS] mode=followers queries={queries}")
            elif mode == "notifications":
                queries = ["site:linkedin.com/in birthday OR anniversary OR promotion OR job change"]

            all_connections = []
            seen_urls = set()

            for q in queries:
                resp = await client.get("https://serpapi.com/search.json", params={
                    "engine": "google",
                    "q": q,
                    "api_key": api_key,
                    "num": per_page * 2,
                    "start": 0,
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
                    title = item.get("title", "")
                    snippet = item.get("snippet", "")
                    if mode == "followers" and not _followers_relevance_ok(link, title, snippet, handle, user_name):
                        continue
                    seen_urls.add(link)
                    name_part, headline_part, initials = _parse_linkedin_title(title, snippet)

                    all_connections.append(ConnectionItem(
                        name=name_part,
                        headline=headline_part,
                        profile_url=link,
                        avatar=initials,
                        event="connection",
                        details=headline_part[:80],
                    ))

            paged = _paginate(all_connections, page, per_page)
            resp = ConnectionsResponse(
                connections=paged["items"],
                total=paged["total"],
                page=paged["page"],
                pageSize=paged["pageSize"],
                hasNext=paged["hasNext"],
                hasPrev=paged["hasPrev"],
                selectedSource=selected_source,
                selectedMode=mode,
                debugMessage=f"Using source={selected_source} mode={mode}.",
            )
            print(f"[FOLLOWERS] mode={mode} selected_source={selected_source} page_results={len(paged['items'])} total_results={paged['total']}")
            if not resp.connections:
                empty_reason = "configured-but-no-public-results" if selected_source in ("oauth", "session") else "serp-no-results"
                print(f"[FOLLOWERS] empty reason={empty_reason}")
                if mode == "followers":
                    resp = ConnectionsResponse(
                        **{
                            **resp.dict(),
                            **_simulated_mode_response("Configured, but no followers were returned. Check backend logs."),
                            "debugMessage": f"Using source={selected_source} mode={mode}. Empty reason={empty_reason}.",
                        }
                    )
                else:
                    resp = ConnectionsResponse(
                        **{
                            **resp.dict(),
                            **_simulated_mode_response("Followers mode active. Real LinkedIn followers require login. Using public search simulation."),
                            "debugMessage": f"Using source={selected_source} mode={mode}. Empty reason={empty_reason}.",
                        }
                    )
            return resp

    except HTTPException:
        raise
    except Exception as e:
        sim = _simulated_mode_response()
        return ConnectionsResponse(
            connections=[],
            total=0,
            page=page,
            pageSize=per_page,
            selectedSource=selected_source if selected_source else "none",
            selectedMode=mode,
            debugMessage=f"Exception while loading connections: {str(e)}",
            **sim,
        )


@router.get("/people", response_model=ConnectionsResponse)
async def search_people(
    key: str = Query(""),
    name: str = Query(""),
    handle: str = Query(""),
    company: str = Query(""),
    title: str = Query(""),
    location: str = Query(""),
    industry: str = Query(""),
    degree: str = Query(""),
    event_type: str = Query(""),
    page: int = Query(1),
    per_page: int = Query(10),
) -> ConnectionsResponse:
    """Search LinkedIn people by name, handle, company, title, location, industry.
    Supports full searchable lookup. Returns simulated flag when real API unavailable.
    """
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
        if location:
            parts.append(f'"{location.strip()}"')
        if industry:
            parts.append(f'"{industry.strip()}"')
        if len(parts) == 1:
            return ConnectionsResponse(connections=[], total=0, page=page, pageSize=per_page)
        query = " ".join(parts)

    start = (page - 1) * per_page

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get("https://serpapi.com/search.json", params={
                "engine": "google",
                "q": query,
                "api_key": api_key,
                "num": per_page * 2,
                "start": start,
            })
            if resp.status_code != 200:
                raise HTTPException(502, f"SerpAPI error: {resp.text}")

            results = []
            seen = set()
            data = resp.json()
            total_serp = data.get("search_information", {}).get("total_results", 0)
            for item in data.get("organic_results", []):
                link = item.get("link", "")
                if "/in/" not in link or link in seen:
                    continue
                seen.add(link)

                raw_title = item.get("title", "")
                snippet = item.get("snippet", "")
                name_part, headline_part, initials = _parse_linkedin_title(raw_title, snippet)

                results.append(ConnectionItem(
                    name=name_part,
                    headline=headline_part,
                    profile_url=link,
                    avatar=initials,
                    event=event_type or "connection",
                    details=headline_part[:80],
                ))

            estimated_total = max(len(results), min(total_serp, 100))
            resp = ConnectionsResponse(
                connections=results,
                total=estimated_total,
                page=page,
                pageSize=per_page,
                hasNext=len(results) >= per_page,
                hasPrev=page > 1,
            )
            if not resp.connections:
                resp = ConnectionsResponse(**{**resp.dict(), **_simulated_mode_response()})
            return resp

    except HTTPException:
        raise
    except Exception as e:
        sim = _simulated_mode_response()
        return ConnectionsResponse(connections=[], total=0, page=page, pageSize=per_page, **sim)


@router.post("/connections/import-csv", response_model=ConnectionsResponse)
async def import_connections_csv(
    file: UploadFile = File(...),
    page: int = Query(1),
    per_page: int = Query(10),
):
    """Import LinkedIn connections from a CSV export."""
    content = await file.read()
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    header_map = {}
    if reader.fieldnames:
        for f in reader.fieldnames:
            fl = f.strip().lower().replace(" ", "_")
            if "first" in fl and "name" in fl:
                header_map["first_name"] = f
            elif "last" in fl and "name" in fl:
                header_map["last_name"] = f
            elif fl in ("name", "full_name"):
                header_map["name"] = f
            elif fl in ("url", "profile_url", "linkedin_url", "profile_link"):
                header_map["url"] = f
            elif fl in ("company", "organization", "employer"):
                header_map["company"] = f
            elif fl in ("title", "position", "job_title", "role"):
                header_map["title"] = f
            elif fl in ("location", "city", "region"):
                header_map["location"] = f
            elif "email" in fl:
                header_map["email"] = f
            elif "connected" in fl and "on" in fl:
                header_map["connected_on"] = f

    connections = []
    for row in reader:
        name = ""
        if "name" in header_map:
            name = row.get(header_map["name"], "").strip()
        if not name and "first_name" in header_map:
            first = row.get(header_map["first_name"], "").strip()
            last = row.get(header_map["last_name"], "").strip() if "last_name" in header_map else ""
            name = f"{first} {last}".strip()
        if not name:
            continue

        url = row.get(header_map.get("url", ""), "").strip()
        company = row.get(header_map.get("company", ""), "").strip()
        title = row.get(header_map.get("title", ""), "").strip()
        location = row.get(header_map.get("location", ""), "").strip()

        headline = f"{title} at {company}" if title and company else title or company or ""
        initials = "".join(w[0].upper() for w in name.split()[:2] if w) if name else "?"

        if not url:
            slug = name.lower().replace(" ", "-")
            url = f"https://www.linkedin.com/in/{slug}"

        connections.append(ConnectionItem(
            name=name[:60],
            headline=headline[:120],
            profile_url=url,
            avatar=initials,
            event="connection",
            details=headline[:80],
            company=company,
            location=location,
        ))

    paged = _paginate(connections, page, per_page)
    return ConnectionsResponse(
        connections=paged["items"],
        total=paged["total"],
        page=paged["page"],
        pageSize=paged["pageSize"],
        hasNext=paged["hasNext"],
        hasPrev=paged["hasPrev"],
    )
