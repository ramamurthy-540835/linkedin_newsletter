"""
Media generation using Imagen 3 (images) and Veo 3 Lite (video) via Vertex AI.
Both Imagen and Veo are accessed through the google-genai SDK with Vertex AI backend.
"""

import asyncio
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.services.local_store import get_media_job, save_media_job, update_media_job

MEDIA_DIR = Path(__file__).resolve().parents[2] / "data" / "media"

# Model constants
IMAGEN_MODEL = "imagen-3.0-generate-001"
VEO_MODEL = "veo-2.0-generate-001"

_client = None


def _get_client():
    global _client
    if _client is None:
        from google import genai
        _client = genai.Client(
            vertexai=True,
            project=settings.gcp_project_id,
            location="us-central1",
        )
    return _client


# ── Prompt builders ────────────────────────────────────────────────────────────

def _image_prompt(title: str, content: str) -> str:
    excerpt = content[:400].replace("\n", " ")
    return (
        f"Professional LinkedIn newsletter cover image. "
        f"Title: '{title}'. "
        f"Topic context: {excerpt}. "
        f"Clean modern corporate design with abstract geometric shapes. "
        f"Professional navy blue and white color palette with subtle gold accents. "
        f"No text. No people. Technology and business theme. "
        f"High quality, wide landscape format."
    )


def _video_prompt(title: str, content: str) -> str:
    excerpt = content[:200].replace("\n", " ")
    return (
        f"Professional 8-second LinkedIn newsletter announcement video. "
        f"Newsletter: '{title}'. "
        f"Topic: {excerpt}. "
        f"Smooth animated corporate motion graphics. "
        f"Clean dark blue gradient background with flowing geometric light shapes. "
        f"Modern business presentation aesthetic. "
        f"Cinematic professional quality, no text overlay."
    )


# ── Image generation (synchronous, Imagen 3) ──────────────────────────────────

def _generate_images_sync(prompt: str, count: int) -> list[dict]:
    """Blocking call — must be run in a thread pool."""
    from google.genai import types

    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    client = _get_client()

    response = client.models.generate_images(
        model=IMAGEN_MODEL,
        prompt=prompt,
        config=types.GenerateImagesConfig(
            number_of_images=count,
            aspect_ratio="16:9",
            safety_filter_level="BLOCK_ONLY_HIGH",
            person_generation="ALLOW_ADULT",
        ),
    )

    results = []
    for i, img in enumerate(response.generated_images):
        if not img.image or not img.image.image_bytes:
            continue
        filename = f"img_{uuid.uuid4().hex[:8]}_{i}.png"
        path = MEDIA_DIR / filename
        path.write_bytes(img.image.image_bytes)
        results.append({"filename": filename, "url": f"/api/media/file/{filename}"})

    return results


async def generate_images(title: str, content: str, count: int = 2) -> list[dict]:
    """Generate newsletter cover images with Imagen 3. Returns list of {filename, url}."""
    prompt = _image_prompt(title, content)
    return await asyncio.to_thread(_generate_images_sync, prompt, count)


# ── Video generation (async job, Veo 3 Lite) ──────────────────────────────────

def _run_video_job(job_id: str, prompt: str, duration: int) -> None:
    """Blocking — runs in a daemon thread. Updates job state throughout."""
    try:
        update_media_job(job_id, {
            "status": "generating",
            "message": f"Generating video with Veo 3 Lite… (model: {VEO_MODEL})",
        })

        MEDIA_DIR.mkdir(parents=True, exist_ok=True)
        client = _get_client()

        from google.genai.types import GenerateVideosConfig, GenerateVideosSource

        operation = client.models.generate_videos(
            model=VEO_MODEL,
            source=GenerateVideosSource(prompt=prompt),
            config=GenerateVideosConfig(
                aspect_ratio="16:9",
                number_of_videos=1,
                duration_seconds=max(8, min(duration, 60)),
                generate_audio=False,
            ),
        )

        update_media_job(job_id, {
            "status": "processing",
            "message": "Video rendering on Google Vertex AI… polling every 5s",
        })

        # Poll until done (max ~5 min)
        for _ in range(60):
            if operation.done:
                break
            time.sleep(5)
            operation = client.operations.get(operation)

        if not operation.done:
            update_media_job(job_id, {"status": "failed", "message": "Timed out waiting for Veo"})
            return

        videos = (
            operation.result.generated_videos
            if operation.result
            else []
        )

        if not videos:
            update_media_job(job_id, {"status": "failed", "message": "Veo returned no video"})
            return

        video_bytes = videos[0].video.video_bytes if videos[0].video else None
        if not video_bytes:
            update_media_job(job_id, {"status": "failed", "message": "Empty video data from Veo"})
            return

        filename = f"vid_{job_id[:8]}.mp4"
        path = MEDIA_DIR / filename
        path.write_bytes(video_bytes)

        update_media_job(job_id, {
            "status": "completed",
            "message": "Video ready",
            "result": {
                "filename": filename,
                "url": f"/api/media/file/{filename}",
                "model": VEO_MODEL,
            },
        })

    except Exception as exc:
        update_media_job(job_id, {"status": "failed", "message": str(exc)})


def start_video_job(title: str, content: str, duration: int = 8) -> str:
    """Start async Veo video generation. Returns job_id immediately."""
    job_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat()
    save_media_job({
        "id": job_id,
        "status": "queued",
        "message": "Queued",
        "result": None,
        "created_at": now,
        "updated_at": now,
    })
    prompt = _video_prompt(title, content)
    threading.Thread(
        target=_run_video_job,
        args=(job_id, prompt, duration),
        daemon=True,
    ).start()
    return job_id
