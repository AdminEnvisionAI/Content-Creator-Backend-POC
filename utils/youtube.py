import httpx
import os
import re
import asyncio
from datetime import datetime
from textblob import TextBlob
from typing import List, Dict, Union, Optional

# ### NEW: Transcript ke liye library import karein ###
from youtube_transcript_api import YouTubeTranscriptApi
# Apne project ke models import karein
from models.influencer import InfluencerProfile, PostStats, Metrics
import colorgram
import io
import requests
# API Key
YOUTUBE_API_KEY =os.getenv("YOUTUBE_API_KEY")


def parse_iso8601_duration(duration_str: str) -> int:

    """YouTube ke 'PT1M30S' jaise duration format ko seconds mein convert karta hai."""

    if not duration_str or not duration_str.startswith('PT'):

        return 0

    duration_str = duration_str[2:]

    total_seconds = 0

    hours_match = re.search(r'(\d+)H', duration_str)

    if hours_match: total_seconds += int(hours_match.group(1)) * 3600

    minutes_match = re.search(r'(\d+)M', duration_str)

    if minutes_match: total_seconds += int(minutes_match.group(1)) * 60

    seconds_match = re.search(r'(\d+)S', duration_str)

    if seconds_match: total_seconds += int(seconds_match.group(1))

    return total_seconds



def analyze_thumbnail_colors(image_url: str) -> List[str]:

    """Ek image URL se 5 sabse dominant colors ke hex codes nikalta hai."""

    if not image_url: return []

    try:

        response = requests.get(image_url)
        response.raise_for_status()
        image_bytes = io.BytesIO(response.content)
        colors = colorgram.extract(image_bytes, 5)
        hex_colors = [f"#{c.rgb.r:02x}{c.rgb.g:02x}{c.rgb.b:02x}" for c in colors]
        return hex_colors

    except Exception as e:
        print(f"    - Thumbnail colors analyze karne mein error: {e}")
        return []



def analyze_visual_keywords(text_data: str) -> List[str]:
    """Diye gaye text mein se visual aesthetic se jude keywords nikalta hai."""
    text_lower = text_data.lower()
    visual_keywords = {
        "Resolution": ["4k", "8k", "hd", "1080p"],
        "Cinematic Style": ["cinematic", "filmic", "b-roll", "short film"],
        "Aesthetic Vibe": ["aesthetic", "minimalist", "cozy", "vibe", "satisfying"],
        "Editing Style": ["montage", "timelapse", "hyperlapse", "slow motion"],
        "Genre": ["vlog", "tutorial", "unboxing", "review", "asmr"]
    }

    found_tags = [keyword for category, keywords in visual_keywords.items() for keyword in keywords if keyword in text_lower]
    return list(set(found_tags))



def calculate_visual_aesthetics_score(video_data: dict) -> int:
    """Ek video ke visual data ke aadhar par 0-100 ka score calculate karta hai."""
    total_score = 0
    # --- 1. Keywords se Score (Max 40 points) ---

    keyword_points = {
        "4k": 20, "8k": 25, "cinematic": 15, "filmic": 15, "b-roll": 12, "aesthetic": 10,
        "minimalist": 8, "vibe": 5, "montage": 7, "timelapse": 7, "1080p": 5, "hd": 3
    }

    found_tags = video_data.get("visual_style_tags", [])
    keyword_score = sum(keyword_points.get(tag, 0) for tag in found_tags)
    total_score += min(keyword_score, 40)
    # --- 2. Speaking Pace se Score (Max 30 points) ---
    pace = video_data.get("speaking_pace_wpm", 0)
    if pace > 0:
        if pace < 120 or pace > 190: total_score += 30 # Stylized pace
        elif pace < 140 or pace > 170: total_score += 20 # Deliberate pace
        else: total_score += 10 # Standard pace
    # --- 3. Thumbnail Colors se Score (Max 30 points) ---
    if len(video_data.get("dominant_colors", [])) >= 5: total_score += 30
    elif len(video_data.get("dominant_colors", [])) >= 3: total_score += 15
   
    return min(total_score, 100)

