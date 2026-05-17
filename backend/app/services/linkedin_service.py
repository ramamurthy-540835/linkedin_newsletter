from pathlib import Path
from urllib.parse import urlencode

import httpx

from app.core.config import settings


class LinkedInService:
    AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
    TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
    UGC_POST_URL = "https://api.linkedin.com/v2/ugcPosts"
    ASSETS_URL = "https://api.linkedin.com/v2/assets"

    def get_auth_url(self, state: str) -> str:
        params = {
            "response_type": "code",
            "client_id": settings.linkedin_client_id,
            "redirect_uri": settings.linkedin_redirect_uri,
            "scope": "openid profile w_member_social r_1st_connections",
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

    async def upload_image(self, access_token: str, author_urn: str, image_bytes: bytes) -> str:
        """Upload image bytes to LinkedIn and return asset URN."""
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
        }
        register_payload = {
            "registerUploadRequest": {
                "owner": author_urn,
                "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                "serviceRelationships": [
                    {
                        "identifier": "urn:li:userGeneratedContent",
                        "relationshipType": "OWNER",
                    }
                ],
                "supportedUploadMechanism": ["SYNCHRONOUS_UPLOAD"],
            }
        }
        async with httpx.AsyncClient(timeout=60) as client:
            reg = await client.post(
                f"{self.ASSETS_URL}?action=registerUpload",
                json=register_payload,
                headers=headers,
            )
            reg.raise_for_status()
            reg_data = reg.json()

            upload_mechanism = reg_data["value"]["uploadMechanism"]
            upload_url = upload_mechanism[
                "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"
            ]["uploadUrl"]
            asset_urn = reg_data["value"]["asset"]

            # Upload binary
            await client.put(
                upload_url,
                content=image_bytes,
                headers={"Authorization": f"Bearer {access_token}"},
            )

        return asset_urn

    async def publish_post(self, access_token: str, author_urn: str, text: str) -> dict:
        """Publish text-only post."""
        return await self._post(access_token, author_urn, text, image_urns=[])

    async def publish_post_with_images(
        self,
        access_token: str,
        author_urn: str,
        text: str,
        image_filenames: list[str],
        media_dir: Path,
    ) -> dict:
        """Upload images from local files and publish as LinkedIn image post."""
        image_urns: list[str] = []
        for filename in image_filenames[:4]:  # LinkedIn max 9, but 4 is a clean carousel
            path = media_dir / filename
            if not path.exists():
                continue
            urn = await self.upload_image(access_token, author_urn, path.read_bytes())
            image_urns.append(urn)
        return await self._post(access_token, author_urn, text, image_urns)

    async def _post(
        self,
        access_token: str,
        author_urn: str,
        text: str,
        image_urns: list[str],
    ) -> dict:
        if image_urns:
            share_content = {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "IMAGE",
                "media": [
                    {
                        "status": "READY",
                        "media": urn,
                        "description": {"text": "Newsletter cover image"},
                    }
                    for urn in image_urns
                ],
            }
        else:
            share_content = {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "NONE",
            }

        payload = {
            "author": author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {"com.linkedin.ugc.ShareContent": share_content},
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
            return {
                "status": "published",
                "location": resp.headers.get("x-restli-id", ""),
                "has_images": bool(image_urns),
                "image_count": len(image_urns),
            }
