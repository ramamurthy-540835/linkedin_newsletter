import os
from typing import Any

from fastapi import APIRouter, HTTPException
from google.cloud import bigquery
from pydantic import BaseModel, ConfigDict

from app.core.config import settings

router = APIRouter()

DATASET = os.getenv("GCP_DATASET", "linkedin_studio")
TABLE = "ai_models"

SEED_ROWS = [
    # Google / Gemini
    ("models/gemini-2.5-flash", "google", "Gemini 2.5 Flash", "chat,realtime,feed,digest,suggestions,ideas,post_generation", 3, 1, True, True, "Real-time apps, chat, APIs — DEFAULT"),
    ("models/gemini-2.5-pro", "google", "Gemini 2.5 Pro", "enterprise,complex,research,suggestions,post_generation", 2, 2, False, True, "Enterprise apps, scalable workloads"),
    ("models/gemini-2.0-flash", "google", "Gemini 2.0 Flash", "realtime,lightweight,feed,suggestions", 3, 1, False, True, "Lightweight real-time processing"),
    ("models/gemini-2.0-flash-lite", "google", "Gemini 2.0 Flash-Lite", "cost,fast,feed", 3, 1, False, True, "Cost-efficient fast inference"),
    ("models/gemini-3-pro-preview", "google", "Gemini 3 Pro Preview", "reasoning,agents,enterprise,complex,post_generation", 1, 3, False, True, "Advanced reasoning, AI agents"),
    ("models/gemini-3.1-pro-preview", "google", "Gemini 3.1 Pro Preview", "coding,complex,enterprise,post_generation", 1, 3, False, True, "Complex workflows, coding"),
    ("models/gemini-3-flash-preview", "google", "Gemini 3 Flash Preview", "fast,nextgen,suggestions,ideas", 3, 2, False, True, "Fast next-gen responses"),
    ("models/imagen-4.0-generate-001", "google", "Imagen 4", "images,creative,ideas", 2, 2, False, True, "Image generation"),
    ("models/imagen-4.0-ultra-generate-001", "google", "Imagen 4 Ultra", "images,highquality,ideas", 1, 3, False, True, "High-quality creative images"),
    ("models/imagen-4.0-fast-generate-001", "google", "Imagen 4 Fast", "images,fast,ideas", 3, 1, False, True, "Fast image generation"),
    ("models/veo-2.0-generate-001", "google", "Veo 2", "video,ideas", 2, 2, False, True, "Video generation"),
    ("models/veo-3.0-generate-001", "google", "Veo 3", "video,advanced,ideas", 1, 3, False, True, "Advanced video creation"),
    ("models/veo-3.1-generate-preview", "google", "Veo 3.1", "video,nextgen,ideas", 1, 3, False, True, "Next-gen video pipelines"),
    ("models/gemini-2.5-flash-native-audio-latest", "google", "Gemini 2.5 Flash Audio", "voice,audio,speech,ideas", 3, 1, False, True, "Voice AI, TTS"),
    ("models/gemma-3-27b-it", "google", "Gemma 3 27B", "local,reasoning,post_generation", 2, 1, False, True, "High-performance local LLM"),
    ("models/gemini-2.5-computer-use-preview-10-2025", "google", "Computer Use Preview", "agents,automation,post_generation", 2, 2, False, True, "AI agents interacting with systems"),
    ("models/deep-research-pro-preview-12-2025", "google", "Deep Research Pro", "research,analysis,digest,post_generation", 1, 3, False, True, "Deep analysis, research workflows"),
    # Anthropic / Claude
    ("claude-sonnet-4-20250514", "anthropic", "Claude Sonnet 4", "chat,suggestions,digest,post_generation,ideas", 2, 2, False, True, "Best balance of speed and quality"),
    ("claude-opus-4-5", "anthropic", "Claude Opus 4", "complex,research,reasoning,post_generation", 1, 3, False, True, "Highest quality, complex research"),
    ("claude-haiku-4-5-20251001", "anthropic", "Claude Haiku 4", "fast,drafts,lightweight,feed,suggestions,ideas", 3, 1, False, True, "Ultra-fast drafts and suggestions"),
    # OpenAI
    ("gpt-4o", "openai", "GPT-4o", "chat,vision,suggestions,post_generation", 2, 2, False, True, "OpenAI multimodal — requires OPENAI_API_KEY"),
    ("gpt-4o-mini", "openai", "GPT-4o Mini", "fast,cost,feed,ideas", 3, 1, False, True, "OpenAI fast low-cost"),
    ("o3", "openai", "OpenAI o3", "reasoning,complex,research,post_generation", 1, 3, False, True, "OpenAI advanced reasoning"),
]


def _bq_client() -> bigquery.Client:
    return bigquery.Client(project=settings.gcp_project_id or None)


