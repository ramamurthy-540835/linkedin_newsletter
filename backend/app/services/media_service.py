"""
Media generation using Imagen 3 (images) and Veo 3 Lite (video) via Vertex AI.
Both Imagen and Veo are accessed through the google-genai SDK with Vertex AI backend.
Multi-provider support: Imagen (Google), Gemini, OpenAI DALL-E.
"""

import asyncio
import json
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.services.xai_usage_service import XAIBudgetError, assert_budget_allows_request, record_xai_usage
from app.services.local_store import get_media_job, save_media_job, update_media_job

MEDIA_DIR = Path(__file__).resolve().parents[2] / "data" / "media"

IMAGEN_MODEL = "imagen-4.0-ultra-generate-001"
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


# ── Style presets ─────────────────────────────────────────────────────────────

STYLE_PRESETS = {
    "corporate": "Clean white background (#FFFFFF). Navy (#003366) and slate grey (#4A5568) for structural elements, labels, and borders. Gold (#C9A84C) as a subtle accent on key nodes only. Flat 2D diagram style — no isometric, no 3D. Board-room ready: clean grid layout, enterprise data flow, executive KPI panels, cloud platform tiers, governance layers. No glow, no gradients, no shadows, no people, no lifestyle objects, no logos, no watermarks, no text overlays.",
    "modern_saas": "Modern SaaS platform scene with dashboard modules, workflow cards, product analytics layers, cloud integration lines, crisp UI-inspired composition, premium enterprise social visual.",
    "infographic": "Dense but organized technical infographic with labeled system blocks, data pipelines, chart widgets, orchestration arrows, and clear hierarchy for LinkedIn readability.",
    "futuristic_ai": "Dark navy background (#0A0F1E). Electric blue (#00D4FF) and violet (#7B2FFF) accent colors for connector lines, node borders, and flow arrows. Soft glow on key nodes only — no excessive neon. Flat isometric illustration with subtle depth. Enterprise AI architecture scene: LLM orchestration layers, vector database nodes, agent reasoning loops, real-time inference pipelines, and observability dashboards. Clean geometric layout — no clutter, no lifestyle objects, no people, no logos, no watermarks, no text overlays.",
    "professional_business": "Boardroom-grade enterprise systems visual with architecture clarity, observability metrics, decision pipelines, and polished executive presentation quality.",
    "minimal": "Minimal enterprise architecture composition with a strong central system map, restrained palette, clean whitespace, and precise technical emphasis.",
    "linkedin_brand": "White background (#FFFFFF). LinkedIn blue (#0A66C2) for all connector lines, icons, node borders, and highlights. Dark charcoal (#1D1D1D) for labels and text elements. Clean flat illustration style optimized for LinkedIn feed — high contrast, minimal detail, bold shapes. Scene shows a professional thought leadership concept: knowledge graph, insight flow, or platform architecture. No people, no faces, no logos, no watermarks, no text overlays, no glow, no dark background.",
    "archiect": "IBM Carbon design language. White background (#FFFFFF). Black labels and titles (#161616). IBM blue (#0F62FE) for all connector lines, arrows, node borders, and accent elements. Flat isometric illustration style. No dark background, no neon glow, no gradients, no blur, no shadows. Clean whitepaper diagram aesthetic. Enterprise architecture scene showing interconnected AI agent workflows, cloud infrastructure nodes, orchestration layers, API integration flow lines, observability metrics panels, and KPI dashboards. Architecture dominates the full frame. No people, no lifestyle objects, no logos, no watermarks, no text overlays.",
    "technical_diagram": "Technical diagram mode with explicit component boundaries, connectors, directional arrows, integration points, control planes, and observability metrics.",
    "executive_dashboard": "Executive dashboard mode with KPI cards, trend charts, anomaly signals, SLA/latency widgets, and decision-support overlays in a premium enterprise layout.",
}

ASPECT_RATIOS = {
    "square": "1:1",
    "portrait": "9:16",
    "landscape": "16:9",
}

VIDEO_STYLES = {
    "corporate": "Professional corporate video with real office environment, bright natural lighting, warm tones, clean modern aesthetic, real people and real workspace, photorealistic cinematic look",
    "tech_demo": "Real technology product demonstration, bright clean modern workspace, natural lighting, hands interacting with real devices, photorealistic, warm white environment",
    "storytelling": "Cinematic narrative with real environments and natural lighting, warm color grading, authentic human moments, photorealistic documentary style",
    "explainer": "Bright well-lit educational setting, real whiteboard or modern presentation space, natural daylight, clean professional environment, photorealistic",
    "social_media": "Bright energetic real-world setting, natural daylight, authentic lifestyle footage, warm colors, photorealistic casual professional look",
}


# ── Prompt builders ───────────────────────────────────────────────────────────

