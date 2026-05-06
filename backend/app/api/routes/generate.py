from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import asyncio
import json

from app.graph.post_generation_graph import run_generation_pipeline
from app.models.schemas import GeneratePostRequest, GeneratePostResponse

router = APIRouter()


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
