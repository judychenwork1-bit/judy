import json
import re
import pandas as pd
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def load_ticker_map() -> dict:
    with open(DATA_DIR / "ticker_map.json") as f:
        raw = json.load(f)
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def load_pairs() -> pd.DataFrame:
    df = pd.read_excel(
        DATA_DIR / "2026_Long_Short_Pairs.xlsx",
        sheet_name="2026 Long-Short Pairs",
    )
    def split_names(cell):
        if not isinstance(cell, str):
            return []
        return [s.strip() for s in re.split(r"[、,，]", cell) if s.strip()]

    df["short_list"] = df["Short"].apply(split_names)
    df["long_list"]  = df["Long"].apply(split_names)
    return df


def resolve_tickers(names: list, ticker_map: dict) -> dict:
    """Return {name: ticker} for each name; warns on missing."""
    result = {}
    for n in names:
        t = ticker_map.get(n)
        if t is None:
            print(f"  [warn] No ticker for '{n}' — add to data/ticker_map.json")
        result[n] = t
    return result


def _cache_path(key: str) -> Path:
    return CACHE_DIR / f"{key}.csv"


def fetch_price_series(ticker: str, start: str, end: str) -> pd.Series:
    cache = _cache_path(ticker)
    if cache.exists():
        df = pd.read_csv(cache, index_col=0, parse_dates=True)
        if not df.empty and str(df.index[-1].date()) >= end:
            return df["close"].rename(ticker)

    try:
        import akshare as ak
        raw = ak.stock_zh_a_hist(
            symbol=ticker, period="daily",
            start_date=start.replace("-", ""),
            end_date=end.replace("-", ""),
            adjust="qfq",
        )
        raw = raw.rename(columns={"日期": "date", "收盘": "close"})
        raw = raw.set_index(pd.to_datetime(raw["date"]))[["close"]]
        raw.to_csv(cache)
        return raw["close"].rename(ticker)
    except Exception as e:
        print(f"  [warn] fetch {ticker}: {e}")
        if cache.exists():
            df = pd.read_csv(cache, index_col=0, parse_dates=True)
            return df["close"].rename(ticker)
        return pd.Series(dtype=float, name=ticker)


def fetch_prices(tickers: list, start: str, end: str = None) -> pd.DataFrame:
    if end is None:
        end = datetime.today().strftime("%Y-%m-%d")
    valid = [t for t in tickers if t is not None]
    series = [fetch_price_series(t, start, end) for t in valid]
    return pd.concat(series, axis=1) if series else pd.DataFrame()


def fetch_index(symbol: str = "000300", start: str = "2024-01-01", end: str = None) -> pd.Series:
    if end is None:
        end = datetime.today().strftime("%Y-%m-%d")
    cache = _cache_path(f"idx_{symbol}")
    if cache.exists():
        df = pd.read_csv(cache, index_col=0, parse_dates=True)
        if not df.empty and str(df.index[-1].date()) >= end:
            return df["close"].rename(symbol)
    try:
        import akshare as ak
        raw = ak.index_zh_a_hist(
            symbol=symbol, period="daily",
            start_date=start.replace("-", ""),
            end_date=end.replace("-", ""),
        )
        raw = raw.rename(columns={"日期": "date", "收盘": "close"})
        raw = raw.set_index(pd.to_datetime(raw["date"]))[["close"]]
        raw.to_csv(cache)
        return raw["close"].rename(symbol)
    except Exception as e:
        print(f"  [warn] fetch index {symbol}: {e}")
        if cache.exists():
            df = pd.read_csv(cache, index_col=0, parse_dates=True)
            return df["close"].rename(symbol)
        return pd.Series(dtype=float, name=symbol)
