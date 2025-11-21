from beanie import Document
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime


# ---- Social Accounts for Creators ----
class SocialAccount(BaseModel):
    platform: Literal["youtube", "instagram", "facebook", "twitter", "tiktok"]
    handle: Optional[str] = None
    profile_url: Optional[str] = None
    followers: Optional[int] = None
    platform_id: Optional[str] = None


# ---- Main Unified User Model ----
class User(Document):
    # Identifies user type
    user_type: Literal["brand", "creator"]

    # Login fields
    email: str
    password: str          # Store hashed
    is_verified: bool = False

    # Common fields (brand + creator both)
    full_name: Optional[str] = None
    profile_pic: Optional[str] = None
    location: Optional[str] = None
    contact_phone: Optional[str] = None

    # ---- Creator Specific Fields ----
    niche: Optional[List[str]] = None
    categories: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)
    social_accounts: List[SocialAccount] = Field(default_factory=list)

    # ---- Brand Specific Fields ----
    company_name: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    target_audience: Optional[str] = None
    campaign_types: List[str] = Field(default_factory=list)
    budget_range: Optional[str] = None

    # Status
    isDeleted: bool = False
    isBlocked: bool = False

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "users"
