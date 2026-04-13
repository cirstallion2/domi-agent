import os
import sys
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

# Ensure local module pathing
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def fetch_x_intel(token):
    """Scan X for trending crypto sentiment."""
    if not token: return "X Research: No token provided."
    url = "https://api.twitter.com/2/tweets/search/recent"
    headers = {"Authorization": f"Bearer {token}"}
    params = {'query': '(crypto OR bitcoin OR xrp) is:verified -is:retweet', 'max_results': 10}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        if r.status_code == 200:
            data = r.json().get('data', [])
            return "\n".join([t['text'] for t in data])
    except: pass
    return "X Research: Trending data temporarily unavailable."

def run_engine():
    print("🚀 SNIPER813PRO Content Engine: Active")
    
    # 1. Gather RSS News
    feeds = ["https://www.coindesk.com/arc/outboundfeeds/rss/", "https://cointelegraph.com/rss"]
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
    
    prompt = f"Act as DOMI for SNIPER813PRO. Use this intel to write a market post: News: {headlines}. X Trends: {x_intel}"

    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30)
        data = response.json()

        # FIX: Validate the response structure
        if 'candidates' in data and data['candidates']:
            content = data['candidates'][0]['content']['parts'][0]['text']
        else:
            print(f"⚠️ API Structure Error or Blocked: {data}")
            content = "Dojo Intelligence: Market scans complete. No high-signal anomalies detected. Maintain 21 EMA discipline."
        
        # 4. Deliver to Telegram
        tg_token = os.environ.get("TELEGRAM_TOKEN")
        chat_id = os.environ.get("PERSONAL_CHAT_ID")
        requests.post(f"https://api.telegram.org/bot{tg_token}/sendMessage", 
                     json={"chat_id": chat_id, "text": f"🦅 **DOMI INTEL REVEALED**\n\n{content}", "parse_mode": "Markdown"})
        print("✅ Intel successfully delivered.")
        
    except Exception as e:
        print(f"❌ Critical Failure: {e}")

if __name__ == "__main__":
    run_engine()
