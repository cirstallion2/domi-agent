"""
DOMI - Phase 5: Content-to-Conversion Loop
content_engine.py

ONE Gemini call per run to stay within 10 RPM free tier.
At post hours: outputs market post for X/Telegram
At other hours: outputs HeyGen video script

Post hours (Medellin UTC-5):
  5:00 AM  = 10:00 UTC
  4:00 PM  = 21:00 UTC
  9:00 PM  = 02:00 UTC
"""

import os
import sys
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

GEMINI_MODEL   = "gemini-2.0-flash"
GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    + GEMINI_MODEL + ":generateContent"
)

PERSONAL_CHAT_ID = os.environ.get("PERSONAL_CHAT_ID", "7419276203")
POST_HOURS_UTC   = {10, 21, 2}   # 5AM, 4PM, 9PM Medellin

RSS_FEEDS = [
    ("CoinDesk",      "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("CoinTelegraph", "https://cointelegraph.com/rss"),
    ("Decrypt",       "https://decrypt.co/feed"),
    ("Bitcoin Mag",   "https://bitcoinmagazine.com/feed"),
]


def fetch_rss(url: str, source: str, limit: int = 5) -> list:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; DOMI-Agent/1.0)"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        articles = []
        for item in root.findall(".//item")[:limit]:
            title = item.findtext("title", "").strip()
            desc  = item.findtext("description", "").strip()[:200]
            link  = item.findtext("link", "").strip()
            if title:
                articles.append({"title": title, "body": desc, "source": source, "url": link})
        return articles
    except Exception as e:
        print(f"[RSS ERROR] {source}: {e}")
        return []


def fetch_crypto_news() -> list:
    all_articles = []
    for source, url in RSS_FEEDS:
        articles = fetch_rss(url, source)
        all_articles.extend(articles)
        if articles:
            print(f"[NEWS] {source}: {len(articles)} articles")
        time.sleep(1)
    print(f"[NEWS] Total: {len(all_articles)} articles")
    return all_articles


def call_gemini_once(prompt: str) -> str:
    """Single Gemini call. No retries that burn quota — fail fast and clean."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("[GEMINI] No API key")
        return ""
    try:
        resp = requests.post(
            GEMINI_API_URL,
            headers={"Content-Type": "application/json"},
            params={"key": api_key},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": 500, "temperature": 0.8},
            },
            timeout=30
        )
        if resp.status_code == 429:
            print(f"[GEMINI] Rate limited (429). Will retry next scheduled run.")
            return ""
        resp.raise_for_status()
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        print(f"[GEMINI ERROR] {e}")
        return ""


def build_market_post_prompt(headlines: str) -> str:
    return (
        "You are DOMI, AI content engine for SNIPER813PRO by 2much813.\n"
        "2much813 is a Market Translator. Voice: direct, technical, high-conviction.\n\n"
        f"Top crypto headlines today:\n{headlines}\n\n"
        "Pick the most market-moving story and write ONE X/Twitter post.\n"
        "Format:\n"
        "- Hook line (punchy, max 280 chars)\n"
        "- 2-3 lines of what this means for price action\n"
        "- End with: The Dojo already saw this coming. Tap in to stay ahead.\n"
        "- 3 hashtags at the very end\n"
        "No bullet points. Write as flowing text."
    )


def build_heygen_prompt(headlines: str) -> str:
    return (
        "You are DOMI, script writer for 2much813's HeyGen AI avatar videos.\n"
        "2much813 is the Sniper in the Dojo - a Market Translator.\n\n"
        f"Top crypto headlines today:\n{headlines}\n\n"
        "Pick the most market-moving story and write a 60-90 second video script.\n"
        "Structure (label each section):\n"
        "[HOOK - 5 sec] Attention-grabbing opening line\n"
        "[CONTEXT - 20 sec] What is happening in the market\n"
        "[THE EDGE - 25 sec] What smart money is watching, what the setup looks like\n"
        "[CTA - 10 sec] Join the Dojo at sniper813alerts on Telegram. Stay sharp. Stay early.\n\n"
        "Written to be spoken naturally on camera. No bullet points in the script."
    )


def send_to_personal(content: str, label: str) -> bool:
    token = os.environ.get("TELEGRAM_TOKEN", "")
    if not token:
        print("[CONTENT] No Telegram token")
        return False

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    message   = f"*DOMI | {label}*\n_{timestamp}_\n\n{content}"

    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id":    PERSONAL_CHAT_ID,
                "text":       message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            },
            timeout=10
        )
        resp.raise_for_status()
        print(f"[CONTENT] Sent to {PERSONAL_CHAT_ID}")
        return True
    except Exception as e:
        print(f"[CONTENT] Send error: {e}")
        return False


def run_content_engine():
    now_utc    = datetime.now(timezone.utc)
    post_mode  = now_utc.hour in POST_HOURS_UTC
    mode_label = "MARKET POST" if post_mode else "HEYGEN SCRIPT"

    print(f"\n[CONTENT] {now_utc.strftime('%Y-%m-%d %H:%M UTC')} | Mode: {mode_label}")

    articles = fetch_crypto_news()
    if not articles:
        print("[CONTENT] No news fetched. Skipping.")
        return

    # Build compact headline list for the prompt
    headlines = "\n".join([
        f"- [{a['source']}] {a['title']}"
        for a in articles[:10]
    ])

    # ONE Gemini call
    prompt  = build_market_post_prompt(headlines) if post_mode else build_heygen_prompt(headlines)
    content = call_gemini_once(prompt)

    if not content:
        print("[CONTENT] No content generated.")
        return

    print(f"\n[CONTENT] Preview:\n{content[:300]}...\n")
    send_to_personal(content, mode_label)


if __name__ == "__main__":
    run_content_engine()
