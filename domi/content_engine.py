"""
DOMI - Phase 5: Content-to-Conversion Loop
content_engine.py

Pulls crypto news from free RSS feeds (no API key needed).
Gemini picks top story + writes post in 2much813 voice.
Sends to personal Telegram for review.
"""

import os
import sys
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

RSS_FEEDS = [
    ("CoinDesk",     "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("CoinTelegraph","https://cointelegraph.com/rss"),
    ("Decrypt",      "https://decrypt.co/feed"),
    ("Bitcoin Mag",  "https://bitcoinmagazine.com/feed"),
]


def fetch_rss(url: str, source: str, limit: int = 5) -> list[dict]:
    """Fetch and parse a single RSS feed."""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; DOMI-Agent/1.0)"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        items = root.findall(".//item")
        articles = []
        for item in items[:limit]:
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


def fetch_crypto_news() -> list[dict]:
    """Fetch headlines from all RSS feeds."""
    all_articles = []
    for source, url in RSS_FEEDS:
        articles = fetch_rss(url, source)
        all_articles.extend(articles)
        if articles:
            print(f"[NEWS] {source}: {len(articles)} articles")

    print(f"[NEWS] Total: {len(all_articles)} articles fetched")
    return all_articles


def call_gemini(prompt: str, system: str = "", max_tokens: int = 300, temp: float = 0.7) -> str:
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
    try:
        resp = requests.post(
            GEMINI_API_URL,
            headers={"Content-Type": "application/json"},
            params={"key": api_key},
            json=body,
            timeout=15
        )
        resp.raise_for_status()
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        print(f"[GEMINI ERROR] {e}")
        return ""


def pick_top_story(articles: list[dict]) -> dict | None:
    """Gemini picks the most market-moving headline."""
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


def write_post(story: dict) -> str:
    """Gemini writes the 2much813 post."""
    prompt = (
        f"News: {story['title']}\n"
        f"Details: {story['body']}\n"
        f"Source: {story['source']}\n\n"
        "Write the 2much813 market post. "
        "Hook first. Then 2-3 lines of what this means for price action. "
        "End with: The Dojo already saw this coming. Tap in to stay ahead. "
        "3 hashtags at the end only."
    )
    return call_gemini(prompt, system=CONTENT_VOICE, max_tokens=350, temp=0.8)


def send_to_personal(post: str, story: dict) -> bool:
    """Send generated post to personal Telegram chat."""
    token = os.environ.get("TELEGRAM_TOKEN", "")
    if not token:
        print("[CONTENT] No Telegram token")
        return False

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    message = (
        f"*DOMI CONTENT DROP*\n"
        f"_{timestamp}_\n"
        f"Source: {story['source']}\n\n"
        f"{post}\n\n"
        f"[Read original]({story['url']})"
    )

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
        print(f"[CONTENT] Sent to personal chat {PERSONAL_CHAT_ID}")
        return True
    except Exception as e:
        print(f"[CONTENT] Send error: {e}")
        return False


def run_content_engine():
    print(f"\n[CONTENT] {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")

    articles = fetch_crypto_news()
    if not articles:
        print("[CONTENT] No news fetched. Skipping.")
        return

    story = pick_top_story(articles)
    if not story:
        print("[CONTENT] No story selected. Skipping.")
        return

    post = write_post(story)
    if not post:
        print("[CONTENT] No post generated. Skipping.")
        return

    print(f"\n[CONTENT] Post preview:\n{post[:200]}...\n")
    send_to_personal(post, story)


if __name__ == "__main__":
    run_content_engine()
