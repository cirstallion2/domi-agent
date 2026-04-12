"""
DOMI - Layer 1: Perception (Extended Crypto via CoinGecko)
yahoo_fetcher.py

Replaces Yahoo Finance with CoinGecko public API for extended crypto,
and yfinance with a direct approach for TradFi (futures/forex).

CoinGecko free tier: 30 calls/min - plenty for our watchlist.
No API key required.
"""

import time
import requests
import pandas as pd
import json
from datetime import datetime, timezone

COINGECKO_BASE = "https://api.coingecko.com/api/v3"

# Map our ticker symbols to CoinGecko coin IDs
COINGECKO_ID_MAP = {
    "ZEC-USD":     "zcash",
    "XMR-USD":     "monero",
    "ZBCN-USD":    "zbcn",
    "VIRTUAL-USD": "virtual-protocol",
    "XCN-USD":     "chain-2",
    "PHNIX-USD":   "phoenixchain",
    "AIXBT-USD":   "aixbt-by-virtuals",
    "KAS-USD":     "kaspa",
    "CRO-USD":     "crypto-com-chain",
    "ZEN-USD":     "horizen",
    "HNT-USD":     "helium",
    "GALA-USD":    "gala",
    "SUI-USD":     "sui",
    "HBAR-USD":    "hedera-hashgraph",
    "FLR-USD":     "flare-networks",
    "ONDO-USD":    "ondo-finance",
    "XDC-USD":     "xdce-crowd-sale",
    "ATH-USD":     "aethir",
}

# TradFi via stablecoins proxy or skip gracefully
TRADFI_ASSETS = {
    "XAUUSD": "gold",
    "OIL":    "crude-oil",
    "US30":   "dow-jones",
    "SP500":  "sp-500",
    "NQ":     "nasdaq-100",
    "IWM":    "russell-2000",
    "EURUSD": "eur-usd",
    "USDJPY": "usd-jpy",
}


def fetch_coingecko_ohlcv(coin_id: str, days: int = 7) -> pd.DataFrame | None:
    """
    Fetch hourly OHLCV from CoinGecko for a single coin.
    CoinGecko returns hourly data for queries up to 90 days.
    """
    url = f"{COINGECKO_BASE}/coins/{coin_id}/ohlc"
    params = {"vs_currency": "usd", "days": str(days)}

    try:
        resp = requests.get(url, params=params, timeout=10)

        if resp.status_code == 429:
            print(f"[COINGECKO] Rate limited on {coin_id}, waiting 60s...")
            time.sleep(60)
            resp = requests.get(url, params=params, timeout=10)

        resp.raise_for_status()
        raw = resp.json()

        if not raw:
            return None

        df = pd.DataFrame(raw, columns=["time", "open", "high", "low", "close"])
        df["time"] = pd.to_datetime(df["time"], unit="ms")
        df.set_index("time", inplace=True)
        df["volume"] = 0.0   # CoinGecko OHLC endpoint doesn't include volume

        return df

    except Exception as e:
        print(f"[COINGECKO ERROR] {coin_id}: {e}")
        return None


def fetch_all_yahoo(cfg: dict, timeframe: str = "1h") -> dict:
    """
    Fetch extended crypto from CoinGecko.
    TradFi assets (Gold, Oil, Indices, Forex) logged as unavailable
    without a paid data source - skipped gracefully.

    Returns dict: { "ZEC-USD": DataFrame, ... }
    """
    results = {}

    # Extended crypto via CoinGecko
    yahoo_crypto = cfg.get("yahoo_crypto", [])
    print(f"[COINGECKO] Fetching {len(yahoo_crypto)} extended crypto assets...")

    for ticker in yahoo_crypto:
        coin_id = COINGECKO_ID_MAP.get(ticker)
        if not coin_id:
            print(f"[--] {ticker} | no CoinGecko ID mapped")
            continue

        df = fetch_coingecko_ohlcv(coin_id, days=7)
        if df is not None and len(df) >= 20:
            results[ticker] = df
            print(f"[OK] {ticker} ({coin_id}) | {len(df)} candles")
        else:
            print(f"[--] {ticker} | skipped")

        time.sleep(2)   # CoinGecko rate limit: 30 req/min on free tier

    # TradFi - log as skipped (requires paid data source)
    tradfi = cfg.get("yahoo_tradfi", {})
    if tradfi:
        print(f"\n[TRADFI] {len(tradfi)} assets require paid data source (Alpha Vantage/Polygon).")
        print("[TRADFI] Skipping gracefully - Kraken crypto scan proceeding.")

    print(f"\n[COINGECKO FETCHER] Loaded {len(results)} extended crypto assets")
    return results


def get_yahoo_spot_price(ticker: str) -> float | None:
    """Get current price from CoinGecko for a ticker."""
    coin_id = COINGECKO_ID_MAP.get(ticker)
    if not coin_id:
        return None

    try:
        url = f"{COINGECKO_BASE}/simple/price"
        params = {"ids": coin_id, "vs_currencies": "usd"}
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return float(data[coin_id]["usd"])
    except Exception as e:
        print(f"[COINGECKO SPOT ERROR] {ticker}: {e}")
        return None


if __name__ == "__main__":
    with open("config/watchlist.json") as f:
        cfg = json.load(f)

    data = fetch_all_yahoo(cfg, timeframe="1h")
    for name, df in list(data.items())[:3]:
        print(f"\n{name}:\n{df.tail(3)}")
