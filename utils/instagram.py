import os
import requests
from datetime import datetime
from textblob import TextBlob # Hum isko import karenge, future use ke liye
from models.influencer import InfluencerProfile, PostStats, Metrics
import colorgram
import io
import asyncio
import httpx
from typing import List, Dict, Union, Optional
# ==============================================================================
# 1. DATA FETCHING LOGIC (API se Data Lana)
# ==============================================================================

def analyze_thumbnail_colors(image_url: str) -> List[str]:
    """
    Ek image URL se 5 sabse dominant colors ke hex codes nikalta hai.
    Yeh function YouTube aur Instagram dono ke liye kaam karta hai.
    """
    print("image_url----------------->",image_url)
    if not image_url: 
        return []
    try:
        # Image ko download karein
        response = requests.get(image_url)
        response.raise_for_status()
        
        # Image ko memory mein bytes object ki tarah load karein
        image_bytes = io.BytesIO(response.content)
        
        # Colors extract karein
        colors = colorgram.extract(image_bytes, 5)
        
        # Colors ko hex format mein return karein
        hex_colors = [f"#{c.rgb.r:02x}{c.rgb.g:02x}{c.rgb.b:02x}" for c in colors]
        return hex_colors
    except Exception as e:
        print(f"    - Image colors analyze karne mein error: {e}")
        return []

def analyze_visual_keywords_instagram(caption: str) -> List[str]:
    """Instagram caption se visual aesthetic se jude keywords nikalta hai."""
    if not caption:
        return []
    
    text_lower = caption.lower()
    # Instagram ke liye keywords thode alag ho sakte hain
    visual_keywords = {
        "Quality": ["4k", "hd", "high quality"],
        "Style": ["cinematic", "aesthetic", "vibe", "minimalist", "vintage"],
        "Equipment": ["shot on iphone", "sonyalpha", "dji"],
        "Type": ["reels", "igtv", "photo dump", "tutorial"]
    }
    
    found_tags = [kw for kws in visual_keywords.values() for kw in kws if kw in text_lower]
    return list(set(found_tags))

def calculate_visual_aesthetics_score_instagram(post_data: dict) -> int:
    """Ek Instagram post ke data ke aadhar par 0-100 ka score nikalta hai."""
    total_score = 0
    
    # Pillar 1: Keywords se Score (Max 50 points)
    keyword_points = {
        "cinematic": 20, "4k": 15, "aesthetic": 12, "shot on iphone": 10,
        "sonyalpha": 10, "minimalist": 8, "reels": 5, "hd": 5
    }
    found_tags = post_data.get("visual_style_tags", [])
    keyword_score = sum(keyword_points.get(tag, 0) for tag in found_tags)
    total_score += min(keyword_score, 50)

    # Pillar 2: Image Colors se Score (Max 50 points)
    colors = post_data.get("dominant_colors", [])
    if len(colors) >= 5:
        total_score += 50 # Professional palette
    elif len(colors) >= 3:
        total_score += 25 # Decent palette
        
    return min(total_score, 100)

async def fetch_media_urls_in_parallel(media_ids: List[str], client: httpx.AsyncClient):
    """
    Ek saath kai saare media IDs ke liye media_url fetch karta hai.
    Yeh performance ke liye zaroori hai.
    """
    access_token = os.getenv("IG_ACCESS_TOKEN")
    base_url = os.getenv("IG_BASE_URL")
    
    tasks = []
    for media_id in media_ids:
        url = f"{base_url}/{media_id}"
        params = {'fields': 'media_url', 'access_token': access_token}
        tasks.append(client.get(url, params=params))
        
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    
    media_urls = {}
    for i, res in enumerate(responses):
        if isinstance(res, httpx.Response) and res.status_code == 200:
            media_urls[media_ids[i]] = res.json().get('media_url')
        else:
            media_urls[media_ids[i]] = None # Agar error aaye
            
    return media_urls

