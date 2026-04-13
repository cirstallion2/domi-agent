import os
import requests
import xml.etree.ElementTree as ET
import time

def run_engine():
    print("🚀 SNIPER813PRO: DOMI Content Engine Active")
    
    # 1. PERCEPTION: Gather 2026 Pulse (XRP & SOL focus)
    headlines = []
    feeds = ["https://www.coindesk.com/arc/outboundfeeds/rss/", "https://cointelegraph.com/rss"]
    for url in feeds:
        try:
            res = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            root = ET.fromstring(res.content)
            headlines.extend([item.findtext('title') for item in root.findall('.//item')[:3]])
        except: continue

    # 2. REASONING: Orchestrator DOMI (Gemini 1.5 Flash)
    api_key = os.environ.get("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    # SAFETY BYPASS: Prevents the brain from blocking market analysis
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
    ]

    prompt = f"""
    Act as DOMI for the 2MUCH813 brand. 
    Intel: {headlines}
    
    TASK: 
    1. Write a 50-word Technical Telegram Update. Focus on XRP/SOL and the 21 EMA. Use aggressive 'Dojo' energy.
    2. Write a 30-Second Video Script:
       - 0-5s: Viral Hook.
       - 5-20s: The Technical Alpha.
       - 20-30s: CTA to join the Elite Dojo.
    """

    content = "Dojo Intelligence: Market scans running. Stay focused on the 21 EMA."
    try:
        payload = {"contents": [{"parts": [{"text": prompt}]}], "safetySettings": safety_settings}
        response = requests.post(url, json=payload, timeout=30)
        data = response.json()
        if 'candidates' in data and data['candidates'][0].get('content'):
            content = data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        print(f"❌ Brain Error: {e}")

    # 3. EXECUTION: Deliver to 2MUCH813
    tg_token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = "7419276203"
    
    # Use HTML to ensure clean delivery
    clean_msg = f"<b>🦅 SNIPER813PRO MASTER INTEL</b>\n\n{content}"
    requests.post(f"https://api.telegram.org/bot{tg_token}/sendMessage", 
                 json={"chat_id": chat_id, "text": clean_msg, "parse_mode": "HTML"})
    print("✅ Intel Delivered.")

if __name__ == "__main__":
    run_engine()