# ... calculate_youtube_metrics function same rahega ...
def calculate_youtube_metrics(channel_data: dict) -> Metrics:
    """Ek YouTube channel ke liye saare zaroori metrics calculate karta hai."""
    
    followers = channel_data.get("subscribers", 0)
    videos = channel_data.get("videos", [])
    
    if not followers or not videos:
        return Metrics()

    total_likes = sum(v.get("likes", 0) for v in videos)
    total_comments_retrieved = sum(v.get("good_comments", 0) + v.get("bad_comments", 0) for v in videos)
    total_actual_comments = sum(v.get("comments_total", 0) for v in videos)
    total_good_comments = sum(v.get("good_comments", 0) for v in videos)
    
    # 1. Engagement Rate
    total_engagements = total_likes + total_actual_comments
    avg_engagement_per_post = total_engagements / len(videos) if videos else 0
    engagement_rate = (avg_engagement_per_post / followers * 100) if followers > 0 else 0

    # 2. Like-Comment Ratio
    like_comment_ratio = total_likes / total_actual_comments if total_actual_comments > 0 else total_likes

    # 3. Post Frequency
    timestamps = sorted([v["published_at"] for v in videos if v.get("published_at")])
    post_frequency = 0
    if len(timestamps) > 1:
        days_span = (timestamps[-1] - timestamps[0]).days
        if days_span > 0:
            post_frequency = len(videos) / (days_span / 7)

    # 4. Sentiment Score
    sentiment_score = (total_good_comments / total_comments_retrieved * 100) if total_comments_retrieved > 0 else 50

    # 5. Overall Score
    overall_score = (
        0.25 * min(engagement_rate, 5) * 20 +
        0.15 * min(like_comment_ratio / 50, 1) * 100 +
        0.15 * min(post_frequency, 3) * 33.3 +
        0.10 * sentiment_score
    )

    # ### NAYA: Average Visual Score calculate karein ###

    visual_scores = [v.get("visual_aesthetics_score", 0) for v in videos if "visual_aesthetics_score" in v]

    avg_visual_score = sum(visual_scores) / len(visual_scores) if visual_scores else 0.0
    return Metrics(
        engagement_rate_per_post=round(engagement_rate, 4),
        like_comment_ratio=round(like_comment_ratio, 2),
        post_frequency_per_week=round(post_frequency, 2),
        sentiment_score=round(sentiment_score, 2),
        overall_score=round(overall_score, 2),
        avg_visual_score=round(avg_visual_score, 2)
    )

# ### NEW: YouTube ki official categories fetch karne ke liye function ###
async def get_youtube_category_map(client: httpx.AsyncClient) -> Dict[str, str]:
    """YouTube se saari video categories aur unke IDs ki mapping laata hai."""
    try:
        base = os.getenv("YOUTUBE_BASE_URL")
        res = await client.get(
            f"{base}/videoCategories",
            params={"part": "snippet", "regionCode": "US", "key": YOUTUBE_API_KEY}
        )
        res.raise_for_status()
        items = res.json().get("items", [])
        return {item['id']: item['snippet']['title'] for item in items}
    except Exception as e:
        print(f"Warning: YouTube categories fetch nahi ho sakin: {e}")
        return {}

# ### NEW: Transcript ke keywords se category decide karne ke liye function ###
def categorize_text_by_keywords(text: str) -> str:
    """Text mein keywords ke aadhar par ek category assign karta hai."""
    if not text:
        return "Unknown"
    
    text_lower = text.lower()
    
    # Aap is dictionary ko aur behtar bana sakte hain
    category_keywords = {
        "Gaming": ["gameplay", "stream", "fortnite", "valorant", "minecraft", "esports"],
        "Tech": ["review", "unboxing", "smartphone", "gadget", "ios", "android", "tech"],
        "Education": ["tutorial", "learn", "how to", "science", "history", "educational"],
        "Comedy": ["funny", "skit", "comedy", "roast", "parody"],
        "Vlog": ["vlog", "daily vlog", "travel", "lifestyle", "my day"],
    }
    
    for category, keywords in category_keywords.items():
        if any(keyword in text_lower for keyword in keywords):
            return category
            
    return "General"


