#!/usr/bin/env python3
"""
housing_price_series.py — 2024-dollar output only

Builds an annual series for the median sales price of new houses (MSPUS),
converts it to 2024 dollars, and saves results to CSV for later combined plots.

No figures are produced here.
"""

import os
from datetime import date
from pathlib import Path
import pandas as pd

# FRED access
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

MSPUS_ID = "MSPUS"       # Median Sales Price of Houses Sold (NSA)
CPI_ID   = "CPIAUCNS"    # CPI-U (NSA)

def fred_series(sid, start, end):
    """Fetch a FRED series."""
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
    df = pd.DataFrame(s)
    df.index = pd.to_datetime(df.index)
    df.columns = [sid]
    return df

def annualize(df, how="mean"):
    """Aggregate to calendar-year mean."""
    rule = "YE-DEC"
    return (df.resample(rule).mean() if how == "mean" else df.resample(rule).last()).rename_axis("date")

def to_year(df):
    out = df.copy()
    out["year"] = out.index.year
    return out.groupby("year").last().sort_index()

def build_series(start, end, base=2000):
    # MSPUS (nominal house price)
    p = to_year(annualize(fred_series(MSPUS_ID, f"{start}-01-01", f"{end}-12-31")))
    p = p.rename(columns={MSPUS_ID: "house_price_nom"})

    # CPI-U (deflator)
    cpi = to_year(annualize(fred_series(CPI_ID, f"{start}-01-01", f"{end}-12-31")))
    cpi = cpi.rename(columns={CPI_ID: "cpi"}).loc[p.index]

    # Real 2024 dollars
    anchor_year = 2024 if 2024 in cpi.index else int(cpi.index.max())
    anchor_val  = float(cpi.loc[anchor_year, "cpi"])
    p["house_price_2024d"] = p["house_price_nom"] * (anchor_val / cpi["cpi"])

    # Nominal index (for reference if needed)
    if base in p.index:
        base_val = float(p.loc[base, "house_price_nom"])
        p[f"index_{base}"] = p["house_price_nom"] / base_val * 100
    else:
        p[f"index_{base}"] = pd.NA

    return p[[f"index_{base}", "house_price_nom", "house_price_2024d"]]

def main():
    start, end = 1963, date.today().year
    outdir = Path("figures/Chapter3/output")
    outdir.mkdir(parents=True, exist_ok=True)

    df = build_series(start, end, base=2000)
    df.reset_index().rename(columns={"index": "year"}).to_csv(outdir / "housing_price_series.csv", index=False)

    print("Saved:")
    print(" -", outdir / "housing_price_series.csv")
    print("Columns: year, index_2000, house_price_nom, house_price_2024d (in 2024 dollars)")

if __name__ == "__main__":
    if not (HAVE_PDR or HAVE_FREDAPI):
        print("Install: pandas-datareader or fredapi"); raise SystemExit(1)
    if HAVE_FREDAPI and not os.getenv("FRED_API_KEY"):
        print("NOTE: FRED_API_KEY not set.")
    main()
