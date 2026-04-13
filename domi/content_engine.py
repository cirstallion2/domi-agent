“””
DOMI - Phase 5: Content-to-Conversion Loop
content_engine.py

Uses Claude (Anthropic API) as the AI brain for content generation.
ONE API call per run. No rate limit issues.

Post hours (Medellin UTC-5):
5:00 AM  = 10:00 UTC - Market post
4:00 PM  = 21:00 UTC - Market post
9:00 PM  = 02:00 UTC - Market post
All other runs       - HeyGen video script
“””

import os
import sys
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(**file**))))

PERSONAL_CHAT_ID = os.environ.get(“PERSONAL_CHAT_ID”, “7419276203”)
POST_HOURS_UTC   = {10, 21, 2}

RSS_FEEDS = [
(“CoinDesk”,      “https://www.coindesk.com/arc/outboundfeeds/rss/”),
(“CoinTelegraph”, “https://cointelegraph.com/rss”),
(“Decrypt”,       “https://decrypt.co/feed”),
(“Bitcoin Mag”,   “https://bitcoinmagazine.com/feed”),
]

def fetch_rss(url: str, source: str, limit: int = 5) -> list:
headers = {“User-Agent”: “Mozilla/5.0 (compatible; DOMI-Agent/1.0)”}
try:
resp = requests.get(url, headers=headers, timeout=10)
resp.raise_for_status()
root = ET.fromstring(resp.content)
articles = []
for item in root.findall(”.//item”)[:limit]:
title = item.findtext(“title”, “”).strip()
desc  = item.findtext(“description”, “”).strip()[:200]
link  = item.findtext(“link”, “”).strip()
if title:
articles.append({“title”: title, “body”: desc, “source”: source, “url”: link})
return articles
except Exception as e:
print(f”[RSS ERROR] {source}: {e}”)
return []

def fetch_crypto_news() -> list:
all_articles = []
for source, url in RSS_FEEDS:
articles = fetch_rss(url, source)
all_articles.extend(articles)
if articles:
print(f”[NEWS] {source}: {len(articles)} articles”)
time.sleep(1)
print(f”[NEWS] Total: {len(all_articles)} articles”)
return all_articles

def call_claude(prompt: str) -> str:
“”“Call Anthropic Claude API. Uses ANTHROPIC_API_KEY secret.”””
api_key = os.environ.get(“ANTHROPIC_API_KEY”, “”)
if not api_key:
print(”[CLAUDE] No API key”)
return “”
try:
resp = requests.post(
“https://api.anthropic.com/v1/messages”,
headers={
“Content-Type”:         “application/json”,
“x-api-key”:            api_key,
“anthropic-version”:    “2023-06-01”,
},
json={
“model”:      “claude-haiku-4-5-20251001”,
“max_tokens”: 500,
“messages”:   [{“role”: “user”, “content”: prompt}],
},
timeout=30
)
resp.raise_for_status()
return resp.json()[“content”][0][“text”].strip()
except Exception as e:
print(f”[CLAUDE ERROR] {e}”)
return “”

def build_market_post_prompt(headlines: str) -> str:
return (
“You are DOMI, AI content engine for SNIPER813PRO by 2much813.\n”
“2much813 is a Market Translator. Voice: direct, technical, high-conviction.\n\n”
f”Top crypto headlines:\n{headlines}\n\n”
“Pick the most market-moving story and write ONE X/Twitter post.\n”
“Format:\n”
“Hook line (punchy, max 280 chars)\n”
“2-3 lines on what this means for price action\n”
“End with: The Dojo already saw this coming. Tap in to stay ahead.\n”
“3 hashtags at the very end only.\n”
“No bullet points. Flowing text only.”
)

def build_heygen_prompt(headlines: str) -> str:
return (
“You are DOMI, script writer for 2much813 HeyGen AI avatar videos.\n”
“2much813 is the Sniper in the Dojo. Market Translator.\n\n”
f”Top crypto headlines:\n{headlines}\n\n”
“Pick the most market-moving story. Write a 60-90 second video script.\n”
“Label each section:\n”
“[HOOK - 5 sec]\n”
“[CONTEXT - 20 sec]\n”
“[THE EDGE - 25 sec]\n”
“[CTA - 10 sec] End: Join the Dojo at sniper813alerts on Telegram. Stay sharp. Stay early.\n\n”
“Written to be spoken naturally on camera. No bullet points.”
)

def send_to_personal(content: str, label: str) -> bool:
token = os.environ.get(“TELEGRAM_TOKEN”, “”)
if not token:
print(”[CONTENT] No Telegram token”)
return False

```
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
```

def run_content_engine():
now_utc    = datetime.now(timezone.utc)
post_mode  = now_utc.hour in POST_HOURS_UTC
mode_label = “MARKET POST” if post_mode else “HEYGEN SCRIPT”

```
print(f"\n[CONTENT] {now_utc.strftime('%Y-%m-%d %H:%M UTC')} | Mode: {mode_label}")

articles = fetch_crypto_news()
if not articles:
    print("[CONTENT] No news fetched. Skipping.")
    return

headlines = "\n".join([
    f"- [{a['source']}] {a['title']}"
    for a in articles[:10]
])

prompt  = build_market_post_prompt(headlines) if post_mode else build_heygen_prompt(headlines)
content = call_claude(prompt)

if not content:
    print("[CONTENT] No content generated.")
    return

print(f"\n[CONTENT] Preview:\n{content[:300]}...\n")
send_to_personal(content, mode_label)
```

if **name** == “**main**”:
run_content_engine()
