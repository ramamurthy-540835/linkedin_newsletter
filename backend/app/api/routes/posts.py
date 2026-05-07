from datetime import datetime, timezone
import json
import time
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.graph.post_generation_graph import run_generation_pipeline
from app.models.schemas import (
    GenerateRequest,
    GenerateResponse,
    Post,
    PublishRequest,
    PublishResponse,
    SavePostRequest,
    SavePostResponse,
)
from app.services.linkedin_service import LinkedInService
from app.services.local_store import POSTS_FILE
from app.services.vertex_service import VertexService

router = APIRouter()
_linkedin = LinkedInService()
_vertex = VertexService()

PUB_POSTS_FILE = POSTS_FILE.parent / "published_posts.json"


@router.post("/generate", response_model=GenerateResponse)
async def generate_post(req: GenerateRequest) -> GenerateResponse:
    data = await run_generation_pipeline(
        topic=req.topic,
        audience=req.audience,
        tone=req.tone,
        objective="engagement",
        min_chars=500,
        max_chars=1200,
    )
    return GenerateResponse(
        content=data["draft_text"],
        hashtags=data["hashtags"],
        cta=data["cta"],
    )


@router.post("/generate/stream")
async def generate_post_stream(req: GenerateRequest):
    async def event_stream():
        try:
            yield f"data: {json.dumps({'stage': 'research', 'status': 'starting', 'message': 'Analyzing topic...'})}\n\n"
            t0 = time.perf_counter()
            research = await _vertex.generate_json(
                "Return JSON with key 'research_points' as 5 concise insights. "
                f"Topic: {req.topic}. Audience: {req.audience}."
            )
            t1 = time.perf_counter() - t0
            print(f"[RESEARCH] done in {t1:.2f}s")
            yield f"data: {json.dumps({'stage': 'research', 'status': 'done', 'timing': f'{t1:.1f}s', 'message': 'Research complete'})}\n\n"

            points = research.get("research_points", [])
            yield f"data: {json.dumps({'stage': 'writer', 'status': 'starting', 'message': 'Writing post...'})}\n\n"
            t0 = time.perf_counter()
            writer = await _vertex.generate_json(
                "Return JSON with key 'draft_text'. Write a LinkedIn post with a strong hook and short paragraphs. "
                f"Topic: {req.topic}. Audience: {req.audience}. Tone: {req.tone}. Research points: {points}. "
                "Target 500-1200 chars."
            )
            t2 = time.perf_counter() - t0
            print(f"[WRITER] done in {t2:.2f}s")
            yield f"data: {json.dumps({'stage': 'writer', 'status': 'done', 'timing': f'{t2:.1f}s', 'message': 'Post written'})}\n\n"

            draft = writer.get("draft_text", "")
            yield f"data: {json.dumps({'stage': 'hashtags', 'status': 'starting', 'message': 'Generating hashtags...'})}\n\n"
            t0 = time.perf_counter()
            hashtag_data = await _vertex.generate_json(
                "Return JSON with key 'hashtags' as 3-7 hashtags with # prefix. "
                f"Post: {draft}"
            )
            t3 = time.perf_counter() - t0
            print(f"[HASHTAGS] done in {t3:.2f}s")
            yield f"data: {json.dumps({'stage': 'hashtags', 'status': 'done', 'timing': f'{t3:.1f}s', 'message': 'Hashtags ready'})}\n\n"

            yield f"data: {json.dumps({'stage': 'cta', 'status': 'starting', 'message': 'Creating CTA...'})}\n\n"
            t0 = time.perf_counter()
            cta_data = await _vertex.generate_json(
                "Return JSON with key 'cta'. Write one short comment-driving CTA question. "
                f"Post: {draft}"
            )
            t4 = time.perf_counter() - t0
            print(f"[CTA] done in {t4:.2f}s")
            yield f"data: {json.dumps({'stage': 'cta', 'status': 'done', 'timing': f'{t4:.1f}s', 'message': 'CTA ready'})}\n\n"

            hashtags = hashtag_data.get("hashtags", [])
            hashtags = [h if str(h).startswith("#") else f"#{h}" for h in hashtags]
            cta = cta_data.get("cta", "")
            yield f"data: {json.dumps({'stage': 'complete', 'status': 'success', 'message': 'Generation complete', 'data': {'content': draft, 'hashtags': hashtags, 'cta': cta}})}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'stage': 'error', 'status': 'failed', 'message': f'Error: {str(exc)}'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/save", response_model=SavePostResponse)
