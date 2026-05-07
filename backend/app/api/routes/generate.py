import asyncio
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.graph.post_generation_graph import run_generation_pipeline
from app.models.schemas import GeneratePostRequest, GeneratePostResponse
from app.services.local_store import get_whitepaper

router = APIRouter()

# Five angles for multi-post white paper generation
_ANGLES = [
    {
        "id": "problem_solution",
        "label": "Problem → Solution",
        "tone": "professional",
        "objective": "awareness",
        "prompt_suffix": "Frame around: what problem this solves and the solution approach.",
    },
    {
        "id": "key_insights",
        "label": "Key Insights",
        "tone": "thought-leader",
        "objective": "education",
        "prompt_suffix": "Highlight 3 key insights using bullet points. Start with the most surprising.",
    },
    {
        "id": "technical",
        "label": "Technical Deep-Dive",
        "tone": "educational",
        "objective": "credibility",
        "prompt_suffix": "Focus on technical depth, architecture, or implementation details.",
    },
    {
        "id": "storytelling",
        "label": "Story & Case Study",
        "tone": "storytelling",
        "objective": "engagement",
        "prompt_suffix": "Tell a narrative story. Use a real-world scenario or case study angle.",
    },
    {
        "id": "discussion",
        "label": "Discussion Starter",
        "tone": "conversational",
        "objective": "community",
        "prompt_suffix": "Pose a thought-provoking question to invite discussion and community debate.",
    },
]


@router.post("", response_model=GeneratePostResponse)
async def generate_post(req: GeneratePostRequest) -> GeneratePostResponse:
    data = await run_generation_pipeline(
        req.topic,
        req.audience,
        req.tone,
        req.objective,
        req.min_chars,
        req.max_chars,
    )
    text = data["post_text"]
    return GeneratePostResponse(
        post_text=text,
        hashtags=data["hashtags"],
        cta=data["cta"],
        estimated_chars=len(text),
    )


@router.post("/stream")
async def generate_post_stream(req: GeneratePostRequest):
    async def event_stream():
        for stage in ["research", "writer", "hashtags", "cta", "compliance"]:
            yield f"data: {json.dumps({'stage': stage, 'status': 'in_progress'})}\n\n"
            await asyncio.sleep(0.25)

        data = await run_generation_pipeline(
            req.topic,
            req.audience,
            req.tone,
            req.objective,
            req.min_chars,
            req.max_chars,
        )
        yield f"data: {json.dumps({'stage': 'done', 'status': 'complete', 'result': data})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


class WhitepaperPostsRequest(GeneratePostRequest):
    whitepaper_id: str = ""
    count: int = 5


@router.post("/whitepaper-posts")
async def generate_whitepaper_posts(req: WhitepaperPostsRequest) -> dict:
    """Generate multiple post variations from a white paper (one per angle)."""
    if req.whitepaper_id:
        wp = get_whitepaper(req.whitepaper_id)
        if not wp:
            raise HTTPException(status_code=404, detail="White paper not found")
        base_topic = (
            f'White paper titled "{wp["title"]}".\n\n'
            + (wp.get("content", "")[:3500] or wp.get("preview", ""))
        )
    else:
        base_topic = req.topic

    angles = _ANGLES[: max(1, min(req.count, len(_ANGLES)))]

    async def _generate_one(angle: dict) -> dict | None:
        topic = f"{base_topic}\n\nAngle: {angle['label']}\nInstructions: {angle['prompt_suffix']}"
        try:
            data = await run_generation_pipeline(
                topic=topic,
                audience=req.audience or "LinkedIn professionals",
                tone=angle["tone"],
                objective=angle["objective"],
                min_chars=req.min_chars or 500,
                max_chars=req.max_chars or 1800,
            )
            return {
                "angle_id": angle["id"],
                "angle_label": angle["label"],
                "post_text": data["post_text"],
                "hashtags": data["hashtags"],
                "cta": data["cta"],
                "estimated_chars": len(data["post_text"]),
            }
        except Exception as exc:
            return {"angle_id": angle["id"], "angle_label": angle["label"], "error": str(exc)}

    results = await asyncio.gather(*[_generate_one(a) for a in angles])
    return {
        "whitepaper_id": req.whitepaper_id,
        "posts": [r for r in results if r],
    }
