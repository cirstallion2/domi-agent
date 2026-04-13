import os
import json
import krakenex
import pandas as pd
from domi.signal_engine import run_scan
from domi.delivery import send_telegram_signal # We'll build this next

def run_scan_mode(cfg):
    print("🦅 SNIPER813PRO: Starting Market Scan...")
    
    # 1. Connect to Kraken
    k = krakenex.API()
    k.key = os.getenv("KRAKEN_API_KEY")
    k.secret = os.getenv("KRAKEN_PRIVACY_KEY")

    market_data = {}
    pairs = cfg["pairs"] # e.g., ["XRP/USD", "SOL/USD", "BTC/USD"]

    # 2. Perception: Fetch OHLC Data
    for p in pairs:
        try:
            # Fetch 1H intervals (60 mins)
            res = k.query_public('OHLC', {'pair': p, 'interval': 60})
            if not res.get('error'):
                pair_key = list(res['result'].keys())[0]
                raw_data = res['result'][pair_key]
                df = pd.DataFrame(raw_data, columns=['time', 'open', 'high', 'low', 'close', 'vwap', 'vol', 'count'])
                df['close'] = df['close'].astype(float)
                df['high'] = df['high'].astype(float)
                df['low'] = df['low'].astype(float)
                market_data[p] = df
        except Exception as e:
            print(f"❌ Error fetching {p}: {e}")

    # 3. Reasoning: Score Signals
    signals = run_scan(market_data, cfg)

    # 4. Execution: Deliver Gold Signals
    for sig in signals:
        if sig.grade == "GOLD":
            send_telegram_signal(sig) # Blasts to your Elite channel
            log_signal(sig) # Saves to signals_log.json for the 'Receipts' engine

def log_signal(sig):
    log_file = "data/signals_log.json"
    os.makedirs("data", exist_ok=True)
    new_data = {
        "timestamp": str(pd.Timestamp.now()),
        "pair": sig.pair,
        "direction": sig.direction,
        "price": sig.price,
        "score": sig.score
    }
    
    # Load existing or create new
    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            data = json.load(f)
    else:
        data = []
    
    data.append(new_data)
    with open(log_file, "w") as f:
        json.dump(data, f, indent=4)
