import httpx


class DevToService:
    API_BASE = "https://dev.to/api"

    async def publish_article(
        self,
        api_key: str,
        title: str,
        body_markdown: str,
        tags: list[str] | None = None,
        published: bool = True,
    ) -> dict:
        headers = {"api-key": api_key, "Content-Type": "application/json"}
        payload = {
            "article": {
                "title": title,
                "body_markdown": body_markdown,
                "tags": tags or ["ai", "llm", "modelops", "generativeai"],
                "published": published,
            }
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.API_BASE}/articles", json=payload, headers=headers
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "status": "published" if published else "draft",
                "url": data.get("url", ""),
                "id": data.get("id"),
            }

    async def test_connection(self, api_key: str) -> dict:
        headers = {"api-key": api_key}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{self.API_BASE}/users/me", headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                return {"valid": True, "username": data.get("username", "")}
            return {"valid": False, "username": ""}
