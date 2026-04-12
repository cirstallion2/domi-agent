"""
DOMI - Layer 1: Perception (TradFi only)
yahoo_fetcher.py

Fetches Gold, Oil, Indices, Forex via yfinance.
60-day window gives 500+ hourly candles for 200 EMA.
"""

import pandas as pd
import json


def fetch_yfinance_ohlcv(ticker: str, period: str = "60d", interval: str = "1h"):
    try:
        import yfinance as yf
        tk = yf.Ticker(ticker)
        df = tk.history(period=period, interval=interval, auto_adjust=True)
        if df.empty:
            return None
        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.columns = ["open", "high", "low", "close", "volume"]
        df.index = pd.to_datetime(df.index, utc=True).tz_localize(None)
        df.index.name = "time"
        return df
    except Exception as e:
        print(f"[YFINANCE ERROR] {ticker}: {e}")
        return None


def fetch_all_yahoo(cfg: dict, timeframe: str = "1h") -> dict:
    """Fetch TradFi assets. Returns dict: { 'XAUUSD': DataFrame, ... }"""
    results = {}
    tradfi = cfg.get("yahoo_tradfi", {})

    if not tradfi:
        return results

    print(f"[TRADFI] Fetching {len(tradfi)} assets (60d)...")
    for display_name, ticker in tradfi.items():
        df = fetch_yfinance_ohlcv(ticker, period="60d", interval="1h")
        if df is not None and len(df) >= 210:
            results[display_name] = df
            print(f"[OK] {display_name} ({ticker}) | {len(df)} candles")
        elif df is not None:
            print(f"[--] {display_name} | only {len(df)} candles (need 210+)")
        else:
            print(f"[--] {display_name} | no data")

    print(f"[TRADFI] Loaded {len(results)} assets")
    return results


def get_yahoo_spot_price(ticker: str) -> float | None:
    try:
        import yfinance as yf
        tk = yf.Ticker(ticker)
        hist = tk.history(period="1d", interval="1m")
        if hist.empty:
            return None
        return float(hist["Close"].iloc[-1])
    except Exception as e:
        print(f"[YFINANCE SPOT ERROR] {ticker}: {e}")
        return None


if __name__ == "__main__":
    with open("config/watchlist.json") as f:
        cfg = json.load(f)
    data = fetch_all_yahoo(cfg)
    for name, df in data.items():
        print(f"{name}: {len(df)} candles")
