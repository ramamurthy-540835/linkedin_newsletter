from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class GeneratePostRequest(BaseModel):
    topic: str
    audience: str
    tone: str = "professional"
    objective: str = "engagement"
    min_chars: int = 500
    max_chars: int = 2000


class GeneratePostResponse(BaseModel):
    post_text: str
    hashtags: list[str]
    cta: str
    estimated_chars: int


class DraftCreateRequest(BaseModel):
    title: str
    content: str
    hashtags: list[str] = Field(default_factory=list)
    cta: str = ""


class Draft(BaseModel):
    id: str
    title: str
    content: str
    hashtags: list[str]
    cta: str
    created_at: datetime
    updated_at: datetime


class ScheduleRequest(BaseModel):
    draft_id: str
    publish_at_utc: datetime


class PublishRequest(BaseModel):
    draft_id: str


class AnalyticsSummary(BaseModel):
    total_posts: int
    total_impressions: int
    total_reactions: int
    total_comments: int
    avg_engagement_rate: float


class OAuthTokenResponse(BaseModel):
    access_token: str
    expires_in: int
    token_type: str
