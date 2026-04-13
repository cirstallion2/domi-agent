import os
import sys
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

# Ensure local module pathing
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def fetch_x_intel(token):
    """Scan X for trending crypto sentiment using Bearer Token."""
    if not token: return "No X Intel available."
    url = "https://api.twitter.com/2/tweets/search/recent"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        'query': '(crypto OR bitcoin OR xrp OR solana) is:verified -is:retweet lang:en',
        'max_results': 10
    }
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        if r.status_code == 200:
            tweets = [t['text'] for t in r.json().get('data', [])]
            return "\n".join(tweets)
    except: pass
    return "X Research currently unavailable."

def run_engine():
    print("🚀 SNIPER813PRO Content Engine: Active")
    
    # 1. Gather RSS News
    feeds = [
        "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "https://cointelegraph.com/rss",
        "https://decrypt.co/feed"
    ]
    headlines = []
    for url in feeds:
        try:
            res = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            root = ET.fromstring(res.content)
            headlines.extend([item.findtext('title') for item in root.findall('.//item')[:3]])
        except: continue

    # 2. Gather X Intelligence
    x_intel = fetch_x_intel(os.environ.get("X_BEARER_TOKEN"))
    
    # 3. Call SNIPER813PRO Brain (Gemini 2.0 Flash)
    api_key = os.environ.get("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    
    prompt = f"""
    You are DOMI, the market translator for SNIPER813PRO by 2much813.
    Use this intelligence to craft a high-conviction market post or script.
    
    LATEST NEWS: {headlines}
    X TRENDS: {x_intel}
    
    VOICE: Direct, technical, no fluff. The Sniper in the Dojo.
    """

    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]})
        content = response.json()['candidates'][0]['content']['parts'][0]['text']
        
        # 4. Deliver to Telegram
        tg_token = os.environ.get("TELEGRAM_TOKEN")
        chat_id = os.environ.get("PERSONAL_CHAT_ID")
        requests.post(f"https://api.telegram.org/bot{tg_token}/sendMessage", 
                     json={"chat_id": chat_id, "text": f"🦅 **DOMI INTEL REVEALED**\n\n{content}", "parse_mode": "Markdown"})
        print("✅ Intel successfully delivered to the Dojo.")
    except Exception as e:
        print(f"❌ Brain Error: {e}")

if __name__ == "__main__":
    run_engine()