# ... baaki ke public functions same rahenge ...
async def fetch_youtube_channels_by_category(category: str, top_result: int, videos_limit: int):
    print(f"▶️ Category ke liye search: '{category}' (Top {top_result} channels)");return await _process_youtube_search(query=category,search_type='category',top_result=top_result,videos_limit=videos_limit)
async def fetch_youtube_channel_by_name(channel_name: str,top_result: int,videos_limit: int):
    print(f"▶️ Specific channel ke liye search: '{channel_name}'");return await _process_youtube_search(query=channel_name,search_type='channel',top_result=top_result,videos_limit=videos_limit)

# ==============================================================================
# INTERNAL PROCESSING FUNCTION (Yahan saare bade badlaav hain)
# ==============================================================================

async def _process_youtube_search(query: str, search_type: str, top_result: int, videos_limit: int) -> Union[List[InfluencerProfile], Dict[str, str]]:
    if not YOUTUBE_API_KEY:
        return {"error": "Server YouTube API key ke saath configure nahi hai."}

    base = os.getenv("YOUTUBE_BASE_URL")
    client = httpx.AsyncClient()
    processed_profiles = []

    # ### NEW: Start mein hi category map fetch kar lein ###
    category_map = await get_youtube_category_map(client)
    loop = asyncio.get_running_loop()


    try:
        # Step 1: Channel(s) ko search karein (Logic same)
        search_res = await client.get(f"{base}/search", params={"part": "snippet","q":query,"type":"channel","maxResults":top_result,"key":YOUTUBE_API_KEY})
        search_res.raise_for_status();search_data=search_res.json();channel_items=search_data.get("items",[]);
        if not channel_items:
            print(f"Query '{query}' ke liye koi channel nahi mila.");
            if search_type=='channel':return {"error": f"'{query}' naam ka koi channel nahi mila."}
            return []
        channel_ids = [item["snippet"]["channelId"] for item in channel_items]
    except Exception as e:
        print(f"Error (Channel Search): {e}");await client.aclose();return {"error": "YouTube API se data fetch nahi ho saka."}

    # Step 2: Har channel ID ko process karein
    ytt_api = YouTubeTranscriptApi()
    for channel_id in channel_ids:
        try:
            # ... Channel ki details fetch karna same hai ...
            channel_res = await client.get(f"{base}/channels",params={"part":"snippet,statistics,contentDetails","id":channel_id,"key":YOUTUBE_API_KEY});cdata=channel_res.json().get("items",[{}])[0];
            if not cdata: continue
            channel_info={"channel_id":channel_id,"name":cdata.get("snippet",{}).get("title"),"subscribers":int(cdata.get("statistics",{}).get("subscriberCount",0)),"profile_pic":cdata.get("snippet",{}).get("thumbnails",{}).get("high",{}).get("url"),"bio":cdata.get("snippet",{}).get("description"),"videos":[]}
            
            # Video IDs fetch karna same hai
            # activity_res=await client.get(f"{base}/activities",params={"part":"contentDetails","channelId":channel_id,"maxResults":videos_limit,"key":YOUTUBE_API_KEY});activity_items=activity_res.json().get("items",[]);video_ids=[item['contentDetails']['upload']['videoId'] for item in activity_items if'upload'in item.get('contentDetails',{})]
            # videos_list_res = await client.get(
            #     f"{base}/search",
            #     params={
            #         "part": "id", 
            #         "channelId": channel_id, 
            #         "maxResults": videos_limit, 
            #         "order": "date",       # Sabse naye videos pehle
            #         "type": "video",       # Sirf videos search karo
            #         "eventType": "completed", # <<< YEH AAPKA ZAROORI FILTER HAI
            #         "key": YOUTUBE_API_KEY
            #     }
            # )
            # video_items = videos_list_res.json().get("items", [])
            # video_ids = [item["id"]["videoId"] for item in video_items]
            uploads_playlist_id = cdata.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
            
            # Agar uploads playlist ID nahi milti (kisi vajah se), toh 'UC' ko 'UU' se badal dein
            if not uploads_playlist_id and channel_id.startswith("UC"):
                uploads_playlist_id = "UU" + channel_id[2:]
                print(f"    - Uploads playlist ID manually banayi: {uploads_playlist_id}")

            video_ids = []
            if uploads_playlist_id:
                # 'playlistItems.list' endpoint ka istemaal karein, yeh 'search' se behtar hai
                playlist_res = await client.get(
                    f"{base}/playlistItems",
                    params={
                        "part": "contentDetails",
                        "playlistId": uploads_playlist_id,
                        "maxResults": videos_limit,
                        "key": YOUTUBE_API_KEY
                    }
                )
                playlist_items = playlist_res.json().get("items", [])
                video_ids = [item["contentDetails"]["videoId"] for item in playlist_items]

            
            if not video_ids:
                # ... (No videos found logic same) ...
                print(f"'{channel_info['name']}' ke liye haal hi mein koi video upload nahi mila.");metrics=calculate_youtube_metrics(channel_info);profile=InfluencerProfile(platform_id=channel_info['channel_id'],platform="youtube",name=channel_info.get('name'),username=channel_info.get('name'),profile_pic_url=channel_info.get('profile_pic'),bio=channel_info.get('bio'),followers=channel_info.get('subscribers'),posts=[],metrics=metrics);await profile.save();print(f"✅ Saved YouTube profile for: {profile.name} (Bina video data ke)");processed_profiles.append(profile);continue
            
            # ### NEW: Videos ki details ke saath 'snippet' bhi maangein taaki categoryId mile ###
            video_details_res = await client.get(
                f"{base}/videos",
                params={"part": "snippet,statistics,contentDetails", "id": ",".join(video_ids), "key": YOUTUBE_API_KEY}
            )
            
            for v_item in video_details_res.json().get("items", []):
                vid = v_item["id"]
                snippet, statistics, content_details = v_item.get("snippet", {}), v_item.get("statistics", {}), v_item.get("contentDetails", {})
                # ### NEW: Transcript nikaalein ###
                transcript_text = None
                try:
                    
                    target_languages = [
                        'en', 'hi', 'bn', 'ur', 'ta', 'te', 'ml', 'kn', 'gu', 'mr', 'pa',
                        'es', 'fr', 'de', 'it', 'pt', 'ru', 'ar', 'fa', 'tr', 'id', 'th', 'vi',
                        'ja', 'ko', 'zh-Hans', 'zh-Hant',
                        'uk', 'pl', 'nl', 'sv', 'no', 'da', 'fi', 'ro', 'cs', 'el', 'hu'
                    ]

                    # Lambda ka istemaal karke function ko arguments ke saath "package" karein
                    transcript_list = await loop.run_in_executor(
                        None,
                        lambda: ytt_api.fetch(vid, languages=target_languages)
                    )
                    transcript_text = " ".join([s.text for s in transcript_list])

                except Exception as transcript_e:
                    print(f"    - Video ID {vid} ke liye transcript nahi mila: {transcript_e}")
                    pass # Chupchap fail ho jaaye agar transcript na mile

                # ### NEW: Official aur Content-based category nikaalein ###
                duration_seconds = parse_iso8601_duration(content_details.get("duration", ""))

                speaking_pace_wpm = 0

                if transcript_text and duration_seconds > 0:

                    speaking_pace_wpm = round(len(transcript_text.split()) / (duration_seconds / 60))

                thumbnail_url = snippet.get("thumbnails", {}).get("high", {}).get("url")

                dominant_colors = await loop.run_in_executor(None, analyze_thumbnail_colors, thumbnail_url)
                tags = snippet.get("tags", [])

                text_for_visuals = f"{snippet.get('title', '')} {snippet.get('description', '')} {' '.join(tags)}"

                visual_style_tags = analyze_visual_keywords(text_for_visuals)
                official_category_id = v_item.get("snippet", {}).get("categoryId")
                official_category_name = category_map.get(official_category_id, "Unknown")
                
                # Title, description aur transcript ko milakar content-based category banayein
                text_for_analysis = (v_item.get("snippet", {}).get("title", "") + " " +
                                     v_item.get("snippet", {}).get("description", "") + " " +
                                     (transcript_text or ""))
                content_based_category = categorize_text_by_keywords(text_for_analysis)

                # ... (Comments wala logic same rahega) ...
                good,bad=0,0;
                try:
                    comment_res = await client.get(
                        f"{base}/commentThreads",
                        params={"part": "snippet", "videoId": vid, "maxResults": 100, "key": YOUTUBE_API_KEY}
                    )
                    if comment_res.status_code == 200:
                        comments = [i["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
                                    for i in comment_res.json().get("items", [])]
                        for c in comments:
                            if TextBlob(c).sentiment.polarity >= 0: good += 1
                            else: bad += 1
                except Exception as comment_e:
                    if 'disabled comments' in str(comment_e).lower():
                        print(f"    - Video ID {vid} ke liye comments disabled hain.")
                    else:
                        print(f"    - Video ID {vid} ke comments fetch karne mein error: {comment_e}")
                published_at_dt = datetime.fromisoformat(v_item["snippet"]["publishedAt"].replace('Z', '+00:00'))

                # ### NEW: Naye fields ko video data mein add karein ###
                temp_video_data={
                    "post_id": vid, "title": v_item["snippet"]["title"],
                    "published_at": published_at_dt,
                    "description":v_item.get("snippet", {}).get("description", ""),
                    "views": int(v_item.get("statistics", {}).get("viewCount", 0)),
                    "likes": int(v_item.get("statistics", {}).get("likeCount", 0)),
                    "comments_total": int(v_item.get("statistics", {}).get("commentCount", 0)),
                    "good_comments": good, "bad_comments": bad,
                    "category": official_category_name,           # Official Category
                    "transcript": transcript_text,               # Poora Transcript
                    "content_based_category": content_based_category, # Hamari custom category
                    "duration_seconds": duration_seconds, "speaking_pace_wpm": speaking_pace_wpm,

                    "thumbnail_url": thumbnail_url, "dominant_colors": dominant_colors,

                    "visual_style_tags": visual_style_tags, "tags": tags
                }
                temp_video_data["visual_aesthetics_score"] = calculate_visual_aesthetics_score(temp_video_data)
                channel_info["videos"].append(temp_video_data)
            
            # ... (Metrics calculate karna aur save karna same hai) ...
            metrics = calculate_youtube_metrics(channel_info);profile=InfluencerProfile(platform_id=channel_info['channel_id'],platform="youtube",name=channel_info.get('name'),username=channel_info.get('name'),profile_pic_url=channel_info.get('profile_pic'),bio=channel_info.get('bio'),followers=channel_info.get('subscribers'),posts=[PostStats(**v)for v in channel_info.get('videos',[])],metrics=metrics);await profile.save();print(f"✅ Saved YouTube profile for: {profile.name} with score {profile.metrics.overall_score}");processed_profiles.append(profile)

        except Exception as e:
            print(f"Channel ID {channel_id} ko process karte samay error aaya: {e}")
            continue

    await client.aclose()
    return processed_profiles