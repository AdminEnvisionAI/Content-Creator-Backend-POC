from typing import List, Dict, Optional
from schemas.channel import ChannelFetchPayload, InfluencerCategoryPayload,InstagramPayload
from models.influencer import InfluencerProfile
from models.users import User
from bson import ObjectId
# from utils.mcp_client import mcp_client
import json
from utils.mcp_client import llm_filter_mongo,llm_select_keys,llm_get_matching_ids
import json
from utils.auth import hash_password,verify_password, create_access_token
from fastapi import HTTPException
import os
import httpx
from utils.dbOperations import delete_many, delete_one, distinct, find,find_one, findWithSort, update_many,create, update_one
async def get_one_user_profile_data_controller(request:Dict):
    try:
        data=await InfluencerProfile.aggregate([
                {"$match":{"_id": ObjectId(request["id"])}},
                {"$addFields": {"_id": {"$toString": "$_id"}}},
                {"$addFields": {"creatorId": {"$toString": "$creatorId"}}},
            ]).to_list()
        return data
        
    except Exception as e:
        raise ValueError("update_question_genrator_user_answers have someting error.")




async def get_one_user_profile_data_creatorId_controller(request:Dict):
    try:
        data=await InfluencerProfile.aggregate([
                {"$match":{"creatorId": ObjectId(request["creatorId"]),"platform":request["platform"]}},
                {"$addFields": {"_id": {"$toString": "$_id"}}},
                {"$addFields": {"creatorId": {"$toString": "$creatorId"}}},
            ]).to_list()
        return data
        
    except Exception as e:
        raise ValueError("update_question_genrator_user_answers have someting error.")



async def get_top_engagemnet_rate_users_controller(request:Dict):
    try:
        data = await InfluencerProfile.aggregate([
            {"$match": {
                "isDeleted": False,
                "platform": request["platform"]
            }},
            {"$addFields": {"_id": {"$toString": "$_id"}}},
            {"$addFields": {"creatorId": {"$toString": "$creatorId"}}},
            {"$sort": {
                "metrics.engagement_rate_per_post": -1   # Descending
            }},
            {"$limit": 5}
        ]).to_list()

        return data
        
    except Exception as e:
        raise ValueError("update_question_genrator_user_answers have someting error.")
    

async def get_influencers_from_llm(user_query: str):
    try:
        FULL_SCHEMA_KEYS = [
            "_id",
            "name",
            "username",
            "bio",
            "platform",
            "followers",
            "metrics.engagement_rate_per_post",
            "metrics.like_comment_ratio",
            "metrics.post_frequency_per_week",
            "metrics.sentiment_score",
            "metrics.overall_score",
            "posts.title",
            "posts.description",
            "posts.published_at",
            "posts.views",
            "posts.likes",
            "posts.comments_total",
            "posts.category",
            "posts.content_based_category"
        ]
        keys_data=llm_select_keys(user_query,FULL_SCHEMA_KEYS)
        print("keys_data------------->",keys_data)
        project_stage = {key: 1 for key in keys_data}
        print("project_stage------------->",project_stage)
        if not project_stage: # Ensure project is not empty
            project_stage = {"_id": 1, "name": 1, "bio": 1} # Safe default
        data = await InfluencerProfile.aggregate([
            {
        "$match": {
            "isDeleted": False
        }
    },
    {"$unwind":{"path":"$posts"}},
    {"$sort":{"metrics.engagement_rate_per_post": -1}},
    {
        "$project":project_stage
    }
        ]).to_list()
        # filter_data=llm_filter_mongo(data,user_query)
        filter_data=llm_get_matching_ids(data,user_query)
        real_data = await InfluencerProfile.aggregate([
    {
        "$match": {
            "isDeleted": False,
            "_id": {
                "$in":  [ObjectId(i) for i in filter_data]
            }
        },
        
    },
     {"$addFields": {"_id": {"$toString": "$_id"}}},
     {"$addFields": {"creatorId": {"$toString": "$creatorId"}}},
]).to_list()
        print("real_data------->",real_data)

        return real_data
        
    except Exception as e:
        print("error=-------------------->",e)
        raise ValueError("update_question_genrator_user_answers have someting error.")
    

