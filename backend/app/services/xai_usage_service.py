from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.core.config import settings
from app.db.local_db import add_xai_usage, xai_usage_summary_month


class XAIBudgetError(RuntimeError):
    pass


def _month_prefix(now: datetime | None = None) -> str:
    dt = now or datetime.now(timezone.utc)
    return dt.strftime("%Y-%m")


def get_month_usage_summary() -> dict:
    summary = xai_usage_summary_month(_month_prefix())
    budget = float(settings.xai_monthly_budget_usd or 0)
    soft = float(settings.xai_soft_stop_usd or 0)
    hard = float(settings.xai_hard_stop_usd or 0)
    used = float(summary.get("used_usd", 0))
    remaining = max(0.0, budget - used)
    avg_cost = (used / summary["request_count"]) if summary.get("request_count") else 0.0
    est_left = int(remaining / avg_cost) if avg_cost > 0 else None
    summary.update(
        {
            "monthly_budget_usd": budget,
            "soft_stop_usd": soft,
            "hard_stop_usd": hard,
            "remaining_usd": remaining,
            "estimated_requests_left": est_left,
            "status": "hard_stop" if used >= hard and hard > 0 else ("soft_stop" if used >= soft and soft > 0 else "ok"),
        }
    )
    return summary


def assert_budget_allows_request() -> dict:
    summary = get_month_usage_summary()
    hard = float(summary.get("hard_stop_usd") or 0)
    used = float(summary.get("used_usd") or 0)
    if hard > 0 and used >= hard:
        raise XAIBudgetError(
            f"xAI monthly hard stop reached: used ${used:.4f} >= ${hard:.4f}. Increase XAI_HARD_STOP_USD to continue."
        )
    return summary


def record_xai_usage(feature: str, model: str, usage: dict | None) -> dict:
    usage = usage or {}
    prompt_tokens = int(usage.get("prompt_tokens") or 0)
    completion_tokens = int(usage.get("completion_tokens") or 0)
    total_tokens = int(usage.get("total_tokens") or (prompt_tokens + completion_tokens))
    ticks = usage.get("cost_in_usd_ticks")
    cost_usd = float(ticks) / 100000000.0 if ticks is not None else 0.0
    now = datetime.now(timezone.utc).isoformat()
    add_xai_usage(
        usage_id=f"xai-{uuid4()}",
        feature=feature,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        cost_usd=cost_usd,
        created_at=now,
    )
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "cost_usd": cost_usd,
    }