def ensure_models_table() -> None:
    try:
        client = _bq_client()
        dataset_id = f"{client.project}.{DATASET}"
        table_id = f"{dataset_id}.{TABLE}"

        dataset = bigquery.Dataset(dataset_id)
        dataset.location = settings.gcp_region or "us-central1"
        client.create_dataset(dataset, exists_ok=True)

        schema = [
            bigquery.SchemaField("model_id", "STRING"),
            bigquery.SchemaField("provider", "STRING"),
            bigquery.SchemaField("display_name", "STRING"),
            bigquery.SchemaField("use_case", "STRING"),
            bigquery.SchemaField("speed_score", "INTEGER"),
            bigquery.SchemaField("cost_tier", "INTEGER"),
            bigquery.SchemaField("is_default", "BOOLEAN"),
            bigquery.SchemaField("is_active", "BOOLEAN"),
            bigquery.SchemaField("notes", "STRING"),
        ]
        client.create_table(bigquery.Table(table_id, schema=schema), exists_ok=True)

        # Clear existing rows to ensure fresh seed
        try:
            client.query(f"DELETE FROM `{table_id}` WHERE TRUE").result()
            print(f"[models] Cleared existing rows from {TABLE}")
        except Exception:
            pass

        # Insert all seed rows
        rows_to_insert = []
        for row in SEED_ROWS:
            rows_to_insert.append({
                "model_id": row[0],
                "provider": row[1],
                "display_name": row[2],
                "use_case": row[3],
                "speed_score": row[4],
                "cost_tier": row[5],
                "is_default": row[6],
                "is_active": row[7],
                "notes": row[8],
            })

        errors = client.insert_rows_json(table_id, rows_to_insert)
        if errors:
            print(f"[models] Insert errors: {errors}")
        else:
            print(f"[models] Seeded {len(rows_to_insert)} models: {len([r for r in SEED_ROWS if r[1]=='google'])} Google, {len([r for r in SEED_ROWS if r[1]=='anthropic'])} Anthropic, {len([r for r in SEED_ROWS if r[1]=='openai'])} OpenAI")
    except Exception as exc:
        print(f"[models] ensure table error: {exc}")


@router.get("")
async def list_models() -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {"google": [], "anthropic": [], "openai": []}
    try:
        client = _bq_client()
        table_id = f"{client.project}.{DATASET}.{TABLE}"
        rows = client.query(
            f"SELECT * FROM `{table_id}` WHERE is_active = TRUE ORDER BY provider, is_default DESC, display_name"
        ).result()
        for row in rows:
            d = dict(row.items())
            d["use_case"] = [x.strip() for x in str(d.get("use_case", "")).split(",") if x.strip()]
            grouped.setdefault(d["provider"], []).append(d)
        return grouped
    except Exception:
        # fallback: return all seed models if BigQuery unavailable
        for row in SEED_ROWS:
            d = {
                "model_id": row[0],
                "provider": row[1],
                "display_name": row[2],
                "use_case": [x.strip() for x in row[3].split(",")],
                "speed_score": row[4],
                "cost_tier": row[5],
                "is_default": row[6],
                "is_active": row[7],
                "notes": row[8],
            }
            grouped.setdefault(d["provider"], []).append(d)
        return grouped


@router.get("/recommend")
async def recommend_model(use_case: str = "general") -> dict[str, str]:
    try:
        client = _bq_client()
        table_id = f"{client.project}.{DATASET}.{TABLE}"
        query = f"""
            SELECT model_id, display_name, provider
            FROM `{table_id}`
            WHERE is_active = TRUE AND use_case LIKE @needle
            ORDER BY is_default DESC, speed_score DESC, cost_tier ASC
            LIMIT 1
        """
        rows = list(
            client.query(
                query,
                job_config=bigquery.QueryJobConfig(
                    query_parameters=[bigquery.ScalarQueryParameter("needle", "STRING", f"%{use_case}%")]
                ),
            ).result()
        )
        if rows:
            row = rows[0]
            return {
                "model_id": row["model_id"],
                "display_name": row["display_name"],
                "provider": row["provider"],
                "reason": f"Best match for use case: {use_case}",
            }
    except Exception:
        pass

    return {
        "model_id": "models/gemini-2.5-flash",
        "display_name": "Gemini 2.5 Flash",
        "provider": "google",
        "reason": "Default high-speed model",
    }


class ModelUpdateRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    model_id: str
    is_default: bool | None = None
    is_active: bool | None = None


@router.post("/update")
async def update_model(body: ModelUpdateRequest) -> dict[str, Any]:
    try:
        client = _bq_client()
        table_id = f"{client.project}.{DATASET}.{TABLE}"
        if body.is_default is not None and body.is_default:
            client.query(f"UPDATE `{table_id}` SET is_default = FALSE").result()
        update_parts = []
        params = [bigquery.ScalarQueryParameter("model_id", "STRING", body.model_id)]
        if body.is_default is not None:
            update_parts.append("is_default = @is_default")
            params.append(bigquery.ScalarQueryParameter("is_default", "BOOL", body.is_default))
        if body.is_active is not None:
            update_parts.append("is_active = @is_active")
            params.append(bigquery.ScalarQueryParameter("is_active", "BOOL", body.is_active))
        if not update_parts:
            raise HTTPException(status_code=400, detail="No update fields provided")
        client.query(
            f"UPDATE `{table_id}` SET {', '.join(update_parts)} WHERE model_id = @model_id",
            job_config=bigquery.QueryJobConfig(query_parameters=params),
        ).result()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to update model: {exc}") from exc


@router.get("/debug")
async def debug_models() -> dict[str, Any]:
    try:
        client = _bq_client()
        table_id = f"{client.project}.{DATASET}.{TABLE}"
        rows = list(client.query(f"SELECT * FROM `{table_id}` ORDER BY provider, display_name").result())

        counts = {}
        for row in rows:
            provider = row["provider"]
            counts[provider] = counts.get(provider, 0) + 1

        print(f"[DEBUG models] Total rows: {len(rows)}, by provider: {counts}")

        return {
            "total_rows": len(rows),
            "by_provider": counts,
            "rows": [dict(r.items()) for r in rows]
        }
    except Exception as e:
        print(f"[DEBUG models] Error: {e}")
        return {
            "error": str(e),
            "fallback_rows": len(SEED_ROWS),
            "by_provider": {"google": 17, "anthropic": 3, "openai": 3}
        }
