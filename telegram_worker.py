
"""
DOMI — Layer 3: Execution
telegram_worker.py

Formats and sends Gold signals to @sniper813alerts Telegram channel.
Called by orchestrator after Gemini analysis is attached.
"""

import os
import requests
from domi.signal_engine import Signal

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"

GRADE_EMOJI = {
    "GOLD":  "🥇",
    "WATCH": "👀",
    "KILL":  "❌",
}

CHECK_EMOJI = {True: "✅", False: "❌"}


def format_signal_message(sig: Signal, gemini_analysis: str = "") -> str:
    """
    Build the Telegram message for a Gold signal.
    """
    direction_emoji = "🟢 LONG" if sig.direction == "LONG" else "🔴 SHORT"
    grade_emoji = GRADE_EMOJI.get(sig.grade, "")

    checks_block = "\n".join([
        f"  {CHECK_EMOJI[sig.checks['ema200_gate']]}  200 EMA Macro Gate",
        f"  {CHECK_EMOJI[sig.checks['triple_alignment']]}  Triple Alignment (EMA20)",
        f"  {CHECK_EMOJI[sig.checks['keltner_break']]}  Keltner Channel Break",
        f"  {CHECK_EMOJI[sig.checks['ema_cross']]}  EMA 9/20 Cross",
        f"  {CHECK_EMOJI[sig.checks['stochastic']]}  Stochastic Filter",
        f"  {CHECK_EMOJI[sig.checks['rsi']]}  RSI Confirmation",
    ])

    analysis_block = f"\n\n🧠 *DOMI Analysis:*\n{gemini_analysis}" if gemini_analysis else ""

    msg = f"""
{grade_emoji} *SNIPER813PRO SIGNAL* {grade_emoji}

*{sig.pair}* | {direction_emoji}
📊 Score: *{sig.score}/6*

💲 Price:     `{sig.price}`
📈 EMA 200:  `{sig.ema200}`
📈 EMA 9:    `{sig.ema9}`
📈 EMA 20:   `{sig.ema20}`
📉 KC Upper: `{sig.keltner_upper}`
📉 KC Lower: `{sig.keltner_lower}`
〽️ Stoch K:  `{sig.stoch_k}`
💹 RSI:      `{sig.rsi}`

*Confirmation Stack:*
{checks_block}{analysis_block}

⚡️ _This is a signal alert — not financial advice._
_Review before executing. You control the trigger._

🔗 [Join The Dojo](https://t.me/sniper813alerts)
""".strip()

    return msg


def send_telegram(message: str, parse_mode: str = "Markdown") -> bool:
    """Send a message to the configured Telegram channel."""
    token   = os.environ["TELEGRAM_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    url     = TELEGRAM_API.format(token=token)

    payload = {
        "chat_id":    chat_id,
        "text":       message,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        print(f"[TELEGRAM] ✓ Message sent ({len(message)} chars)")
        return True
    except requests.RequestException as e:
        print(f"[TELEGRAM ERROR] {e}")
        return False


def blast_signal(sig: Signal, gemini_analysis: str = "") -> bool:
    """Format and send a signal. Only blasts GOLD grade."""
    if sig.grade != "GOLD":
        print(f"[TELEGRAM] Skipping {sig.pair} — grade {sig.grade}")
        return False

    msg = format_signal_message(sig, gemini_analysis)
    return send_telegram(msg)


def send_domi_briefing(briefing_text: str) -> bool:
    """Send DOMI's morning/evening macro briefing."""
    header = "🦅 *DOMI MORNING BRIEFING*\n_2much813 | Serverless Quantitative Desk_\n\n"
    return send_telegram(header + briefing_text)


if __name__ == "__main__":
    # Smoke test — prints formatted message without sending
    from domi.signal_engine import Signal
    test_sig = Signal(
        pair="XBT/USD", direction="LONG", score=6,
        checks={
            "ema200_gate": True, "triple_alignment": True,
            "keltner_break": True, "ema_cross": True,
            "stochastic": True, "rsi": True
        },
        price=67420.50, ema200=61000.00,
        keltner_upper=67300.00, keltner_lower=63000.00,
        ema9=67100.00, ema20=66500.00,
        stoch_k=22.5, rsi=56.3
    )
    msg = format_signal_message(test_sig, "Breakout confirmed. Volume spike on 1H. 200 EMA slope bullish.")
    print(msg)
