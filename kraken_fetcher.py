
"""
DOMI — Layer 1: Perception
kraken_fetcher.py

Fetches OHLCV data from Kraken for all watchlist pairs.
Returns clean DataFrames ready for signal_engine.py
"""

import os
import time
import json
import krakenex
import pandas as pd
from datetime import datetime

# ── Kraken interval map (minutes) ──────────────────────────────────────────
TF_MAP = {"1h": 60, "4h": 240, "1d": 1440}

def get_client():
    api = krakenex.API()
    api.key    = os.environ["KRAKEN_API_KEY"]
    api.secret = os.environ["KRAKEN_PRIVACY_KEY"]
    return api

def fetch_ohlcv(api: krakenex.API, pair: str, timeframe: str = "1h", limit: int = 300) -> pd.DataFrame | None:
    """
    Fetch OHLCV candles for a single pair/timeframe.
    Returns DataFrame with columns: open, high, low, close, volume
    Returns None on error.
    """
    interval = TF_MAP.get(timeframe, 60)

    try:
        resp = api.query_public("OHLC", {"pair": pair, "interval": interval})

        if resp.get("error"):
            print(f"[KRAKEN ERROR] {pair} {timeframe}: {resp['error']}")
            return None

        # Kraken returns pair name as key (sometimes altered), grab first key
        data_key = [k for k in resp["result"] if k != "last"][0]
        raw = resp["result"][data_key]

        df = pd.DataFrame(raw, columns=[
            "time", "open", "high", "low", "close", "vwap", "volume", "count"
        ])
        df = df[["time", "open", "high", "low", "close", "volume"]].copy()
        df[["open","high","low","close","volume"]] = df[["open","high","low","close","volume"]].astype(float)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        df.set_index("time", inplace=True)

        return df.tail(limit)

    except Exception as e:
        print(f"[FETCH ERROR] {pair} {timeframe}: {e}")
        return None


def fetch_all_pairs(pairs: list, timeframe: str = "1h") -> dict:
    """
    Fetch OHLCV for all pairs in watchlist.
    Returns dict: { "XBT/USD": DataFrame, ... }
    Respects Kraken rate limits with sleep.
    """
    api = get_client()
    results = {}

    for pair in pairs:
        df = fetch_ohlcv(api, pair, timeframe)
        if df is not None and len(df) >= 50:
            results[pair] = df
            print(f"[✓] {pair} | {timeframe} | {len(df)} candles")
        else:
            print(f"[✗] {pair} | skipped (insufficient data)")
        time.sleep(0.5)   # Kraken rate limit buffer

    print(f"\n[FETCHER] Loaded {len(results)}/{len(pairs)} pairs")
    return results


def fetch_ticker_price(pair: str) -> float | None:
    """Get current spot price for a single pair."""
    api = get_client()
    try:
        resp = api.query_public("Ticker", {"pair": pair})
        if resp.get("error"):
            return None
        data_key = list(resp["result"].keys())[0]
        return float(resp["result"][data_key]["c"][0])   # last trade price
    except Exception as e:
        print(f"[TICKER ERROR] {pair}: {e}")
        return None


if __name__ == "__main__":
    # Quick smoke test
    with open("config/watchlist.json") as f:
        cfg = json.load(f)

    data = fetch_all_pairs(cfg["pairs"][:3], timeframe="1h")
    for pair, df in data.items():
        print(f"\n{pair}:\n{df.tail(3)}")
