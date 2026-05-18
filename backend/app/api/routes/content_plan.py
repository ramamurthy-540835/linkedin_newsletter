"""
Unified content plan endpoint — Gemini generates post text, image prompt,
video script, hashtags, alt text, and title from a single topic.
"""

import json
from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.services.vertex_service import VertexService

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
    visualStyle: str = "archiect"
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
            '"imagePrompt": "a style-aware image prompt that strictly follows Visual Style input and use case context",'
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
- Visual Style selected by user: {req.visualStyle}
- If visualStyle is "corporate" or "professional_business":
  - Generate photorealistic editorial image prompts (real office/people/objects, natural light, stock-photo quality).
- If visualStyle is "archiect", "futuristic_ai", "modern_saas", "infographic", or "linkedin_brand":
  - Generate attractive stylized digital-art prompts (animated/illustrated look is allowed).
  - Prefer technical motifs relevant to the topic: UI flows, network nodes, code overlays, system diagrams, product screens, motion-like composition.
  - When topic/use-case fits, include campaign and analytics motifs: performance dashboard cards, KPI charts, funnel stages, attribution flow, and modern data-dashboard layouts.
  - Use cinematic contrast, clean composition, and brand-aligned accent colors.
  - Do NOT force desk-only stock-photography language.
- If visualStyle is "minimal":
  - Generate minimal clean composition with strong focal subject and subtle technical context.
- Brand colors for accents and composition: {req.brandColors or 'professional blue/white'}.
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
Visual Style: {req.visualStyle}
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
- Keep LinkedIn post professional, executive-friendly, and highly informative.
- Avoid generic AI buzzwords like "revolutionize", "game-changer", "unlock".
- Avoid stale year references. Current year is {date.today().year}. Today is {date.today().strftime("%B %d, %Y")}.
- Post should tell a story, share an insight, or provoke thought.
- Open with a strong single-line hook.
- Structure the post into 4-6 short paragraphs with blank lines between paragraphs.
- Include one compact bullet list (2-4 bullets) using "•" for scanability.
- Include 1-2 important phrases wrapped in **bold** for emphasis.
- 3-7 hashtags, relevant to the topic.
- CTA should drive comments.{media_instructions}"""

    try:
        svc = VertexService()
        result = await svc.generate_json(prompt)
        if not isinstance(result, dict):
            raise HTTPException(status_code=500, detail="Content plan generation failed: invalid AI JSON response")
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
            {"value": "xai-image", "label": "xAI Image Generation"},
        ],
        "videoProviders": [
            {"value": "xai-video", "label": "xAI Video Generation"},
        ],
    }