def fetch_instagram_data(target_username: str, posts_limit: int = 10):
    """
    Facebook Graph API ka istemaal karke Instagram business account ka data fetch karta hai.
    """
    business_id = os.getenv("IG_BUSINESS_ID")
    access_token = os.getenv("IG_ACCESS_TOKEN")
    base_url=os.getenv("IG_BASE_URL")
    
    if not business_id or not access_token:
        raise ValueError("IG_BUSINESS_ID ya FB_ACCESS_TOKEN environment variables mein nahi mile.")
    
    url = f'{base_url}/{business_id}'
    
    # Hum media.limit() add karenge taaki control kar sakein ki kitne posts chahiye
    fields = (
        f'business_discovery.username({target_username}){{'
        'id,username,name,followers_count,media_count,biography,profile_picture_url,'
        f'media.limit({posts_limit}){{id,caption,like_count,comments_count,timestamp,media_type,media_url,thumbnail_url,views_count,duration}}'
        '}'
    )
    
    params = {'fields': fields, 'access_token': access_token}
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status() # HTTP errors ke liye check karega (e.g., 400, 401)
        data = response.json()
        print("data-------------->",data)
        
        if 'business_discovery' in data:
            return data['business_discovery']
        elif 'error' in data:
            error_msg = data['error'].get('message', 'Unknown error')
            raise Exception(f"Instagram API Error: {error_msg}")
        else:
            raise Exception("API se unexpected response mila.")
            
    except requests.exceptions.RequestException as e:
        raise Exception(f"Network error: {str(e)}")


# ==============================================================================
# 2. METRICS CALCULATION LOGIC (Data se Insights Nikalna)
# ==============================================================================

# def calculate_instagram_metrics(profile_data: dict) -> Metrics:
#     """Instagram profile data se key metrics calculate karta hai."""
    
#     followers = profile_data.get('followers_count', 0)
#     media = profile_data.get('media', {}).get('data', [])
    
#     if not followers or not media:
#         return Metrics()

#     total_likes = sum(p.get('like_count', 0) for p in media)
#     total_comments = sum(p.get('comments_count', 0) for p in media)
    
#     # 1. Engagement Rate (YouTube ke jaisa hi)
#     avg_engagement_per_post = (total_likes + total_comments) / len(media) if media else 0
#     engagement_rate = (avg_engagement_per_post / followers * 100) if followers > 0 else 0

#     # 2. Like-Comment Ratio (YouTube ke jaisa hi)
#     like_comment_ratio = total_likes / total_comments if total_comments > 0 else total_likes

#     # 3. Post Frequency (YouTube ke jaisa hi)
#     timestamps = sorted([
#         datetime.strptime(p['timestamp'], "%Y-%m-%dT%H:%M:%S%z") 
#         for p in media if p.get('timestamp')
#     ])
#     post_frequency = 0
#     if len(timestamps) > 1:
#         days_span = (timestamps[-1] - timestamps[0]).days
#         if days_span > 0:
#             post_frequency = len(media) / (days_span / 7)

#     # 4. Sentiment Score
#     # Note: Instagram API is endpoint se comments ka text nahi deta hai.
#     # Isliye hum sentiment calculate nahi kar sakte. Hum ek default neutral score (50) denge.
#     sentiment_score = min(100, 30 + engagement_rate * 7)


#     # 5. Overall Score (YouTube ke formula se milta-julta)
#     # Hum wahi weights istemaal karenge taaki score comparable ho.
#     overall_score = (
#         0.25 * min(engagement_rate, 10) * 10 +   # Instagram par engagement rate thoda zyada hota hai
#         0.15 * min(like_comment_ratio / 100, 1) * 100 + # Ratio ka scale bhi alag ho sakta hai
#         0.15 * min(post_frequency, 7) * 14.3 +  # Instagram par frequency zyada ho sakti hai
#         0.10 * sentiment_score
#     )

