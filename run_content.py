import os
import sys
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

# SNIPER813PRO Environment Pathing
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def fetch_x_intel(token):
    """Scan X for trending crypto sentiment."""
    if not token: return "X Research: No token provided."
    url = "https://api.twitter.com/2/tweets/search/recent"
    headers = {"Authorization": f"Bearer {token}"}
    params = {'query': '(crypto OR bitcoin OR xrp OR solana) is:verified -is:retweet', 'max_results': 10}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        if r.status_code == 200:
            data = r.json().get('data', [])
            return "\n".join([t['text'] for t in data])
    except: pass
    return "X Research: Signal restricted."

def run_engine():
    print("🚀 SNIPER813PRO Content Engine: Active")
    
    # 1. Gather News Intelligence
    feeds = ["https://www.coindesk.com/arc/outboundfeeds/rss/", "https://cointelegraph.com/rss"]
    headlines = []
    for url in feeds:
        try:
            res = requests.get(url, timeout=10, headers={"User-Agent": "SNIPER813PRO-Agent"})
            root = ET.fromstring(res.content)
            headlines.extend([item.findtext('title') for item in root.findall('.//item')[:3]])
        except: continue

    x_intel = fetch_x_intel(os.environ.get("X_BEARER_TOKEN"))
    
    # 2. Call SNIPER813PRO Brain (Gemini 1.5 Flash + Safety Overrides)
    api_key = os.environ.get("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    # SAFETY: Prevents the brain from blocking market-talk
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
    ]

    prompt = f"Act as DOMI for SNIPER813PRO. Use this intel: News: {headlines}. X: {x_intel}. Write a high-conviction, technical market status for 2MUCH813. Focus on EMA 21 and Dojo discipline."

    content = ""
    for attempt in range(3):
        try:
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "safetySettings": safety_settings
            }
            response = requests.post(url, json=payload, timeout=30)
            data = response.json()

            if response.status_code == 429:
                print(f"⚠️ Quota hit. Attempt {attempt+1}: Sleeping 20s...")
                time.sleep(20)
                continue

            if 'candidates' in data and data['candidates'][0].get('content'):
                content = data['candidates'][0]['content']['parts'][0]['text']
                break
            else:
                # Identify if it was a filter or a quota issue
                reason = data.get('promptFeedback', {}).get('blockReason', 'QUOTA_LIMIT')
                content = f"Dojo Intelligence: Brain recalibrating ({reason}). Stay focused on the 21 EMA. Signal pending."
                break
        except Exception as e:
            print(f"❌ Attempt {attempt} Error: {e}")
            content = "Dojo Intelligence: Transmission bottleneck. Maintain sniper discipline."

    # 3. Deliver to Telegram
    tg_token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("PERSONAL_CHAT_ID")
    try:
        requests.post(f"https://api.telegram.org/bot{tg_token}/sendMessage", 
                     json={"chat_id": chat_id, "text": f"🦅 **SNIPER813PRO INTEL**\n\n{content}", "parse_mode": "Markdown"})
        print("✅ Intel cycle complete.")
    except Exception as e:
        print(f"❌ TG Error: {e}")

if __name__ == "__main__":
    run_engine()
