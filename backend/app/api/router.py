from fastapi import APIRouter

from app.api.routes import admin, ai, auth, config, content_plan, discovery_reports, interests, media, models, posts, published_posts, serp, trends, xai

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(config.router, prefix="/config", tags=["config"])
api_router.include_router(models.router, prefix="/models", tags=["models"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(posts.router, prefix="/posts", tags=["posts"])
api_router.include_router(published_posts.router, prefix="/published-posts", tags=["published-posts"])
api_router.include_router(admin.router, prefix="/admin/platforms", tags=["admin"])
api_router.include_router(serp.router, prefix="/serp", tags=["serp"])
api_router.include_router(discovery_reports.router, prefix="/discovery-reports", tags=["discovery-reports"])
api_router.include_router(media.router, prefix="/media", tags=["media"])
api_router.include_router(content_plan.router, prefix="/generate", tags=["generate"])
api_router.include_router(trends.router, prefix="/trends", tags=["trends"])
api_router.include_router(interests.router, prefix="/interests", tags=["interests"])
api_router.include_router(xai.router, prefix="/xai", tags=["xai"])
