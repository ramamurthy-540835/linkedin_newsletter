"""Encryption and platform-connection testing for admin credential management."""

import base64
import hashlib
from typing import Any

import httpx

from app.core.config import settings


class CredentialsService:
    def __init__(self) -> None:
        self._fernet: Any = None

    def _get_fernet(self) -> Any:
        if self._fernet is None:
            from cryptography.fernet import Fernet  # lazy import

            key = settings.credentials_encryption_key
            if not key:
                # Dev fallback — deterministic but NOT safe for production.
                # Set CREDENTIALS_ENCRYPTION_KEY in .env for production.
                raw = hashlib.sha256(b"linkedin-post-gen-dev-encryption-key-v1").digest()
                key = base64.urlsafe_b64encode(raw).decode()
            self._fernet = Fernet(key.encode() if isinstance(key, str) else key)
        return self._fernet

    def encrypt(self, value: str) -> str:
        if not value:
            return ""
        try:
            return self._get_fernet().encrypt(value.encode()).decode()
        except Exception:
            return ""

    def decrypt(self, encrypted: str) -> str:
        if not encrypted:
            return ""
        try:
            return self._get_fernet().decrypt(encrypted.encode()).decode()
        except Exception:
            return ""

    def mask(self, value: str) -> str:
        """Return a masked string showing only the last 4 chars."""
        if not value:
            return ""
        if len(value) <= 4:
            return "••••"
        if len(value) <= 8:
            return value[:2] + "••••••••"
        return value[:3] + "••••••••" + value[-4:]

    # ── Platform test connections ─────────────────────────────────────────────

    async def test_linkedin(self, access_token: str) -> dict:
        if not access_token:
            return {"valid": False, "message": "No access token provided", "user_info": None}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    "https://api.linkedin.com/v2/me",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
            if resp.status_code == 200:
                d = resp.json()
                first = d.get("localizedFirstName", "")
                last = d.get("localizedLastName", "")
                return {
                    "valid": True,
                    "message": "Connected successfully",
                    "user_info": {"name": f"{first} {last}".strip()},
                }
            return {
                "valid": False,
                "message": f"LinkedIn API returned {resp.status_code}",
                "user_info": None,
            }
        except Exception as exc:
            return {"valid": False, "message": f"Connection error: {exc}", "user_info": None}

    async def test_twitter(self, bearer_token: str) -> dict:
        if not bearer_token:
            return {"valid": False, "message": "No bearer token provided", "user_info": None}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    "https://api.twitter.com/2/users/me",
                    headers={"Authorization": f"Bearer {bearer_token}"},
                )
            if resp.status_code == 200:
                username = resp.json().get("data", {}).get("username", "unknown")
                return {
                    "valid": True,
                    "message": "Connected successfully",
                    "user_info": {"username": f"@{username}"},
                }
            return {
                "valid": False,
                "message": f"Twitter API returned {resp.status_code}",
                "user_info": None,
            }
        except Exception as exc:
            return {"valid": False, "message": f"Connection error: {exc}", "user_info": None}

    async def test_facebook(self, access_token: str) -> dict:
        if not access_token:
            return {"valid": False, "message": "No access token provided", "user_info": None}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    "https://graph.facebook.com/v18.0/me",
                    params={"access_token": access_token, "fields": "id,name"},
                )
            if resp.status_code == 200:
                d = resp.json()
                return {
                    "valid": True,
                    "message": "Connected successfully",
                    "user_info": {"name": d.get("name", ""), "id": d.get("id", "")},
                }
            return {
                "valid": False,
                "message": f"Facebook API returned {resp.status_code}",
                "user_info": None,
            }
        except Exception as exc:
            return {"valid": False, "message": f"Connection error: {exc}", "user_info": None}

    async def test_medium(self, api_key: str) -> dict:
        if not api_key:
            return {"valid": False, "message": "No integration token provided", "user_info": None}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    "https://api.medium.com/v1/me",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                )
            if resp.status_code == 200:
                name = resp.json().get("data", {}).get("name", "")
                return {
                    "valid": True,
                    "message": "Connected successfully",
                    "user_info": {"name": name},
                }
            return {
                "valid": False,
                "message": f"Medium API returned {resp.status_code}",
                "user_info": None,
            }
        except Exception as exc:
            return {"valid": False, "message": f"Connection error: {exc}", "user_info": None}
