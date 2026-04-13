import os
import requests

def send_telegram_signal(sig):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    msg = (
        f"🚨 <b>SNIPER813PRO GOLD SIGNAL</b> 🚨\n\n"
        f"<b>Pair:</b> {sig.pair}\n"
        f"<b>Direction:</b> {sig.direction} 🚀\n"
        f"<b>Entry Price:</b> ${sig.price}\n"
        f"<b>Strategy:</b> Goalden Setup (6/6)\n\n"
        f"<i>EMA 200: {sig.ema200} | RSI: {sig.rsi}</i>\n"
        f"<b>Dojo Status:</b> EXECUTING"
    )
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"})
