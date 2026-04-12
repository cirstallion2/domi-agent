"""
DOMI - Phase 5: Content-to-Conversion Loop
content_engine.py

Scans macro crypto news via web search.
Gemini writes post in 2much813 voice.
Sends to personal Telegram chat for review before posting to X.

Schedule: runs 3x daily via GitHub Actions
"""

import os
import sys
import requests
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
    "Write for X (Twitter) - max 280 characters for the hook, "
    "then 2-3 follow-up lines of context. "
    "Always end with a CTA: 'The Dojo already saw this coming. Tap in.' "
    "No hashtags in body. Add 3 relevant hashtags at the end only."
)

NEWS_SOURCES = [
    "https://cryptopanic.com/api/v1/posts/?auth_token=public&kind=news&filter=hot",
    "https://min-api.cryptocompare.com/data/v2/news/?lang=EN&sortOrder=latest",
]


def fetch_crypto_news() -> list[dict]:
    """
    Fetch latest hot crypto news from free public APIs.
    Returns list of {title, url, source} dicts.
    """
    articles = []

    # CryptoCompare free news API
    try:
        resp = requests.get(
            "https://min-api.cryptocompare.com/data/v2/news/?lang=EN&sortOrder=latest",
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json().get("Data", [])
        for item in data[:10]:
            articles.append({
                "title":  item.get("title", ""),
                "body":   item.get("body", "")[:300],
                "source": item.get("source_info", {}).get("name", ""),
                "url":    item.get("url", ""),
            })
        print(f"[NEWS] Fetched {len(articles)} articles from CryptoCompare")
    except Exception as e:
        print(f"[NEWS ERROR] CryptoCompare: {e}")

    # CryptoPanic backup
    if not articles:
        try:
            resp = requests.get(
                "https://cryptopanic.com/api/v1/posts/?auth_token=public&kind=news&filter=hot",
                timeout=10
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])
            for item in results[:10]:
                articles.append({
                    "title":  item.get("title", ""),
                    "body":   "",
                    "source": item.get("source", {}).get("title", ""),
                    "url":    item.get("url", ""),
                })
            print(f"[NEWS] Fetched {len(articles)} articles from CryptoPanic")
        except Exception as e:
            print(f"[NEWS ERROR] CryptoPanic: {e}")

    return articles


def pick_top_story(articles: list[dict]) -> dict | None:
    """Use Gemini to pick the most tradeable story from the headlines."""
    if not articles:
        return None

    headlines = "\n".join([
        f"{i+1}. {a['title']} ({a['source']})"
        for i, a in enumerate(articles)
    ])

    prompt = (
        "You are DOMI, market intelligence AI for SNIPER813PRO.\n"
        "Pick the ONE most market-moving crypto news story from this list.\n"
        "Choose based on: macro impact, price action potential, trader relevance.\n"
        "Reply with ONLY the number of the story. Nothing else.\n\n"
        f"{headlines}"
    )

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return articles[0]

    try:
        resp = requests.post(
            GEMINI_API_URL,
            headers={"Content-Type": "application/json"},
            params={"key": api_key},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": 5, "temperature": 0.3},
            },
            timeout=15
        )
        resp.raise_for_status()
        pick = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        idx = int(pick) - 1
        if 0 <= idx < len(articles):
            print(f"[CONTENT] Top story: {articles[idx]['title'][:60]}...")
            return articles[idx]
    except Exception as e:
        print(f"[CONTENT] Story picker error: {e}")

    return articles[0]


def write_content_post(story: dict) -> str:
    """Gemini writes the 2much813 post from the news story."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return ""

    prompt = (
        f"News story: {story['title']}\n"
        f"Details: {story['body']}\n"
        f"Source: {story['source']}\n\n"
        "Write a 2much813 market post about this news. "
        "Hook line first (max 280 chars). "
        "Then 2-3 lines of technical context - what does this mean for price? "
        "What should traders watch? "
        "End with: The Dojo already saw this coming. Tap in to stay ahead. "
        "Add 3 hashtags at the end. "
        "Total post should fit in a Telegram message."
    )

    try:
        resp = requests.post(
            GEMINI_API_URL,
            headers={"Content-Type": "application/json"},
            params={"key": api_key},
            json={
                "system_instruction": {"parts": [{"text": CONTENT_VOICE}]},
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": 300, "temperature": 0.8},
            },
            timeout=15
        )
        resp.raise_for_status()
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        print(f"[CONTENT] Write error: {e}")
        return ""


def send_to_personal(message: str) -> bool:
    """Send content post to personal Telegram chat for review."""
    token = os.environ.get("TELEGRAM_TOKEN", "")
    if not token:
        print("[CONTENT] No Telegram token")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    header = (
        "📝 *DOMI CONTENT DROP*\n"
        "_Review before posting to X_\n"
        f"_{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_\n\n"
        "---\n\n"
    )

    payload = {
        "chat_id":    PERSONAL_CHAT_ID,
        "text":       header + message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        print(f"[CONTENT] Post sent to personal chat ({PERSONAL_CHAT_ID})")
        return True
    except requests.RequestException as e:
        print(f"[CONTENT] Send error: {e}")
        return False


def run_content_engine():
    """Full pipeline: fetch news -> pick story -> write post -> send to personal chat."""
    print(f"\n[CONTENT] Running at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")

    articles = fetch_crypto_news()
    if not articles:
        print("[CONTENT] No news fetched. Skipping.")
        return

    story = pick_top_story(articles)
    if not story:
        print("[CONTENT] No story selected. Skipping.")
        return

    post = write_content_post(story)
    if not post:
        print("[CONTENT] No post generated. Skipping.")
        return

    print(f"\n[CONTENT] Generated post:\n{post[:200]}...")
    send_to_personal(post)


if __name__ == "__main__":
    run_content_engine()
