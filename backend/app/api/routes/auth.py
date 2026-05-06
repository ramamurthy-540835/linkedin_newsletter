from fastapi import APIRouter, Query

from app.services.linkedin_service import LinkedInService

router = APIRouter()
linkedin = LinkedInService()


@router.get("/linkedin/url")
async def linkedin_auth_url(state: str = Query(default="dev-state")) -> dict:
    return {"url": linkedin.get_auth_url(state)}


@router.get("/linkedin/callback")
async def linkedin_callback(code: str, state: str) -> dict:
    token = await linkedin.exchange_code_for_token(code)
    return {"state": state, "token": token}
