# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

Hedge fund portfolio management tools for a Chinese A-share equity PM running a 2026 Long-Short Pairs strategy. Sectors covered: AI infrastructure (算力租赁, PCB, CCL, GPU, AI电源), clean energy (储能, 硅片, 新能源材料), industrials (燃机, 机器人), and related supply chains.

## Setup

```bash
pip install -r requirements.txt
```

`akshare` is used for A-share price data (requires `py-mini-racer` and `beautifulsoup4`). Prices are cached in `data/cache/` as CSV after first fetch.

## Key Commands

```bash
# Full risk report (positions → betas → factor attribution → scenario P&L → catalysts)
python scripts/portfolio_risk.py

# Custom notional (default 1M CNY per pair)
python scripts/portfolio_risk.py --notional 2000000

# Dollar-neutral instead of beta-neutral
python scripts/portfolio_risk.py --dollar-neutral

# Scenario drill-down for a specific shock
python scripts/portfolio_risk.py --drill "CCL price  +10%"

# Catalyst tracker
python scripts/catalyst_check.py                                            # show all
python scripts/catalyst_check.py --pending                                  # pending only
python scripts/catalyst_check.py --fire  PCB "GB300/Rubin放量" "confirmed"  # mark fired
python scripts/catalyst_check.py --miss  GPU "国产算力招标" "delayed to Q3"  # mark missed
python scripts/catalyst_check.py --reset PCB "GB300/Rubin放量"              # revert to pending
```

## Architecture

```
judy/
├── data/
│   ├── 2026_Long_Short_Pairs.xlsx   # source pairs (read-only)
│   ├── ticker_map.json              # company name → 6-digit A-share code (VERIFY before trading)
│   ├── catalyst_status.json         # mutable: tracks fired/missed/pending catalysts
│   ├── factor_sensitivities.json    # per-ticker elasticities to commodity/macro factors
│   └── cache/                       # auto-generated price CSVs from akshare
├── src/
│   ├── data_loader.py               # load pairs, fetch & cache prices (akshare), resolve tickers
│   ├── catalyst_tracker.py          # fire/miss/reset/dashboard for catalyst_status.json
│   ├── position_sizing.py           # beta-neutral & dollar-neutral sizing; portfolio summary
│   ├── factor_attribution.py        # market beta / momentum / size exposures, sector attribution
│   └── sensitivity.py               # scenario P&L from factor shocks; drill-down by position
└── scripts/
    ├── portfolio_risk.py            # main report (stitches all src modules)
    └── catalyst_check.py            # standalone catalyst CLI
```

### Data flow

`load_pairs()` → splits multi-name legs (e.g. "奥飞数据、协创数据") → `resolve_tickers()` maps names to 6-digit codes → `fetch_prices()` hits akshare and writes CSV cache → `compute_betas()` runs OLS vs CSI 300 (000300) → `beta_neutral_sizes()` solves for w_long / w_short such that `w_long × β_long = w_short × β_short` → factor table and scenario engine consume the final position table.

### Factor sensitivities

`data/factor_sensitivities.json` stores per-ticker elasticities (% stock return per 1% factor move) for: `ai_capex`, `ccl_price`, `copper_price`, `silicon_price`, `battery_price`, `natgas_price`, `robot_demand`. Initial values are illustrative estimates — calibrate from regression before use in live sizing.

### Ticker map

`data/ticker_map.json` maps Chinese company names to 6-digit A-share codes. **Verify all codes** before any live execution; several entries (协创数据, 金安国纪, 奥飞数据) should be cross-checked against Wind/Bloomberg.

### Adding a new pair

1. Add a row to `2026_Long_Short_Pairs.xlsx` with 板块, Short, Long, 2026边际变化, 后续催化剂.
2. Add any new company names to `data/ticker_map.json`.
3. Add catalysts to `data/catalyst_status.json`.
4. Optionally add factor elasticities for new tickers in `data/factor_sensitivities.json`.
