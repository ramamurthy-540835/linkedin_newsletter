from fastapi import APIRouter

from app.api.routes import auth, drafts, generate, publish, schedule, analytics

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(drafts.router, prefix="/drafts", tags=["drafts"])
api_router.include_router(generate.router, prefix="/generate", tags=["generate"])
api_router.include_router(publish.router, prefix="/publish", tags=["publish"])
api_router.include_router(schedule.router, prefix="/schedule", tags=["schedule"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
