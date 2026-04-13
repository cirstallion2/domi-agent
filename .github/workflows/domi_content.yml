"""
DOMI - Phase 5: Content-to-Conversion Loop
content_engine.py

REWRITTEN: Removed tweepy. Uses X Bearer Token for Research only.
"""

import os
import sys
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PERSONAL_CHAT_ID = os.environ.get("PERSONAL_CHAT_ID", "7419276203")
POST_HOURS_UTC   = {10, 21, 2}   # 5AM, 4PM, 9PM Medellin/Tampa

RSS_FEEDS = [
    ("CoinDesk",      "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("CoinTelegraph", "https://cointelegraph.com/rss"),
    ("Decrypt",       "https://decrypt.co/feed"),
    ("Bitcoin Mag",   "https://bitcoinmagazine.com/feed"),
]

def fetch_x_research(bearer_token: str) -> str:
    """Pull recent high-signal tweets for context."""
    if not bearer_token:
        return "X Data: Unavailable (No Token)"
    
    headers = {"Authorization": f"Bearer {bearer_token}"}
    url = "https://api.twitter.com/2/tweets/search/recent"
    params = {
        'query': '(crypto OR bitcoin OR altcoins) is:verified -is:retweet lang:en',
        'max_results': 10,
        'tweet.fields': 'public_metrics'
    }
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        if resp.status_code == 200:
            tweets = [f"- {t['text']}" for t in resp.json().get('data', [])]
            return "\n".join(tweets)
    except Exception as e:
        print(f"[X ERROR] {e}")
    return "X Data: Search failed."

def fetch_news() -> str:
    """Fetch and filter relevant news headlines."""
    all_news = []
    headers = {"User-Agent": "Mozilla/5.0 (DOMI-Agent/1.0)"}
    
    for source, url in RSS_FEEDS:
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            root = ET.fromstring(resp.content)
            for item in root.findall(".//item")[:3]:
                title = item.findtext("title", "").strip()
                all_news.append(f"[{source}] {title}")
            time.sleep(1)
        except Exception as e:
            print(f"[RSS ERROR] {source}: {e}")
    return "\n".join(all_news)

def call_sniper_brain(prompt: str) -> str:
    """The SNIPER813PRO Brain (Gemini 2.0 Flash)."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    
    for _ in range(3): # Retry loop for rate limits
        try:
            resp = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30)
            if resp.status_code == 429:
                time.sleep(10)
                continue
            resp.raise_for_status()
            return resp.json()['candidates'][0]['content']['parts'][0]['text'].strip()
        except Exception as e:
            print(f"[BRAIN ERROR] {e}")
    return ""

def send_to_telegram(content: str, label: str):
    """Deliver to the Dojo HQ (Personal Telegram)."""
    token = os.environ.get("TELEGRAM_TOKEN", "")
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    msg = f"🦅 **SNIPER813PRO | {label}**\n_{timestamp}_\n\n{content}"
    
    try:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                      json={"chat_id": PERSONAL_CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    except Exception as e:
        print(f"[TELEGRAM ERROR] {e}")

def run_content_engine():
    now_utc = datetime.now(timezone.utc)
    is_post_time = now_utc.hour in POST_HOURS_UTC
    
    print(f"[CONTENT] Running Research Mode...")
    intel_x = fetch_x_research(os.environ.get("X_BEARER_TOKEN"))
    intel_news = fetch_news()
    
    context = f"LATEST X TRENDS:\n{intel_x}\n\nLATEST NEWS:\n{intel_news}"
    
    if is_post_time:
        # Prompt logic (assumed in your prompt_builders.py or added here)
        content = call_sniper_brain(f"Write a high-conviction market post based on:\n{context}")
        send_to_telegram(content, "MARKET POST (X/TG)")
    else:
        content = call_sniper_brain(f"Write a 60s HeyGen video script based on:\n{context}")
        send_to_telegram(content, "HEYGEN VIDEO SCRIPT")

if __name__ == "__main__":
    run_content_engine()
