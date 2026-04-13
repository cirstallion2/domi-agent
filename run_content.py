import os
import sys
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

# SNIPER813PRO Pathing
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def fetch_x_intel(token):
    """Pull X trends without the heavy Tweepy bloat."""
    if not token: return "X Research: No Bearer Token."
    url = "https://api.twitter.com/2/tweets/search/recent"
    headers = {"Authorization": f"Bearer {token}"}
    params = {'query': '(crypto OR bitcoin OR xrp OR solana) is:verified -is:retweet', 'max_results': 10}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        if r.status_code == 200:
            tweets = [t['text'] for t in r.json().get('data', [])]
            return "\n".join(tweets)
    except: pass
    return "X Research: Limited signal detected."

def run_engine():
    print("🚀 SNIPER813PRO Content Engine: Active")
    
    # 1. RSS Intel
    feeds = ["https://www.coindesk.com/arc/outboundfeeds/rss/", "https://cointelegraph.com/rss"]
    headlines = []
    for url in feeds:
        try:
            res = requests.get(url, timeout=10, headers={"User-Agent": "SNIPER813PRO-Agent"})
            root = ET.fromstring(res.content)
            headlines.extend([item.findtext('title') for item in root.findall('.//item')[:3]])
        except: continue

    x_intel = fetch_x_intel(os.environ.get("X_BEARER_TOKEN"))
    
    # 2. Call SNIPER813PRO Brain (Gemini 1.5 Flash for Quota Stability)
    api_key = os.environ.get("GEMINI_API_KEY")
    # Swapped to 1.5-flash to avoid 'limit: 0' error
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    prompt = f"Act as DOMI for SNIPER813PRO. High-conviction market post. News: {headlines}. X Trends: {x_intel}. Focus: EMA 21, Volume, and Sniper discipline."

    content = "Dojo Intelligence: Market scans running. Stay focused on the 21 EMA." # Default fallback

    for attempt in range(3):
        try:
            response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30)
            data = response.json()

            if response.status_code == 429:
                print(f"⚠️ Quota hit. Attempt {attempt+1}: Sleeping 10s...")
                time.sleep(10)
                continue

            if 'candidates' in data and data['candidates']:
                content = data['candidates'][0]['content']['parts'][0]['text']
                break
        except Exception as e:
            print(f"❌ Attempt {attempt} Error: {e}")
            time.sleep(2)

    # 3. Deliver to Telegram
    tg_token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("PERSONAL_CHAT_ID")
    try:
        requests.post(f"https://api.telegram.org/bot{tg_token}/sendMessage", 
                     json={"chat_id": chat_id, "text": f"🦅 **SNIPER813PRO INTEL**\n\n{content}", "parse_mode": "Markdown"})
        print("✅ Intel successfully delivered to 2MUCH813.")
    except Exception as e:
        print(f"❌ TG Delivery Error: {e}")

if __name__ == "__main__":
    run_engine()
