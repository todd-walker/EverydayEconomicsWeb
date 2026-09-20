#!/usr/bin/env python3
"""
auto_price_series.py — 2024-dollar data only (no plots)

Builds an annual automobile price series using CPI:
  - CUUR0000SETA01: New Vehicles (NSA)
  - Anchored to $48,108 in 2024 (avg new-vehicle ATP July 2024)
  - Base year: 2000 (for reference index)

Outputs:
  - figures/Chapter3/output/auto_price_series.csv
"""

import os
from datetime import date
from pathlib import Path
import pandas as pd

# Prefer pandas_datareader; fall back to fredapi
try:
    from pandas_datareader import data as pdr
    HAVE_PDR = True
except Exception:
    HAVE_PDR = False
try:
    from fredapi import Fred
    HAVE_FREDAPI = True
except Exception:
    HAVE_FREDAPI = False

# ---- Hard-coded config ----
AUTO_ID       = "CUUR0000SETA01"  # CPI (NSA): New Vehicles
AUTO_ANCHOR_2024 = 48108.0        # 2024-dollar anchor (ATP). Change if you have a different benchmark.
BASE_YEAR     = 2000

def fred_series(sid: str, start: str, end: str) -> pd.DataFrame:
    """Fetch a FRED series as DataFrame."""
    if HAVE_PDR:
        try:
            df = pdr.DataReader(sid, "fred", start, end)
            df.columns = [sid]
            return df
        except Exception:
            pass
    if not HAVE_FREDAPI:
        raise ImportError("Install: pandas-datareader or fredapi")
    key = os.getenv("FRED_API_KEY")
    if not key:
        raise RuntimeError("Set FRED_API_KEY env var")
    fred = Fred(api_key=key)
    s = fred.get_series(sid, observation_start=start, observation_end=end)
    df = pd.DataFrame(s); df.index = pd.to_datetime(df.index); df.columns = [sid]
    return df

def annualize(df: pd.DataFrame, how: str = "mean") -> pd.DataFrame:
    """Aggregate to calendar-year mean."""
    rule = "YE-DEC"
    out = df.resample(rule).mean() if how == "mean" else df.resample(rule).last()
    out.index.name = "date"
    return out

def to_year(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy(); d["year"] = d.index.year
    return d.groupby("year").last().sort_index()

def build_series(start_year: int, end_year: int) -> pd.DataFrame:
    # New Vehicles CPI → annual mean
    a_m = fred_series(AUTO_ID, start=f"{start_year}-01-01", end=f"{end_year}-12-31")
    a_a = to_year(annualize(a_m, "mean")).rename(columns={AUTO_ID: "auto_cpi_index"})
    a_a = a_a.loc[(a_a.index >= start_year) & (a_a.index <= end_year)].copy()

    # Index (2000 = 100)
    a_a[f"index_{BASE_YEAR}"] = pd.NA
    if BASE_YEAR in a_a.index:
        base_val = float(a_a.loc[BASE_YEAR, "auto_cpi_index"])
        a_a[f"index_{BASE_YEAR}"] = (a_a["auto_cpi_index"] / base_val) * 100.0

    # Convert to TRUE 2024-dollar LEVEL via anchor:
    # auto_2024d(y) = AUTO_ANCHOR_2024 * (CPI_auto(y) / CPI_auto(2024))
    if (a_a.index == 2024).any():
        idx_2024 = float(a_a.loc[2024, "auto_cpi_index"])
    else:
        idx_2024 = float(a_a["auto_cpi_index"].iloc[-1])  # fallback to last year if 2024 not present
    a_a["auto_2024d"] = AUTO_ANCHOR_2024 * (a_a["auto_cpi_index"] / idx_2024)

    return a_a[[f"index_{BASE_YEAR}", "auto_cpi_index", "auto_2024d"]]

def main():
    start_year, end_year = 1947, date.today().year
    outdir = Path("figures/Chapter3/output")
    outdir.mkdir(parents=True, exist_ok=True)

    df = build_series(start_year, end_year)
    df.reset_index().rename(columns={"index": "year"}).to_csv(outdir / "auto_price_series.csv", index=False)

    print("Saved:")
    print(" -", outdir / "auto_price_series.csv")
    print("Columns: year, index_2000, auto_cpi_index, auto_2024d (in 2024 dollars)")
    print(f"Anchored 2024-dollar level: ${AUTO_ANCHOR_2024:,.0f}")

if __name__ == "__main__":
    if not (HAVE_PDR or HAVE_FREDAPI):
        print("Install: pandas-datareader or fredapi"); raise SystemExit(1)
    if HAVE_FREDAPI and not os.getenv("FRED_API_KEY"):
        print("NOTE: FRED_API_KEY not set.")
    main()