def _image_prompt(title: str, content: str) -> str:
    excerpt = _sanitize_prompt(content[:400].replace("\n", " "))
    return (
        f"Photorealistic high-end editorial photograph for a LinkedIn post. "
        f"Subject: '{title}'. "
        f"Context: {excerpt}. "
        f"MANDATORY: Bright white or very light neutral background. Natural soft studio lighting. "
        f"Real physical objects, real textures, real materials. "
        f"Looks like a professional stock photo taken with a DSLR, NOT computer generated. "
        f"FORBIDDEN: dark background, neon, abstract digital art, illustration. "
        f"No text, no watermarks, no logos. "
        f"Clean, bright, warm, inviting."
    )


def _sanitize_prompt(prompt: str) -> str:
    import re
    cleaned = re.sub(r"\s{2,}", " ", (prompt or "")).strip()
    return cleaned


def _styled_image_prompt(prompt: str, style: str, brand_colors: str = "") -> str:
    sanitized = _sanitize_prompt(prompt)
    style_desc = STYLE_PRESETS.get(style, STYLE_PRESETS["corporate"])
    brand_colors_raw = (brand_colors or "").lower()
    enforce_white_bg = ("#ffffff" in brand_colors_raw) or ("#fff" in brand_colors_raw) or ("white" in brand_colors_raw)
    parts = [
        f"{sanitized}.",
        style_desc,
        "Expand beyond a single screen into a full immersive enterprise systems architecture scene.",
        "Include interconnected AI agent workflows, BigQuery-style data warehouse nodes, Python orchestration panels, cloud infrastructure components, streaming analytics, API integration flow lines, orchestration arrows, observability metrics, and KPI widgets.",
        "FORBIDDEN: coffee cup, notebook, keyboard, mouse, desk clutter, chair edges, lifestyle/home office objects, room/window background elements.",
        "Architecture must dominate the full frame with rich technical depth.",
        "No text overlays, no watermarks, no logos.",
    ]
    if brand_colors:
        light_colors = [c.strip() for c in brand_colors.split(",") if not _is_dark_color(c.strip())]
        if light_colors:
            parts.insert(2, f"Subtle accent colors: {', '.join(light_colors)}.")
    final_prompt = " ".join(parts)
    if enforce_white_bg:
        final_prompt = (
            "MANDATORY: Pure white background (#FFFFFF). "
            "No dark background, no black background, no navy background, "
            "no gradient background. The background must be completely white. "
            + final_prompt
            + " CRITICAL OVERRIDE: Background is white (#FFFFFF). "
            "Reject any dark or colored background."
        )
    return final_prompt


def _is_dark_color(hex_color: str) -> bool:
    """Return True if a hex color is dark (luminance < 0.3)."""
    c = hex_color.lstrip("#")
    if len(c) != 6:
        return False
    try:
        r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return luminance < 0.35
    except ValueError:
        return False


def _video_prompt(title: str, content: str) -> str:
    excerpt = content[:200].replace("\n", " ")
    return (
        f"Professional 8-second LinkedIn video. "
        f"Subject: '{title}'. "
        f"Context: {excerpt}. "
        f"Bright modern office or workspace with large windows and natural daylight. "
        f"Real environment, photorealistic cinematic footage. "
        f"Warm natural color grading, clean white and neutral tones. "
        f"No dark backgrounds, no neon, no glowing effects. "
        f"Professional quality, no text overlay."
    )


def _enhanced_video_prompt(topic: str, script: str, duration: int, style: str) -> str:
    style_desc = VIDEO_STYLES.get(style, VIDEO_STYLES["corporate"])
    return (
        f"Professional {duration}-second LinkedIn video. "
        f"Topic: {topic}. "
        f"Script context: {script[:300]}. "
        f"{style_desc}. "
        f"Bright environment with natural lighting, no dark backgrounds. "
        f"Photorealistic cinematic quality, no text overlay."
    )


# ── Image generation (synchronous, Imagen 3) ─────────────────────────────────

