from mcp.server.fastmcp import FastMCP
from pymongo import MongoClient
import google.generativeai as genai
import os
import json
from bson import json_util 

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
GEMINI_MODEL = os.getenv("GEMINI_MODEL")
gemini_model = genai.GenerativeModel(GEMINI_MODEL) # Using a more recent model


def llm_filter_mongo(mongo_data: dict,user_query:str) -> dict:
    """
    Convert user natural language into valid MongoDB query using Gemini.
    """
    
    json_data_string = json_util.dumps(mongo_data, indent=2)
    print("json_data_string------------>",json_data_string,"user_query----->",user_query)
    prompt = f"""
You are an AI search and relevance engine. Your goal is to find the most relevant influencer objects from the provided JSON data that match the user's intent.

**Core Task:**
- Understand the user's query, including its underlying intent and concepts.
- Search through the `influencer_data` to find the most relevant matches.
- Return a JSON array of the matching objects. If no relevant objects are found, return an empty array `[]`.

**Search & Relevance Instructions:**
1.  **Semantic Matching:** Do not just look for exact keywords. Understand the topic. For example, if the user asks for "psychology", an influencer who discusses "philosophy" and "logic" is highly relevant.
2.  **Broad Field Search:** You MUST search for relevance across all meaningful text fields, primarily: `name`, `username`, `bio`, `posts.title`, `posts.description`, and `posts.category`. The `bio` is especially important.
3.  **Typo Tolerance:** Be tolerant of minor spelling errors in the user's query (e.g., 'physcology' should be treated as 'psychology').
4.  **Closest Match:** If you cannot find a perfect match, return the CLOSEST and MOST RELEVANT object(s). It is better to return a partially relevant result than nothing.

**CRITICAL OUTPUT FORMATTING RULE:**
- Your final output MUST be a perfectly valid JSON array.
- **Do NOT add escape backslashes `\` before Unicode characters.** The Hindi word 'नमस्ते' should be represented as `"नमस्ते"`, NOT as `"\न\म\स\्\त\े"`. Return all characters directly.
Now filter the following:

mongo_data:
{json_data_string}

user_query:
"{user_query}"

Return only the filtered JSON array.
"""

    response = gemini_model.generate_content(prompt)
    print("response----------->", response.text)

    # Clean up potential markdown formatting from the LLM
    text = response.text.replace("```json", "").replace("```", "").strip()
    print("text----------->", text)
    
    # It's safer to parse the JSON here and return a dict
    # to ensure the output is valid.
    try:
        data = json.loads(text)
        return {"data": data}
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from LLM: {e}")
        return {"error": "Failed to generate valid JSON query", "raw_output": text}
    





def llm_get_matching_ids(full_mongo_data: list, user_query: str) -> list[str]:
    """
    Analyzes a user query against a summary of influencer data and returns a list
    of matching MongoDB ObjectId strings.
    """
    
    # 1. PRE-PROCESSING: Create a detailed, "augmented" summary for the LLM.
    # Hum poora data nahi bhejenge, sirf zaroori fields bhejenge.
    
    json_data_string = json_util.dumps(full_mongo_data, indent=2)
    print("user_query----->", user_query,"json_data_string------->",json_data_string)
    
    # 2. PROMPT ENGINEERING: Ask for IDENTIFIERS ONLY.
    # Yahan humne prompt ko badal diya hai to ask for only _id.
    prompt = f"""
You are a highly intelligent AI assistant that matches user queries to the best influencers from a provided list.

**Your Goal:**
Analyze the `user_query` and return the `_id` objects of the most relevant influencers from the `influencer_data_summary`.

**Reasoning Instructions:**
1.  **Understand the Query:** Break down the query into its core components (Topic, Ranking, etc.). Match against `bio`, `metrics`, and `content_topics`.
2.  **Handle Ambiguity:** Interpret Hinglish and typos correctly.
3.  **Synthesize Information:** Use ALL the provided fields to make the best possible decision.

**CRITICAL OUTPUT FORMAT:**
- You MUST return a valid JSON array containing ONLY the `_id` object of the matching influencer(s).
- For "top" queries, usually return only the single best match.
- If no one is a good match, return an empty array `[]`.

**Example of correct output:**
```json
[
  {{
    "_id": {{
      "$oid": "691724b51e8fb83641deaeea"
    }}
  }}
]

mongo_data:
{json_data_string}

user_query:
"{user_query}"

JSON Array of Matching _id Objects:
"""
    response = gemini_model.generate_content(prompt)
    print("LLM Response (IDs)----------->", response.text)

    text = response.text.replace("```json", "").replace("```", "").strip()

    # 3. POST-PROCESSING: Extract just the ID strings.
    try:
        id_objects_from_llm = json.loads(text)
        
        if not isinstance(id_objects_from_llm, list):
            print("Warning: LLM did not return a list.")
            return []

        # Extract the actual string value from the {'_id': {'$oid': '...'}} structure
        matching_ids = [
            item['_id']['$oid'] 
            for item in id_objects_from_llm 
            if isinstance(item, dict) and '_id' in item and isinstance(item['_id'], dict) and '$oid' in item['_id']
        ]
        
        print("Extracted Matching IDs:", matching_ids)
        return matching_ids

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        print(f"Error processing LLM ID response: {e}. Raw output: {text}")
        return [] # Return empty list on failure




