#!/usr/bin/env python3
"""
health_price_series.py — 2024-dollar data only (no plots)

Builds an annual health-care price series from CPI:
  - CPIMEDSL: Medical Care (Seasonally Adjusted, index 1982–84=100)
  - Anchors to a 2024 dollar level (default: $6,500) so the series is in 2024 USD
  - Also provides a 2000=100 reference index

Outputs:
  - figures/Chapter3/output/health_price_series.csv
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
HEALTH_ID         = "CPIMEDSL"   # CPI (SA): Medical Care
HEALTH_ANCHOR_2024 = 6500.0      # 2024-dollar anchor (edit to your benchmark if desired)
BASE_YEAR         = 2000

def fred_series(sid: str, start: str, end: str) -> pd.DataFrame:
    """Fetch a FRED series as DataFrame with one column named <sid>."""
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
    # Medical Care CPI (SA) → annual mean
    h_m = fred_series(HEALTH_ID, start=f"{start_year}-01-01", end=f"{end_year}-12-31")
    h_a = to_year(annualize(h_m, "mean")).rename(columns={HEALTH_ID: "health_cpi_index"})
    h_a = h_a.loc[(h_a.index >= start_year) & (h_a.index <= end_year)].copy()

    # Reference index (2000=100)
    h_a[f"index_{BASE_YEAR}"] = pd.NA
    if BASE_YEAR in h_a.index:
        base_val = float(h_a.loc[BASE_YEAR, "health_cpi_index"])
        h_a[f"index_{BASE_YEAR}"] = (h_a["health_cpi_index"] / base_val) * 100.0

    # TRUE 2024-dollar LEVEL via anchor:
    # health_2024d(y) = HEALTH_ANCHOR_2024 * (CPI_health(y) / CPI_health(2024))
    if (h_a.index == 2024).any():
        idx_2024 = float(h_a.loc[2024, "health_cpi_index"])
    else:
        idx_2024 = float(h_a["health_cpi_index"].iloc[-1])  # fallback if 2024 not available
    h_a["health_2024d"] = HEALTH_ANCHOR_2024 * (h_a["health_cpi_index"] / idx_2024)

    return h_a[[f"index_{BASE_YEAR}", "health_cpi_index", "health_2024d"]]

def main():
    start_year, end_year = 1947, date.today().year
    outdir = Path("figures/Chapter3/output")
    outdir.mkdir(parents=True, exist_ok=True)

    df = build_series(start_year, end_year)
    df.reset_index().rename(columns={"index": "year"}).to_csv(outdir / "health_price_series.csv", index=False)

    print("Saved:")
    print(" -", outdir / "health_price_series.csv")
    print("Columns: year, index_2000, health_cpi_index, health_2024d (in 2024 dollars)")
    print(f"Anchored 2024-dollar level: ${HEALTH_ANCHOR_2024:,.0f}")
    print(f"Series used: {HEALTH_ID} (Medical Care, SA)")

if __name__ == "__main__":
    if not (HAVE_PDR or HAVE_FREDAPI):
        print("Install: pandas-datareader or fredapi"); raise SystemExit(1)
    if HAVE_FREDAPI and not os.getenv("FRED_API_KEY"):
        print("NOTE: FRED_API_KEY not set.")
    main()
