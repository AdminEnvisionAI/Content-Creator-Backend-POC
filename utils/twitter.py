import requests
import os
from textblob import TextBlob
from datetime import datetime, timezone
import statistics
from typing import List, Optional

# Apne project ke models import karein
# Make sure your models file is accessible from this script
from models.influencer import InfluencerProfile, PostStats, Metrics

# API Configuration
API_BASE_URL = os.getenv("TWITTER_BASE_URL")

# --- SECURITY BEST PRACTICE ---
# Apne Bearer Token ko yahan hardcode na karein. Environment variable ka istemaal karein.
# In your terminal: export TWITTER_BEARER_TOKEN="YOUR_REAL_BEARER_TOKEN"
BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")


# ==============================================================================
# HELPER FUNCTIONS (API Calls and Analysis)
# ==============================================================================

def get_user_data(username: str) -> Optional[dict]:
    """
    Ek Twitter username ke liye user ID, public metrics, description, aur profile picture
    ek hi API call mein fetch karta hai.
    """
    if not BEARER_TOKEN or BEARER_TOKEN == "FALLBACK_TOKEN_IF_NEEDED":
        print("❌ Error: TWITTER_BEARER_TOKEN environment variable set nahi hai.")
        return None

    url = f"{API_BASE_URL}/users/by/username/{username}"
    params = {"user.fields": "public_metrics,description,profile_image_url"}
    headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        print(f"    - Response for get_user_data('{username}'): <{response}>")
        response.raise_for_status()
        resp_json = response.json()

        if "data" in resp_json:
            return resp_json
        else:
            print(f"    - API Error: User '{username}' nahi mila. Response: {resp_json}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"    - HTTP Request failed (get_user_data): {e}")
        return None

def get_recent_tweets(user_id: str, max_results=20) -> List[dict]:
    """Ek user ID ke liye haal hi ke tweets fetch karta hai."""
    if not BEARER_TOKEN: return []
        
    url = f"{API_BASE_URL}/users/{user_id}/tweets"
    params = {
        # 'impression_count' ke liye 'non_public_metrics' bhi maangna zaroori hai
        "tweet.fields": "public_metrics,created_at,text",
        "max_results": max_results,
        "exclude": "retweets,replies"
    }
    headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}
    
    try:
        response = requests.get(url, params=params, headers=headers)
        print("response----------------->111",response)
        response.raise_for_status()
        resp_json = response.json()
        print("resp_json----------------->111",resp_json)
        if "data" in resp_json:
            return resp_json["data"]
        else:
            print(f"    - User ID '{user_id}' ke liye koi tweets nahi mile.")
            return []
    except requests.exceptions.RequestException as e:
        print(f"    - HTTP Request failed (get_recent_tweets): {e}")
        return []

def get_replies_for_tweet(tweet_id: str, max_replies=25) -> List[str]:
    """
    Ek specific tweet ID ke replies (comments) fetch karta hai.
    WARNING: Yeh API call Free Tier par bahut limited hai (1 call / 15 min).
    """
    if not BEARER_TOKEN: return []
        
    url = f"{API_BASE_URL}/tweets/search/recent"
    params = {
        "query": f"conversation_id:{tweet_id}",
        "max_results": max_replies,
        "tweet.fields": "text"
    }
    headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}
    
    try:
        response = requests.get(url, params=params, headers=headers)
        if response.status_code == 429:
            print(f"    - Replies fetch karne ke liye Rate Limit hit ho gayi. Skipping for tweet {tweet_id}.")
            return []
        response.raise_for_status()
        resp_json = response.json()
        
        replies_data = resp_json.get("data", [])
        print("replies_data----------->",replies_data)
        return [reply.get("text", "") for reply in replies_data]
        
    except requests.exceptions.RequestException as e:
        print(f"    - Tweet {tweet_id} ke replies fetch karne mein error: {e}")
        return []

def categorize_text_by_keywords(text: str) -> str:
    """Tweet ke text mein keywords ke aadhar par ek category assign karta hai."""
    if not text: return "Unknown"
    text_lower = text.lower()
    
    category_keywords = {
        "Tech": ["tech", "gadget", "apple", "android", "ai", "crypto", "coding", "software"],
        "Gaming": ["gaming", "valorant", "bgmi", "esports", "stream", "playstation", "xbox"],
        "Entertainment": ["movie", "song", "roast", "comedy", "actor", "series", "video"],
        "Politics & News": ["politics", "government", "news", "election", "bjp", "congress"],
        "Lifestyle & Opinion": ["life", "thoughts", "feeling", "happy", "sad", "motivation"],
        "Sports": ["cricket", "football", "ipl", "team india", "virat kohli"]
    }
    
    for category, keywords in category_keywords.items():
        if any(keyword in text_lower for keyword in keywords):
            return category
    return "General"

