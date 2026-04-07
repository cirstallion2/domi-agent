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
        
        # Calculate MAs
        df['ma20'] = df['close'].rolling(20).mean()
        df['ma50'] = df['close'].rolling(50).mean()
        df['ma100'] = df['close'].rolling(100).mean()
        df['ma200'] = df['close'].rolling(200).mean()
        
        price = df['close'].iloc[-1]
        momentum = price - df['close'].iloc[-2]
        
        # Priority Logic: Find the CLOSEST MA to price
        best_ma = None
        min_diff = 100 # placeholder high number

        for ma in [20, 50, 100, 200]:
            ma_val = df[f'ma{ma}'].iloc[-1]
            diff = abs(((price - ma_val) / ma_val) * 100)
            
            # Check if this MA is currently being touched/crossed (under 0.8%)
            if diff < 0.8 and diff < min_diff:
                min_diff = diff
                best_ma = ma
        
        # If we found a valid MA cross/touch, build the one box for this asset
        if best_ma:
            hits += 1
            status = "🟢 BUY / LONG" if momentum > 0 else "🔴 SELL / SHORT"
            strength = "HIGH" if abs(momentum) > (price * 0.001) else "STABLE"
            
            body += f"💎 ASSET: {name}\n"
            body += f"💰 PRICE: ${price:,.4f}\n"
            body += f"🎯 SIGNAL: {status}\n"
            body += f"📊 LEVEL: {best_ma}MA Cross\n"
            body += f"⚡️ MOMENTUM: {strength}\n"
            body += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        
    if hits == 0:
        return None 
    return header + body

def send_telegram(message):
    if not message: return
    token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                  data={'chat_id': chat_id, 'text': message})

if __name__ == "__main__":
    report = analyze_assets()
    send_telegram(report)
