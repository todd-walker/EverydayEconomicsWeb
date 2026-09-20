#!/usr/bin/env python3
"""
education_price_series.py — 2024-dollar data only (no plots)

Builds an annual education price series using CPI:
  - CUSR0000SEEB: Tuition, Other School Fees, and Childcare (SA)
  - Anchored to $38,270 (NCES/IPEDS, 2024)
  - Base year: 2000 (for reference index)

Outputs:
  - figures/Chapter3/output/tuition_price_series.csv
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
TUITION_ID   = "CUSR0000SEEB"  # Education CPI (SA): tuition, fees, childcare
ANCHOR_2024  = 38270.0         # 2024 average annual cost (NCES/IPEDS)
BASE_YEAR    = 2000

def fred_series(series_id: str, start: str, end: str) -> pd.DataFrame:
    """Fetch FRED series as DataFrame."""
    if HAVE_PDR:
        try:
            df = pdr.DataReader(series_id, "fred", start, end)
            df.columns = [series_id]
            return df
        except Exception:
            pass
    if not HAVE_FREDAPI:
        raise ImportError("Install: pandas-datareader or fredapi")
    key = os.getenv("FRED_API_KEY")
    if not key:
        raise RuntimeError("Set FRED_API_KEY env var")
    fred = Fred(api_key=key)
    s = fred.get_series(series_id, observation_start=start, observation_end=end)
    df = pd.DataFrame(s); df.index = pd.to_datetime(df.index); df.columns = [series_id]
    return df

def annualize(df: pd.DataFrame, how: str = "mean") -> pd.DataFrame:
    """Calendar-year aggregation (mean)."""
    rule = "YE-DEC"
    out = df.resample(rule).mean() if how == "mean" else df.resample(rule).last()
    out.index.name = "date"
    return out

def to_year(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["year"] = d.index.year
    return d.groupby("year").last().sort_index()

def build_series(start_year: int, end_year: int) -> pd.DataFrame:
    # Education CPI → annual mean
    edu_m = fred_series(TUITION_ID, start=f"{start_year}-01-01", end=f"{end_year}-12-31")
    edu_a = to_year(annualize(edu_m, "mean")).rename(columns={TUITION_ID: "tuition_cpi_index"})
    edu_a = edu_a.loc[(edu_a.index >= start_year) & (edu_a.index <= end_year)].copy()

    # Index (2000=100)
    edu_a[f"index_{BASE_YEAR}"] = pd.NA
    if BASE_YEAR in edu_a.index:
        base_val = float(edu_a.loc[BASE_YEAR, "tuition_cpi_index"])
        edu_a[f"index_{BASE_YEAR}"] = (edu_a["tuition_cpi_index"] / base_val) * 100.0

    # Convert to 2024-dollar LEVEL
    if (edu_a.index == 2024).any():
        idx_2024 = float(edu_a.loc[2024, "tuition_cpi_index"])
    else:
        idx_2024 = float(edu_a["tuition_cpi_index"].iloc[-1])  # fallback to last year
    edu_a["tuition_2024d"] = ANCHOR_2024 * (edu_a["tuition_cpi_index"] / idx_2024)

    return edu_a[[f"index_{BASE_YEAR}", "tuition_cpi_index", "tuition_2024d"]]

def main():
    start_year, end_year = 1978, date.today().year
    outdir = Path("figures/Chapter3/output")
    outdir.mkdir(parents=True, exist_ok=True)

    df = build_series(start_year, end_year)
    df.reset_index().rename(columns={"index": "year"}).to_csv(outdir / "tuition_price_series.csv", index=False)

    print("Saved:")
    print(" -", outdir / "tuition_price_series.csv")
    print("Columns: year, index_2000, tuition_cpi_index, tuition_2024d (in 2024 dollars)")
    print(f"Anchored 2024-dollar level: ${ANCHOR_2024:,.0f} (NCES/IPEDS)")

if __name__ == "__main__":
    if not (HAVE_PDR or HAVE_FREDAPI):
        print("Install: pandas-datareader or fredapi"); raise SystemExit(1)
    if HAVE_FREDAPI and not os.getenv("FRED_API_KEY"):
        print("NOTE: FRED_API_KEY not set.")
    main()
