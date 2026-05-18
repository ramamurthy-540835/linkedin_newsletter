from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.core.config import settings
from app.services.content_sanitizer import sanitize_content
from app.services.devto_service import DevToService
from app.services.linkedin_service import LinkedInService

router = APIRouter()
linkedin = LinkedInService()
devto = DevToService()

PROJECT_ROOT = Path(__file__).resolve().parents[4]
REPORTS_DIR = PROJECT_ROOT / "reports"
VALID_PROVIDERS = {"anthropic", "openai", "xai"}
_SAFE_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
)


def _find_file(provider_dir: Path, patterns: list[str]) -> Path | None:
    for pattern in patterns:
        matches = sorted(provider_dir.glob(pattern), reverse=True)
        if matches:
            return matches[0]
    return None


def _scan_provider(provider: str) -> dict | None:
    provider_dir = REPORTS_DIR / provider
    if not provider_dir.is_dir():
        return None

    dashboard = _find_file(
        provider_dir,
        [f"dashboard_provider_{provider}_*.png", "model_chart_*.png"],
    )
    architecture = _find_file(
        provider_dir,
        [
            f"architecture_renderer_xai_provider_{provider}_*.png",
            f"xai_architecture_*.png",
            f"architecture_*_{provider}_*.png",
        ],
    )
    linkedin_post = _find_file(provider_dir, ["linkedin_post_*.txt"])
    medium_article = _find_file(provider_dir, ["medium_article_*.md"])
    medium_draft = _find_file(provider_dir, ["medium_draft_*.md"])

    return {
        "name": provider,
        "display_name": provider.upper(),
        "dashboard_image": dashboard.name if dashboard else None,
        "architecture_image": architecture.name if architecture else None,
        "linkedin_post_file": linkedin_post.name if linkedin_post else None,
        "medium_article_file": medium_article.name if medium_article else None,
        "medium_draft_file": medium_draft.name if medium_draft else None,
    }


@router.get("")
async def list_discovery_reports() -> dict:
    providers = []
    for name in sorted(VALID_PROVIDERS):
        info = _scan_provider(name)
        if info:
            providers.append(info)
    return {"providers": providers}


@router.get("/{provider}")
async def get_discovery_report(provider: str) -> dict:
    if provider not in VALID_PROVIDERS:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider}")

    info = _scan_provider(provider)
    if not info:
        raise HTTPException(status_code=404, detail=f"No reports for {provider}")

    provider_dir = REPORTS_DIR / provider

    linkedin_text = ""
    if info["linkedin_post_file"]:
        linkedin_text = (provider_dir / info["linkedin_post_file"]).read_text()

    medium_content = ""
    article_file = info["medium_article_file"] or info["medium_draft_file"]
    if article_file:
        medium_content = (provider_dir / article_file).read_text()

    return {**info, "linkedin_text": linkedin_text, "medium_content": medium_content}


@router.get("/{provider}/image/{filename}")
async def get_report_image(provider: str, filename: str) -> FileResponse:
    if provider not in VALID_PROVIDERS:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider}")
    if not all(c in _SAFE_CHARS for c in filename):
        raise HTTPException(status_code=400, detail="Invalid filename")

    path = (REPORTS_DIR / provider / filename).resolve()
    if not str(path).startswith(str(REPORTS_DIR.resolve())):
        raise HTTPException(status_code=400, detail="Invalid path")
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(path, media_type="image/png", filename=filename)


class PublishLinkedInRequest(BaseModel):
    include_image: bool = True


@router.post("/{provider}/publish/linkedin")
async def publish_to_linkedin(provider: str, req: PublishLinkedInRequest) -> dict:
    if provider not in VALID_PROVIDERS:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider}")

    token = settings.linkedin_access_token
    urn = settings.linkedin_author_urn
    if not urn:
        raise HTTPException(
            status_code=400,
            detail="Missing LINKEDIN_AUTHOR_URN -- configure in Admin Settings",
        )
    if not token:
        raise HTTPException(
            status_code=400,
            detail="Missing LINKEDIN_ACCESS_TOKEN -- complete OAuth in Admin Settings",
        )

    info = _scan_provider(provider)
    if not info or not info["linkedin_post_file"]:
        raise HTTPException(status_code=404, detail="No LinkedIn post found")

    provider_dir = REPORTS_DIR / provider
    text = sanitize_content((provider_dir / info["linkedin_post_file"]).read_text().strip())

    image_urns: list[str] = []
    if req.include_image and info["dashboard_image"]:
        img_path = provider_dir / info["dashboard_image"]
        if img_path.exists():
            asset_urn = await linkedin.upload_image(
                token, urn, img_path.read_bytes()
            )
            image_urns.append(asset_urn)

    result = await linkedin._post(token, urn, text, image_urns)
    return {**result, "provider": provider}


class PublishDevToRequest(BaseModel):
    tags: list[str] = []
    published: bool = True


@router.post("/{provider}/publish/devto")
async def publish_to_devto(provider: str, req: PublishDevToRequest) -> dict:
    if provider not in VALID_PROVIDERS:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider}")

    api_key = settings.devto_api_key
    if not api_key:
        raise HTTPException(
            status_code=400, detail="Missing DEVTO_API_KEY in environment"
        )

    info = _scan_provider(provider)
    article_file = info.get("medium_article_file") or info.get("medium_draft_file") if info else None
    if not info or not article_file:
        raise HTTPException(status_code=404, detail="No article found")

    provider_dir = REPORTS_DIR / provider
    body = (provider_dir / article_file).read_text()

    title = f"{provider.upper()} AI Model Discovery Report"
    for line in body.splitlines():
        if line.startswith("# "):
            title = line.lstrip("# ").strip()
            break

    tags = req.tags or ["ai", "llm", "modelops", "generativeai"]

    result = await devto.publish_article(api_key, title, body, tags, req.published)
    return {**result, "provider": provider}