async def save_post(req: SavePostRequest) -> SavePostResponse:
    post_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    payload = {
        "id": post_id,
        "title": req.title,
        "topic": req.topic,
        "audience": req.audience,
        "tone": req.tone,
        "content": req.content,
        "hashtags": req.hashtags,
        "cta": req.cta,
        "status": "draft",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    rows = []
    if POSTS_FILE.exists():
        rows = json.loads(POSTS_FILE.read_text(encoding="utf-8"))
    rows.append(payload)
    POSTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    POSTS_FILE.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return SavePostResponse(post_id=post_id, success=True)


@router.post("", response_model=SavePostResponse)
async def create_post(req: SavePostRequest) -> SavePostResponse:
    # Compatibility endpoint for clients using POST /api/posts
    return await save_post(req)


@router.post("/publish", response_model=PublishResponse)
async def publish_post(req: PublishRequest) -> PublishResponse:
    rows = []
    if POSTS_FILE.exists():
        rows = json.loads(POSTS_FILE.read_text(encoding="utf-8"))
    post = next((p for p in rows if p.get("id") == req.post_id), None)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    hashtag_str = " ".join(post.get("hashtags", []))
    cta = post.get("cta", "")
    parts = [post["content"]]
    if cta:
        parts.append(cta)
    if hashtag_str:
        parts.append(hashtag_str)
    full_text = "\n\n".join(parts)

    linkedin_post_id = ""
    linkedin_url = ""
    try:
        author_urn = settings.linkedin_author_urn
        token = req.access_token or settings.linkedin_access_token
        if author_urn and token:
            result = await _linkedin.publish_post(
                access_token=token,
                author_urn=author_urn,
                text=full_text,
            )
            linkedin_post_id = result.get("location", "")
            if linkedin_post_id:
                linkedin_url = f"https://www.linkedin.com/feed/update/{linkedin_post_id}/"
        else:
            # Local publish mode when LinkedIn credentials are not configured.
            linkedin_post_id = f"local-{req.post_id}"
            linkedin_url = "https://www.linkedin.com/"
    except Exception as exc:
        # Do not fail publish flow for local/demo usage.
        print(f"[PUBLISH] LinkedIn publish failed, falling back to local publish: {exc}")
        linkedin_post_id = f"local-{req.post_id}"
        linkedin_url = "https://www.linkedin.com/"
    now = datetime.now(timezone.utc)

    pub_rows = []
    if PUB_POSTS_FILE.exists():
        pub_rows = json.loads(PUB_POSTS_FILE.read_text(encoding="utf-8"))
    pub_rows.append(
        {
            "id": str(uuid.uuid4()),
            "post_id": req.post_id,
            "linkedin_post_id": linkedin_post_id,
            "linkedin_url": linkedin_url,
            "views": 0,
            "likes": 0,
            "comments": 0,
            "shares": 0,
            "published_at": now.isoformat(),
        }
    )
    PUB_POSTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PUB_POSTS_FILE.write_text(json.dumps(pub_rows, indent=2), encoding="utf-8")

    for row in rows:
        if row.get("id") == req.post_id:
            row["status"] = "published"
            row["updated_at"] = now.isoformat()
            break
    POSTS_FILE.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    return PublishResponse(
        linkedin_post_id=linkedin_post_id,
        linkedin_url=linkedin_url,
        success=True,
    )


@router.post("/{post_id}/publish", response_model=PublishResponse)
async def publish_post_by_id(post_id: str) -> PublishResponse:
    # Compatibility endpoint for clients using POST /api/posts/{id}/publish
    return await publish_post(PublishRequest(post_id=post_id, access_token=""))


@router.get("", response_model=list[Post])
async def list_posts() -> list[Post]:
    rows = []
    if POSTS_FILE.exists():
        rows = json.loads(POSTS_FILE.read_text(encoding="utf-8"))
    rows.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    normalized: list[Post] = []
    for row in rows:
        # Skip legacy/non-post rows (older draft schema etc.)
        if "id" not in row and "draft_id" in row:
            continue
        if "id" not in row or "content" not in row:
            continue
        safe = {
            "id": row.get("id"),
            "title": row.get("title") or row.get("topic") or "Untitled",
            "topic": row.get("topic") or "",
            "audience": row.get("audience") or "general",
            "tone": row.get("tone") or "professional",
            "content": row.get("content") or "",
            "hashtags": row.get("hashtags") or [],
            "cta": row.get("cta") or "",
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at") or datetime.now(timezone.utc).isoformat(),
            "updated_at": row.get("updated_at") or row.get("created_at") or datetime.now(timezone.utc).isoformat(),
        }
        try:
            normalized.append(Post(**safe))
        except Exception:
            continue
    return normalized


@router.get("/{post_id}", response_model=Post)
async def get_post(post_id: str) -> Post:
    rows = []
    if POSTS_FILE.exists():
        rows = json.loads(POSTS_FILE.read_text(encoding="utf-8"))
    row = next((p for p in rows if p.get("id") == post_id), None)
    if not row:
        raise HTTPException(status_code=404, detail="Post not found")
    return Post(**row)


@router.delete("/{post_id}")
async def delete_post(post_id: str):
    rows = []
    if POSTS_FILE.exists():
        rows = json.loads(POSTS_FILE.read_text(encoding="utf-8"))
    before = len(rows)
    rows = [r for r in rows if r.get("id") != post_id]
    if len(rows) == before:
        raise HTTPException(status_code=404, detail="Post not found")
    POSTS_FILE.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return {"success": True, "message": "Post deleted"}
