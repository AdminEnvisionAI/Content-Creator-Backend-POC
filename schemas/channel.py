from pydantic import BaseModel

class ChannelFetchPayload(BaseModel):
    channel_id: str

class InfluencerCategoryPayload(BaseModel):
    category: str
    top_result: int = 2
    videos_limit: int = 2

class InstagramPayload(BaseModel):
    username: str
    posts_limit: int = 2
