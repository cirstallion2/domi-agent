"""
DOMI - Phase 5: Content-to-Conversion Loop
content_engine.py

Schedule (Medellin time / UTC-5):
  5:00 AM  (10:00 UTC) - Morning market post
  4:00 PM  (21:00 UTC) - Afternoon market post  
  9:00 PM  (02:00 UTC) - Evening market post
  All other runs       - HeyGen video script

Sends to personal Telegram chat for review.
"""

import os
import sys
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

GEMINI_MODEL   = "gemini-1.5-flash"
GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    + GEMINI_MODEL + ":generateContent"
)

PERSONAL_CHAT_ID = os.environ.get("PERSONAL_CHAT_ID", "7419276203")

CONTENT_VOICE = (
    "You are DOMI, the AI content engine of SNIPER813PRO by 2much813. "
    "2much813 is a Market Translator - not a content creator. "
    "Voice: direct, technical, high-conviction. Short punchy sentences. "
    "No fluff. No hedging. You front-run the rotation while retail guesses. "
    "Write for X (Twitter). Hook line first (max 280 chars). "
    "Then 2-3 lines of technical context - what does this mean for price? "
    "End with: The Dojo already saw this coming. Tap in to stay ahead. "
    "Add 3 relevant hashtags at the end only. No hashtags in body."
)

HEYGEN_VOICE = (
    "You are DOMI, script writer for 2much813's HeyGen AI avatar videos. "
    "2much813 is a Market Translator and Sniper in the Dojo. "
    "Write a 60-90 second video script for an AI avatar to read on camera. "
    "Structure: Hook (5 sec) | Context (20 sec) | The Edge/Setup (25 sec) | CTA (10 sec). "
    "Voice: direct, confident, technical but simple enough for retail to follow. "
    "No bullet points in the script - it must flow naturally when spoken aloud. "
    "End CTA: Join the Dojo at sniper813alerts on Telegram. Stay sharp. Stay early."
)

RSS_FEEDS = [
    ("CoinDesk",      "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("CoinTelegraph", "https://cointelegraph.com/rss"),
    ("Decrypt",       "https://decrypt.co/feed"),
    ("Bitcoin Mag",   "https://bitcoinmagazine.com/feed"),
]

# Post times in UTC (Medellin is UTC-5)
POST_HOURS_UTC = [10, 21, 2]   # 5AM, 4PM, 9PM Medellin


def is_post_hour() -> bool:
    """Check if current UTC hour is a content post hour."""
    current_hour = datetime.now(timezone.utc).hour
    return current_hour in POST_HOURS_UTC


def fetch_rss(url: str, source: str, limit: int = 5) -> list:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; DOMI-Agent/1.0)"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        articles = []
        for item in root.findall(".//item")[:limit]:
            title = item.findtext("title", "").strip()
            desc  = item.findtext("description", "").strip()[:300]
            link  = item.findtext("link", "").strip()
            if title:
                articles.append({
                    "title":  title,
                    "body":   desc,
                    "source": source,
                    "url":    link,
                })
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
        time.sleep(2)   # stagger RSS fetches
    print(f"[NEWS] Total: {len(all_articles)} articles")
    return all_articles


