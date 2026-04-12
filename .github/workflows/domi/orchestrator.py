“””
DOMI — Layer 2: Reasoning (Part A)
signal_engine.py

Applies the SNIPER813PRO Goalden Setup to OHLCV data.
Scores each signal 0-6. DOMI only passes Gold signals (score >= threshold).

CONFIRMATION STACK:
[1] 200 EMA Macro Gate       — price above/below macro trend
[2] Triple Alignment Filter  — price vs EMA20 on Daily/4H/1H aligned
[3] Keltner Channel Break     — price breaks KC band (volatility squeeze)
[4] EMA Cross (9/20)          — momentum cross on 1H
[5] Stochastic Filter         — oversold (<25) for LONG / overbought (>75) for SHORT
[6] RSI Confirmation          — RSI > 50 LONG / < 50 SHORT

Score 6/6 = GOLD  → blast to Elite Telegram
Score 4-5 = WATCH → log only
Score <4   = KILL  → discard
“””

import pandas as pd
import pandas_ta as ta
import json
from dataclasses import dataclass, field
from typing import Literal

Direction = Literal[“LONG”, “SHORT”, “NONE”]

@dataclass
class Signal:
pair: str
direction: Direction
score: int
checks: dict
price: float
ema200: float
keltner_upper: float
keltner_lower: float
ema9: float
ema20: float
stoch_k: float
rsi: float
grade: str = field(init=False)

```
def __post_init__(self):
    if self.score >= 6:
        self.grade = "GOLD"
    elif self.score >= 4:
        self.grade = "WATCH"
    else:
        self.grade = "KILL"
```

def compute_indicators(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
“”“Add all indicators to DataFrame in-place.”””
df = df.copy()

```
# EMAs
for period in cfg["ema_periods"]:
    df[f"ema{period}"] = ta.ema(df["close"], length=period)

# Keltner Channel
kc = ta.kc(df["high"], df["low"], df["close"],
            length=cfg["keltner_period"],
            scalar=cfg["keltner_atr_mult"])
# pandas_ta returns KCLe_20_2.0 / KCUe_20_2.0
kc_cols = kc.columns.tolist()
lower_col = [c for c in kc_cols if "L" in c][0]
upper_col = [c for c in kc_cols if "U" in c][0]
df["kc_lower"] = kc[lower_col]
df["kc_upper"] = kc[upper_col]

# Stochastic
stoch = ta.stoch(df["high"], df["low"], df["close"],
                 k=cfg["stoch_k"], d=cfg["stoch_d"])
df["stoch_k"] = stoch[f"STOCHk_{cfg['stoch_k']}_{cfg['stoch_d']}_3"]

# RSI
df["rsi"] = ta.rsi(df["close"], length=cfg["rsi_period"])

return df
```

def score_signal(df: pd.DataFrame, pair: str) -> Signal:
“””
Run the 6-point Goalden Setup on the latest candle.
Returns a Signal dataclass.
“””
row = df.iloc[-1]
price = row[“close”]
score = 0
checks = {}

```
# ── [1] 200 EMA Macro Gate ─────────────────────────────────────────────
above_200 = price > row["ema200"]
checks["ema200_gate"] = above_200
if above_200:
    direction_bias: Direction = "LONG"
else:
    direction_bias: Direction = "SHORT"
score += 1   # macro gate always scores if data is valid

# ── [2] Triple Alignment: price vs EMA20 ──────────────────────────────
# We only have 1H data here; alignment check uses same df
# (Full multi-TF alignment handled by orchestrator passing 3 dfs)
aligned = (price > row["ema20"]) if direction_bias == "LONG" else (price < row["ema20"])
checks["triple_alignment"] = aligned
if aligned:
    score += 1

# ── [3] Keltner Channel Break ──────────────────────────────────────────
kc_break_long  = price > row["kc_upper"]
kc_break_short = price < row["kc_lower"]
kc_hit = kc_break_long if direction_bias == "LONG" else kc_break_short
checks["keltner_break"] = kc_hit
if kc_hit:
    score += 1

# ── [4] EMA 9/20 Cross ────────────────────────────────────────────────
prev = df.iloc[-2]
cross_long  = (prev["ema9"] <= prev["ema20"]) and (row["ema9"] > row["ema20"])
cross_short = (prev["ema9"] >= prev["ema20"]) and (row["ema9"] < row["ema20"])
cross_hit = cross_long if direction_bias == "LONG" else cross_short
checks["ema_cross"] = cross_hit
if cross_hit:
    score += 1

# ── [5] Stochastic Filter ─────────────────────────────────────────────
stoch_long  = row["stoch_k"] < 25    # oversold → buy pressure building
stoch_short = row["stoch_k"] > 75    # overbought → sell pressure building
stoch_hit = stoch_long if direction_bias == "LONG" else stoch_short
checks["stochastic"] = stoch_hit
if stoch_hit:
    score += 1

# ── [6] RSI Confirmation ──────────────────────────────────────────────
rsi_long  = row["rsi"] > 50
rsi_short = row["rsi"] < 50
rsi_hit = rsi_long if direction_bias == "LONG" else rsi_short
checks["rsi"] = rsi_hit
if rsi_hit:
    score += 1

return Signal(
    pair=pair,
    direction=direction_bias,
    score=score,
    checks=checks,
    price=round(price, 6),
    ema200=round(row["ema200"], 6),
    keltner_upper=round(row["kc_upper"], 6),
    keltner_lower=round(row["kc_lower"], 6),
    ema9=round(row["ema9"], 6),
    ema20=round(row["ema20"], 6),
    stoch_k=round(row["stoch_k"], 2),
    rsi=round(row["rsi"], 2),
)
```

def run_scan(market_data: dict, cfg: dict) -> list[Signal]:
“””
Scan all pairs. Return list of signals sorted by score desc.
Filters out KILL signals.
“””
signals = []

```
for pair, df in market_data.items():
    try:
        df_ind = compute_indicators(df, cfg)
        sig = score_signal(df_ind, pair)
        print(f"[SCAN] {pair} | {sig.direction} | Score: {sig.score}/6 | {sig.grade}")
        if sig.grade != "KILL":
            signals.append(sig)
    except Exception as e:
        print(f"[SCAN ERROR] {pair}: {e}")

signals.sort(key=lambda s: s.score, reverse=True)
print(f"\n[ENGINE] {len(signals)} signals passed filter")
return signals
```

if **name** == “**main**”:
# Smoke test with synthetic data
import numpy as np
np.random.seed(42)
n = 300
close = 45000 + np.cumsum(np.random.randn(n) * 100)
df_test = pd.DataFrame({
“open”: close - 50, “high”: close + 100,
“low”: close - 100, “close”: close,
“volume”: np.random.rand(n) * 1000
})

```
with open("config/watchlist.json") as f:
    cfg = json.load(f)

df_ind = compute_indicators(df_test, cfg)
sig = score_signal(df_ind, "XBT/USD")
print(f"\nTest Signal: {sig}")
```
