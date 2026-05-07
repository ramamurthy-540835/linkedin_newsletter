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


class GenerateVideoRequest(BaseModel):
    title: str
    content: str
    duration: int = Field(default=8, ge=5, le=30)


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
