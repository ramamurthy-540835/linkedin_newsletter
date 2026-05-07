import io
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.services.local_store import get_whitepaper, read_whitepapers, save_whitepaper

router = APIRouter()

try:
    from pypdf import PdfReader
    _HAS_PDF = True
except ImportError:
    _HAS_PDF = False


@router.post("/upload")
async def upload_whitepaper(file: UploadFile = File(...)) -> dict:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    raw = await file.read()
    text = ""
    page_count = 0

    if _HAS_PDF:
        try:
            reader = PdfReader(io.BytesIO(raw))
            page_count = len(reader.pages)
            pages = [p.extract_text() or "" for p in reader.pages]
            text = "\n\n".join(pages)
        except Exception:
            text = ""

    title = (
        file.filename.replace(".pdf", "")
        .replace("_", " ")
        .replace("-", " ")
        .strip()
    )

    record = {
        "id": str(uuid4()),
        "title": title,
        "filename": file.filename,
        "size_bytes": len(raw),
        "pages": page_count,
        "preview": text[:500] if text else "(no text extracted)",
        "content": text[:12000] if text else "",
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
    return save_whitepaper(record)


@router.get("")
async def list_whitepapers() -> list:
    return read_whitepapers()


@router.get("/{wp_id}")
async def get_whitepaper_by_id(wp_id: str) -> dict:
    wp = get_whitepaper(wp_id)
    if not wp:
        raise HTTPException(status_code=404, detail="White paper not found")
    return wp