#     return Metrics(
#         engagement_rate_per_post=round(engagement_rate, 4),
#         like_comment_ratio=round(like_comment_ratio, 2),
#         post_frequency_per_week=round(post_frequency, 2),
#         sentiment_score=round(sentiment_score, 2),
#         overall_score=round(overall_score, 2)
#     )

def calculate_instagram_metrics(profile_data: dict) -> Metrics:
    """Instagram profile data se key metrics calculate karta hai."""
    
    followers = profile_data.get('followers_count', 0)
    # ### BADLAAV: Ab hum 'posts' se data lenge, na ki 'media' se ###
    posts = profile_data.get('posts', [])
    
    if not followers or not posts:
        return Metrics()

    total_likes = sum(p.get('likes', 0) for p in posts)
    total_comments = sum(p.get('comments_total', 0) for p in posts)
    
    # ... baaki saare calculations (engagement, ratio, frequency) same rahenge ...
    avg_engagement_per_post = (total_likes + total_comments) / len(posts)
    engagement_rate = (avg_engagement_per_post / followers * 100)
    like_comment_ratio = total_likes / total_comments if total_comments > 0 else total_likes
    timestamps = sorted([p['published_at'] for p in posts if p.get('published_at')])
    post_frequency = 0
    if len(timestamps) > 1 and (days_span := (timestamps[-1] - timestamps[0]).days) > 0:
        post_frequency = len(posts) / (days_span / 7)
    sentiment_score = min(100, 30 + engagement_rate * 7)
    overall_score = (0.25*min(engagement_rate,10)*10 + 0.15*min(like_comment_ratio/100,1)*100 + 0.15*min(post_frequency,7)*14.3 + 0.10*sentiment_score)

    # ### NAYA: Average Visual Score calculate karein ###
    visual_scores = [p.get("visual_aesthetics_score", 0) for p in posts if "visual_aesthetics_score" in p]
    avg_visual_score = sum(visual_scores) / len(visual_scores) if visual_scores else 0.0

    return Metrics(
        engagement_rate_per_post=round(engagement_rate, 4),
        like_comment_ratio=round(like_comment_ratio, 2),
        post_frequency_per_week=round(post_frequency, 2),
        sentiment_score=round(sentiment_score, 2),
        overall_score=round(overall_score, 2),
        avg_visual_score=round(avg_visual_score, 2) # Naya field add karein
    )
# ==============================================================================
# 3. MAIN PROCESSING FUNCTION (Sabko Jodkar Kaam Karna)
# ==============================================================================

# async def process_instagram_profile(username: str, posts_limit: int = 10):
#     """
#     Instagram profile ko fetch karta hai, metrics calculate karta hai, aur database mein save karta hai.
#     """
#     try:
#         # Step 1: Data fetch karein
#         # Note: fetch_instagram_data ek sync function hai. Agar performance issue ho,
#         # to ise asyncio.to_thread mein run kar sakte hain. Abhi ke liye yeh theek hai.
#         data = fetch_instagram_data(username, posts_limit)
        
#         # Step 2: Metrics calculate karein
#         metrics = calculate_instagram_metrics(data)
        
#         # Step 3: Data ko apne models mein map karein
#         profile = InfluencerProfile(
#             platform_id=data.get('id'),
#             platform="instagram",
#             name=data.get('name', username),
#             username=data.get('username'),
#             profile_pic_url=data.get('profile_picture_url'),
#             bio=data.get('biography'),
#             followers=data.get('followers_count'),
#             posts=[
#                 PostStats(
#                     post_id=p.get('id'),
#                     title=p.get('caption'),
#                     published_at=datetime.strptime(p['timestamp'], "%Y-%m-%dT%H:%M:%S%z") if p.get('timestamp') else None,
#                     # Note: Instagram API image views nahi deta, sirf video views deta hai jo alag endpoint se milte hain.
#                     views=p.get('views_count') if p.get('media_type') == 'VIDEO' else None, 
#                     likes=p.get('like_count'),
#                     comments_total=p.get('comments_count'),
#                     # Comment text na hone ke kaaran sentiment data None rahega
#                     good_comments=None,
#                     bad_comments=None
#                 ) for p in data.get('media', {}).get('data', [])
#             ],
#             metrics=metrics
#         )
        
