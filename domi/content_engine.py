name: DOMI Content Engine

on:
  schedule:
    - cron: '30 10 * * *'
    - cron: '30 21 * * *'
    - cron: '30 2  * * *'
    - cron: '30 13 * * *'
    - cron: '30 16 * * *'
    - cron: '30 19 * * *'
    - cron: '30 0  * * *'
  workflow_dispatch:

jobs:
  content:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    env:
      FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true

    steps:
      - name: Checkout repo
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: |
          pip install --no-cache-dir pandas==2.2.2 numpy==1.26.4 requests==2.31.0 yfinance==0.2.54 krakenex==2.1.0
          # Use the 2026-compliant fork for Python 3.11 stability
          pip install pandas-ta-openbb

      - name: Run DOMI Content Engine
        env:
          GEMINI_API_KEY:  ${{ secrets.GEMINI_CONTENT_KEY }}
          TELEGRAM_TOKEN:  ${{ secrets.TELEGRAM_TOKEN }}
          PERSONAL_CHAT_ID: "7419276203"
          X_BEARER_TOKEN:  ${{ secrets.X_BEARER_TOKEN }}
          PYTHONPATH:      ${{ github.workspace }}
        run: python run_content.py
