"""
Factor attribution across three axes:
  1. Market beta  — OLS beta vs CSI 300
  2. Momentum     — 12-1 month trailing return (standard academic definition)
  3. Size         — log(market cap), sourced from akshare or estimated from price

All exposures are reported at position level and aggregated to long/short/net.
"""

import numpy as np
import pandas as pd
from typing import Optional


def compute_momentum(prices: pd.DataFrame, lookback: int = 252, skip: int = 21) -> pd.Series:
    """12-1 month momentum: return from t-252 to t-21."""
    if len(prices) < lookback:
        return pd.Series(dtype=float)
    p_end   = prices.iloc[-(skip + 1)]
    p_start = prices.iloc[-(lookback + 1)] if len(prices) > lookback else prices.iloc[0]
    mom = (p_end / p_start - 1).rename("momentum")
    return mom


def fetch_market_caps(tickers: list) -> pd.Series:
    """Return {ticker: market_cap_CNY}. Falls back to NaN on failure."""
    caps = {}
    try:
        import akshare as ak
        for t in tickers:
            try:
                df = ak.stock_individual_info_em(symbol=t)
                row = df[df["item"] == "总市值"]
                if not row.empty:
                    val = row["value"].iloc[0]
                    val_str = str(val).replace("亿", "").replace(",", "")
                    caps[t] = float(val_str) * 1e8  # 亿 → CNY
                else:
                    caps[t] = np.nan
            except Exception:
                caps[t] = np.nan
    except Exception:
        caps = {t: np.nan for t in tickers}
    return pd.Series(caps, name="market_cap")


def size_factor(market_caps: pd.Series) -> pd.Series:
    """Log market cap, standardized (z-score)."""
    log_cap = np.log(market_caps.replace(0, np.nan))
    return ((log_cap - log_cap.mean()) / log_cap.std()).rename("size_z")


def build_factor_table(
    positions: pd.DataFrame,
    betas: dict,
    prices: Optional[pd.DataFrame] = None,
    market_caps: Optional[pd.Series] = None,
) -> pd.DataFrame:
    """
    Attach factor exposures to each position row.
    Returns positions enriched with columns: beta, momentum, size_z.
    """
    df = positions.copy()

    # Market beta
    df["beta"] = df["ticker"].map(lambda t: betas.get(t, np.nan) if t else np.nan)

    # Momentum
    if prices is not None and not prices.empty:
        mom = compute_momentum(prices)
        df["momentum"] = df["ticker"].map(lambda t: mom.get(t, np.nan) if t else np.nan)
    else:
        df["momentum"] = np.nan

    # Size
    if market_caps is not None:
        sz = size_factor(market_caps)
        df["size_z"] = df["ticker"].map(lambda t: sz.get(t, np.nan) if t else np.nan)
    else:
        df["size_z"] = np.nan

    # Dollar-weighted exposures for aggregation
    abs_notional = df["notional"].abs()
    sign = df["notional"].apply(lambda x: 1 if x >= 0 else -1)
    for factor in ("beta", "momentum", "size_z"):
        df[f"{factor}_contrib"] = df[factor] * sign * abs_notional

    return df


def attribution_summary(factor_df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate factor exposures: Long / Short / Net, notional-weighted average.
    """
    rows = []
    for factor in ("beta", "momentum", "size_z"):
        for side, grp in factor_df.groupby("side"):
            w = grp["notional"].abs().sum()
            if w > 0:
                exp = grp[f"{factor}_contrib"].sum() / w
            else:
                exp = np.nan
            rows.append({"factor": factor, "side": side, "exposure": exp})

    wide = pd.DataFrame(rows).pivot(index="factor", columns="side", values="exposure")
    wide.columns.name = None
    if "Long" in wide.columns and "Short" in wide.columns:
        wide["Net"] = wide.get("Long", 0) - wide.get("Short", 0).abs()
    return wide.round(3)


def print_attribution(factor_df: pd.DataFrame):
    from tabulate import tabulate

    agg = attribution_summary(factor_df)
    print()
    print("  FACTOR ATTRIBUTION  (notional-weighted average exposure)")
    print(tabulate(agg.reset_index(), headers=["Factor", *agg.columns], tablefmt="simple", floatfmt="+.3f"))

    # Per-sector beta
    print()
    print("  BETA BY SECTOR")
    sector_beta = (
        factor_df.groupby(["sector", "side"])
        .apply(lambda g: np.average(g["beta"].fillna(1), weights=g["notional"].abs()), include_groups=False)
        .unstack("side")
        .round(2)
    )
    if "Long" in sector_beta and "Short" in sector_beta:
        sector_beta["Net β"] = sector_beta["Long"] - sector_beta.get("Short", 0).abs()
    print(tabulate(sector_beta.reset_index(), headers=["Sector", *sector_beta.columns], tablefmt="simple", floatfmt="+.2f"))
    print()
