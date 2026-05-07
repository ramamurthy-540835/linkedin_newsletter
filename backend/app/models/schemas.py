from datetime import datetime
from pydantic import BaseModel


class GenerateRequest(BaseModel):
    topic: str
    audience: str = "LinkedIn professionals"
    tone: str = "professional"


class GenerateResponse(BaseModel):
    content: str
    hashtags: list[str]
    cta: str


class SavePostRequest(BaseModel):
    title: str
    topic: str
    audience: str
    tone: str
    content: str
    hashtags: list[str]
    cta: str


class SavePostResponse(BaseModel):
    post_id: str
    success: bool


class PublishRequest(BaseModel):
    post_id: str
    access_token: str


class PublishResponse(BaseModel):
    linkedin_post_id: str
    linkedin_url: str
    success: bool


class Post(BaseModel):
    id: str
    title: str
    topic: str
    audience: str
    tone: str
    content: str
    hashtags: list[str]
    cta: str
    status: str
    created_at: datetime
    updated_at: datetime


class PublishedPost(BaseModel):
    id: str
    post_id: str
    linkedin_post_id: str
    linkedin_url: str
    views: int
    likes: int
    comments: int
    shares: int
    published_at: datetime
