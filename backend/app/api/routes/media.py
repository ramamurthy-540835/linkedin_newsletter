from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.services import media_service
from app.services.local_store import get_media_job

router = APIRouter()

MEDIA_DIR = Path(__file__).resolve().parents[3] / "data" / "media"

_SAFE_CHARS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.")


class GenerateImagesRequest(BaseModel):
    title: str
    content: str
    count: int = Field(default=2, ge=1, le=4)


class EnhancedImageRequest(BaseModel):
    prompt: str
    style: str = "corporate"
    aspect_ratio: str = "landscape"
    provider: str = "imagen"
    brand_colors: str = ""
    count: int = Field(default=2, ge=1, le=4)


class GenerateVideoRequest(BaseModel):
    title: str
    content: str
    duration: int = Field(default=8, ge=5, le=30)


class EnhancedVideoRequest(BaseModel):
    topic: str
    script: str = ""
    duration: int = Field(default=30, ge=8, le=60)
    voice: str = "none"
    captions: bool = False
    style: str = "corporate"


class VideoScriptRequest(BaseModel):
    topic: str
    style: str = "corporate"
    duration: int = Field(default=30, ge=15, le=60)


# ── Original endpoints (backward compat) ─────────────────────────────────────

@router.post("/images")
async def generate_images(req: GenerateImagesRequest) -> list:
    if not req.content.strip():
        raise HTTPException(status_code=400, detail="content is required")
    try:
        return await media_service.generate_images(req.title, req.content, req.count)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/video")
async def start_video(req: GenerateVideoRequest) -> dict:
    if not req.content.strip():
        raise HTTPException(status_code=400, detail="content is required")
    job_id = media_service.start_video_job(req.title, req.content, req.duration)
    return {"job_id": job_id, "status": "queued"}


# ── Enhanced endpoints ────────────────────────────────────────────────────────

@router.post("/images/generate")
async def generate_images_enhanced(req: EnhancedImageRequest) -> dict:
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="prompt is required")
    try:
        images = await media_service.generate_images_with_options(
            prompt=req.prompt,
            style=req.style,
            aspect_ratio=req.aspect_ratio,
            provider=req.provider,
            brand_colors=req.brand_colors,
            count=req.count,
        )
        return {
            "images": images,
            "style": req.style,
            "aspect_ratio": req.aspect_ratio,
            "provider": req.provider,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/video/script")
async def generate_video_script(req: VideoScriptRequest) -> dict:
    if not req.topic.strip():
        raise HTTPException(status_code=400, detail="topic is required")
    try:
        script = await media_service.generate_video_script(req.topic, req.style, req.duration)
        return script
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/video/generate")
async def start_enhanced_video(req: EnhancedVideoRequest) -> dict:
    if not req.topic.strip():
        raise HTTPException(status_code=400, detail="topic is required")
    job_id = media_service.start_enhanced_video_job(
        topic=req.topic,
        script=req.script,
        duration=req.duration,
        voice=req.voice,
        captions=req.captions,
        style=req.style,
    )
    return {"job_id": job_id, "status": "queued"}


@router.get("/styles")
async def get_styles() -> dict:
    return {
        "image_styles": list(media_service.STYLE_PRESETS.keys()),
        "video_styles": list(media_service.VIDEO_STYLES.keys()),
        "aspect_ratios": list(media_service.ASPECT_RATIOS.keys()),
    }


# ── Shared endpoints ─────────────────────────────────────────────────────────

@router.get("/job/{job_id}")
async def get_job_status(job_id: str) -> dict:
    job = get_media_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/file/{filename}")
async def get_media_file(filename: str) -> FileResponse:
    if not all(c in _SAFE_CHARS for c in filename):
        raise HTTPException(status_code=400, detail="Invalid filename")
    path = MEDIA_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    media_type = "video/mp4" if filename.endswith(".mp4") else "image/png"
    return FileResponse(path, media_type=media_type, filename=filename)
