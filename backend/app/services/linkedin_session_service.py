import re
from typing import Any

import httpx


class LinkedInSessionService:
    """LinkedIn session-based fetcher using li_at cookie."""

    def __init__(self, li_at_cookie: str):
        self.li_at_cookie = (li_at_cookie or "").strip()

    def is_configured(self) -> bool:
        return bool(self.li_at_cookie)

    async def fetch_followers(self) -> list[dict[str, Any]]:
        if not self.is_configured():
            return []
        html = await self._get_html("https://www.linkedin.com/feed/followers/")
        return self._parse_profile_links(html)

    async def fetch_notifications(self) -> list[dict[str, Any]]:
        if not self.is_configured():
            return []
        html = await self._get_html("https://www.linkedin.com/notifications/")
        return self._parse_profile_links(html)

    async def _get_html(self, url: str) -> str:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Cookie": f"li_at={self.li_at_cookie}",
        }
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                return ""
            return resp.text

    def _parse_profile_links(self, html: str) -> list[dict[str, Any]]:
        if not html:
            return []
        # Minimal parser scaffold; can be upgraded with robust DOM extraction.
        matches = re.findall(r"https://www\.linkedin\.com/in/[A-Za-z0-9\-_%]+/?", html)
        seen = set()
        out = []
        for url in matches:
            if url in seen:
                continue
            seen.add(url)
            slug = url.rstrip("/").split("/")[-1]
            out.append(
                {
                    "name": slug.replace("-", " ").title(),
                    "headline": "",
                    "profile_url": url,
                    "avatar": "".join([p[0].upper() for p in slug.split("-")[:2] if p]) or "?",
                    "event": "connection",
                    "details": "",
                }
            )
        return out
