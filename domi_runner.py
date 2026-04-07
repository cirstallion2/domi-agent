import os
import requests
import pandas as pd
import numpy as np

WATCHLIST = {
    "BTC": "XXBTZUSD",
    "XRP": "XRPUSD",
    "XLM": "XLMUSD",
    "ZBCN": "ZBCNUSD",
    "JASMY": "JASMYUSD"
}

def get_kraken_data(pair, interval=60):
    url = f"https://api.kraken.com/0/public/OHLC?pair={pair}&interval={interval}"
    try:
        resp = requests.get(url).json()
        data_key = list(resp['result'].keys())[0]
        data = resp['result'][data_key]
        df = pd.DataFrame(data, columns=['ts', 'open', 'high', 'low', 'close', 'vwap', 'vol', 'count'])
        df['close'] = df['close'].astype(float)
        return df
    except: return None

def analyze_assets():
    header = "⚡️ SNIPER813PRO | DOMI INTELLIGENCE ⚡️\n"
    header += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    body = ""
    hits = 0

    for name, ticker in WATCHLIST.items():
        df = get_kraken_data(ticker)
        if df is None: continue
        
        # MAs
        df['ma20'] = df['close'].rolling(20).mean()
        df['ma50'] = df['close'].rolling(50).mean()
        df['ma100'] = df['close'].rolling(100).mean()
        df['ma200'] = df['close'].rolling(200).mean()
        
        price = df['close'].iloc[-1]
        momentum = price - df['close'].iloc[-2]
        
        for ma in [20, 50, 100, 200]:
            ma_val = df[f'ma{ma}'].iloc[-1]
            diff = ((price - ma_val) / ma_val) * 100
            
            # THE VIP LOGIC: If price is crossing UP through MA = BUY. If crossing DOWN = SELL.
            if abs(diff) < 0.8:
                hits += 1
                status = "🟢 BUY / LONG" if momentum > 0 else "🔴 SELL / SHORT"
                strength = "HIGH" if abs(momentum) > (price * 0.001) else "STABLE"
                
                body += f"💎 ASSET: {name}\n"
                body += f"💰 PRICE: ${price:,.4f}\n"
                body += f"🎯 SIGNAL: {status}\n"
                body += f"📊 LEVEL: {ma}MA Cross\n"
                body += f"⚡️ MOMENTUM: {strength}\n"
                body += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        
    if hits == 0:
        return None # Only send if there is a real play
    return header + body

def send_telegram(message):
    if not message: return
    token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                  data={'chat_id': chat_id, 'text': message, 'parse_mode': 'Markdown'})

if __name__ == "__main__":
    report = analyze_assets()
    send_telegram(report)
