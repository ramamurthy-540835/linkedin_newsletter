from fastapi import APIRouter
from app.models.schemas import AnalyticsSummary

router = APIRouter()


@router.get("/summary", response_model=AnalyticsSummary)
async def analytics_summary() -> AnalyticsSummary:
    # Placeholder values until LinkedIn metrics sync job is implemented.
    return AnalyticsSummary(
        total_posts=0,
        total_impressions=0,
        total_reactions=0,
        total_comments=0,
        avg_engagement_rate=0.0,
    )
