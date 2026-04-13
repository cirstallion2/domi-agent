import os
import sys
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

# SNIPER813PRO Environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_engine():
    print("🚀 SNIPER813PRO Content Engine: Active")
    
    # ... [Keep your existing News and X fetching logic here] ...
    headlines = "Market Scanning..." # Simplified for this fix
    x_intel = "Sentiment Analysis..."

    # 1. Call the Brain
    api_key = os.environ.get("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    prompt = f"Act as DOMI for SNIPER813PRO. Use this intel: News: {headlines}. X: {x_intel}. Write a short, high-conviction market update. No special characters like underscores."

    content = "Dojo Intelligence: Market scans complete. Stay disciplined." # Default fallback

    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30)
        data = response.json()
        if 'candidates' in data:
            content = data['candidates'][0]['content']['parts'][0]['text']
    except:
        print("⚠️ Brain connection weak. Using fallback.")

    # 2. THE FIX: Hardened Telegram Delivery
    tg_token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("PERSONAL_CHAT_ID", "7419276203")
    
    # We remove Markdown and use HTML to prevent "silent failures"
    # Telegram is very picky about mismatched * or _ in Markdown
    clean_content = content.replace("<", "&lt;").replace(">", "&gt;") 
    tg_msg = f"<b>🦅 SNIPER813PRO INTEL</b>\n\n{clean_content}"

    print(f"📡 Attempting delivery to ID: {chat_id}...")
    
    try:
        tg_url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": tg_msg,
            "parse_mode": "HTML" # Switched to HTML for better reliability
        }
        res = requests.post(tg_url, json=payload, timeout=10)
        
        if res.status_code == 200:
            print("✅ TELEGRAM DELIVERED.")
        else:
            print(f"❌ TELEGRAM REJECTED: {res.text}")
            
    except Exception as e:
        print(f"❌ CRITICAL TG ERROR: {e}")

if __name__ == "__main__":
    run_engine()
