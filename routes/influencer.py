from fastapi import APIRouter, HTTPException
from models.influencer import InfluencerProfile
from schemas.channel import ChannelFetchPayload, InfluencerCategoryPayload,InstagramPayload
from utils.youtube import fetch_youtube_channels_by_category,fetch_youtube_channel_by_name
from utils.instagram import process_instagram_profile,run_full_authenticated_flow
# from utils.facebook import process_facebook_profile
from utils.twitter import get_twitter_insights
from controller.influencer import get_one_user_profile_data_controller,get_top_engagemnet_rate_users_controller,get_influencers_from_llm,add_user_controller,login_controller,get_user_stats_controller,get_one_user_profile_data_creatorId_controller,download_insta_reel_controller,exchange_code_controller
from typing import List, Dict, Optional
from fastapi.responses import RedirectResponse
router = APIRouter()

@router.post("/fetch-influencer-youtube-channel-name")
async def fetch_and_store_influencer(payload: InfluencerCategoryPayload):
    data = await fetch_youtube_channel_by_name(payload.category, payload.top_result, payload.videos_limit)
 
    return {"message": "stored", "count": len(data), "data": data}



@router.post("/fetch-influencer-youtube-category-name")
async def fetch_and_store_influencer(payload: InfluencerCategoryPayload):
    data = await fetch_youtube_channels_by_category(payload.category, payload.top_result, payload.videos_limit)
 
    return {"message": "stored", "count": len(data), "data": data}




@router.post("/fetch-influencer-instagram")
async def fetch_and_store_influencer(payload: InstagramPayload):
    data = await process_instagram_profile(payload.username, payload.posts_limit)
 
    return {"message": "stored", "data": data}



@router.post("/fetch-influencer-instagram-igId")
async def fetch_and_store_influencer(payload: InstagramPayload):
    data = await run_full_authenticated_flow(payload.posts_limit)
 
    return {"message": "stored", "data": data}

# @router.post("/fetch-influencer-facebook")
# async def fetch_and_store_influencer(payload: InfluencerCategoryPayload):
#     data = await process_facebook_profile(payload.category)
 
#     return {"message": "stored","data": data}


@router.post("/fetch-influencer-twitter")
async def fetch_and_store_influencer(payload: InfluencerCategoryPayload):
    data = await get_twitter_insights(payload.category)
 
    return {"message": "stored","data": data}


@router.post("/get-one-user-profile-data")
async def get_one_user_profile_data(request:Dict):
    data = await get_one_user_profile_data_controller(request)
 
    return {"message": "stored","data": data}


@router.post("/get-one-user-profile-data-creatorId")
async def get_one_user_profile_data(request:Dict):
    data = await get_one_user_profile_data_creatorId_controller(request)
 
    return {"message": "stored","data": data}


@router.post("/get-top-engagemnet-rate")
async def get_top_engagemnet_rate_users(request:Dict):
    data = await get_top_engagemnet_rate_users_controller(request)
 
    return {"message": "stored","data": data}


@router.post("/search-influencers")
async def search_influencers(request: Dict):
    data = await get_influencers_from_llm(request["query"])
    return {"message": "stored","data": data}


@router.post("/add-user")
async def add_user(request: Dict):
    data = await add_user_controller(request)
    return {"message": "stored","data": data}


@router.post("/login")
async def login(request: Dict):
    data = await login_controller(request)
    return {"message": "stored","data": data}


@router.post("/get_user_stats")
async def get_user_stats():
    data = await get_user_stats_controller()
    return {"message": "stored","data": data}



@router.post("/download_insta_reel")
async def download_insta_reel():
    data = await download_insta_reel_controller()
    return {"message": "stored","data": data}



@router.get("/exchange_code")
async def exchange_code(code: str,state: str):
    print("code-------->",code)
    print("state------->aaaaa",state)
    data = await exchange_code_controller(code,state)
    frontend_url = "http://localhost:3000/#/dashboard?success=true"
    return RedirectResponse(url=frontend_url)