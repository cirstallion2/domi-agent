import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

def run_engine():
    print("🚀 SNIPER813PRO: DOMI Content Engine Active")
    
    # 1. PERCEPTION: Gather 2026 Pulse
    # Targets: XRP Utility, SOL Speed, and the April '26 DeAI Boom
    headlines = []
    feeds = ["https://www.coindesk.com/arc/outboundfeeds/rss/", "https://cointelegraph.com/rss"]
    for url in feeds:
        try:
            res = requests.get(url, timeout=10)
            root = ET.fromstring(res.content)
            headlines.extend([item.findtext('title') for item in root.findall('.//item')[:2]])
        except: continue

    # 2. REASONING: Orchestrator DOMI (Gemini 1.5 Flash)
    api_key = os.environ.get("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    prompt = f"""
    Act as DOMI, the Master AI Orchestrator for 2MUCH813. 
    Current Market Pulse: {headlines}
    
    TASK: Generate two items:
    1. A Technical Telegram Update (Aggressive, high-conviction).
    2. A 30-Second Video Script (Hook, Alpha, CTA).
    
    Tone: Sniper, Dojo-focused, No fluff. Focus on the 21 EMA and 2026 Narratives (XRP/DeAI).
    """

    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30)
        data = response.json()
        content = data['candidates'][0]['content']['parts'][0]['text']
    except:
        content = "Dojo Intelligence: Market scans running. Stay focused on the 21 EMA."

    # 3. EXECUTION: Deliver to 2MUCH813
    tg_token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = "7419276203"
    
    # Format for readability
    clean_msg = f"<b>🦅 DOMI MASTER INTEL</b>\n\n{content.replace('*', '')}"
    
    requests.post(f"https://api.telegram.org/bot{tg_token}/sendMessage", 
                 json={"chat_id": chat_id, "text": clean_msg, "parse_mode": "HTML"})
    print("✅ Alpha Delivered.")

if __name__ == "__main__":
    run_engine()
