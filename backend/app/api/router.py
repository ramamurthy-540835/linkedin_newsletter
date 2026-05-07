from fastapi import APIRouter

from app.api.routes import admin, auth, posts, published_posts

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(posts.router, prefix="/posts", tags=["posts"])
api_router.include_router(published_posts.router, prefix="/published-posts", tags=["published-posts"])
api_router.include_router(admin.router, prefix="/admin/platforms", tags=["admin"])