def llm_select_keys(user_query: str, available_fields: list) -> list:
    """
    Analyzes the user query and returns a list of necessary database keys
    to fulfill the request. This is the first stage of a two-stage query planner.
    """
    print(f"--- Stage 1: Selecting Keys for Query: '{user_query}' ---")
    
    # Format the list of keys nicely for the prompt
    fields_json_string = json.dumps(available_fields, indent=2)

    prompt = f"""
You are an intelligent MongoDB Query Planner. Your task is to analyze a user's natural language query and determine the minimum set of fields (keys) required from a database to answer that query.

**Input:**
1.  **`user_query`**: A natural language query from a user.
2.  **`available_fields`**: A JSON array of all possible keys in the database schema.

**Your Instructions:**
1.  Read the `user_query` to understand the user's intent (e.g., are they ranking, searching for a topic, or just looking for someone?).
2.  Select ONLY the keys from `available_fields` that are absolutely necessary to answer the query.
3.  **ALWAYS include `_id` and `platform` in your response**, as they are essential for identification and basic filtering.
4.  Handle Hinglish/typos: 'engamnet' means engagement, 'sabse zyada followers' means followers.
5.  Your output MUST be a valid JSON array of strings. Each string must be a key from the `available_fields` list. Do NOT invent new keys.

**Examples:**
-   **user_query**: "top engamnet wlaa youtuber"
    **Expected Output**: ["_id", "platform", "metrics.engagement_rate_per_post"]
-   **user_query**: "Find influencers who promote AI products like perplexity"
    **Expected Output**: ["_id", "platform", "bio", "posts.title", "posts.description"]
-   **user_query**: "instagram pe sabse zyada followers kiske hai"
    **Expected Output**: ["_id", "platform", "followers"]
-   **user_query**: "Show me Vikas Divyakirti's bio"
    **Expected Output**: ["_id", "platform", "name", "username", "bio"]

---
**`available_fields`**:
{fields_json_string}

**`user_query`**:
"{user_query}"

**Required Keys (JSON array of strings only):**
"""

    response = gemini_model.generate_content(prompt)
    print("LLM Response for keys:", response.text)

    text = response.text.replace("```json", "").replace("```", "").strip()

    try:
        # The output should be a list of strings, e.g., ['_id', 'platform', 'followers']
        selected_keys = json.loads(text)
        if isinstance(selected_keys, list) and all(isinstance(key, str) for key in selected_keys):
            print("Successfully selected keys:", selected_keys)
            return selected_keys
        else:
            raise ValueError("LLM did not return a list of strings.")
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Error parsing keys from LLM: {e}. Falling back to default keys.")
        # Fallback to a safe default if the LLM fails
        return ["_id", "name", "username", "bio", "platform", "followers", "metrics.engagement_rate_per_post"]