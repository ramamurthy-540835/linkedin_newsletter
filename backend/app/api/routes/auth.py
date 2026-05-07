from fastapi import APIRouter, Query
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.services.linkedin_service import LinkedInService

router = APIRouter()
_linkedin = LinkedInService()


@router.get("/linkedin/url")
async def linkedin_auth_url(state: str = Query(default="dev-state")) -> dict:
    return {"url": _linkedin.get_auth_url(state)}


@router.get("/linkedin/authorize")
async def linkedin_authorize() -> RedirectResponse:
    url = _linkedin.get_auth_url(state="linkedin-post-gen")
    return RedirectResponse(url)


@router.get("/linkedin/callback")
async def linkedin_callback(code: str, state: str = "") -> RedirectResponse:
    token_data = await _linkedin.exchange_code_for_token(code)
    access_token = token_data.get("access_token", "")
    return RedirectResponse(f"{settings.frontend_url}/publish?access_token={access_token}")
