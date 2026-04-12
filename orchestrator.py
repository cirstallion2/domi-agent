"""
DOMI — Layer 2: Reasoning (Master Orchestrator)
orchestrator.py

The Brain. Coordinates all workers:
  1. Calls kraken_fetcher → gets market data
  2. Calls signal_engine  → scores signals
  3. Calls Gemini API     → adds AI analysis in 2much813 voice
  4. Calls telegram_worker → blasts Gold signals

Run modes:
  python -m domi.orchestrator --mode scan      (hourly scan)
  python -m domi.orchestrator --mode briefing  (morning/evening briefing)
"""

import os
import json
import argparse
import requests
from datetime import datetime

from domi.kraken_fetcher       import fetch_all_pairs
from domi.yahoo_fetcher        import fetch_all_yahoo
from domi.forexfactory_scraper import fetch_forexfactory_events, check_news_window, format_upcoming_events
from domi.signal_engine        import run_scan, Signal
from domi.telegram_worker      import blast_signal, send_domi_briefing

# ── Gemini Config ──────────────────────────────────────────────────────────
GEMINI_MODEL   = "gemini-2.0-flash"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

DOMI_SYSTEM_VOICE = """
You are DOMI — the AI market intelligence core of SNIPER813PRO, 
the Serverless Quantitative Desk run by 2much813.

Your voice is:
- Direct and high-conviction. No hedging. No "maybe." The data speaks.
- Technical but readable. You translate complexity into edge.
- Short and punchy. Max 3 sentences per analysis.
- You don't "think" the market will move. The setup says it's moving.

You are the Sniper in the Dojo. Retail guesses. You front-run the rotation.
"""


def call_gemini(prompt: str) -> str:
    """Call Gemini Flash API and return text response."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("[GEMINI] No API key — skipping AI analysis")
        return ""

    headers = {"Content-Type": "application/json"}
    params  = {"key": api_key}

    body = {
        "system_instruction": {
            "parts": [{"text": DOMI_SYSTEM_VOICE}]
        },
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "maxOutputTokens": 200,
            "temperature": 0.7,
        }
    }

    try:
        resp = requests.post(GEMINI_API_URL, headers=headers, params=params, json=body, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return text.strip()
    except Exception as e:
        print(f"[GEMINI ERROR] {e}")
        return ""


def build_signal_prompt(sig: Signal) -> str:
    checks_passed = [k for k, v in sig.checks.items() if v]
    checks_failed = [k for k, v in sig.checks.items() if not v]

    return f"""
Signal detected on {sig.pair}.

Direction: {sig.direction}
Score: {sig.score}/6
Price: {sig.price}
EMA 200: {sig.ema200}
EMA 9: {sig.ema9} | EMA 20: {sig.ema20}
Keltner Upper: {sig.keltner_upper} | Lower: {sig.keltner_lower}
Stochastic K: {sig.stoch_k}
RSI: {sig.rsi}

Confirmations passed: {', '.join(checks_passed)}
Confirmations failed: {', '.join(checks_failed) if checks_failed else 'None'}

Write a 2-3 sentence signal analysis in the DOMI voice. 
State what the setup is saying, why it's valid, and what to watch.
Do not use bullet points. Write as flowing sentences.
""".strip()


def build_briefing_prompt(signals: list[Signal], timestamp: str) -> str:
    top_signals = signals[:5] if signals else []
    signal_summary = "\n".join([
        f"- {s.pair}: {s.direction} | Score {s.score}/6 | Price {s.price}"
        for s in top_signals
    ]) or "No qualifying signals at this time."

    return f"""
DOMI market scan complete. Time: {timestamp}

Top signals from the SNIPER813PRO Goalden Setup scan:
{signal_summary}

Write a 4-5 sentence morning briefing in the DOMI voice for the 2much813 Telegram channel.
Cover: what the market is doing overall, the top opportunity, and a sharp CTA ending with:
"The Dojo already saw this coming. Tap in to stay ahead."
Do not use bullet points.
""".strip()


def run_scan_mode(cfg: dict):
    """Hourly scan: ForexFactory check → fetch → score → analyze → blast Gold signals."""
    print(f"\n{'='*50}")
    print(f"[DOMI] SCAN MODE | {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*50}\n")

    # Step 0: ForexFactory news window check
    print("[DOMI] Checking ForexFactory news calendar...")
    ff_events  = fetch_forexfactory_events(cfg)
    news_check = check_news_window(ff_events, cfg)
    print(f"[FF] {news_check['reason']}")

    if news_check["kill"]:
        print("[DOMI] High-impact event imminent. Killing scan to protect capital.")
        return

    # Step 1: Fetch market data -- Kraken + Yahoo
    print("\n[DOMI] Fetching Kraken pairs...")
    kraken_data = fetch_all_pairs(cfg["kraken_pairs"], timeframe=cfg["primary_tf"])

    print("\n[DOMI] Fetching Yahoo Finance assets...")
    yahoo_data  = fetch_all_yahoo(cfg, timeframe=cfg["primary_tf"])

    market_data = {**kraken_data, **yahoo_data}

    if not market_data:
        print("[DOMI] No market data retrieved. Aborting.")
        return

    # Step 2: Score signals
    signals      = run_scan(market_data, cfg)
    gold_signals = [s for s in signals if s.grade == "GOLD"]

    print(f"\n[DOMI] Gold signals: {len(gold_signals)}")

    if not gold_signals:
        print("[DOMI] No Gold signals this scan. Staying sharp.")
        return

    # Step 3 + 4: Gemini analysis → Telegram blast
    news_flag = f"\n\n⚠️ *News Flag:* {news_check['reason']}" if news_check["flag"] else ""

    for sig in gold_signals:
        print(f"\n[DOMI] Analyzing {sig.pair}...")
        prompt   = build_signal_prompt(sig)
        analysis = call_gemini(prompt) + news_flag
        print(f"[GEMINI] {analysis[:100]}...")
        blast_signal(sig, analysis)


def run_briefing_mode(cfg: dict):
    """Morning/evening briefing: scan + ForexFactory events + write briefing + send."""
    print(f"\n{'='*50}")
    print(f"[DOMI] BRIEFING MODE | {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*50}\n")

    ff_events   = fetch_forexfactory_events(cfg)
    events_text = format_upcoming_events(ff_events)

    kraken_data = fetch_all_pairs(cfg["kraken_pairs"][:12], timeframe=cfg["primary_tf"])
    yahoo_data  = fetch_all_yahoo(cfg, timeframe=cfg["primary_tf"])
    market_data = {**kraken_data, **yahoo_data}
    signals     = run_scan(market_data, cfg) if market_data else []
    timestamp   = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    prompt   = build_briefing_prompt(signals, timestamp) + f"\n\nUpcoming high-impact events:\n{events_text}"
    briefing = call_gemini(prompt)

    if briefing:
        send_domi_briefing(briefing)
    else:
        send_domi_briefing(f"[{timestamp}] DOMI scan complete. {len(signals)} signals in the queue. Stay sharp.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DOMI Orchestrator")
    parser.add_argument("--mode", choices=["scan", "briefing"], default="scan")
    args = parser.parse_args()

    with open("config/watchlist.json") as f:
        cfg = json.load(f)

    if args.mode == "scan":
        run_scan_mode(cfg)
    elif args.mode == "briefing":
        run_briefing_mode(cfg)