def call_gemini(prompt: str, system: str = "", max_tokens: int = 400, temp: float = 0.7) -> str:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("[GEMINI] No API key")
        return ""

    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temp},
    }
    if system:
        body["system_instruction"] = {"parts": [{"text": system}]}

    for attempt in range(4):
        wait = 60 * (attempt + 1)
        try:
            time.sleep(10)   # always pause before calling Gemini
            resp = requests.post(
                GEMINI_API_URL,
                headers={"Content-Type": "application/json"},
                params={"key": api_key},
                json=body,
                timeout=30
            )
            if resp.status_code == 429:
                print(f"[GEMINI] Rate limited. Waiting {wait}s (attempt {attempt+1}/4)...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            print(f"[GEMINI ERROR] attempt {attempt+1}: {e}")
            time.sleep(wait)

    return ""


def pick_top_story(articles: list) -> dict | None:
    if not articles:
        return None

    headlines = "\n".join([
        f"{i+1}. [{a['source']}] {a['title']}"
        for i, a in enumerate(articles)
    ])

    prompt = (
        "You are a crypto market analyst. "
        "Pick the ONE most market-moving story from this list. "
        "Choose based on: macro impact, price action potential, trader relevance. "
        "Reply with ONLY the number. Nothing else.\n\n"
        + headlines
    )

    pick = call_gemini(prompt, max_tokens=5, temp=0.2)
    try:
        idx = int(pick.strip()) - 1
        if 0 <= idx < len(articles):
            print(f"[CONTENT] Top story: {articles[idx]['title'][:70]}...")
            return articles[idx]
    except Exception:
        pass
    return articles[0]


def write_market_post(story: dict) -> str:
    """Write X/Telegram market post in 2much813 voice."""
    prompt = (
        f"News: {story['title']}\n"
        f"Details: {story['body']}\n"
        f"Source: {story['source']}\n\n"
        "Write the 2much813 market post. "
        "Hook first. Then 2-3 lines on what this means for price action. "
        "End: The Dojo already saw this coming. Tap in to stay ahead. "
        "3 hashtags at the end only."
    )
    return call_gemini(prompt, system=CONTENT_VOICE, max_tokens=350, temp=0.8)


def write_heygen_script(story: dict) -> str:
    """Write a 60-90 second HeyGen avatar video script."""
    prompt = (
        f"News hook: {story['title']}\n"
        f"Context: {story['body']}\n\n"
        "Write a 60-90 second HeyGen video script for the 2much813 AI avatar. "
        "Structure: Hook | Market Context | The Trading Edge | CTA to join Dojo. "
        "Written to be spoken naturally on camera. No bullet points."
    )
    return call_gemini(prompt, system=HEYGEN_VOICE, max_tokens=500, temp=0.75)


def send_to_personal(message: str, label: str = "CONTENT DROP") -> bool:
    token = os.environ.get("TELEGRAM_TOKEN", "")
    if not token:
        print("[CONTENT] No Telegram token")
        return False

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    full_msg = f"*DOMI {label}*\n_{timestamp}_\n\n{message}"

    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id":    PERSONAL_CHAT_ID,
                "text":       full_msg,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            },
            timeout=10
        )
        resp.raise_for_status()
        print(f"[CONTENT] Sent to personal chat {PERSONAL_CHAT_ID}")
        return True
    except Exception as e:
        print(f"[CONTENT] Send error: {e}")
        return False


def run_content_engine():
    now_utc = datetime.now(timezone.utc)
    print(f"\n[CONTENT] {now_utc.strftime('%Y-%m-%d %H:%M UTC')}")

    post_mode = is_post_hour()
    mode_label = "MARKET POST" if post_mode else "HEYGEN SCRIPT"
    print(f"[CONTENT] Mode: {mode_label}")

    articles = fetch_crypto_news()
    if not articles:
        print("[CONTENT] No news fetched. Skipping.")
        return

    story = pick_top_story(articles)
    if not story:
        print("[CONTENT] No story selected. Skipping.")
        return

    time.sleep(15)   # breathe before writing

    if post_mode:
        content = write_market_post(story)
        label = "MARKET POST - ready for X"
    else:
        content = write_heygen_script(story)
        label = "HEYGEN SCRIPT - ready for avatar"

    if not content:
        print("[CONTENT] No content generated. Skipping.")
        return

    print(f"\n[CONTENT] Preview:\n{content[:200]}...\n")

    source_line = f"Source: {story['source']} | {story['url']}\n\n"
    send_to_personal(source_line + content, label)


if __name__ == "__main__":
    run_content_engine()
