from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import RedirectResponse
import os
import uuid
import httpx
from urllib.parse import urlencode

from app.core.config import settings
from app.services.linkedin_service import LinkedInService

router = APIRouter()
_linkedin = LinkedInService()


@router.get("/linkedin/inject")
async def linkedin_inject() -> RedirectResponse:
    """Skip OAuth — use token already in .env and redirect frontend as if OAuth completed."""
    token = settings.linkedin_access_token
    author_urn = settings.linkedin_author_urn
    frontend_url = os.getenv("FRONTEND_URL", "http://10.100.15.27:3007")
    if not token:
        raise HTTPException(400, "LINKEDIN_ACCESS_TOKEN not set in .env")
    name, headline = "Arun Kumar G", "LinkedIn Member"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get("https://api.linkedin.com/v2/userinfo",
                                 headers={"Authorization": f"Bearer {token}"})
            if r.status_code == 200:
                u = r.json()
                name = u.get("name", name)
                if not author_urn:
                    author_urn = f"urn:li:person:{u.get('sub','')}"
    except Exception:
        pass
    settings.linkedin_access_token = token
    settings.linkedin_author_urn = author_urn
    profile_url = "https://www.linkedin.com/in/arunkumargofficial"
    q = urlencode({"name": name, "headline": headline,
                   "profile_url": profile_url,
                   "access_token": token, "author_urn": author_urn,
                   "fresh": "1"})
    return RedirectResponse(f"{frontend_url}/?{q}")


@router.get("/linkedin/url")
async def linkedin_auth_url(state: str = Query(default="dev-state")) -> dict:
    return {"url": _linkedin.get_auth_url(state)}


@router.get("/linkedin")
async def linkedin_oauth() -> RedirectResponse:
    client_id = os.getenv("LINKEDIN_CLIENT_ID", settings.linkedin_client_id).strip()
    if not client_id:
        raise HTTPException(400, "Missing LINKEDIN_CLIENT_ID")
    redirect_uri = settings.linkedin_redirect_uri or f"http://10.100.15.44:{settings.port}/api/auth/linkedin/callback"
    state = str(uuid.uuid4())
    params = urlencode({
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": "openid profile email w_member_social r_1st_connections",
        "state": state,
    })
    url = f"https://www.linkedin.com/oauth/v2/authorization?{params}"
    return RedirectResponse(url)


@router.get("/linkedin/authorize")
async def linkedin_authorize() -> RedirectResponse:
    url = _linkedin.get_auth_url(state="linkedin-post-gen")
    return RedirectResponse(url)


@router.get("/linkedin/callback")
async def linkedin_callback(code: str, state: str = "") -> RedirectResponse:
    """Handles LinkedIn OAuth callback, stores credentials, and redirects to dashboard."""
    frontend_url = os.getenv("FRONTEND_URL", "http://10.100.15.44:3007")
    try:
        client_id = os.getenv("LINKEDIN_CLIENT_ID", settings.linkedin_client_id).strip()
        client_secret = os.getenv("LINKEDIN_CLIENT_SECRET", settings.linkedin_client_secret).strip()
        redirect_uri = settings.linkedin_redirect_uri or f"http://10.100.15.44:{settings.port}/api/auth/linkedin/callback"
        async with httpx.AsyncClient(timeout=15) as client:
            token_resp = await client.post("https://www.linkedin.com/oauth/v2/accessToken", data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": client_id,
                "client_secret": client_secret,
            })
            token_resp.raise_for_status()
            token = token_resp.json().get("access_token", "")
            name = "LinkedIn User"
            headline = "LinkedIn Member"
            profile_url = ""
            author_urn = ""
            if token:
                user_resp = await client.get("https://api.linkedin.com/v2/userinfo", headers={"Authorization": f"Bearer {token}"})
                if user_resp.status_code == 200:
                    u = user_resp.json()
                    sub = u.get("sub", "")
                    if sub:
                        author_urn = f"urn:li:person:{sub}"
                    name = u.get("name") or f"{u.get('given_name','')} {u.get('family_name','')}".strip() or name
                    headline = u.get("headline") or headline
                    profile_url = u.get("profile") or profile_url

            # Persist credentials on the backend so publish works without frontend passing them
            if token and author_urn:
                settings.linkedin_access_token = token
                settings.linkedin_author_urn = author_urn
                print(f"[OAuth] Stored LinkedIn credentials for {name} ({author_urn})")

        q = urlencode({
            "name": name,
            "headline": headline,
            "profile_url": profile_url,
            "access_token": token,
            "author_urn": author_urn,
        })
        return RedirectResponse(f"{frontend_url}/?{q}")
    except Exception as e:
        return RedirectResponse(f"{frontend_url}/?oauth_error={str(e)}")
