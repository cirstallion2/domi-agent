import os
import sys
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def fetch_x_intel(token):
    if not token: return "X Research: Unavailable."
    url = "https://api.twitter.com/2/tweets/search/recent"
    headers = {"Authorization": f"Bearer {token}"}
    params = {'query': '(crypto OR bitcoin OR xrp) is:verified -is:retweet', 'max_results': 10}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        if r.status_code == 200:
            return "\n".join([t['text'] for t in r.json().get('data', [])])
    except: pass
    return "X Research: Data temporarily restricted."

def run_engine():
    print("🚀 SNIPER813PRO Content Engine: Active")
    
    # 1. Gather Intel
    feeds = ["https://www.coindesk.com/arc/outboundfeeds/rss/", "https://cointelegraph.com/rss"]
    headlines = []
    for url in feeds:
        try:
            res = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            root = ET.fromstring(res.content)
            headlines.extend([item.findtext('title') for item in root.findall('.//item')[:3]])
        except: continue

    x_intel = fetch_x_intel(os.environ.get("X_BEARER_TOKEN"))
    
    # 2. Call SNIPER813PRO Brain (Switching to 1.5 Flash for higher quota)
    api_key = os.environ.get("GEMINI_API_KEY")
    # Swapped 2.0-flash -> 1.5-flash
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    prompt = f"Act as DOMI for SNIPER813PRO. Create a high-conviction market update. News: {headlines}. X Trends: {x_intel}"

    for attempt in range(3):
        try:
            response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30)
            data = response.json()

            if response.status_code == 429:
                print(f"⚠️ Quota hit. Sleeping {attempt * 10 + 5}s...")
                time.sleep(attempt * 10 + 5)
                continue

            if 'candidates' in data and data['candidates']:
                content = data['candidates'][0]['content']['parts'][0]['text']
                break
            else:
                content = "Dojo Intelligence: Market scans running. High volatility detected near the 21 EMA. Stay focused."
                break
        except Exception as e:
            print(f"❌ Attempt {attempt} failed: {e}")
            content = "Dojo Intelligence: Connection bottleneck. Maintain current positions."
    
    # 3. Deliver to Telegram
    tg_token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("PERSONAL_CHAT_ID")
    requests.post(f"https://api.telegram.org/bot{tg_token}/sendMessage", 
                 json={"chat_id": chat_id, "text": f"🦅 **SNIPER813PRO INTEL**\n\n{content}", "parse_mode": "Markdown"})
    print("✅ Intel cycle complete.")

if __name__ == "__main__":
    run_engine()
