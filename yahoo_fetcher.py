"""
DOMI -- Layer 1: Perception (TradFi + Extended Crypto)
yahoo_fetcher.py

Fetches OHLCV data from Yahoo Finance for:
  - Gold (GC=F), Oil (CL=F), Indices (YM=F, ES=F, NQ=F)
  - ETFs (IWM)
  - Forex (EURUSD=X, USDJPY=X)
  - Crypto not on Kraken (ZBCN, KAS, GALA, etc.)

Uses yfinance -- no API key required.
"""

import yfinance as yf
import pandas as pd
import json

INTERVAL_MAP = {
    "1h": "1h",
    "4h": "1h",   # resample from 1h
    "1d": "1d",
}

PERIOD_MAP = {
    "1h": "7d",
    "4h": "60d",
    "1d": "200d",
}


def fetch_yahoo_ohlcv(ticker: str, timeframe: str = "1h", limit: int = 200):
    """
    Fetch OHLCV from Yahoo Finance for a single ticker.
    Returns DataFrame with columns: open, high, low, close, volume
    """
    yf_interval = INTERVAL_MAP.get(timeframe, "1h")
    period = PERIOD_MAP.get(timeframe, "7d")

    try:
        tk = yf.Ticker(ticker)
        df = tk.history(period=period, interval=yf_interval, auto_adjust=True)

        if df.empty:
            print(f"[YAHOO] No data for {ticker}")
            return None

        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.columns = ["open", "high", "low", "close", "volume"]
        df.index = pd.to_datetime(df.index, utc=True).tz_localize(None)
        df.index.name = "time"

        if timeframe == "4h":
            df = df.resample("4h").agg({
                "open":   "first",
                "high":   "max",
                "low":    "min",
                "close":  "last",
                "volume": "sum",
            }).dropna()

        return df.tail(limit)

    except Exception as e:
        print(f"[YAHOO ERROR] {ticker}: {e}")
        return None


def fetch_all_yahoo(cfg: dict, timeframe: str = "1h") -> dict:
    """
    Fetch all Yahoo assets: TradFi + extended crypto.
    Returns unified dict: { "XAUUSD": DataFrame, "ZBCN-USD": DataFrame, ... }
    """
    results = {}

    tradfi = cfg.get("yahoo_tradfi", {})
    for display_name, ticker in tradfi.items():
        df = fetch_yahoo_ohlcv(ticker, timeframe)
        if df is not None and len(df) >= 50:
            results[display_name] = df
            print(f"[OK] {display_name} ({ticker}) | {timeframe} | {len(df)} candles")
        else:
            print(f"[--] {display_name} ({ticker}) | skipped")

    for ticker in cfg.get("yahoo_crypto", []):
        df = fetch_yahoo_ohlcv(ticker, timeframe)
        if df is not None and len(df) >= 50:
            results[ticker] = df
            print(f"[OK] {ticker} | {timeframe} | {len(df)} candles")
        else:
            print(f"[--] {ticker} | skipped")

    print(f"\n[YAHOO FETCHER] Loaded {len(results)} assets")
    return results


def get_yahoo_spot_price(ticker: str) -> float | None:
    """Get current price for any Yahoo ticker."""
    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(period="1d", interval="1m")
        if hist.empty:
            return None
        return float(hist["Close"].iloc[-1])
    except Exception as e:
        print(f"[YAHOO SPOT ERROR] {ticker}: {e}")
        return None


if __name__ == "__main__":
    with open("config/watchlist.json") as f:
        cfg = json.load(f)

    data = fetch_all_yahoo(cfg, timeframe="1h")
    for name, df in list(data.items())[:3]:
        print(f"\n{name}:\n{df.tail(3)}")