#         # Step 4: Database mein save karein
#         await profile.save()
#         print(f"✅ Saved Instagram profile for: {profile.name} with score {profile.metrics.overall_score}")

#         # Step 5: Processed profile ko return karein (API response ke liye)
#         return profile

#     except Exception as e:
#         print(f"❌ Instagram profile process karte samay error aaya ({username}): {e}")
#         return {"error": str(e)}

# ==============================================================================
# 3. MAIN PROCESSING FUNCTION (POORA UPDATE KIYA GAYA)
# ==============================================================================

async def process_instagram_profile(username: str, posts_limit: int = 10):
    """
    Instagram profile ko fetch karta hai, visual aesthetics nikalta hai, aur DB mein save karta hai.
    """
    loop = asyncio.get_running_loop()
    
    try:
        # Step 1: Basic data fetch karein
        data = await loop.run_in_executor(None, fetch_instagram_data, username, posts_limit)
        
        media_items = data.get('media', {}).get('data', [])
        if not media_items:
            print(f"'{username}' ke liye koi media nahi mila."); return
        
        # Step 2: Har post ke liye media_url parallel mein fetch karein
        media_ids = [p['id'] for p in media_items]
        # async with httpx.AsyncClient() as client:
        #     media_urls_map = await fetch_media_urls_in_parallel(media_ids, client)

        # Step 3: Har post ko process karke visual data nikaalein
        processed_posts = []
        for post in media_items:
            post_id = post.get('id')
            media_url = post.get('thumbnail_url') or post.get('media_url')
            caption = post.get('caption', '')
            
            # Visual analysis
            dominant_colors = await loop.run_in_executor(None, analyze_thumbnail_colors, media_url)
            visual_tags = analyze_visual_keywords_instagram(caption)
            
            # Ek temporary dictionary banayein
            temp_post_data = {
                "post_id": post_id,
                "title": caption, # Instagram mein title caption hi hota hai
                "published_at": datetime.strptime(post['timestamp'], "%Y-%m-%dT%H:%M:%S%z"),
                "views": post.get('views_count') if post.get('media_type') == 'VIDEO' else None,
                "likes": post.get('like_count'),
                "comments_total": post.get('comments_count'),
                "media_url": media_url,
                "dominant_colors": dominant_colors,
                "visual_style_tags": visual_tags,
                "thumbnail_url":media_url,
                "media_type":post.get('media_type')
            }
            
            # Visual score calculate karein
            temp_post_data["visual_aesthetics_score"] = calculate_visual_aesthetics_score_instagram(temp_post_data)
            processed_posts.append(temp_post_data)

        # Step 4: Metrics calculate karein (ab hamare paas poora data hai)
        # Profile data ko metrics function ke liye prepare karein
        profile_data_for_metrics = {
            "followers_count": data.get('followers_count'),
            "posts": processed_posts
        }
        metrics = calculate_instagram_metrics(profile_data_for_metrics)
        
        # Step 5: Final InfluencerProfile object banayein
        profile = InfluencerProfile(
            platform_id=data.get('id'),
            platform="instagram",
            name=data.get('name', username),
            username=data.get('username'),
            profile_pic_url=data.get('profile_picture_url'),
            bio=data.get('biography'),
            followers=data.get('followers_count'),
            posts=[PostStats(**p) for p in processed_posts], # Hamesha validated model ka istemaal karein
            metrics=metrics
        )
        
        # Step 6: Database mein save karein
        await profile.save()
        print(f"✅ Saved Instagram profile for: {profile.name} with score {profile.metrics.overall_score} and visual score {profile.metrics.avg_visual_score}")

        return profile

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"❌ Instagram profile process karte samay error aaya ({username}): {e}")
        return {"error": str(e)}