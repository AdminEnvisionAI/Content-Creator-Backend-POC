# from mcp.server.fastmcp import FastMCP
# from pymongo import MongoClient
# import google.generativeai as genai
# import os
# import json

# # -----------------------
# # ENV VARIABLES
# # -----------------------
# MONGO_URI = "mongodb+srv://agarwalkunal196:XqWnpbu7RKlZW5KG@cluster0.b4ypg.mongodb.net/?appName=Cluster0"
# GEMINI_API_KEY ="AIzaSyD0OqXQ1m95vMiwn3E-o3dnM0w7KOKSh24"
# GEMINI_MODEL = "gemini-2.0-flash-lite"

# # -----------------------
# # MCP SERVER
# # -----------------------
# mcp = FastMCP()

# # -----------------------
# # MongoDB Connect
# # -----------------------
# mongo = MongoClient(MONGO_URI)
# db = mongo["influencer_db"]
# collection = db["influencers"]

# # -----------------------
# # Gemini Client
# # -----------------------
# gemini_model = genai.GenerativeModel("gemini-2.0-flash-lite")


# # ============================================================
# #  TOOL 1 → LLM converts natural language → MongoDB query
# # ============================================================
# @mcp.tool()
# def llm_to_mongo(query: str) -> dict:
#     """
#     Convert user natural language into valid MongoDB query using Gemini.
#     """
#     print("query------------->",query)
#     prompt = f"""
# You are an AI that converts user questions into MongoDB filter queries.

# MongoDB collection fields:
# - name: string
# - platform: "youtube" | "instagram" | "twitter" | "facebook"
# - niche: string (gaming, fitness, tech, beauty, etc.)
# - followers: number
# - engagement_rate: number
# - categories: list of interests
# - country: string

# User Query:
# "{query}"

# Rules:
# 1. ALWAYS return pure JSON (MongoDB query only)
# 2. DO NOT add code block formatting
# 3. If user mentions:
#    - "top" → sort by engagement_rate desc
#    - "best" → sort by engagement_rate desc
# 4. Use regex for partial matches
# 5. If platform mentioned (e.g. youtube/instragram) add: {"platform": value}

# Return only JSON query.
# """

#     response = gemini_model.generate_content(prompt)
#     print("response----------->",response)

#     text = response.text.replace("```json", "").replace("```", "").strip()
#     print("text----------->",text)

#     return {"mongo_query": text}


# # ============================================================
# #  TOOL 2 → Query MongoDB
# # ============================================================
# @mcp.tool()
# def mongo_search(query: dict) -> list:
#     """
#     Run MongoDB query produced by LLM.
#     """

#     results = list(collection.find(query).sort("engagement_rate", -1).limit(20))

#     # Convert ObjectId to string
#     for r in results:
#         r["_id"] = str(r["_id"])

#     return results


# # ============================================================
# # START MCP SERVER
# # ============================================================
# if __name__ == "__main__":
#     mcp.run(transport="sse")



# mcp_server.py (CORRECTED)

from mcp.server.fastmcp import FastMCP
from pymongo import MongoClient
import google.generativeai as genai
import os
import json

# -----------------------
# ENV VARIABLES
# -----------------------
MONGO_URI = "mongodb+srv://agarwalkunal196:XqWnpbu7RKlZW5KG@cluster0.b4ypg.mongodb.net/?appName=Cluster0"
# It's better practice to load keys from environment variables
genai.configure(api_key="AIzaSyDwmaaQCRpAalCZO9okbXreHqddNPy2GwQ")
GEMINI_MODEL = "gemini-2.0-flash-lite"

# -----------------------
# MCP SERVER
# -----------------------
mcp = FastMCP()

# -----------------------
# MongoDB Connect
# -----------------------
mongo = MongoClient(MONGO_URI)
db = mongo["influencer_db"]
collection = db["influencers"]

# -----------------------
# Gemini Client
# -----------------------
# The new genai SDK recommends this initialization
gemini_model = genai.GenerativeModel("gemini-2.0-flash-lite") # Using a more recent model


# ============================================================
#  TOOL 1 → LLM converts natural language → MongoDB query
# ============================================================
@mcp.tool()
def llm_to_mongo(query: str) -> dict:
    """
    Convert user natural language into valid MongoDB query using Gemini.
    """
    print("query------------->", query)
    prompt = f"""
You are an AI that converts user questions into MongoDB filter queries.

MongoDB collection fields:
- name: string
- platform: "youtube" | "instagram" | "twitter" | "facebook"
- niche: string (gaming, fitness, tech, beauty, etc.)
- followers: number
- engagement_rate: number
- categories: list of interests
- country: string

User Query:
"{query}"

Rules:
1. ALWAYS return pure JSON (MongoDB query only)
2. DO NOT add code block formatting like ```json.
3. If user mentions "top" or "best", the query should filter and the sorting will be handled separately. Don't add a sort clause.
4. Use regex for partial, case-insensitive matches on string fields. For example, for "tech", use {{"niche": {{"$regex": "tech", "$options": "i"}}}}.
5. If a platform is mentioned (e.g., youtube, instagram), add it to the filter like: {{"platform": "youtube"}}.

Return only the JSON filter object.
"""

    response = gemini_model.generate_content(prompt)
    print("response----------->", response.text)

    # Clean up potential markdown formatting from the LLM
    text = response.text.replace("```json", "").replace("```", "").strip()
    print("text----------->", text)
    
    # It's safer to parse the JSON here and return a dict
    # to ensure the output is valid.
    try:
        mongo_query = json.loads(text)
        return {"mongo_query": mongo_query}
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from LLM: {e}")
        return {"error": "Failed to generate valid JSON query", "raw_output": text}


# ============================================================
#  TOOL 2 → Query MongoDB
# ============================================================
@mcp.tool()
def mongo_search(query: dict) -> list:
    """
    Run MongoDB query produced by LLM.
    """
    print(f"Executing MongoDB query: {query}")
    results = list(collection.find(query).sort("engagement_rate", -1).limit(20))

    # Convert ObjectId to string
    for r in results:
        r["_id"] = str(r["_id"])

    return results


# ============================================================
# START MCP SERVER
# ============================================================
if __name__ == "__main__":
    mcp.run(transport="sse")