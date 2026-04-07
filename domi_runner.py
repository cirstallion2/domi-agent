import os
import requests
import pandas as pd
import numpy as np

WATCHLIST = {"BTC": "XXBTZUSD", "XRP": "XRPUSD", "XLM": "XLMUSD", "ZBCN": "ZBCNUSD", "JASMY": "JASMYUSD"}

def get_kraken_data(pair):
    url = f"https://api.kraken.com/0/public/OHLC?pair={pair}&interval=60"
    try:
        resp = requests.get(url).json()
        data_key = list(resp['result'].keys())[0]
        df = pd.DataFrame(resp['result'][data_key], columns=['ts', 'open', 'high', 'low', 'close', 'vwap', 'vol', 'count'])
        df['close'] = df['close'].astype(float)
        return df
    except: return None

def analyze_assets():
    report = "🦅 SNIPER813PRO | CROSSOVER RADAR 🦅\n"
    report += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    found = False
    
    mas = [20, 50, 100, 200]

    for name, ticker in WATCHLIST.items():
        df = get_kraken_data(ticker)
        if df is None: continue
        
        # Calculate all MA levels
        for m in mas:
            df[f'ma{m}'] = df['close'].rolling(m).mean()
        
        price = df['close'].iloc[-1]
        
        # Check every combination (20vs50, 50vs200, etc.)
        for i in range(len(mas)):
            for j in range(i + 1, len(mas)):
                ma_fast = mas[i]
                ma_slow = mas[j]
                
                val_fast = df[f'ma{ma_fast}'].iloc[-1]
                val_slow = df[f'ma{ma_slow}'].iloc[-1]
                
                # Check for "The Squeeze" (within 0.5% of each other)
                diff = abs(val_fast - val_slow) / val_slow * 100
                
                if diff < 0.5:
                    found = True
                    # Determine Trend
                    trend = "🚀 BULLISH CHARGE" if val_fast > val_slow else "💀 BEARISH DROP"
                    
                    report += f"💎 ASSET: {name}\n"
                    report += f"⚔️ CROSS: {ma_fast}MA x {ma_slow}MA\n"
                    report += f"🎯 STATUS: {trend}\n"
                    report += f"💰 PRICE: ${price:,.4f}\n"
                    report += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        
    return report if found else None

def send_telegram(message):
    if not message: return
    token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                  data={'chat_id': chat_id, 'text': message})

if __name__ == "__main__":
    print("SNIPER813PRO SCANNING...")
    output = analyze_assets()
    send_telegram(output)
