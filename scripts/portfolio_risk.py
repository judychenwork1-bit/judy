#!/usr/bin/env python3
"""
Full portfolio risk report: positions → betas → factor attribution → scenarios.

Usage:
  python scripts/portfolio_risk.py                           # full report
  python scripts/portfolio_risk.py --notional 2000000       # 2M CNY per pair
  python scripts/portfolio_risk.py --drill "CCL price  +10%"  # scenario drill-down
  python scripts/portfolio_risk.py --dollar-neutral          # skip beta adjustment
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd

from src.data_loader      import load_pairs, load_ticker_map, fetch_prices, fetch_index
from src.position_sizing  import compute_betas, beta_neutral_sizes, dollar_neutral_sizes, print_positions, portfolio_summary
from src.factor_attribution import build_factor_table, print_attribution, fetch_market_caps
from src.sensitivity      import load_sensitivities, print_scenarios, drill_down
from src.catalyst_tracker import print_dashboard

# ── CLI args ────────────────────────────────────────────────────────────────

args = sys.argv[1:]
notional_per_pair = 1_000_000
use_dollar_neutral = "--dollar-neutral" in args
drill_label = None

for i, a in enumerate(args):
    if a == "--notional" and i + 1 < len(args):
        notional_per_pair = float(args[i + 1])
    if a == "--drill" and i + 1 < len(args):
        drill_label = args[i + 1]

# ── Header ───────────────────────────────────────────────────────────────────

today = datetime.today().strftime("%Y-%m-%d")
print()
print("=" * 66)
print(f"  PORTFOLIO RISK REPORT — 2026 Long-Short Pairs")
print(f"  As of {today}  |  Notional/pair: {notional_per_pair:,.0f} CNY")
print("=" * 66)

# ── Load data ────────────────────────────────────────────────────────────────

pairs      = load_pairs()
ticker_map = load_ticker_map()

all_names  = []
for _, row in pairs.iterrows():
    all_names += row["long_list"] + row["short_list"]
all_names  = list(dict.fromkeys(all_names))  # deduplicate, preserve order
all_tickers = [ticker_map.get(n) for n in all_names]
valid_tickers = [t for t in all_tickers if t]

# ── Fetch prices ─────────────────────────────────────────────────────────────

start_date = (datetime.today() - timedelta(days=400)).strftime("%Y-%m-%d")
print(f"\n  Fetching prices for {len(valid_tickers)} tickers (since {start_date})…")

prices = fetch_prices(valid_tickers, start=start_date, end=today)
index  = fetch_index("000300", start=start_date, end=today)

# ── Compute betas ─────────────────────────────────────────────────────────────

if not prices.empty and not index.empty:
    betas = compute_betas(prices, index)
    print(f"  Betas computed. CSI-300 observations: {len(index)}")
else:
    betas = {t: 1.0 for t in valid_tickers}
    print("  [warn] Could not fetch market data — using beta = 1.0 for all")

# ── Position sizing ───────────────────────────────────────────────────────────

if use_dollar_neutral:
    positions = dollar_neutral_sizes(pairs, ticker_map, notional_per_pair)
    positions["beta_contribution"] = positions["notional"] * positions.get("beta", 1.0)
    mode = "Dollar-Neutral"
else:
    positions = beta_neutral_sizes(pairs, ticker_map, betas, notional_per_pair)
    mode = "Beta-Neutral"

print(f"\n  Mode: {mode}")
print_positions(positions)

# ── Factor attribution ────────────────────────────────────────────────────────

print("  Fetching market caps…")
market_caps = fetch_market_caps(valid_tickers) if valid_tickers else None

factor_df = build_factor_table(positions, betas, prices if not prices.empty else None, market_caps)
print_attribution(factor_df)

# ── Scenario analysis ─────────────────────────────────────────────────────────

sensitivities = load_sensitivities()
summ = portfolio_summary(positions)
print_scenarios(positions, gross_notional=summ["gross_notional"], sensitivities=sensitivities)

if drill_label:
    drill_down(positions, drill_label, sensitivities)

# ── Catalyst dashboard ────────────────────────────────────────────────────────

print_dashboard()
