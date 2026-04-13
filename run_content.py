import os
import sys
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

# 1. GATHER INTEL
def fetch_x_intel(token):
    if not token: return "Market sentiment: Neutral."
    url = "https://api.twitter.com/2/tweets/search/recent"
    headers = {"Authorization": f"Bearer {token}"}
    params = {'query': '(crypto OR xrp OR solana) is:verified -is:retweet', 'max_results': 5}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        if r.status_code == 200:
            return " ".join([t['text'] for t in r.json().get('data', [])])
    except: return "Sentiment scanning..."

def run_engine():
    print("🚀 SNIPER813PRO Content Engine: Active")
    
    # 2. CALL THE BRAIN (Switching to 1.5-Flash for maximum quota)
    api_key = os.environ.get("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    # Explicit instructions to keep the brain focused
    prompt = "Write a high-conviction market update for the SNIPER813PRO brand. Mention XRP or SOL based on general bullish sentiment. Keep it under 50 words. Be aggressive and technical."

    content = "Dojo Intelligence: Market scans complete. Stay disciplined." # Fallback

    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30)
        data = response.json()
        
        # DEBUG: Let's see what the brain is actually doing in the logs
        print(f"DEBUG BRAIN RESPONSE: {data}")

        if 'candidates' in data and data['candidates'][0].get('content'):
            content = data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        print(f"❌ Brain connection error: {e}")

    # 3. TELEGRAM DELIVERY (HTML MODE)
    tg_token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = "7419276203" # Your verified ID
    
    clean_content = content.replace("<", "&lt;").replace(">", "&gt;") 
    tg_msg = f"<b>🦅 SNIPER813PRO INTEL</b>\n\n{clean_content}"

    try:
        res = requests.post(f"https://api.telegram.org/bot{tg_token}/sendMessage", 
                            json={"chat_id": chat_id, "text": tg_msg, "parse_mode": "HTML"}, timeout=10)
        if res.status_code == 200:
            print("✅ TELEGRAM DELIVERED.")
        else:
            print(f"❌ TG REJECTED: {res.text}")
    except Exception as e:
        print(f"❌ TG CRITICAL ERROR: {e}")

if __name__ == "__main__":
    run_engine()
