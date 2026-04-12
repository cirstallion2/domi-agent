"""
DOMI - Phase 4: Receipts Engine
receipts_engine.py

Every Gold signal DOMI fires gets logged with entry price + timestamp.
24 hours later this script checks the outcome and posts proof.

Flow:
  Signal fires -> log_signal() saves to signals_log.json
  24h later    -> check_outcomes() runs, compares price
  Win (>2%)    -> Gemini writes hype post -> blast to Telegram
  Loss (<-2%)  -> logged silently, not posted
  Pending      -> skipped until 24h passes

GitHub Actions workflow: runs every hour alongside the scan.
Storage: signals_log.json committed back to repo via git.
"""

import os
import sys
import json
import requests
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from domi.kraken_fetcher  import fetch_ticker_price
from domi.telegram_worker import send_telegram

LOG_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "signals_log.json"
)

WIN_THRESHOLD  =  0.02   # +2% = win
LOSS_THRESHOLD = -0.02   # -2% = loss
CHECK_AFTER_HOURS = 24

GEMINI_MODEL   = "gemini-2.0-flash"
GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    + GEMINI_MODEL
    + ":generateContent"
)

RECEIPTS_VOICE = (
    "You are DOMI, the AI core of SNIPER813PRO by 2much813. "
    "Write a short, high-energy proof post for Telegram celebrating a winning trade signal. "
    "Be direct, confident, and use the win as social proof. "
    "End with a CTA to join The Dojo. Max 4 sentences. No bullet points."
)


def load_log() -> list:
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    if not os.path.exists(LOG_FILE):
        return []
    try:
        with open(LOG_FILE) as f:
            return json.load(f)
    except Exception:
        return []


def save_log(log: list):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "w") as f:
        json.dump(log, f, indent=2)


def log_signal(pair: str, direction: str, entry_price: float, score: int):
    """Called by orchestrator when a Gold signal fires."""
    log = load_log()

    entry = {
        "id":          f"{pair}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}",
        "pair":        pair,
        "direction":   direction,
        "entry_price": entry_price,
        "score":       score,
        "fired_at":    datetime.now(timezone.utc).isoformat(),
        "status":      "pending",
        "exit_price":  None,
        "pnl_pct":     None,
        "checked_at":  None,
    }

    log.append(entry)
    save_log(log)
    print(f"[RECEIPTS] Logged signal: {pair} {direction} @ {entry_price}")


def call_gemini_receipts(prompt: str) -> str:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return ""
    headers = {"Content-Type": "application/json"}
    params  = {"key": api_key}
    body = {
        "system_instruction": {"parts": [{"text": RECEIPTS_VOICE}]},
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 150, "temperature": 0.8},
    }
    try:
        resp = requests.post(GEMINI_API_URL, headers=headers, params=params, json=body, timeout=15)
        resp.raise_for_status()
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        print(f"[GEMINI RECEIPTS ERROR] {e}")
        return ""


def build_win_prompt(entry: dict) -> str:
    direction_word = "long" if entry["direction"] == "LONG" else "short"
    return (
        f"DOMI called a {direction_word} signal on {entry['pair']} "
        f"at ${entry['entry_price']:,.4f}. "
        f"24 hours later the price is ${entry['exit_price']:,.4f}. "
        f"That is a {entry['pnl_pct']*100:.1f}% move in our favor. "
        f"Signal score was {entry['score']}/6 on the Goalden Setup. "
        "Write the win post now."
    )


def format_receipts_message(entry: dict, hype_text: str) -> str:
    direction_emoji = "🟢" if entry["direction"] == "LONG" else "🔴"
    pnl = entry["pnl_pct"] * 100

    return (
        f"🧾 *RECEIPTS* | SNIPER813PRO\n\n"
        f"{direction_emoji} *{entry['pair']}* {entry['direction']}\n"
        f"Entry:  `${entry['entry_price']:,.4f}`\n"
        f"Exit:   `${entry['exit_price']:,.4f}`\n"
        f"Result: *+{pnl:.1f}%* in 24h\n"
        f"Score:  {entry['score']}/6 Goalden Setup\n\n"
        f"{hype_text}\n\n"
        f"_The Dojo saw this coming._\n"
        f"[Join @sniper813alerts](https://t.me/sniper813alerts)"
    )


def check_outcomes():
    """
    Run every hour. Check all pending signals older than 24h.
    Post wins to Telegram. Log losses silently.
    """
    log = load_log()
    now = datetime.now(timezone.utc)
    updated = False

    for entry in log:
        if entry["status"] != "pending":
            continue

        fired_at = datetime.fromisoformat(entry["fired_at"])
        hours_elapsed = (now - fired_at).total_seconds() / 3600

        if hours_elapsed < CHECK_AFTER_HOURS:
            remaining = CHECK_AFTER_HOURS - hours_elapsed
            print(f"[RECEIPTS] {entry['pair']} | {remaining:.1f}h until check")
            continue

        print(f"[RECEIPTS] Checking outcome: {entry['pair']} {entry['direction']}")

        # Get current price from Kraken
        current_price = fetch_ticker_price(entry["pair"])
        if current_price is None:
            print(f"[RECEIPTS] Could not fetch price for {entry['pair']} - skipping")
            continue

        entry_price = entry["entry_price"]

        if entry["direction"] == "LONG":
            pnl_pct = (current_price - entry_price) / entry_price
        else:
            pnl_pct = (entry_price - current_price) / entry_price

        entry["exit_price"] = current_price
        entry["pnl_pct"]    = round(pnl_pct, 4)
        entry["checked_at"] = now.isoformat()
        updated = True

        print(f"[RECEIPTS] {entry['pair']} | PnL: {pnl_pct*100:.2f}%")

        if pnl_pct >= WIN_THRESHOLD:
            entry["status"] = "win"
            print(f"[RECEIPTS] WIN - generating hype post...")
            hype = call_gemini_receipts(build_win_prompt(entry))
            msg  = format_receipts_message(entry, hype)
            send_telegram(msg)
            print(f"[RECEIPTS] Receipts posted to Telegram")

        elif pnl_pct <= LOSS_THRESHOLD:
            entry["status"] = "loss"
            print(f"[RECEIPTS] LOSS - logged silently")

        else:
            entry["status"] = "breakeven"
            print(f"[RECEIPTS] BREAKEVEN - logged silently")

    if updated:
        save_log(log)

    wins   = len([e for e in log if e["status"] == "win"])
    losses = len([e for e in log if e["status"] == "loss"])
    pending = len([e for e in log if e["status"] == "pending"])
    print(f"\n[RECEIPTS] Record: {wins}W / {losses}L | {pending} pending")


def get_stats() -> dict:
    """Return win rate stats for briefings."""
    log = load_log()
    resolved = [e for e in log if e["status"] in ("win", "loss", "breakeven")]
    wins = [e for e in resolved if e["status"] == "win"]
    if not resolved:
        return {"win_rate": 0, "total": 0, "wins": 0}
    return {
        "win_rate": round(len(wins) / len(resolved) * 100, 1),
        "total":    len(resolved),
        "wins":     len(wins),
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["check", "stats"], default="check")
    args = parser.parse_args()

    if args.mode == "check":
        check_outcomes()
    elif args.mode == "stats":
        stats = get_stats()
        print(f"Win Rate: {stats['win_rate']}% ({stats['wins']}/{stats['total']})")
