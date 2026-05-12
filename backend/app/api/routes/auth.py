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


@router.get("/linkedin/url")
async def linkedin_auth_url(state: str = Query(default="dev-state")) -> dict:
    return {"url": _linkedin.get_auth_url(state)}


@router.get("/linkedin")
async def linkedin_oauth() -> RedirectResponse:
    client_id = os.getenv("LINKEDIN_CLIENT_ID", settings.linkedin_client_id).strip()
    if not client_id:
        raise HTTPException(400, "Missing LINKEDIN_CLIENT_ID")
    backend_base = os.getenv("BACKEND_URL", f"http://10.100.15.44:{settings.port}")
    redirect_uri = f"{backend_base}/api/auth/linkedin/callback"
    state = str(uuid.uuid4())
    params = urlencode({
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": "openid profile email w_member_social",
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
    """Handles LinkedIn OAuth callback and redirects to settings with oauth params."""
    try:
        client_id = os.getenv("LINKEDIN_CLIENT_ID", settings.linkedin_client_id).strip()
        client_secret = os.getenv("LINKEDIN_CLIENT_SECRET", settings.linkedin_client_secret).strip()
        backend_base = os.getenv("BACKEND_URL", f"http://10.100.15.44:{settings.port}")
        redirect_uri = f"{backend_base}/api/auth/linkedin/callback"
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
            profile_url = "https://www.linkedin.com/in/ramavala"
            if token:
                user_resp = await client.get("https://api.linkedin.com/v2/userinfo", headers={"Authorization": f"Bearer {token}"})
                if user_resp.status_code == 200:
                    u = user_resp.json()
                    name = u.get("name") or f"{u.get('given_name','')} {u.get('family_name','')}".strip() or name
                    headline = u.get("headline") or headline
                    profile_url = u.get("profile") or profile_url
        frontend_url = os.getenv("FRONTEND_URL", "http://10.100.15.44:3007")
        q = urlencode({"oauth": "success", "name": name, "headline": headline, "profile_url": profile_url})
        redirect_url = f"{frontend_url}/admin/settings?{q}"
        return RedirectResponse(redirect_url)
    except Exception as e:
        frontend_url = os.getenv("FRONTEND_URL", "http://10.100.15.44:3007")
        return RedirectResponse(f"{frontend_url}/admin/settings?oauth=error&message={str(e)}")
