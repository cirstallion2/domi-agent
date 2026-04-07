import os
import requests
import pandas as pd
import numpy as np

WATCHLIST = {"BTC": "XXBTZUSD", "XRP": "XRPUSD", "XLM": "XLMUSD", "ZBCN": "ZBCNUSD", "JASMY": "JASMYUSD"}

def get_kraken_data(pair, interval=60):
    url = f"https://api.kraken.com/0/public/OHLC?pair={pair}&interval={interval}"
    try:
        resp = requests.get(url).json()
        data_key = list(resp['result'].keys())[0]
        df = pd.DataFrame(resp['result'][data_key], columns=['ts', 'open', 'high', 'low', 'close', 'vwap', 'vol', 'count'])
        df['close'] = df['close'].astype(float)
        df['vol'] = df['vol'].astype(float)
        return df
    except: return None

def analyze_assets():
    header = "🦅 SNIPER813PRO | TRINITY COMMAND 🦅\n"
    header += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    body = ""
    hits = 0

    for name, ticker in WATCHLIST.items():
        df_1h = get_kraken_data(ticker, 60)   # 1-Hour for Execution
        df_4h = get_kraken_data(ticker, 240)  # 4-Hour for True North
        if df_1h is None or df_4h is None: continue
        
        # 1H Metrics
        df_1h['ma20'] = df_1h['close'].rolling(20).mean()
        df_1h['ma50'] = df_1h['close'].rolling(50).mean()
        avg_vol = df_1h['vol'].rolling(20).mean().iloc[-1]
        curr_vol = df_1h['vol'].iloc[-1]
        
        # 4H True North (Is the big trend with us?)
        df_4h['ma50'] = df_4h['close'].rolling(50).mean()
        true_north = "BULLISH" if df_4h['close'].iloc[-1] > df_4h['ma50'].iloc[-1] else "BEARISH"
        
        price = df_1h['close'].iloc[-1]
        momentum = "UP" if price > df_1h['close'].iloc[-2] else "DOWN"
        
        # LOGIC: 1. Price near MA | 2. Volume Spike (>1.5x) | 3. Aligned with 4H Trend
        for ma in [20, 50]:
            ma_val = df_1h[f'ma{ma}'].iloc[-1]
            diff = abs(((price - ma_val) / ma_val) * 100)
            
            if diff < 0.8: # Near the cross
                vol_surge = curr_vol > (avg_vol * 1.5)
                trend_align = (momentum == "UP" and true_north == "BULLISH") or (momentum == "DOWN" and true_north == "BEARISH")
                
                if vol_surge and trend_align:
                    hits += 1
                    status = "🟢 SNIPER LONG" if momentum == "UP" else "🔴 SNIPER SHORT"
                    
                    # KILL SWITCH: 2% Stop Loss logic
                    stop_loss = price * 0.98 if momentum == "UP" else price * 1.02
                    
                    body += f"💎 ASSET: {name}\n"
                    body += f"🎯 ACTION: {status}\n"
                    body += f"🔥 VOL SURGE: {curr_vol/avg_vol:.1f}x AVG\n"
                    body += f"🌍 TRUE NORTH: {true_north} (4H)\n"
                    body += f"💰 PRICE: ${price:,.4f}\n"
                    body += f"🚫 KILL SWITCH: ${stop_loss:,.4f}\n"
                    body += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        
    return header + body if hits > 0 else None

def send_telegram(message):
    if not message: return
    token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={'chat_id': chat_id, 'text': message})

if __name__ == "__main__":
    output = analyze_assets()
    send_telegram(output)
