"""
DOMI - Phase 5: Content-to-Conversion Loop
content_engine.py

Data Sources:
  - X API v2: trending crypto topics + top account tweets
  - RSS feeds: CoinDesk, Yahoo Finance, Bloomberg, Reuters, Forbes Crypto

AI Writer: Gemini 2.0 Flash (dedicated content key)

Output -> Personal Telegram:
  5AM / 4PM / 9PM Medellin -> Market post (copy/paste to X)
  All other runs            -> HeyGen video script
"""

import os
import sys
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PERSONAL_CHAT_ID = os.environ.get("PERSONAL_CHAT_ID", "7419276203")
POST_HOURS_UTC   = {10, 21, 2}   # 5AM, 4PM, 9PM Medellin

GEMINI_MODEL   = "gemini-2.0-flash"
GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    + GEMINI_MODEL + ":generateContent"
)

# Top crypto/finance accounts to pull inspiration from
X_ACCOUNTS = [
    "CoinDesk", "Cointelegraph", "WatcherGuru",
    "whale_alert", "glassnode", "APompliano",
    "PeterSchiff", "saylor", "VitalikButerin"
]

# Reliable news RSS feeds
RSS_FEEDS = [
    ("CoinDesk",       "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("CoinTelegraph",  "https://cointelegraph.com/rss"),
    ("Yahoo Finance",  "https://finance.yahoo.com/news/rssindex"),
    ("Reuters Crypto", "https://feeds.reuters.com/reuters/businessNews"),
    ("Decrypt",        "https://decrypt.co/feed"),
    ("Bitcoin Mag",    "https://bitcoinmagazine.com/feed"),
    ("Forbes Crypto",  "https://www.forbes.com/crypto-blockchain/feed/"),
]


def fetch_x_data(bearer_token: str) -> dict:
    """
    Pull trending topics and top account tweets from X API v2.
    Returns: { "trending": [...], "tweets": [...] }
    """
    if not bearer_token:
        print("[X] No bearer token")
        return {"trending": [], "tweets": []}

    headers = {"Authorization": f"Bearer {bearer_token}"}
    tweets  = []

    print(f"[X] Fetching from {len(X_ACCOUNTS)} accounts...")
    for account in X_ACCOUNTS[:5]:
        try:
            # Get user ID
            u = requests.get(
                f"https://api.twitter.com/2/users/by/username/{account}",
                headers=headers, timeout=10
            )
            if u.status_code != 200:
                continue
            uid = u.json()["data"]["id"]

            # Get recent tweets
            t = requests.get(
                f"https://api.twitter.com/2/users/{uid}/tweets",
                headers=headers,
                params={
                    "max_results":   5,
                    "tweet.fields":  "text,public_metrics",
                    "exclude":       "retweets,replies"
                },
                timeout=10
            )
            if t.status_code != 200:
                continue

            for tw in t.json().get("data", []):
                text    = tw.get("text", "").strip()
                metrics = tw.get("public_metrics", {})
                likes   = metrics.get("like_count", 0)
                if len(text) > 30 and likes > 10:
                    tweets.append(f"[@{account} | {likes} likes] {text[:250]}")

            time.sleep(1)

        except Exception as e:
            print(f"[X] {account}: {e}")

    # Try trending topics (requires Elevated access - skip gracefully if unavailable)
    trending = []
    try:
        tr = requests.get(
            "https://api.twitter.com/2/trends/by/woeid/1",
            headers=headers, timeout=10
        )
        if tr.status_code == 200:
            for item in tr.json().get("data", [])[:10]:
                name = item.get("name", "")
                if any(kw in name.lower() for kw in ["btc","eth","crypto","defi","bitcoin","sol","xrp"]):
                    trending.append(name)
    except Exception:
        pass

    print(f"[X] Got {len(tweets)} tweets | {len(trending)} trending topics")
    return {"trending": trending, "tweets": tweets}


def fetch_rss(url: str, source: str, limit: int = 4) -> list:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; DOMI-Agent/1.0)"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        articles = []
        for item in root.findall(".//item")[:limit]:
            title = item.findtext("title", "").strip()
            desc  = item.findtext("description", "").strip()[:150]
            if title and any(kw in (title + desc).lower() for kw in
                           ["bitcoin","crypto","btc","eth","fed","inflation",
                            "market","trading","blockchain","defi","sec"]):
                articles.append(f"[{source}] {title}")
        return articles
    except Exception as e:
        print(f"[RSS] {source}: {e}")
        return []


def fetch_news() -> list:
    all_news = []
    for source, url in RSS_FEEDS:
        items = fetch_rss(url, source)
        all_news.extend(items)
        if items:
            print(f"[NEWS] {source}: {len(items)} relevant articles")
        time.sleep(1)
    print(f"[NEWS] Total: {len(all_news)} articles")
    return all_news


