import os
import requests
import pandas as pd
import numpy as np

# --- SYSTEM CONFIG (GitHub Secrets) ---
KRAKEN_LINK = os.getenv('KRAKEN_REF_LINK')
TG_TOKEN = os.getenv('TELEGRAM_TOKEN')
TG_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Watchlist: Added Wall Street ETFs
WATCHLIST = {
    "BTC": "XXBTZUSD", 
    "XRP": "XRPUSD", 
    "ZBCN": "ZBCNUSD", 
    "JASMY": "JASMYUSD",
    "GBTC": "GBTC",      # Grayscale Bitcoin Trust
    "IBIT": "IBIT"       # iShares Bitcoin Trust (BlackRock)
}

def get_kraken_data(pair, interval=60):
    # Kraken API handles xStocks/ETFs via the same OHLC endpoint
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
            # Indicator Logic
            df_1h['ma20'] = df_1h['close'].rolling(20).mean()
            df_4h['ma50'] = df_4h['close'].rolling(50).mean()
            
            price = df_1h['close'].iloc[-1]
            avg_vol = df_1h['vol'].rolling(20).mean().iloc[-1]
            curr_vol = df_1h['vol'].iloc[-1]
            
            # FILTERS: Proximity to MA + Volume Confirmation
            ma_dist = abs(((price - df_1h['ma20'].iloc[-1]) / df_1h['ma20'].iloc[-1]) * 100)
            true_north = "BULLISH" if price > df_4h['ma50'].iloc[-1] else "BEARISH"
            vol_spike = curr_vol > (avg_vol * 1.3)
            
            if ma_dist < 1.0 and vol_spike:
                hits += 1
                status = "🟢 SNIPER LONG" if true_north == "BULLISH" else "🔴 SNIPER SHORT"
                sl = price * 0.98 if "LONG" in status else price * 1.02
                
                # Custom branding for ETFs
                label = "🏛️ INSTITUTIONAL" if name in ["GBTC", "IBIT"] else "💎 CRYPTO"
                
                body += f"{label}: {name}\n"
                body += f"🎯 ACTION: {status}\n"
                body += f"🔥 VOL: {curr_vol/avg_vol:.1f}x AVG\n"
                body += f"🌍 TREND: {true_north}\n"
                body += f"💰 PRICE: ${price:,.2f}\n"
                body += f"🚫 EXIT: ${sl:,.2f}\n"
                body += f"🔗 {KRAKEN_LINK}\n"
                body += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        except: continue
            
    return header + body if hits > 0 else None

def send_telegram(message):
    if not message or not TG_TOKEN: return
    requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                  data={'chat_id': TG_CHAT_ID, 'text': message})

if __name__ == "__main__":
    output = analyze_assets()
    send_telegram(output)
