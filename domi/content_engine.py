"""
DOMI - Phase 5: Content-to-Conversion Loop
content_engine.py

Pipeline:
  1. Pull trending crypto topics from X (Bearer Token)
  2. Pull latest headlines from RSS feeds
  3. Claude writes content in 2much813 voice
  4. Send to personal Telegram for review

Post hours (Medellin UTC-5):
  5:00 AM  = 10:00 UTC -> X/Telegram market post (ready to copy/paste)
  4:00 PM  = 21:00 UTC -> X/Telegram market post
  9:00 PM  = 02:00 UTC -> X/Telegram market post
  All other hours      -> HeyGen video script
"""

import os
import sys
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PERSONAL_CHAT_ID = os.environ.get("PERSONAL_CHAT_ID", "7419276203")
POST_HOURS_UTC   = {10, 21, 2}

RSS_FEEDS = [
    ("CoinDesk",      "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("CoinTelegraph", "https://cointelegraph.com/rss"),
    ("Decrypt",       "https://decrypt.co/feed"),
    ("Bitcoin Mag",   "https://bitcoinmagazine.com/feed"),
]

CRYPTO_ACCOUNTS = [
    "CoinDesk", "Cointelegraph", "WatcherGuru",
    "whale_alert", "glassnode", "woonomic"
]


def fetch_x_trending(bearer_token: str) -> list:
    """
    Pull recent tweets from top crypto accounts using X API v2.
    Used as content inspiration - not posted back to X.
    """
    if not bearer_token:
        return []

    headers = {"Authorization": f"Bearer {bearer_token}"}
    tweets  = []

    for account in CRYPTO_ACCOUNTS[:3]:   # limit to 3 accounts to save quota
        try:
            # Get user ID first
            user_resp = requests.get(
                f"https://api.twitter.com/2/users/by/username/{account}",
                headers=headers,
                timeout=10
            )
            if user_resp.status_code != 200:
                continue
            user_id = user_resp.json()["data"]["id"]

            # Get recent tweets
            tweet_resp = requests.get(
                f"https://api.twitter.com/2/users/{user_id}/tweets",
                headers=headers,
                params={
                    "max_results": 5,
                    "tweet.fields": "text,created_at",
                    "exclude": "retweets,replies"
                },
                timeout=10
            )
            if tweet_resp.status_code != 200:
                continue

            for t in tweet_resp.json().get("data", []):
                text = t.get("text", "").strip()
                if len(text) > 20:
                    tweets.append(f"[@{account}] {text[:200]}")

            time.sleep(1)

        except Exception as e:
            print(f"[X] {account}: {e}")

    print(f"[X] Pulled {len(tweets)} tweets for inspiration")
    return tweets


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
            if title:
                articles.append(f"[{source}] {title} - {desc}")
        return articles
    except Exception as e:
        print(f"[RSS ERROR] {source}: {e}")
        return []


def fetch_crypto_news() -> list:
    all_news = []
    for source, url in RSS_FEEDS:
        items = fetch_rss(url, source)
        all_news.extend(items)
        if items:
            print(f"[NEWS] {source}: {len(items)} articles")
        time.sleep(1)
    return all_news


def call_claude(prompt: str) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("[CLAUDE] No API key")
        return ""
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "Content-Type":      "application/json",
                "x-api-key":         api_key,
                "anthropic-version": "2023-06-01",
            },
            json={
                "model":      "claude-haiku-4-5-20251001",
                "max_tokens": 600,
                "messages":   [{"role": "user", "content": prompt}],
            },
            timeout=30
        )
        resp.raise_for_status()
        return resp.json()["content"][0]["text"].strip()
    except Exception as e:
        print(f"[CLAUDE ERROR] {e}")
        return ""


def build_market_post_prompt(news: list, tweets: list) -> str:
    news_block   = "\n".join(news[:8])
    tweets_block = "\n".join(tweets[:5]) if tweets else "No X data available."

    return (
        "You are DOMI, AI content engine for SNIPER813PRO by 2much813.\n"
        "2much813 is a Market Translator. Voice: direct, technical, high-conviction.\n"
        "Retail guesses. 2much813 front-runs the rotation.\n\n"
        f"Latest crypto news:\n{news_block}\n\n"
        f"What crypto Twitter is talking about:\n{tweets_block}\n\n"
        "Using this as inspiration, write ONE market post for X and Telegram.\n"
        "Structure:\n"
        "- Hook (1 punchy line that stops the scroll)\n"
        "- 2-3 lines: what is happening, what it means for price, what to watch\n"
        "- End with: The Dojo already saw this coming. Tap in to stay ahead.\n"
        "- 3 relevant hashtags on the last line\n\n"
        "Keep it under 280 characters total if possible. No bullet points."
    )


def build_heygen_prompt(news: list, tweets: list) -> str:
    news_block   = "\n".join(news[:8])
    tweets_block = "\n".join(tweets[:5]) if tweets else "No X data available."

    return (
        "You are DOMI, script writer for 2much813 HeyGen AI avatar videos.\n"
        "2much813 is the Sniper in the Dojo. Market Translator.\n"
        "The avatar speaks directly to camera in a confident, technical voice.\n\n"
        f"Latest crypto news:\n{news_block}\n\n"
        f"What crypto Twitter is talking about:\n{tweets_block}\n\n"
        "Pick the most relevant topic and write a 60-90 second spoken video script.\n\n"
        "[HOOK - 5 sec]\n"
        "One line that grabs attention immediately.\n\n"
        "[CONTEXT - 20 sec]\n"
        "What is happening in the market right now. Keep it simple.\n\n"
        "[THE EDGE - 25 sec]\n"
        "What smart money is watching. What the SNIPER813PRO setup says.\n"
        "Reference EMA alignment, key levels, or macro context.\n\n"
        "[CTA - 10 sec]\n"
        "Join the Dojo at sniper813alerts on Telegram. Stay sharp. Stay early.\n\n"
        "Write it to be spoken naturally. No bullet points. No stage directions."
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
        print(f"[CONTENT] Delivered to personal Telegram")
        return True
    except Exception as e:
        print(f"[CONTENT] Telegram error: {e}")
        return False


def run_content_engine():
    now_utc   = datetime.now(timezone.utc)
    post_mode = now_utc.hour in POST_HOURS_UTC
    label     = "MARKET POST - ready to copy/paste" if post_mode else "HEYGEN SCRIPT - ready for avatar"

    print(f"\n[CONTENT] {now_utc.strftime('%Y-%m-%d %H:%M UTC')} | {'MARKET POST' if post_mode else 'HEYGEN SCRIPT'}")

    # Pull data
    bearer = os.environ.get("X_BEARER_TOKEN", "")
    tweets = fetch_x_trending(bearer)
    news   = fetch_crypto_news()

    if not news:
        print("[CONTENT] No news fetched. Skipping.")
        return

    # One Claude call
    prompt  = build_market_post_prompt(news, tweets) if post_mode else build_heygen_prompt(news, tweets)
    content = call_claude(prompt)

    if not content:
        print("[CONTENT] No content generated.")
        return

    print(f"\n[CONTENT] Preview:\n{content[:300]}...\n")
    send_to_personal(content, label)


if __name__ == "__main__":
    run_content_engine()
