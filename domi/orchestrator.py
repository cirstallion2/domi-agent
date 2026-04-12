"""
DOMI - Layer 2: Reasoning (Master Orchestrator)
orchestrator.py

Run modes:
  python domi/orchestrator.py --mode scan
  python domi/orchestrator.py --mode briefing
"""

import os
import sys
import json
import argparse
import requests
from datetime import datetime

# Ensure repo root is on path when called as a script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from domi.kraken_fetcher       import fetch_all_pairs
from domi.yahoo_fetcher        import fetch_all_yahoo
from domi.forexfactory_scraper import fetch_forexfactory_events, check_news_window, format_upcoming_events
from domi.signal_engine        import run_scan, Signal
from domi.telegram_worker      import blast_signal, send_domi_briefing

GEMINI_MODEL   = "gemini-2.0-flash"
GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    + GEMINI_MODEL
    + ":generateContent"
)

DOMI_SYSTEM_VOICE = (
    "You are DOMI, the AI market intelligence core of SNIPER813PRO, "
    "the Serverless Quantitative Desk run by 2much813. "
    "Your voice is direct and high-conviction. No hedging. No maybe. The data speaks. "
    "Technical but readable. Short and punchy. Max 3 sentences per analysis. "
    "You do not think the market will move. The setup says it is moving. "
    "You are the Sniper in the Dojo. Retail guesses. You front-run the rotation."
)


def call_gemini(prompt: str) -> str:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("[GEMINI] No API key - skipping AI analysis")
        return ""

    headers = {"Content-Type": "application/json"}
    params  = {"key": api_key}
    body = {
        "system_instruction": {"parts": [{"text": DOMI_SYSTEM_VOICE}]},
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 200, "temperature": 0.7},
    }

    try:
        resp = requests.post(GEMINI_API_URL, headers=headers, params=params, json=body, timeout=15)
        resp.raise_for_status()
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        print(f"[GEMINI ERROR] {e}")
        return ""


def build_signal_prompt(sig: Signal) -> str:
    passed = [k for k, v in sig.checks.items() if v]
    failed = [k for k, v in sig.checks.items() if not v]
    return (
        f"Signal detected on {sig.pair}.\n"
        f"Direction: {sig.direction}\n"
        f"Score: {sig.score}/6\n"
        f"Price: {sig.price} | EMA200: {sig.ema200}\n"
        f"EMA9: {sig.ema9} | EMA20: {sig.ema20}\n"
        f"KC Upper: {sig.keltner_upper} | KC Lower: {sig.keltner_lower}\n"
        f"Stoch K: {sig.stoch_k} | RSI: {sig.rsi}\n"
        f"Passed: {', '.join(passed)}\n"
        f"Failed: {', '.join(failed) if failed else 'None'}\n\n"
        "Write a 2-3 sentence signal analysis in the DOMI voice. "
        "State what the setup is saying, why it is valid, and what to watch. "
        "No bullet points. Flowing sentences only."
    )


def build_briefing_prompt(signals: list, timestamp: str, events_text: str = "") -> str:
    top = signals[:5] if signals else []
    summary = "\n".join(
        [f"- {s.pair}: {s.direction} | Score {s.score}/6 | Price {s.price}" for s in top]
    ) or "No qualifying signals at this time."

    return (
        f"DOMI market scan complete. Time: {timestamp}\n\n"
        f"Top signals:\n{summary}\n\n"
        f"Upcoming high-impact events:\n{events_text or 'None scheduled.'}\n\n"
        "Write a 4-5 sentence morning briefing in the DOMI voice for the 2much813 Telegram channel. "
        "Cover what the market is doing overall, the top opportunity, and end with: "
        "The Dojo already saw this coming. Tap in to stay ahead. "
        "No bullet points."
    )


def load_config() -> dict:
    cfg_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "watchlist.json")
    with open(cfg_path) as f:
        return json.load(f)


def run_scan_mode(cfg: dict):
    print(f"\n{'='*50}")
    print(f"[DOMI] SCAN MODE | {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*50}\n")

    # Step 0: ForexFactory news check
    print("[DOMI] Checking ForexFactory...")
    ff_events  = fetch_forexfactory_events(cfg)
    news_check = check_news_window(ff_events, cfg)
    print(f"[FF] {news_check['reason']}")

    if news_check["kill"]:
        print("[DOMI] High-impact event imminent. Killing scan.")
        return

    # Step 1: Fetch data
    print("\n[DOMI] Fetching Kraken pairs...")
    kraken_data = fetch_all_pairs(cfg["kraken_pairs"], timeframe=cfg["primary_tf"])

    print("\n[DOMI] Fetching Yahoo assets...")
    yahoo_data  = fetch_all_yahoo(cfg, timeframe=cfg["primary_tf"])

    market_data = {**kraken_data, **yahoo_data}

    if not market_data:
        print("[DOMI] No market data. Aborting.")
        return

    # Step 2: Score signals
    signals      = run_scan(market_data, cfg)
    gold_signals = [s for s in signals if s.grade == "GOLD"]
    print(f"\n[DOMI] Gold signals: {len(gold_signals)}")

    if not gold_signals:
        print("[DOMI] No Gold signals this scan. Staying sharp.")
        return

    # Step 3+4: Gemini analysis + Telegram blast
    news_flag = f"\n\nNews Flag: {news_check['reason']}" if news_check["flag"] else ""

    for sig in gold_signals:
        print(f"\n[DOMI] Analyzing {sig.pair}...")
        analysis = call_gemini(build_signal_prompt(sig)) + news_flag
        print(f"[GEMINI] {analysis[:80]}...")
        blast_signal(sig, analysis)


def run_briefing_mode(cfg: dict):
    print(f"\n{'='*50}")
    print(f"[DOMI] BRIEFING MODE | {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*50}\n")

    ff_events   = fetch_forexfactory_events(cfg)
    events_text = format_upcoming_events(ff_events)

    kraken_data = fetch_all_pairs(cfg["kraken_pairs"][:12], timeframe=cfg["primary_tf"])
    yahoo_data  = fetch_all_yahoo(cfg, timeframe=cfg["primary_tf"])
    market_data = {**kraken_data, **yahoo_data}

    signals   = run_scan(market_data, cfg) if market_data else []
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    briefing = call_gemini(build_briefing_prompt(signals, timestamp, events_text))

    if briefing:
        send_domi_briefing(briefing)
    else:
        send_domi_briefing(
            f"[{timestamp}] DOMI scan complete. "
            f"{len(signals)} signals in the queue. Stay sharp."
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DOMI Orchestrator")
    parser.add_argument("--mode", choices=["scan", "briefing"], default="scan")
    args = parser.parse_args()

    cfg = load_config()

    if args.mode == "scan":
        run_scan_mode(cfg)
    elif args.mode == "briefing":
        run_briefing_mode(cfg)
