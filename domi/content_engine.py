import os
import sys
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PERSONAL_CHAT_ID = os.environ.get("PERSONAL_CHAT_ID", "7419276203")
POST_HOURS_UTC   = {10, 21, 2}   # 5AM, 4PM, 9PM Medellin/Tampa

# CLEANED RSS FEEDS - Removed dead links to prevent hangs
RSS_FEEDS = [
    ("CoinDesk",      "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("CoinTelegraph", "https://cointelegraph.com/rss"),
    ("Decrypt",       "https://decrypt.co/feed"),
    ("Bitcoin Mag",   "https://bitcoinmagazine.com/feed"),
]

def fetch_x_trends(bearer_token: str):
    """Pulls trending crypto topics using only the X Bearer Token."""
    if not bearer_token:
        return "No X data available."
    
    headers = {"Authorization": f"Bearer {bearer_token}"}
    # Using the v2 search endpoint to find recent high-engagement crypto tweets
    url = "https://api.twitter.com/2/tweets/search/recent"
    params = {
        'query': '(crypto OR bitcoin OR xrp) is:verified -is:retweet lang:en',
        'max_results': 10,
        'tweet.fields': 'public_metrics'
    }
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        if resp.status_code == 200:
            tweets = [t['text'] for t in resp.json().get('data', [])]
            return "\n".join(tweets)
    except Exception as e:
        print(f"[X API ERROR] {e}")
    return "X Research currently unavailable."

def call_sniper_brain(prompt: str) -> str:
    """SNIPER813PRO Gemini Brain with Retry Logic."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    
    for attempt in range(3):
        try:
            resp = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30)
            if resp.status_code == 429:
                time.sleep(10)
                continue
            resp.raise_for_status()
            return resp.json()['candidates'][0]['content']['parts'][0]['text'].strip()
        except Exception as e:
            print(f"[BRAIN ERROR] {e}")
            time.sleep(2)
    return ""

# ... [fetch_rss and fetch_news functions remain the same] ...

def run_content_engine():
    now_utc = datetime.now(timezone.utc)
    is_post_time = now_utc.hour in POST_HOURS_UTC
    
    # 1. Gather Intelligence
    x_research = fetch_x_trends(os.environ.get("X_BEARER_TOKEN"))
    news_data = fetch_news() # From your existing logic
    
    headlines = "\n".join(news_data[:10])
    intelligence = f"X TRENDS:\n{x_research}\n\nNEWS:\n{headlines}"

    # 2. Generate and Send to Telegram
    if is_post_time:
        prompt = build_market_post_prompt(intelligence)
        content = call_sniper_brain(prompt)
        send_to_personal(content, "MARKET POST - COPY TO X")
    else:
        prompt = build_heygen_prompt(intelligence)
        content = call_sniper_brain(prompt)
        send_to_personal(content, "HEYGEN SCRIPT")

if __name__ == "__main__":
    run_content_engine()
