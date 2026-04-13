import os
import json
import krakenex
import pandas as pd
from domi.signal_engine import run_scan

def load_config():
    """Load the watchlist and strategy settings."""
    config_path = "config/watchlist.json"
    if not os.path.exists(config_path):
        # Default fallback if file is missing
        return {
            "pairs": ["XRP/USD", "SOL/USD", "BTC/USD"],
            "ema_periods": [9, 20, 200],
            "keltner_period": 20,
            "keltner_atr_mult": 2.0,
            "stoch_k": 14,
            "stoch_d": 3,
            "rsi_period": 14
        }
    with open(config_path, "r") as f:
        return json.load(f)

def run_scan_mode(cfg):
    print("🦅 SNIPER813PRO: Initializing Dojo Scan...")
    
    # Connect to Kraken
    k = krakenex.API()
    k.key = os.getenv("KRAKEN_API_KEY")
    k.secret = os.getenv("KRAKEN_PRIVACY_KEY")

    market_data = {}
    
    # 1. Perception: Fetching 1H Candles
    for pair in cfg.get("pairs", []):
        try:
            # interval 60 = 1 Hour
            res = k.query_public('OHLC', {'pair': pair, 'interval': 60})
            
            if res.get('error'):
                print(f"❌ Kraken Error for {pair}: {res['error']}")
                continue
                
            pair_key = list(res['result'].keys())[0]
            raw_ticks = res['result'][pair_key]
            
            # Convert to DataFrame
            df = pd.DataFrame(raw_ticks, columns=[
                'time', 'open', 'high', 'low', 'close', 'vwap', 'vol', 'count'
            ])
            
            # Clean numeric types
            for col in ['open', 'high', 'low', 'close', 'vol']:
                df[col] = df[col].astype(float)
            
            market_data[pair] = df
            print(f"✅ Data retrieved for {pair}")
            
        except Exception as e:
            print(f"❌ Failed to fetch {pair}: {e}")

    # 2. Reasoning: Pass to Signal Engine
    if market_data:
        signals = run_scan(market_data, cfg)
        # Signals are now scored 0-6 by your signal_engine.py
    else:
        print("⚠️ No market data available to scan.")
