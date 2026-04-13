"""
DOMI - Phase 5: Content-to-Conversion Loop
content_engine.py

Now with 100% Direct X (Twitter) Integration.
Uses SNIPER813PRO (Gemini) for high-conviction market narratives.
"""

import os
import sys
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import tweepy  # You'll need to add this to requirements.txt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PERSONAL_CHAT_ID = os.environ.get("PERSONAL_CHAT_ID", "7419276203")
POST_HOURS_UTC   = {10, 21, 2} # 5 AM, 4 PM, 9 PM Medellin/Tampa

RSS_FEEDS = [
    ("CoinDesk",      "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("CoinTelegraph", "https://cointelegraph.com/rss"),
    ("Decrypt",       "https://decrypt.co/feed"),
]

def post_to_x(text: str):
    """Directly posts to X using Tweepy (Twitter API v2)."""
    try:
        client = tweepy.Client(
            consumer_key=os.environ.get("X_API_KEY"),
            consumer_secret=os.environ.get("X_API_SECRET"),
            access_token=os.environ.get("X_ACCESS_TOKEN"),
            access_token_secret=os.environ.get("X_ACCESS_SECRET")
        )
        response = client.create_tweet(text=text)
        print(f"[X SUCCESS] Tweet ID: {response.data['id']}")
        return True
    except Exception as e:
        print(f"[X ERROR] Failed to post: {e}")
        return False

def call_sniper_brain(prompt: str) -> str:
    """Uses the SNIPER813PRO (Gemini) brain for content."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    
    try:
        resp = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30)
        resp.raise_for_status()
        return resp.json()['candidates'][0]['content']['parts'][0]['text'].strip()
    except Exception as e:
        print(f"[BRAIN ERROR] {e}")
        return ""

# ... [fetch_rss and fetch_crypto_news logic remains the same] ...

def run_content_engine():
    now_utc = datetime.now(timezone.utc)
    is_post_time = now_utc.hour in POST_HOURS_UTC
    
    articles = fetch_crypto_news()
    if not articles: return

    headlines = "\n".join([f"- {a['title']}" for a in articles[:8]])

    if is_post_time:
        print(f"[CONTENT] {now_utc.hour}:00 UTC - Executing Direct X Post")
        prompt = build_market_post_prompt(headlines)
        content = call_sniper_brain(prompt)
        
        if content:
            # Post to X and notify you that it's live
            if post_to_x(content):
                send_to_personal(f"🚀 **LIVE ON X:**\n\n{content}", "X POST EXECUTED")
    else:
        print(f"[CONTENT] {now_utc.hour}:00 UTC - Generating HeyGen Script")
        prompt = build_heygen_prompt(headlines)
        content = call_sniper_brain(prompt)
        if content:
            send_to_personal(content, "HEYGEN SCRIPT")

if __name__ == "__main__":
    run_content_engine()
