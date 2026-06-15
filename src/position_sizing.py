"""
Computes beta-neutral and dollar-neutral position sizes for each pair.

Beta regression uses 252 trading days of daily returns vs CSI 300 (000300).
For multi-name legs, notional is split equally across names in that leg.
"""

import numpy as np
import pandas as pd
from typing import Optional


def compute_beta(stock_returns: pd.Series, index_returns: pd.Series) -> float:
    """OLS beta of stock vs index on aligned daily returns."""
    aligned = pd.concat([stock_returns, index_returns], axis=1).dropna()
    if len(aligned) < 20:
        return 1.0  # fallback
    x = aligned.iloc[:, 1].values
    y = aligned.iloc[:, 0].values
    cov = np.cov(y, x)
    return float(cov[0, 1] / cov[1, 1]) if cov[1, 1] != 0 else 1.0


def compute_betas(prices: pd.DataFrame, index_prices: pd.Series, window: int = 252) -> dict:
    """Return {ticker: beta} using trailing `window` daily returns."""
    rets = prices.pct_change().iloc[-window:]
    idx_ret = index_prices.pct_change().iloc[-window:]
    return {col: compute_beta(rets[col], idx_ret) for col in rets.columns}


def dollar_neutral_sizes(pairs_df: pd.DataFrame, ticker_map: dict, notional_per_pair: float = 1_000_000) -> pd.DataFrame:
    """
    Returns position table with dollar-neutral sizing.
    Long and short legs each receive notional_per_pair / 2, split equally
    across names within each leg.
    """
    rows = []
    half = notional_per_pair / 2
    for _, row in pairs_df.iterrows():
        sector = row["板块"]
        for name in row["long_list"]:
            ticker = ticker_map.get(name)
            n = len(row["long_list"])
            rows.append({"sector": sector, "side": "Long", "name": name,
                         "ticker": ticker, "notional": half / n, "beta": None, "beta_adj_notional": None})
        for name in row["short_list"]:
            ticker = ticker_map.get(name)
            n = len(row["short_list"])
            rows.append({"sector": sector, "side": "Short", "name": name,
                         "ticker": ticker, "notional": -half / n, "beta": None, "beta_adj_notional": None})
    return pd.DataFrame(rows)


def beta_neutral_sizes(pairs_df: pd.DataFrame, ticker_map: dict, betas: dict,
                       notional_per_pair: float = 1_000_000) -> pd.DataFrame:
    """
    Beta-neutral sizing: for each pair, size long and short so that
    sum(w_long * beta_long) == sum(w_short * beta_short).

    Within each leg, individual names are equally weighted.
    Returns position table with columns: sector, side, name, ticker, beta,
    notional, beta_adj_notional.
    """
    rows = []
    for _, row in pairs_df.iterrows():
        sector = row["板块"]
        longs  = row["long_list"]
        shorts = row["short_list"]

        l_betas = [betas.get(ticker_map.get(n), 1.0) for n in longs]
        s_betas = [betas.get(ticker_map.get(n), 1.0) for n in shorts]

        avg_l_beta = np.mean(l_betas) if l_betas else 1.0
        avg_s_beta = np.mean(s_betas) if s_betas else 1.0

        # w_long * avg_l_beta = w_short * avg_s_beta, w_long + w_short = notional
        total = notional_per_pair
        w_long  = total * avg_s_beta / (avg_l_beta + avg_s_beta)
        w_short = total * avg_l_beta / (avg_l_beta + avg_s_beta)

        for name, beta in zip(longs, l_betas):
            ticker = ticker_map.get(name)
            rows.append({
                "sector": sector, "side": "Long", "name": name, "ticker": ticker,
                "beta": round(beta, 2),
                "notional": round(w_long / len(longs), 0),
                "beta_contribution": round(w_long / len(longs) * beta, 0),
            })
        for name, beta in zip(shorts, s_betas):
            ticker = ticker_map.get(name)
            rows.append({
                "sector": sector, "side": "Short", "name": name, "ticker": ticker,
                "beta": round(beta, 2),
                "notional": round(-w_short / len(shorts), 0),
                "beta_contribution": round(-w_short / len(shorts) * beta, 0),
            })
    return pd.DataFrame(rows)


def portfolio_summary(positions: pd.DataFrame) -> dict:
    long_notional  = positions.loc[positions["side"] == "Long",  "notional"].sum()
    short_notional = positions.loc[positions["side"] == "Short", "notional"].sum()
    net_notional   = long_notional + short_notional  # short is negative
    gross_notional = long_notional - short_notional

    net_beta_contrib = positions["beta_contribution"].sum() if "beta_contribution" in positions else None

    return {
        "long_notional":   long_notional,
        "short_notional":  short_notional,
        "net_notional":    net_notional,
        "gross_notional":  gross_notional,
        "net_beta":        round(net_beta_contrib / gross_notional, 4) if net_beta_contrib and gross_notional else None,
        "l_s_ratio":       round(abs(long_notional / short_notional), 3) if short_notional != 0 else None,
    }


def print_positions(positions: pd.DataFrame, betas: Optional[dict] = None):
    from tabulate import tabulate

    display = positions.copy()
    display["notional_k"] = (display["notional"] / 1000).map("{:,.0f}K".format)
    display["beta_str"]   = display["beta"].map(lambda x: f"{x:.2f}" if pd.notna(x) else "—")

    cols = ["sector", "side", "name", "ticker", "beta_str", "notional_k"]
    headers = ["Sector", "Side", "Name", "Ticker", "Beta", "Notional"]

    long_rows  = display[display["side"] == "Long"][cols].values.tolist()
    short_rows = display[display["side"] == "Short"][cols].values.tolist()

    print()
    print("  POSITIONS — Beta-Neutral Sizing")
    print(tabulate(long_rows + short_rows, headers=headers, tablefmt="simple"))

    summ = portfolio_summary(positions)
    print()
    print(f"  Long  {summ['long_notional']:>12,.0f}  Short  {summ['short_notional']:>12,.0f}")
    print(f"  Net   {summ['net_notional']:>12,.0f}  Gross  {summ['gross_notional']:>12,.0f}")
    if summ["net_beta"] is not None:
        print(f"  Net Beta  {summ['net_beta']:+.4f}  (target: ~0.0000)")
    print()
