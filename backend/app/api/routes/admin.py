"""Admin routes for platform credential management."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.db.firestore_client import get_firestore_client
from app.services.credentials_service import CredentialsService

router = APIRouter()
_creds = CredentialsService()

COLLECTION = "platform_credentials"
PLATFORMS = ["linkedin", "twitter", "facebook", "medium"]

_META = {
    "linkedin": {"name": "LinkedIn", "icon": "💼", "default_type": "oauth"},
    "twitter": {"name": "Twitter / X", "icon": "𝕏", "default_type": "api_key"},
    "facebook": {"name": "Facebook", "icon": "📘", "default_type": "oauth"},
    "medium": {"name": "Medium", "icon": "M", "default_type": "api_key"},
}


def _env_fallback(platform: str) -> dict:
    """Check whether .env has credentials for a platform (read-only fallback)."""
    mapping = {
        "linkedin": bool(settings.linkedin_client_id),
        "twitter": bool(settings.twitter_api_key),
        "facebook": bool(settings.facebook_app_id),
        "medium": bool(settings.medium_api_key),
    }
    return {"has_env": mapping.get(platform, False)}


def _compute_status(data: dict, now: datetime) -> str:
    expires_at = data.get("token_expires_at")
    if expires_at:
        ts = expires_at.timestamp() if hasattr(expires_at, "timestamp") else 0
        if ts < now.timestamp():
            return "expired"
    return data.get("status", "active")


# ── List all platforms ────────────────────────────────────────────────────────

@router.get("/list")
async def list_platforms() -> dict:
    db = get_firestore_client()
    now = datetime.now(timezone.utc)
    result = []

    for platform in PLATFORMS:
        meta = _META[platform]
        doc = db.collection(COLLECTION).document(platform).get()

        if doc.exists:
            data = doc.to_dict()
            expires_at = data.get("token_expires_at")
            status = _compute_status(data, now)
            result.append(
                {
                    "platform": platform,
                    "name": meta["name"],
                    "icon": meta["icon"],
                    "status": status,
                    "type": data.get("type", meta["default_type"]),
                    "masked_client_id": _creds.mask(
                        _creds.decrypt(data.get("client_id_enc", ""))
                    ),
                    "masked_api_key": _creds.mask(
                        _creds.decrypt(data.get("api_key_enc", ""))
                    ),
                    "token_expires_at": (
                        expires_at.isoformat()
                        if expires_at and hasattr(expires_at, "isoformat")
                        else None
                    ),
                    "last_updated": (
                        data["updated_at"].isoformat()
                        if data.get("updated_at")
                        else None
                    ),
                    "source": "database",
                }
            )
        else:
            env = _env_fallback(platform)
            result.append(
                {
                    "platform": platform,
                    "name": meta["name"],
                    "icon": meta["icon"],
                    "status": "env_configured" if env["has_env"] else "not_configured",
                    "type": meta["default_type"],
                    "masked_client_id": "",
                    "masked_api_key": "",
                    "token_expires_at": None,
                    "last_updated": None,
                    "source": "env" if env["has_env"] else "none",
                }
            )

    return {"platforms": result}


# ── Get single platform ───────────────────────────────────────────────────────

@router.get("/{platform_id}")
async def get_platform(platform_id: str) -> dict:
    if platform_id not in PLATFORMS:
        raise HTTPException(status_code=404, detail="Unknown platform")

    db = get_firestore_client()
    doc = db.collection(COLLECTION).document(platform_id).get()

    if not doc.exists:
        env = _env_fallback(platform_id)
        return {
            "platform": platform_id,
            "configured": False,
            "env_configured": env["has_env"],
        }

    data = doc.to_dict()
    now = datetime.now(timezone.utc)
    expires_at = data.get("token_expires_at")

    return {
        "platform": platform_id,
        "configured": True,
        "type": data.get("type", ""),
        "status": _compute_status(data, now),
        "masked_client_id": _creds.mask(_creds.decrypt(data.get("client_id_enc", ""))),
        "masked_client_secret": _creds.mask(
            _creds.decrypt(data.get("client_secret_enc", ""))
        ),
        "masked_api_key": _creds.mask(_creds.decrypt(data.get("api_key_enc", ""))),
        "masked_access_token": _creds.mask(
            _creds.decrypt(data.get("access_token_enc", ""))
        ),
        "token_expires_at": (
            expires_at.isoformat()
            if expires_at and hasattr(expires_at, "isoformat")
            else None
        ),
        "updated_at": (
            data["updated_at"].isoformat() if data.get("updated_at") else None
        ),
    }


# ── Configure credentials ─────────────────────────────────────────────────────

class ConfigureRequest(BaseModel):
    type: str = "oauth"
    client_id: str = ""
    client_secret: str = ""
    api_key: str = ""
    access_token: str = ""
    refresh_token: str = ""
    token_expires_at: Optional[datetime] = None


@router.post("/{platform_id}/configure")
async def configure_platform(platform_id: str, req: ConfigureRequest) -> dict:
    if platform_id not in PLATFORMS:
        raise HTTPException(status_code=404, detail="Unknown platform")

    db = get_firestore_client()
    doc_ref = db.collection(COLLECTION).document(platform_id)
    existing = doc_ref.get()
    now = datetime.now(timezone.utc)

    update: dict = {"type": req.type, "status": "active", "updated_at": now}

    # Only overwrite encrypted fields that the caller actually provided
    if req.client_id:
        update["client_id_enc"] = _creds.encrypt(req.client_id)
    if req.client_secret:
        update["client_secret_enc"] = _creds.encrypt(req.client_secret)
    if req.api_key:
        update["api_key_enc"] = _creds.encrypt(req.api_key)
    if req.access_token:
        update["access_token_enc"] = _creds.encrypt(req.access_token)
    if req.refresh_token:
        update["refresh_token_enc"] = _creds.encrypt(req.refresh_token)
    if req.token_expires_at:
        update["token_expires_at"] = req.token_expires_at

    if existing.exists:
        doc_ref.update(update)
    else:
        update["created_at"] = now
        doc_ref.set(update)

    return {"success": True, "platform_id": platform_id, "status": "active"}


# ── Test connection ────────────────────────────────────────────────────────────

class TestRequest(BaseModel):
    client_id: str = ""
    client_secret: str = ""
    api_key: str = ""
    access_token: str = ""
    use_stored: bool = False


@router.post("/{platform_id}/test")
async def test_platform(platform_id: str, req: TestRequest) -> dict:
    if platform_id not in PLATFORMS:
        raise HTTPException(status_code=404, detail="Unknown platform")

    access_token = req.access_token
    api_key = req.api_key

    # Fall back to stored credentials when nothing is supplied from the form
    if req.use_stored or (not access_token and not api_key):
        db = get_firestore_client()
        doc = db.collection(COLLECTION).document(platform_id).get()
        if doc.exists:
            data = doc.to_dict()
            access_token = _creds.decrypt(data.get("access_token_enc", ""))
            api_key = _creds.decrypt(data.get("api_key_enc", ""))
        else:
            # Try env fallback values
            env_map = {
                "linkedin": settings.linkedin_access_token,
                "twitter": settings.twitter_api_key,
                "facebook": "",
                "medium": settings.medium_api_key,
            }
            access_token = env_map.get(platform_id, "")
            api_key = env_map.get(platform_id, "")

    test_fn = {
        "linkedin": lambda: _creds.test_linkedin(access_token),
        "twitter": lambda: _creds.test_twitter(api_key),
        "facebook": lambda: _creds.test_facebook(access_token),
        "medium": lambda: _creds.test_medium(api_key),
    }
    result = await test_fn[platform_id]()

    # Persist updated status when re-testing stored creds
    if req.use_stored or (not req.access_token and not req.api_key):
        db = get_firestore_client()
        doc_ref = db.collection(COLLECTION).document(platform_id)
        if doc_ref.get().exists:
            doc_ref.update(
                {
                    "status": "active" if result["valid"] else "invalid",
                    "updated_at": datetime.now(timezone.utc),
                }
            )

    return result


# ── Delete credentials ────────────────────────────────────────────────────────

@router.delete("/{platform_id}")
async def delete_platform(platform_id: str) -> dict:
    if platform_id not in PLATFORMS:
        raise HTTPException(status_code=404, detail="Unknown platform")

    db = get_firestore_client()
    doc_ref = db.collection(COLLECTION).document(platform_id)
    if not doc_ref.get().exists:
        raise HTTPException(
            status_code=404, detail="No credentials stored for this platform"
        )
    doc_ref.delete()
    return {"success": True, "platform_id": platform_id}


# ── Status ────────────────────────────────────────────────────────────────────

@router.get("/{platform_id}/status")
async def get_platform_status(platform_id: str) -> dict:
    if platform_id not in PLATFORMS:
        raise HTTPException(status_code=404, detail="Unknown platform")

    db = get_firestore_client()
    doc = db.collection(COLLECTION).document(platform_id).get()

    if not doc.exists:
        env = _env_fallback(platform_id)
        return {
            "connected": env["has_env"],
            "source": "env" if env["has_env"] else "none",
            "status": "env_configured" if env["has_env"] else "not_configured",
            "expires_at": None,
            "last_updated": None,
        }

    data = doc.to_dict()
    now = datetime.now(timezone.utc)
    status = _compute_status(data, now)
    expires_at = data.get("token_expires_at")

    return {
        "connected": status == "active",
        "status": status,
        "source": "database",
        "expires_at": (
            expires_at.isoformat()
            if expires_at and hasattr(expires_at, "isoformat")
            else None
        ),
        "last_updated": (
            data["updated_at"].isoformat() if data.get("updated_at") else None
        ),
    }
