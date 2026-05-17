from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class GenerateRequest(BaseModel):
    topic: str
    audience: str = "LinkedIn professionals"
    tone: str = "professional"


class GenerateResponse(BaseModel):
    content: str
    hashtags: list[str]
    cta: str


class MediaAsset(BaseModel):
    enabled: bool = False
    provider: str = ""
    prompt: str = ""
    filename: str = ""
    url: str = ""
    mime_type: str = ""
    alt_text: str = ""
    style: str = ""
    aspect_ratio: str = ""
    status: str = ""


class VideoAsset(BaseModel):
    enabled: bool = False
    provider: str = ""
    prompt: str = ""
    script: str = ""
    filename: str = ""
    url: str = ""
    mime_type: str = "video/mp4"
    duration: int = 0
    style: str = ""
    status: str = ""
    job_id: str = ""


class CarouselSlide(BaseModel):
    slide_num: int = 0
    heading: str = ""
    body: str = ""
    bullets: list[str] = []
    visual_prompt: str = ""
    image_url: str = ""


class PostMedia(BaseModel):
    image: Optional[MediaAsset] = None
    video: Optional[VideoAsset] = None


class SavePostRequest(BaseModel):
    title: str
    topic: str
    audience: str
    tone: str
    content: str
    hashtags: list[str]
    cta: str
    content_type: str = "text"
    media: Optional[PostMedia] = None
    carousel_slides: Optional[list[CarouselSlide]] = None


class SavePostResponse(BaseModel):
    post_id: str
    success: bool


class PublishRequest(BaseModel):
    post_id: str
    access_token: str = ""
    author_urn: str = ""


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
    content_type: str = "text"
    media: Optional[PostMedia] = None
    carousel_slides: Optional[list[dict]] = None
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