async def add_user_controller(request: dict):
    try:
        print("helo---------------->",request,"email of request", request["email"])
        existing = await User.find_one(User.email == request["email"])
        print("helo---------------->2",existing)
        if existing:
            raise HTTPException(status_code=400, detail="Email already exists")

        request["password"] = hash_password(request["password"])
        print("request-------------->",request)
        user = User(**request)
        saved = await user.insert()

        return {
            "message": "Signup successful",
            "user_id": str(saved.id),
            "user_type": saved.user_type
        }
    except Exception as e:
        print("e---------->",e)
        raise HTTPException(status_code=500, detail=str(e))
    


async def login_controller(request: dict):
    try:
        email = request["email"]
        password = request["password"]
        user_type = request["user_type"]

        user = await User.find_one(User.email == email, User.isDeleted == False,User.user_type==request["user_type"])

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if not verify_password(password, user.password):
            raise HTTPException(status_code=401, detail="Incorrect password")

        token = create_access_token({"user_id": str(user.id)})

        return {
            "message": "Login successful",
            "token": token,
            "user": {
                "id": str(user.id),
                "email": user.email,
                "user_type": user.user_type,
                "isFBGraphConnected":user.isFBGraphConnected
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    


async def get_user_stats_controller():
    try:
        total_creators = await User.find(User.user_type == "creator", User.isDeleted == False).count()
        total_brands = await User.find(User.user_type == "brand", User.isDeleted == False).count()

        return {
            "total_creators": total_creators,
            "total_brands": total_brands,
            "total_users": total_creators + total_brands
        }
    except Exception as e:
        return {"error": str(e)}    
    



# import whisper

# model = whisper.load_model("small")  # free model
# result = model.transcribe("public/reels/DRehAjYk4FZ.mp4")
# print(result["text"])



async def download_insta_reel_controller():
    import os
    from pathlib import Path
    from yt_dlp import YoutubeDL

    # Path of current file (controllers/download_insta_reel_controller.py)
    script_dir = Path(__file__).parent

    # Move to project root (one level up)
    project_root = script_dir.parent

    # public/reels path
    target_dir = project_root / "public" / "reels"

    # Create folder if not exists
    target_dir.mkdir(parents=True, exist_ok=True)

    print(f"Saving reel to: {target_dir}")

    url = "https://www.instagram.com/reel/DRehAjYk4FZ/"

    # Save output exactly in public/reels
    output_template = str(target_dir / "%(id)s.%(ext)s")

    ydl_opts = {
        "outtmpl": output_template,              # Save video file in public/reels
        "format": "bestvideo+bestaudio/best",    # Merge audio + video
        "merge_output_format": "mp4"
    }

    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    return {
        "message": "Reel downloaded successfully!",
        "file_path": str(target_dir)
    }



async def exchange_code_controller(code: str,state: str):
    print("state------->",state)
    token_url = "https://graph.facebook.com/v24.0/oauth/access_token"
    params = {
        "client_id": os.getenv("FB_APP_ID"),
        "redirect_uri": os.getenv("REDIRECT_URI"),
        "client_secret": os.getenv("FB_APP_SECRET"),
        "code": code,
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(token_url, params=params)

    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to exchange code for token")

    data = response.json()
    access_token = data.get("access_token")
    data=await update_one(
       User,
      {
      
        "_id": ObjectId(state)
       },
      {
        "$set": {
            "fb_access_token":access_token,
            "isFBGraphConnected": True
        }
      }
      )
    print("access_token------------->",access_token)
    if not access_token:
        raise HTTPException(status_code=400, detail="Access token not found")

    return {"access_token": access_token}