def analyze_twitter_metrics(user_data: dict, tweets: List[dict]) -> dict:
    """User data aur tweets ke aadhar par performance metrics calculate karta hai."""
    if not tweets: return {"engagement_rate_per_post": 0, "like_comment_ratio": 0, "post_frequency_per_week": 0, "sentiment_score": 0, "overall_score": 0}
    followers = user_data["data"]["public_metrics"]["followers_count"]
    if followers == 0: return {"engagement_rate_per_post": 0, "like_comment_ratio": 0, "post_frequency_per_week": 0, "sentiment_score": 0, "overall_score": 0}

    total_likes = sum(t["public_metrics"]["like_count"] for t in tweets)
    total_replies = sum(t["public_metrics"]["reply_count"] for t in tweets)
    total_retweets = sum(t["public_metrics"]["retweet_count"] for t in tweets)
    avg_engagement = (total_likes + total_replies + total_retweets) / len(tweets)
    engagement_rate = (avg_engagement / followers) * 100
    like_comment_ratio = total_likes / (total_replies + 1)
    
    # Tweet text se sentiment nikalein (yeh fallback ke taur par use hoga)
    sentiments = [TextBlob(t.get("text", "")).sentiment.polarity for t in tweets]
    sentiment_score = statistics.mean(sentiments) if sentiments else 0

    post_frequency = 0
    if len(tweets) > 1:
        tweet_dates = [datetime.fromisoformat(t["created_at"].replace('Z', '+00:00')) for t in tweets]
        tweet_dates.sort()
        days_span = (tweet_dates[-1] - tweet_dates[0]).days
        if days_span > 0:
            post_frequency = len(tweets) / (days_span / 7.0)
    
    overall_score = (
        0.4 * min(engagement_rate, 5) * 20 +
        0.3 * (sentiment_score + 1) * 50 +
        0.3 * min(post_frequency, 4) * 25
    )

    return {
        "engagement_rate_per_post": round(engagement_rate, 4),
        "like_comment_ratio": round(like_comment_ratio, 2),
        "post_frequency_per_week": round(post_frequency, 2),
        "sentiment_score": round(sentiment_score, 2),
        "overall_score": round(min(overall_score, 100), 2)
    }

# ==============================================================================
# MAIN FUNCTION (Entry Point)
# ==============================================================================

async def get_twitter_insights(username: str) -> Optional[InfluencerProfile]:
    """
    Ek Twitter user ka poora data fetch karta hai, analyze karta hai, 
    aur database mein save karke profile return karta hai.
    """
    print(f"\n--- 🐦 Twitter insights fetch/save process shuru for: '{username}' ---")
    
    user_data = get_user_data(username)
    if not user_data or "data" not in user_data:
        print(f"❌ Aborting for '{username}' - user data nahi mila.")
        return None 
    
    user_info = user_data["data"]
    user_id = user_info["id"]
    tweets = get_recent_tweets(user_id, max_results=20)
    print(f"    - Found {len(tweets)} recent tweets for '{username}'.")
    
    posts_list: List[PostStats] = []
    for i, tweet in enumerate(tweets):
        public_metrics = tweet.get("public_metrics", {})
        non_public_metrics = tweet.get("non_public_metrics", {}) # 'impression_count' ke liye
        good_comments, bad_comments = 0, 0

        # --- RATE LIMIT JUGAAD ---
        # Sirf sabse naye 1 tweet ke replies fetch karein taaki rate limit na hit ho.
        if i < 1:
            print(f"    - Sabse naye tweet ({tweet['id']}) ke replies fetch kiye jaa rahe hain...")
            replies = get_replies_for_tweet(tweet['id'])
            print(f"        ... {len(replies)} replies mile.")
            for reply_text in replies:
                if TextBlob(reply_text).sentiment.polarity >= 0:
                    good_comments += 1
                else:
                    bad_comments += 1
        
        content_category = categorize_text_by_keywords(tweet.get("text", ""))

        post_stat = PostStats(
            post_id=tweet["id"],
            title=tweet.get("text", ""),
            published_at=datetime.fromisoformat(tweet["created_at"].replace('Z', '+00:00')),
            description=tweet.get("text", ""),
            views=0,
            likes=public_metrics.get("like_count", 0),
            comments_total=public_metrics.get("reply_count", 0),
            good_comments=good_comments,
            bad_comments=bad_comments,
            category="General",
            transcript=None,
            content_based_category=content_category
        )
        posts_list.append(post_stat)

    metrics_dict = analyze_twitter_metrics(user_data, tweets)
    
    # Agar comments mile hain, toh unse sentiment score ko behtar banayein
    total_analyzed_comments = sum(p.good_comments + p.bad_comments for p in posts_list)
    if total_analyzed_comments > 0:
        total_good_comments = sum(p.good_comments for p in posts_list)
        # Scale to -1 to 1 like TextBlob
        new_sentiment_score = (total_good_comments / total_analyzed_comments) * 2 - 1
        metrics_dict['sentiment_score'] = round(new_sentiment_score, 2)

    metrics_obj = Metrics(**metrics_dict)
    
    profile = InfluencerProfile(
        platform_id=user_id,
        platform="twitter",
        name=user_info.get("name"),
        username=user_info.get("username"),
        profile_pic_url=user_info.get("profile_image_url"),
        bio=user_info.get("description"),
        followers=user_info.get("public_metrics", {}).get("followers_count", 0),
        posts=posts_list,
        metrics=metrics_obj
    )

    try:
        await profile.save()
        print(f"✅ Successfully saved Twitter profile for: {profile.name} (Score: {profile.metrics.overall_score})")
        print("----------------------------------------------------------------------\n")
        return profile
    except Exception as e:
        print(f"❌ Database mein '{profile.name}' ko save karte waqt error aaya: {e}")
        return None