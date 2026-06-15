# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

This is a hedge fund portfolio management repository for a Chinese A-share equity PM. It currently centers on a 2026 Long-Short Pairs strategy across sectors including AI infrastructure (算力租赁, PCB, CCL, GPU, AI电源), clean energy (储能, 硅片, 新能源材料), industrials (燃机, 机器人), and related supply chain names.

The core data artifact is `2026_Long_Short_Pairs.xlsx`, which contains:
- **板块** — sector grouping
- **Short / Long** — specific ticker names for each leg
- **2026边际变化（投资逻辑）** — marginal investment thesis for 2026
- **后续催化剂** — upcoming catalysts to monitor

## Repository Conventions

- Primary language: **Python 3**
- Data files: Excel (`.xlsx`) via `pandas` + `openpyxl`; CSV for lightweight outputs
- Financial data: use `akshare` for A-share market data, `yfinance` for global benchmarks
- All monetary values in **CNY** unless explicitly noted; use basis points (bps) for spread/return differences
- Ticker format: A-share 6-digit codes (e.g. `300529.SZ`, `002463.SZ`); always include exchange suffix

## Development Setup

```bash
pip install pandas openpyxl akshare yfinance matplotlib seaborn
```

## Key Workflows

### Load the pairs data
```python
import pandas as pd
df = pd.read_excel("2026_Long_Short_Pairs.xlsx", sheet_name="2026 Long-Short Pairs")
```

### Running scripts
```bash
python scripts/<script_name>.py
```

### Running tests (once test suite exists)
```bash
pytest tests/ -v
pytest tests/test_pairs.py -v   # single test file
```

## Architecture Notes

As the codebase grows, follow this layout:

```
judy/
├── data/           # raw Excel/CSV inputs, never modified in-place
├── scripts/        # one-off analysis scripts
├── src/            # importable modules (pairs logic, data loaders, risk)
├── notebooks/      # exploratory Jupyter notebooks
├── tests/          # pytest tests mirroring src/ structure
└── outputs/        # generated charts, reports (gitignored)
```

Keep `data/` read-only. Scripts write to `outputs/`. Any reusable logic (position sizing, P&L attribution, catalyst tracking) lives in `src/` and is imported by scripts and notebooks.
