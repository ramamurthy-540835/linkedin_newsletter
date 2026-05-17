"""
Unified content plan endpoint — Gemini generates post text, image prompt,
video script, hashtags, alt text, and title from a single topic.
"""

import json
from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter()

IMAGEN_MODELS = {
    "google-imagen-3": "imagen-3.0-generate-001",
    "google-imagen-4": "imagen-4.0-generate-001",
    "google-imagen-4-fast": "imagen-4.0-fast-generate-001",
    "google-imagen-4-ultra": "imagen-4.0-ultra-generate-001",
}

VEO_MODELS = {
    "google-veo": "veo-2.0-generate-001",
    "google-veo-lite": "veo-2.0-generate-001",
}


class ContentPlanRequest(BaseModel):
    topic: str
    audience: str = "LinkedIn professionals"
    tone: str = "professional"
    contentType: str = "text"
    brandColors: str = ""
    visualStyle: str = "corporate"
    aspectRatio: str = "16:9"
    generateImage: bool = False
    generateVideo: bool = False
    imageProvider: str = "google-imagen-3"
    videoProvider: str = "google-veo"
    videoDuration: int = 30
    videoStyle: str = "corporate"


@router.post("/content-plan")
async def generate_content_plan(req: ContentPlanRequest) -> dict:
    """Generate a unified content plan using Gemini 2.5."""
    if not req.topic.strip():
        raise HTTPException(status_code=400, detail="topic is required")

    media_sections = []
    if req.generateImage:
        media_sections.append(
            '"imagePrompt": "a detailed photorealistic image prompt describing a REAL physical scene — real objects on a real desk or in a real office, natural window light, bright white or cream background, warm tones, looks like an editorial stock photo from Unsplash shot with a Canon 5D — NEVER describe digital interfaces, abstract shapes, data streams, glowing elements, neon, dark backgrounds, or anything that looks like computer-generated art",'
            '\n  "imageTitle": "short image title",'
            '\n  "altText": "accessibility alt text for the image",'
        )
    if req.generateVideo:
        media_sections.append(
            '"videoScript": "narration script for the video",'
            '\n  "videoScenes": [{"scene_num": 1, "duration_sec": 5, "description": "visual desc", "narration": "what to say"}],'
        )

    media_instructions = ""
    if req.generateImage:
        media_instructions += f"""
- CRITICAL IMAGE PROMPT RULES (you MUST follow ALL of these):
  1. Describe a REAL physical scene: a real desk, real office, real coffee cup, real notebook, real laptop, real plants.
  2. ALWAYS: bright white or cream background, natural window light or soft studio light, warm inviting tones.
  3. NEVER EVER include: dark background, black background, digital interface, abstract shapes, data streams, neon glow, holographic, gradient mesh, geometric patterns, futuristic elements, glowing accents, connection points.
  4. The prompt must produce an image that looks like a real photograph from Unsplash or Getty Images, NOT like AI-generated digital art.
  5. Think: editorial lifestyle photography, product flat-lay, bright office scene, professional workspace.
  6. Even if the topic is about technology or AI, show REAL physical objects (laptop, whiteboard, team meeting) not digital abstractions.
- Brand colors (for small accents like a mug or notebook, NOT the background): {req.brandColors or 'professional blue/white'}.
- Aspect ratio: {req.aspectRatio}."""
    if req.generateVideo:
        media_instructions += f"""
- Video script should be short, scene-based, suitable for {req.videoDuration} seconds.
- Keep total narration under {req.videoDuration} seconds when read aloud.
- 3-6 scenes depending on duration.
- Video style: {req.videoStyle}."""

    content_type_instruction = ""
    if req.contentType == "carousel":
        content_type_instruction = '\n  "carouselSlides": [{"slide_num": 1, "heading": "...", "body": "...", "bullets": ["..."]}],'
    elif req.contentType == "poll":
        content_type_instruction = '\n  "pollQuestion": "...",\n  "pollOptions": ["option1", "option2", "option3", "option4"],'

    prompt = f"""You are an expert LinkedIn content strategist, enterprise AI storyteller, image prompt engineer, and video scene planner.

Given the following inputs, generate a comprehensive content plan:

Topic: {req.topic}
Target Audience: {req.audience}
Tone: {req.tone}
Content Type: {req.contentType}
Generate Image: {req.generateImage}
Generate Video: {req.generateVideo}

Return ONLY strict JSON (no markdown fences, no explanation):
{{
  "postText": "full LinkedIn post text, professional and human, 500-1800 chars",
  "suggestedTitle": "short post title",
  "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"],
  "cta": "engaging call-to-action question",
  {"".join(media_sections)}
  {content_type_instruction}
  "done": true
}}

Rules:
- Return strict JSON only.
- Do not include markdown outside JSON.
- Keep LinkedIn post professional and human.
- Avoid generic AI buzzwords like "revolutionize", "game-changer", "unlock".
- Avoid stale year references. Current year is {date.today().year}. Today is {date.today().strftime("%B %d, %Y")}.
- Post should tell a story, share an insight, or provoke thought.
- 3-7 hashtags, relevant to the topic.
- CTA should drive comments.{media_instructions}"""

    try:
        from google import genai

        client = genai.Client(
            vertexai=True,
            project=settings.gcp_project_id,
            location="us-central1",
        )

        response = client.models.generate_content(
            model=settings.vertex_model,
            contents=["Return valid JSON only. No markdown fences.", prompt],
        )

        raw = (response.text or "{}").strip()
        if raw.startswith("```"):
            raw = raw.split("```json")[-1].split("```")[0].strip() if "```json" in raw else raw.replace("```", "").strip()

        result = json.loads(raw)
        return result

    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"Failed to parse AI response as JSON: {str(exc)}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Content plan generation failed: {str(exc)}") from exc


@router.get("/providers")
async def get_providers() -> dict:
    """Return available image and video provider options."""
    return {
        "imageProviders": [
            {"value": "google-imagen-3", "label": "Google Imagen 3"},
            {"value": "google-imagen-4", "label": "Google Imagen 4"},
            {"value": "google-imagen-4-fast", "label": "Google Imagen 4 Fast"},
            {"value": "google-imagen-4-ultra", "label": "Google Imagen 4 Ultra"},
        ],
        "videoProviders": [
            {"value": "google-veo", "label": "Google Veo"},
            {"value": "google-veo-lite", "label": "Google Veo Lite"},
        ],
    }
