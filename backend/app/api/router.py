from fastapi import APIRouter

from app.api.routes import admin, ai, auth, config, models, posts, published_posts, serp

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(config.router, prefix="/config", tags=["config"])
api_router.include_router(models.router, prefix="/models", tags=["models"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(posts.router, prefix="/posts", tags=["posts"])
api_router.include_router(published_posts.router, prefix="/published-posts", tags=["published-posts"])
api_router.include_router(admin.router, prefix="/admin/platforms", tags=["admin"])
api_router.include_router(serp.router, prefix="/serp", tags=["serp"])
