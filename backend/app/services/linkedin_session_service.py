import re
from typing import Any

import httpx
from pathlib import Path
import os


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

    @staticmethod
    def auto_import_li_at(user_data_dir: str = "/tmp/linkedin_playwright_profile", timeout_sec: int = 180) -> str:
        """Open a persistent browser session and import li_at after login."""
        try:
            from playwright.sync_api import sync_playwright
        except Exception as exc:
            raise RuntimeError("Playwright is not installed. Run: pip install playwright && playwright install") from exc

        profile_dir = Path(user_data_dir)
        profile_dir.mkdir(parents=True, exist_ok=True)
        has_display = bool(os.getenv("DISPLAY"))
        print(f"[PLAYWRIGHT] launch_profile={profile_dir} has_display={has_display}")
        if not has_display:
            raise RuntimeError("Open backend browser not available on this server. Use manual li_at paste or run auto-connect locally with desktop browser.")

        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir),
                headless=False,
            )
            page = ctx.new_page()
            page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
            print(f"[PLAYWRIGHT] landed_url={page.url}")
            page.wait_for_timeout(3000)
            deadline_ms = timeout_sec * 1000
            elapsed = 0
            li_at = ""
            while elapsed < deadline_ms:
                for c in ctx.cookies():
                    if c.get("name") == "li_at" and c.get("value"):
                        li_at = c["value"]
                        break
                if li_at:
                    break
                page.wait_for_timeout(2000)
                elapsed += 2000
            ctx.close()
            print(f"[PLAYWRIGHT] li_at_found={bool(li_at)}")
            if not li_at:
                raise RuntimeError("Could not capture li_at cookie. Please login in the opened browser and retry.")
            return li_at