def call_gemini(prompt: str) -> str:
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
                "generationConfig": {
                    "maxOutputTokens": 600,
                    "temperature":     0.8
                },
            },
            timeout=30
        )
        if resp.status_code == 429:
            print("[GEMINI] Rate limited - will retry next run")
            return ""
        resp.raise_for_status()
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        print(f"[GEMINI ERROR] {e}")
        return ""


def build_market_post_prompt(news: list, x_data: dict) -> str:
    news_block     = "\n".join(news[:10]) or "No news available."
    tweets_block   = "\n".join(x_data["tweets"][:6]) or "No tweets available."
    trending_block = ", ".join(x_data["trending"]) or "No trending data."

    return f"""You are DOMI, the AI content engine for SNIPER813PRO by 2much813.

BRAND VOICE:
- 2much813 is a Market Translator, not a content creator
- Direct, technical, high-conviction. No fluff. No hedging.
- Retail guesses. 2much813 front-runs the rotation.
- The Sniper in the Dojo.

WHAT CRYPTO TWITTER IS TALKING ABOUT:
{tweets_block}

TRENDING TOPICS:
{trending_block}

LATEST NEWS FROM COINDESK, YAHOO FINANCE, BLOOMBERG, REUTERS:
{news_block}

TASK: Write ONE market post for X and Telegram.

FORMAT:
Line 1: Hook - one punchy line that stops the scroll (max 100 chars)
Lines 2-4: What is happening + what it means for price + what to watch
Last line: "The Dojo already saw this coming. Tap in to stay ahead."
Final line: 3 relevant hashtags only

Keep total under 280 characters if possible. No bullet points. Flowing text."""


def build_heygen_prompt(news: list, x_data: dict) -> str:
    news_block   = "\n".join(news[:10]) or "No news available."
    tweets_block = "\n".join(x_data["tweets"][:6]) or "No tweets available."

    return f"""You are DOMI, script writer for 2much813 HeyGen AI avatar videos.

BRAND: SNIPER813PRO by 2much813 - The Sniper in the Dojo. Market Translator.
AVATAR: Speaks directly to camera. Confident, technical, clear.

WHAT CRYPTO TWITTER IS TALKING ABOUT:
{tweets_block}

LATEST NEWS FROM COINDESK, YAHOO FINANCE, BLOOMBERG, REUTERS:
{news_block}

TASK: Pick the most market-relevant topic. Write a 60-90 second video script.

STRUCTURE (label each section exactly like this):

[HOOK - 5 sec]
One line. Grabs attention. Makes them stop scrolling.

[CONTEXT - 20 sec]
What is happening right now. Simple. Clear. No jargon.

[THE EDGE - 25 sec]
What smart money is watching. Key levels. EMA alignment.
What the SNIPER813PRO Goalden Setup is showing.
What retail is missing.

[CTA - 10 sec]
Join the Dojo at sniper813alerts on Telegram. Stay sharp. Stay early.

RULES: Natural spoken language. No bullet points. No stage directions. No parentheses."""


def send_to_personal(content: str, label: str) -> bool:
    token = os.environ.get("TELEGRAM_TOKEN", "")
    if not token:
        print("[CONTENT] No Telegram token")
        return False

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    message   = f"*DOMI | {label}*\n_{timestamp}_\n\n{content}"

    # Telegram max message length is 4096 chars
    if len(message) > 4096:
        message = message[:4090] + "..."

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
        print(f"[CONTENT] Delivered to personal Telegram {PERSONAL_CHAT_ID}")
        return True
    except Exception as e:
        print(f"[CONTENT] Telegram error: {e}")
        return False


def run_content_engine():
    now_utc   = datetime.now(timezone.utc)
    post_mode = now_utc.hour in POST_HOURS_UTC
    mode      = "MARKET POST" if post_mode else "HEYGEN SCRIPT"
    label     = "MARKET POST - copy/paste to X" if post_mode else "HEYGEN SCRIPT - paste into HeyGen"

    print(f"\n[CONTENT] {now_utc.strftime('%Y-%m-%d %H:%M UTC')} | Mode: {mode}")

    # Pull data from X and news feeds
    bearer = os.environ.get("X_BEARER_TOKEN", "")
    x_data = fetch_x_data(bearer)
    news   = fetch_news()

    if not news and not x_data["tweets"]:
        print("[CONTENT] No data available. Skipping.")
        return

    # One Gemini call
    prompt  = build_market_post_prompt(news, x_data) if post_mode else build_heygen_prompt(news, x_data)
    content = call_gemini(prompt)

    if not content:
        print("[CONTENT] No content generated.")
        return

    print(f"\n[CONTENT] Preview:\n{content[:300]}...\n")
    send_to_personal(content, label)


if __name__ == "__main__":
    run_content_engine()
