from urllib.parse import urlencode
import httpx

from app.core.config import settings


class LinkedInService:
    AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
    TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
    UGC_POST_URL = "https://api.linkedin.com/v2/ugcPosts"

    def get_auth_url(self, state: str) -> str:
        params = {
            "response_type": "code",
            "client_id": settings.linkedin_client_id,
            "redirect_uri": settings.linkedin_redirect_uri,
            "scope": "openid profile w_member_social",
            "state": state,
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"

    async def exchange_code_for_token(self, code: str) -> dict:
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.linkedin_redirect_uri,
            "client_id": settings.linkedin_client_id,
            "client_secret": settings.linkedin_client_secret,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(self.TOKEN_URL, data=data)
            resp.raise_for_status()
            return resp.json()

    async def publish_post(self, access_token: str, author_urn: str, text: str) -> dict:
        payload = {
            "author": author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(self.UGC_POST_URL, json=payload, headers=headers)
            resp.raise_for_status()
            return {"status": "published", "location": resp.headers.get("x-restli-id", "")}