def _generate_images_sync(prompt: str, count: int, aspect_ratio: str = "16:9") -> list[dict]:
    from google.genai import types

    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    client = _get_client()

    response = client.models.generate_images(
        model=IMAGEN_MODEL,
        prompt=prompt,
        config=types.GenerateImagesConfig(
            number_of_images=count,
            aspect_ratio=aspect_ratio,
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


IMAGEN_MODELS = {
    "google-imagen-3": "imagen-3.0-generate-001",
    "google-imagen-4": "imagen-4.0-generate-001",
    "google-imagen-4-fast": "imagen-4.0-fast-generate-001",
    "google-imagen-4-ultra": "imagen-4.0-ultra-generate-001",
}


async def generate_images_with_options(
    prompt: str,
    style: str = "corporate",
    aspect_ratio: str = "landscape",
    provider: str = "imagen",
    brand_colors: str = "",
    count: int = 2,
) -> list[dict]:
    """Generate images with style, aspect ratio, and provider options."""
    ar = ASPECT_RATIOS.get(aspect_ratio, "16:9")
    styled_prompt = _styled_image_prompt(prompt, style, brand_colors)

    if provider in ("xai-image", "xai"):
        return await _generate_images_xai(styled_prompt, count, ar)
    elif provider == "openai":
        return await _generate_images_openai(styled_prompt, count, ar)
    elif provider == "gemini":
        return await _generate_images_gemini(styled_prompt, count, ar)
    else:
        model = IMAGEN_MODELS.get(provider, IMAGEN_MODEL)
        return await asyncio.to_thread(_generate_images_sync_model, styled_prompt, count, ar, model)


async def _generate_images_xai(prompt: str, count: int, aspect_ratio: str) -> list[dict]:
    """Generate images using xAI's OpenAI-compatible images API."""
    import base64
    import httpx

    try:
        budget = assert_budget_allows_request()
    except XAIBudgetError as e:
        raise ValueError(str(e))
    api_key = (settings.xai_api_key or "").strip()
    base = (settings.xai_base_url or "").rstrip("/")
    model = (settings.xai_image_model or "").strip()

    if not api_key:
        raise ValueError("XAI_API_KEY missing")
    if not base:
        raise ValueError("XAI_BASE_URL not configured")
    if not model:
        raise ValueError("XAI_IMAGE_MODEL is required for image generation")

    MEDIA_DIR.mkdir(parents=True, exist_ok=True)

    ratio_hint = {
        "16:9": "Create as a LinkedIn landscape 16:9 visual.",
        "1:1": "Create as a LinkedIn square 1:1 visual.",
        "9:16": "Create as a LinkedIn portrait 9:16 visual.",
    }.get(aspect_ratio, "Create as a LinkedIn landscape 16:9 visual.")
    final_prompt = f"{prompt}. {ratio_hint}"

    results = []
    async with httpx.AsyncClient(timeout=90) as client:
        payload = {
            "model": model,
            "prompt": final_prompt,
            "n": 1,
            "response_format": "b64_json",
        }
        print("XAI_IMAGE_PAYLOAD_KEYS", list(payload.keys()))
        resp = await client.post(
            f"{base}/images/generations",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
        )
        if resp.status_code >= 400:
            raise ValueError(f"xAI image API error: {resp.text}")
        data = resp.json()
        record_xai_usage(feature="image_generate", model=model, usage=data.get("usage") or {})
        soft = float(settings.xai_soft_stop_usd or 0)
        used = float(budget.get("used_usd") or 0)
        if soft > 0 and used >= soft:
            print(f"[xai-budget] soft stop reached before image request: used=${used:.4f} soft=${soft:.4f}")
        images = data.get("data") or []
        if not images:
            raise ValueError("xAI image API returned empty image payload")
        for i, item in enumerate(images):
            b64 = (item.get("b64_json") or "").strip()
            if not b64:
                continue
            mime = (item.get("mime_type") or "image/png").strip().lower()
            img_bytes = base64.b64decode(b64)
            filename = f"img_{uuid.uuid4().hex[:8]}_{i}.png"
            path = MEDIA_DIR / filename
            path.write_bytes(img_bytes)
            results.append({"filename": filename, "url": f"/api/media/file/{filename}", "mime_type": mime})
    if not results:
        raise ValueError("xAI image API returned empty image payload")
    return results


def _generate_images_sync_model(prompt: str, count: int, aspect_ratio: str, model: str) -> list[dict]:
    """Generate images with a specific model ID."""
    from google.genai import types

    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    client = _get_client()

    response = client.models.generate_images(
        model=model,
        prompt=prompt,
        config=types.GenerateImagesConfig(
            number_of_images=count,
            aspect_ratio=aspect_ratio,
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


async def _generate_images_openai(prompt: str, count: int, aspect_ratio: str) -> list[dict]:
    """Generate images using OpenAI DALL-E API."""
    import httpx

    api_key = settings.openai_api_key
    if not api_key:
        raise ValueError("OpenAI API key not configured. Set OPENAI_API_KEY in backend .env or Settings.")

    MEDIA_DIR.mkdir(parents=True, exist_ok=True)

    size_map = {"1:1": "1024x1024", "16:9": "1792x1024", "9:16": "1024x1792"}
    size = size_map.get(aspect_ratio, "1024x1024")

    results = []
    async with httpx.AsyncClient(timeout=60) as client:
        for i in range(min(count, 4)):
            resp = await client.post(
                "https://api.openai.com/v1/images/generations",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": "dall-e-3", "prompt": prompt, "n": 1, "size": size, "response_format": "b64_json"},
            )
            if resp.status_code != 200:
                raise ValueError(f"OpenAI API error: {resp.text}")
            data = resp.json()
            import base64
            img_bytes = base64.b64decode(data["data"][0]["b64_json"])
            filename = f"img_{uuid.uuid4().hex[:8]}_{i}.png"
            path = MEDIA_DIR / filename
            path.write_bytes(img_bytes)
            results.append({"filename": filename, "url": f"/api/media/file/{filename}"})

    return results


async def _generate_images_gemini(prompt: str, count: int, aspect_ratio: str) -> list[dict]:
    """Generate images using Gemini's native image generation."""
    return await asyncio.to_thread(_generate_images_sync, prompt, count, aspect_ratio)


# ── Video generation (async job, Veo) ────────────────────────────────────────

def _run_video_job(job_id: str, prompt: str, duration: int) -> None:
    try:
        update_media_job(job_id, {
            "status": "generating",
            "message": f"Generating video with Veo 3 Lite... (model: {VEO_MODEL})",
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
            "status": "rendering",
            "message": "Video rendering on Google Vertex AI... polling every 5s",
        })

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


# ── Enhanced video generation with script ────────────────────────────────────

async def generate_video_script(topic: str, style: str = "corporate", duration: int = 30) -> dict:
    """Generate a video script using AI."""
    from app.services.vertex_service import VertexService
    vs = VertexService()
    prompt = f"""Generate a professional LinkedIn video script for a {duration}-second video.
Topic: {topic}
Style: {style}

Return valid JSON only:
{{
  "title": "video title",
  "script": "full narration script",
  "scenes": [
    {{"scene_num": 1, "duration_sec": 5, "description": "visual description", "narration": "what to say"}},
    ...
  ],
  "hashtags": ["#tag1", "#tag2"]
}}

Rules:
- Keep total narration under {duration} seconds when read aloud
- 3-6 scenes depending on duration
- Each scene has clear visual direction
- Professional but engaging tone"""

    result = await vs.generate_json(prompt)
    return result


def start_enhanced_video_job(
    topic: str,
    script: str = "",
    duration: int = 30,
    voice: str = "none",
    captions: bool = False,
    style: str = "corporate",
) -> str:
    """Start enhanced async video generation with script support. Returns job_id."""
    job_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat()
    save_media_job({
        "id": job_id,
        "status": "queued",
        "message": "Queued — preparing video generation",
        "result": None,
        "stages": {
            "script": "pending",
            "scenes": "pending",
            "rendering": "pending",
            "final": "pending",
        },
        "created_at": now,
        "updated_at": now,
    })

    threading.Thread(
        target=_run_enhanced_video_job,
        args=(job_id, topic, script, duration, voice, captions, style),
        daemon=True,
    ).start()
    return job_id


def _run_enhanced_video_job(
    job_id: str,
    topic: str,
    script: str,
    duration: int,
    voice: str,
    captions: bool,
    style: str,
) -> None:
    """Enhanced video job with progress stages."""
    try:
        update_media_job(job_id, {
            "status": "generating",
            "message": "Generating video script...",
            "stages": {"script": "in_progress", "scenes": "pending", "rendering": "pending", "final": "pending"},
        })

        if not script:
            import asyncio
            loop = asyncio.new_event_loop()
            try:
                script_data = loop.run_until_complete(generate_video_script(topic, style, duration))
                script = script_data.get("script", topic)
            finally:
                loop.close()

        update_media_job(job_id, {
            "message": "Script ready. Planning scenes...",
            "stages": {"script": "completed", "scenes": "in_progress", "rendering": "pending", "final": "pending"},
        })

        prompt = _enhanced_video_prompt(topic, script, duration, style)

        update_media_job(job_id, {
            "message": f"Rendering video with Veo ({duration}s)...",
            "stages": {"script": "completed", "scenes": "completed", "rendering": "in_progress", "final": "pending"},
        })

        _run_video_job_core(job_id, prompt, duration)

    except Exception as exc:
        update_media_job(job_id, {
            "status": "failed",
            "message": str(exc),
            "stages": {"script": "completed", "scenes": "completed", "rendering": "failed", "final": "failed"},
        })


def _run_video_job_core(job_id: str, prompt: str, duration: int) -> None:
    """Core Veo rendering — shared by basic and enhanced jobs."""
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

    for _ in range(60):
        if operation.done:
            break
        time.sleep(5)
        operation = client.operations.get(operation)

    if not operation.done:
        update_media_job(job_id, {"status": "failed", "message": "Timed out waiting for Veo"})
        return

    videos = operation.result.generated_videos if operation.result else []
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
        "stages": {"script": "completed", "scenes": "completed", "rendering": "completed", "final": "completed"},
        "result": {
            "filename": filename,
            "url": f"/api/media/file/{filename}",
            "model": VEO_MODEL,
        },
    })
