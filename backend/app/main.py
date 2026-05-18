import threading

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.api.routes.models import ensure_models_table
from app.core.config import settings
from app.db.local_db import init_local_db

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.on_event("startup")
async def startup_seed_models() -> None:
    if settings.local_dev_mode or settings.disable_gcp or settings.disable_bigquery:
        init_local_db()
        return
    # Do not block API boot on BigQuery availability/auth.
    threading.Thread(target=ensure_models_table, daemon=True).start()


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "app": settings.app_name}
