from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config.platform_loader import (
    list_platforms,
    load_platform_yaml,
    save_platform_yaml,
    set_platform_enabled,
    validate_yaml,
)

router = APIRouter()


class PlatformSaveRequest(BaseModel):
    yaml_content: str


class PlatformToggleRequest(BaseModel):
    enabled: bool


@router.get("/platforms")
async def get_all_platforms() -> dict:
    return {"platforms": list_platforms()}


@router.get("/platforms/{platform_id}")
async def get_platform(platform_id: str) -> dict:
    try:
        yaml_content = load_platform_yaml(platform_id)
        return {"platform_id": platform_id, "yaml_content": yaml_content}
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/platforms/{platform_id}")
async def save_platform(platform_id: str, body: PlatformSaveRequest) -> dict:
    is_valid, errors = validate_yaml(body.yaml_content)
    if not is_valid:
        raise HTTPException(status_code=422, detail={"errors": errors})
    try:
        save_platform_yaml(platform_id, body.yaml_content)
        return {"success": True, "platform_id": platform_id}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/platforms/{platform_id}/validate")
async def validate_platform(platform_id: str, body: PlatformSaveRequest) -> dict:
    is_valid, errors = validate_yaml(body.yaml_content)
    return {"valid": is_valid, "errors": errors}


@router.patch("/platforms/{platform_id}/toggle")
async def toggle_platform(platform_id: str, body: PlatformToggleRequest) -> dict:
    try:
        set_platform_enabled(platform_id, body.enabled)
        return {"success": True, "platform_id": platform_id, "enabled": body.enabled}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
