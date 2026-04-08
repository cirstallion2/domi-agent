import os
import requests
import pandas as pd
import numpy as np

# --- SYSTEM CONFIG (Pulled from GitHub Secrets) ---
KRAKEN_LINK = os.getenv('KRAKEN_REF_LINK')
TG_TOKEN = os.getenv('TELEGRAM_TOKEN')
TG_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Watchlist: Added Institutional ETFs
WATCHLIST = {
    "BTC": "XXBTZUSD", 
    "XRP": "XRPUSD", 
    "ZBCN": "ZBCNUSD", 
    "JASMY": "JASMYUSD",
    "GBTC": "GBTC",      # Grayscale Bitcoin Trust
    "IBIT": "IBIT"       # iShares Bitcoin Trust
}

def get_kraken_data(pair, interval=60):
    url = f"https://api.kraken.com/0/public/OHLC?pair={pair}&interval={interval}"
    try:
        resp = requests.get(url, timeout=10).json()
        if 'result' not in resp: return None
        data_key = list(resp['result'].keys())[0]
        df = pd.DataFrame(resp['result'][data_key], columns=['ts', 'open', 'high', 'low', 'close', 'vwap', 'vol', 'count'])
        df['close'] = pd.to_numeric(df['close'])
        df['vol'] = pd.to_numeric(df['vol'])
        return df
    except: return None

def analyze_assets():
    header = "⚡️ SNIPER813PRO | DOMI INTELLIGENCE ⚡️\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
    body = ""
    hits = 0

    for name, ticker in WATCHLIST.items():
        df_1h = get_kraken_data(ticker, 60)
        df_4h = get_kraken_data(ticker, 240)
        
        if df_1h is None or df_4h is None or len(df_1h) < 50: continue
        
        try:
            # Indicator Logic: MA Alignment
            df_1h['ma20'] = df_1h['close'].rolling(20).mean()
            df_4h['ma50'] = df_4h['close'].rolling(50).mean()
            
            price = df_1h['close'].iloc[-1]
            avg_vol = df_1h['vol'].rolling(20).mean().iloc[-1]
            curr_vol = df_1h['vol'].iloc[-1]
            
            # THE SNIPER813PRO FILTERS
            ma_dist = abs(((price - df_1h['ma20'].iloc[-1]) / df_1h['ma20'].iloc[-1]) * 100)
            true_north = "BULLISH" if price > df_4h['ma50'].iloc[-1] else "BEARISH"
            vol_spike = curr_vol > (avg_vol * 1.3)
            
            # Logic: Signal triggers if price is near MA and volume confirms the move
            if ma_dist < 1.0 and vol_spike:
                hits += 1
                status = "🟢 SNIPER LONG" if true_north == "BULLISH" else "🔴 SNIPER SHORT"
                sl = price * 0.98 if "LONG" in status else price * 1.02
                
                # Check if asset is an ETF for custom hype
                asset_type = "🏛️ INSTITUTIONAL ETF" if name in ["GBTC", "IBIT"] else "💎 CRYPTO ASSET"
                
                body += f"{asset_type}: {name}\n"
                body += f"🎯 ACTION: {status}\n"
                body += f"🔥 VOL SURGE: {curr_vol/avg_vol:.1f}x AVG\n"
                body += f"🌍 TRUE NORTH: {true_north}\n"
                body += f"💰 PRICE: ${price:,.2f}\n"
                body += f"🚫 STOP: ${sl:,.2f}\n"
                body += f"🔗 ENTRY: {KRAKEN_LINK}\n"
                body += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        except Exception: continue
            
    return header + body if hits > 0 else None

def send_telegram(message):
    if not message or not TG_TOKEN: return
    requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                  data={'chat_id': TG_CHAT_ID, 'text': message})

if __name__ == "__main__":
    output = analyze_assets()
    send_telegram(output)
