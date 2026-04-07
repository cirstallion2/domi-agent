import os
import requests
import pandas as pd
import numpy as np
import tweepy

# SNIPER813PRO Global Config
WATCHLIST = {"BTC": "XXBTZUSD", "XRP": "XRPUSD", "XLM": "XLMUSD", "ZBCN": "ZBCNUSD", "JASMY": "JASMYUSD"}
KRAKEN_LINK = "https://invite.kraken.com/JDNW/dg8lekjs"
TELEGRAM_CHANNEL = "YOUR_TELEGRAM_LINK_HERE" # Put your public channel link here

def post_to_x(asset, status):
    # API Credentials from your Developer Portal
    client = tweepy.Client(
        consumer_key=os.getenv('X_API_KEY'),
        consumer_secret=os.getenv('X_API_SECRET'),
        access_token=os.getenv('X_ACCESS_TOKEN'),
        access_token_secret=os.getenv('X_ACCESS_TOKEN_SECRET')
    )
    
    # Hype Templates
    if "LONG" in status:
        text = f"🚨 SNIPER ALERT: {asset} is loading a massive move. Momentum is shifting. 🚀\n\nFull technical breakdown & entry levels inside the Dojo. Don't get left behind.\n\n👇 JOIN THE HUNT\n{TELEGRAM_CHANNEL}"
    else:
        text = f"⚠️ WARNING: {asset} structure is breaking. Liquidity grab incoming. 💀\n\nWe just dropped the short-side levels in the Dojo. Be the wolf, not the sheep.\n\n👇 GET THE INTEL\n{TELEGRAM_CHANNEL}"
    
    try:
        client.create_tweet(text=text)
        print(f"X Post Sent for {asset}")
    except Exception as e:
        print(f"X Error: {e}")

# ... [Keep your existing get_kraken_data and analyze_assets functions here] ...
# In your main analyze loop, simply add this line where the signal triggers:
# post_to_x(name, status)
