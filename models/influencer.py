from beanie import Document,PydanticObjectId
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Literal
from bson import ObjectId
from pydantic import Field, field_validator
from pydantic import Field

# ✅ NEW: A dedicated model for all calculated metrics
class Metrics(BaseModel):
    # Engagement metrics
    engagement_rate_per_post: Optional[float] = None  # (Likes + Comments) / Followers
    like_comment_ratio: Optional[float] = None       # Likes / Comments
    
    # Content metrics
    post_frequency_per_week: Optional[float] = None  # How many posts per week on average
    
    # Audience sentiment metrics
    sentiment_score: Optional[float] = None          # (Good Comments / Total Comments) * 100
    
    # Final credibility score
    overall_score: Optional[float] = None            # The weighted score you defined

    avg_visual_score: float = 0.0

# A generic post model, can be a YouTube video, FB post, or IG post
class PostStats(BaseModel):
    post_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    # Timestamps are crucial for frequency analysis
    published_at: Optional[datetime] = None
    
    # Core stats
    views: Optional[int] = None
    likes: Optional[int] = None
    comments_total: Optional[int] = None
    
    # For sentiment
    good_comments: Optional[int] = None
    bad_comments: Optional[int] = None
    category: Optional[str] = None
    transcript: Optional[str] = None
    content_based_category: Optional[str] = None

    duration_seconds: Optional[int] = 0
    speaking_pace_wpm: Optional[int] = 0
    thumbnail_url: Optional[str] = None
    dominant_colors: Optional[List[str]] = []
    visual_style_tags: Optional[List[str]] = []
    tags: Optional[List[str]] = []
    visual_aesthetics_score: Optional[int] = 0
    media_url: Optional[str] = None
    media_type: Optional[str] = None

# ✅ RENAMED & ENHANCED: This is our main, unified model
class InfluencerProfile(Document):
    # Identifier
    platform_id: str  # e.g., YouTube Channel ID, FB Page ID, IG Username
    platform: Literal["youtube", "facebook", "instagram","twitter"]

    # Basic info
    name: Optional[str] = None
    username: Optional[str] = None
    profile_pic_url: Optional[str] = None
    bio: Optional[str] = None
    
    # Audience stats
    followers: Optional[int] = None # Renamed from subscribers for generality
    
    # List of recent posts/videos
    posts: List[PostStats] = Field(default_factory=list)
    
    # ✅ OUR GOAL: Calculated metrics are stored here
    metrics: Optional[Metrics] = None
    isDeleted: bool = False
    creatorId: Optional[ObjectId]=None 
    # Metadata
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "influencer_profiles" # A new collection for all platforms

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: str,
            PydanticObjectId: str,
            datetime: lambda v: v.isoformat()
        }    