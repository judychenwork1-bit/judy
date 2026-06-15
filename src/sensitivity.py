"""
Greeks-like scenario analysis.

Each scenario shocks one factor by a given percentage and estimates
portfolio P&L using pre-calibrated per-ticker elasticities stored in
data/factor_sensitivities.json.

Example:
    results = run_scenarios(positions, factor_sensitivities)
    print_scenarios(results, gross_notional=20_000_000)
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path

SENS_FILE = Path(__file__).parent.parent / "data" / "factor_sensitivities.json"

SCENARIOS = {
    "CCL price  +10%":    ("ccl_price",     +0.10),
    "CCL price  -10%":    ("ccl_price",     -0.10),
    "Copper     +10%":    ("copper_price",  +0.10),
    "Copper     -10%":    ("copper_price",  -0.10),
    "AI capex   +20%":    ("ai_capex",      +0.20),
    "AI capex   -20%":    ("ai_capex",      -0.20),
    "Silicon    -20%":    ("silicon_price", -0.20),
    "Battery    -15%":    ("battery_price", -0.15),
    "Nat gas    +20%":    ("natgas_price",  +0.20),
    "Robot demand+30%":   ("robot_demand",  +0.30),
}


def load_sensitivities() -> dict:
    with open(SENS_FILE) as f:
        raw = json.load(f)
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def scenario_pnl(positions: pd.DataFrame, factor: str, shock: float,
                 sensitivities: dict) -> dict:
    """
    For a given factor shock, estimate P&L on each position and aggregate.

    P&L_i = notional_i × elasticity_i × shock
    Short positions have negative notional, so a negative elasticity on a
    short is actually a gain (cost to cover falls).
    """
    long_pnl  = 0.0
    short_pnl = 0.0
    rows = []

    for _, pos in positions.iterrows():
        ticker = pos.get("ticker")
        if ticker is None:
            continue
        sens = sensitivities.get(ticker, {})
        elast = sens.get(factor, 0.0)
        pnl = pos["notional"] * elast * shock  # notional already signed
        rows.append({
            "name":    pos["name"],
            "ticker":  ticker,
            "side":    pos["side"],
            "elast":   elast,
            "pnl":     pnl,
        })
        if pos["side"] == "Long":
            long_pnl += pnl
        else:
            short_pnl += pnl

    return {
        "long_pnl":  long_pnl,
        "short_pnl": short_pnl,
        "net_pnl":   long_pnl + short_pnl,
        "detail":    pd.DataFrame(rows),
    }


def run_scenarios(positions: pd.DataFrame, sensitivities: dict = None) -> pd.DataFrame:
    """Run all pre-defined scenarios; return summary DataFrame."""
    if sensitivities is None:
        sensitivities = load_sensitivities()

    results = []
    for label, (factor, shock) in SCENARIOS.items():
        r = scenario_pnl(positions, factor, shock, sensitivities)
        results.append({
            "Scenario":   label,
            "Long P&L":   r["long_pnl"],
            "Short P&L":  r["short_pnl"],
            "Net P&L":    r["net_pnl"],
        })
    return pd.DataFrame(results)


def print_scenarios(positions: pd.DataFrame, gross_notional: float = None,
                    sensitivities: dict = None):
    from tabulate import tabulate

    if sensitivities is None:
        sensitivities = load_sensitivities()

    df = run_scenarios(positions, sensitivities)

    if gross_notional:
        df["Net %"] = (df["Net P&L"] / gross_notional * 100).map("{:+.2f}%".format)

    fmt_k = lambda x: f"{x/1000:+,.0f}K"
    display = df.copy()
    for col in ("Long P&L", "Short P&L", "Net P&L"):
        display[col] = display[col].map(fmt_k)

    print()
    print("  SCENARIO ANALYSIS — Greeks-like P&L Estimates")
    print("  (Based on factor elasticities in data/factor_sensitivities.json)")
    cols = ["Scenario", "Long P&L", "Short P&L", "Net P&L"]
    if "Net %" in display.columns:
        cols.append("Net %")
    print(tabulate(display[cols].values, headers=cols, tablefmt="simple"))
    print()


def drill_down(positions: pd.DataFrame, scenario_label: str, sensitivities: dict = None):
    """Print per-position breakdown for a single scenario."""
    from tabulate import tabulate

    if sensitivities is None:
        sensitivities = load_sensitivities()

    factor, shock = SCENARIOS[scenario_label]
    r = scenario_pnl(positions, factor, shock, sensitivities)
    detail = r["detail"].sort_values("pnl", ascending=False)

    print(f"\n  DRILL-DOWN: {scenario_label}")
    detail["pnl_k"] = (detail["pnl"] / 1000).map("{:+,.1f}K".format)
    detail["elast"] = detail["elast"].map("{:+.2f}".format)
    print(tabulate(
        detail[["name", "ticker", "side", "elast", "pnl_k"]].values,
        headers=["Name", "Ticker", "Side", "Elasticity", "P&L"],
        tablefmt="simple",
    ))
    print(f"\n  Net P&L: {r['net_pnl']/1000:+,.1f}K  "
          f"(Long: {r['long_pnl']/1000:+,.1f}K  Short: {r['short_pnl']/1000:+,.1f}K)\n")
