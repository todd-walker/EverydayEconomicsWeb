#!/usr/bin/env python3
"""Download financing-rate series from FRED for time-cost amortization."""
import os
from pathlib import Path
import pandas as pd
from fredapi import Fred

OUTDIR = Path("data/raw/fred")
OUTDIR.mkdir(parents=True, exist_ok=True)

fred = Fred(api_key=os.environ["FRED_API_KEY"])

SERIES = {
    "MORTGAGE30US": "30yr_fixed_mortgage",      # weekly, 1971-  (Freddie Mac PMMS)
    "TERMCBAUTO48NS": "auto_loan_48m",          # monthly, 1972- (Fed G.19)
}

for sid, label in SERIES.items():
    s = fred.get_series(sid)
    df = s.rename(label).to_frame()
    df.index.name = "date"
    df = df.reset_index()
    df["year"] = pd.to_datetime(df["date"]).dt.year
    annual = df.groupby("year", as_index=False)[label].mean()
    annual.to_csv(OUTDIR / f"{sid}.csv", index=False)
    print(f"Wrote {OUTDIR / f'{sid}.csv'}  ({annual['year'].min()}-{annual['year'].max()})")
