import os
import requests
import pandas as pd
import numpy as np
import time

# SNIPER813PRO Asset Mapping
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
        # Kraken returns the key based on the pair name provided
        data_key = list(resp['result'].keys())[0]
        data = resp['result'][data_key]
        df = pd.DataFrame(data, columns=['ts', 'open', 'high', 'low', 'close', 'vwap', 'vol', 'count'])
        df['close'] = df['close'].astype(float)
        return df
    except Exception as e:
        print(f"Error fetching {pair}: {e}")
        return None

def analyze_assets():
    final_report = "🛡️ DOMI SNIPER813PRO SCAN 🛡️\n"
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
        
        asset_msg = f"\n-- {name} (${price:,.4f}) --\n"
        found_signal = False

        for ma in [20, 50, 100, 200]:
            ma_val = df[f'ma{ma}'].iloc[-1]
            diff = ((price - ma_val) / ma_val) * 100
            
            # Logic: If price is within 0.75% of MA, alert the cross anticipation
            if abs(diff) < 0.75:
                direction = "🔥 BULLISH" if momentum > 0 else "🧊 BEARISH"
                asset_msg += f"⚠️ {ma}MA Cross Incoming ({diff:.2f}%) | Momentum: {direction}\n"
                found_signal = True
                hits += 1
        
        if found_signal:
            final_report += asset_msg
            
    if hits == 0:
        return "DOMI Status: Markets scanned. All assets stable within MA ranges."
    return final_report

def send_telegram(message):
    token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    if not token or not chat_id:
        print("Missing Telegram Config.")
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, data={'chat_id': chat_id, 'text': message})

if __name__ == "__main__":
    print("DOMI STARTING SCAN...")
    report = analyze_assets()
    send_telegram(report)
    print("SCAN COMPLETE.")
