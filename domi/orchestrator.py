"""
DOMI - Master Orchestrator
Run: python domi/orchestrator.py --mode scan
     python domi/orchestrator.py --mode briefing
"""

import os
import sys
import json
import argparse
import requests
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from domi.kraken_fetcher       import fetch_all_pairs
from domi.forexfactory_scraper import fetch_forexfactory_events, check_news_window, format_upcoming_events
from domi.signal_engine        import run_scan, Signal
from domi.telegram_worker      import blast_signal, send_domi_briefing
from domi.receipts_engine      import log_signal, check_outcomes

GEMINI_MODEL   = "gemini-2.0-flash"
GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    + GEMINI_MODEL + ":generateContent"
)

DOMI_VOICE = (
    "You are DOMI, the AI market intelligence core of SNIPER813PRO by 2much813. "
    "Voice: direct, high-conviction, no hedging. The data speaks. "
    "Max 3 sentences. No bullet points."
)


def call_gemini(prompt: str) -> str:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return ""
    try:
        resp = requests.post(
            GEMINI_API_URL,
            headers={"Content-Type": "application/json"},
            params={"key": api_key},
            json={
                "system_instruction": {"parts": [{"text": DOMI_VOICE}]},
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": 200, "temperature": 0.7},
            },
            timeout=15
        )
        resp.raise_for_status()
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        print(f"[GEMINI ERROR] {e}")
        return ""


def build_signal_prompt(sig) -> str:
    passed = [k for k, v in sig.checks.items() if v]
    failed = [k for k, v in sig.checks.items() if not v]
    return (
        f"Signal: {sig.pair} {sig.direction} | Score {sig.score}/6\n"
        f"Price: {sig.price} | EMA200: {sig.ema200}\n"
        f"EMA9: {sig.ema9} | EMA20: {sig.ema20}\n"
        f"KC Upper: {sig.keltner_upper} | KC Lower: {sig.keltner_lower}\n"
        f"Stoch K: {sig.stoch_k} | RSI: {sig.rsi}\n"
        f"Passed: {', '.join(passed)}\n"
        f"Failed: {', '.join(failed) if failed else 'None'}\n\n"
        "Write 2-3 sentence signal analysis in DOMI voice. No bullets."
    )


def build_briefing_prompt(signals: list, timestamp: str, events_text: str = "") -> str:
    top = signals[:5] if signals else []
    summary = "\n".join(
        [f"- {s.pair}: {s.direction} | Score {s.score}/6 | ${s.price}" for s in top]
    ) or "No qualifying signals."
    return (
        f"DOMI scan complete. {timestamp}\n\n"
        f"Top signals:\n{summary}\n\n"
        f"Upcoming events:\n{events_text or 'None.'}\n\n"
        "Write 4-5 sentence morning briefing in DOMI voice. "
        "End with: The Dojo already saw this coming. Tap in to stay ahead."
    )


def load_config() -> dict:
    cfg_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "config", "watchlist.json"
    )
    with open(cfg_path) as f:
        return json.load(f)


def run_scan_mode(cfg: dict):
    print(f"\n{'='*50}")
    print(f"[DOMI] SCAN MODE | {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*50}\n")

    # ForexFactory check
    print("[DOMI] Checking ForexFactory...")
    ff_events  = fetch_forexfactory_events(cfg)
    news_check = check_news_window(ff_events, cfg)
    print(f"[FF] {news_check['reason']}")

    if news_check["kill"]:
        print("[DOMI] High-impact event imminent. Killing scan.")
        return

    # Fetch + score
    print("\n[DOMI] Fetching Kraken pairs...")
    market_data  = fetch_all_pairs(cfg["kraken_pairs"], timeframe=cfg["primary_tf"])

    if not market_data:
        print("[DOMI] No market data. Aborting.")
        return

    signals      = run_scan(market_data, cfg)
    gold_signals = [s for s in signals if s.grade == "GOLD"]
    print(f"\n[DOMI] Gold signals: {len(gold_signals)}")

    # Blast Gold signals + log for receipts
    news_flag = f"\n\nNews Flag: {news_check['reason']}" if news_check["flag"] else ""
    for sig in gold_signals:
        print(f"\n[DOMI] Analyzing {sig.pair}...")
        analysis = call_gemini(build_signal_prompt(sig)) + news_flag
        print(f"[GEMINI] {analysis[:80]}...")
        blast_signal(sig, analysis)
        log_signal(sig.pair, sig.direction, sig.price, sig.score)

    if not gold_signals:
        print("[DOMI] No Gold signals this scan. Staying sharp.")

    # Always check previous signal outcomes
    print("\n[DOMI] Checking signal outcomes...")
    check_outcomes()


def run_briefing_mode(cfg: dict):
    print(f"\n{'='*50}")
    print(f"[DOMI] BRIEFING MODE | {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*50}\n")

    ff_events   = fetch_forexfactory_events(cfg)
    events_text = format_upcoming_events(ff_events)
    market_data = fetch_all_pairs(cfg["kraken_pairs"], timeframe=cfg["primary_tf"])
    signals     = run_scan(market_data, cfg) if market_data else []
    timestamp   = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    briefing = call_gemini(build_briefing_prompt(signals, timestamp, events_text))
    if briefing:
        send_domi_briefing(briefing)
    else:
        send_domi_briefing(f"[{timestamp}] DOMI scan complete. {len(signals)} signals queued. Stay sharp.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DOMI Orchestrator")
    parser.add_argument("--mode", choices=["scan", "briefing"], default="scan")
    args = parser.parse_args()
    cfg = load_config()
    if args.mode == "scan":
        run_scan_mode(cfg)
    elif args.mode == "briefing":
        run_briefing_mode(cfg)
