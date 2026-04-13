import os
import sys
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import tweepy

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PERSONAL_CHAT_ID = os.environ.get("PERSONAL_CHAT_ID", "7419276203")
POST_HOURS_UTC   = {10, 21, 2}   # 5AM, 4PM, 9PM Medellin/Tampa

# CLEANED RSS FEEDS - Removed Reuters and Forbes (Broken)
RSS_FEEDS = [
    ("CoinDesk",      "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("CoinTelegraph", "https://cointelegraph.com/rss"),
    ("Decrypt",       "https://decrypt.co/feed"),
    ("Bitcoin Mag",   "https://bitcoinmagazine.com/feed"),
]

def call_sniper_brain(prompt: str) -> str:
    """SNIPER813PRO Gemini Brain with Retry Logic for Rate Limits."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    
    for attempt in range(3):
        try:
            resp = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30)
            if resp.status_code == 429:
                print(f"[BRAIN] Rate limited. Cooling down {10 * (attempt+1)}s...")
                time.sleep(10 * (attempt+1))
                continue
            resp.raise_for_status()
            return resp.json()['candidates'][0]['content']['parts'][0]['text'].strip()
        except Exception as e:
            print(f"[BRAIN ERROR] {e}")
            time.sleep(2)
    return ""

def post_to_x(text: str):
    """Direct X Post using API v2 credentials."""
    try:
        client = tweepy.Client(
            consumer_key=os.environ.get("X_API_KEY"),
            consumer_secret=os.environ.get("X_API_SECRET"),
            access_token=os.environ.get("X_ACCESS_TOKEN"),
            access_token_secret=os.environ.get("X_ACCESS_SECRET")
        )
        # Trim to X limits just in case
        clean_text = text[:280] if len(text) > 280 else text
        response = client.create_tweet(text=clean_text)
        print(f"[X SUCCESS] Posted Tweet ID: {response.data['id']}")
        return True
    except Exception as e:
        print(f"[X ERROR] {e}")
        return False

# ... [Keep your fetch_rss and fetch_news functions from your snippet] ...

def run_content_engine():
    now_utc = datetime.now(timezone.utc)
    is_post_time = now_utc.hour in POST_HOURS_UTC
    mode_label = "MARKET POST" if is_post_time else "HEYGEN SCRIPT"

    print(f"\n[CONTENT] {now_utc.strftime('%Y-%m-%d %H:%M UTC')} | Mode: {mode_label}")

    news = fetch_news()
    if not news:
        print("[CONTENT] No news data. Skipping.")
        return

    headlines = "\n".join(news[:10])
    
    if is_post_time:
        prompt = build_market_post_prompt(news, {"tweets": [], "trending": []}) # Simplified for X post
        content = call_sniper_brain(prompt)
        if content:
            # Post to X AND send to you for records
            post_to_x(content)
            send_to_personal(content, "LIVE X POST EXECUTED")
    else:
        prompt = build_heygen_prompt(news, {"tweets": []})
        content = call_sniper_brain(prompt)
        if content:
            send_to_personal(content, "HEYGEN SCRIPT - READY FOR VIDEO")

if __name__ == "__main__":
    run_content_engine()
