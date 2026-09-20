#!/usr/bin/env python3
"""
Regenerate time_costs_total_share_by_cohort.pdf/png with the 65+ cohort removed.
Reads time_costs_repagent_by_age.csv from compute_time_costs.py.
"""
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from pathlib import Path

OUTDIR = Path("figures/Chapter3/output")
INFILE = OUTDIR / "time_costs_repagent_by_age.csv"

# Working-age cohorts only (65+ excluded)
COHORTS = [
    "25 to 34 Years",
    "35 to 44 Years",
    "45 to 54 Years",
    "55 to 64 Years",
]

def pctfmt(x, _pos):
    return f"{x*100:,.0f}%"

def main():
    df = pd.read_csv(INFILE)
    df = df[(df["year"] >= 1980) & (df["age_group"].isin(COHORTS))]
    df = df.sort_values(["year", "age_group"]).reset_index(drop=True)

    fig, ax = plt.subplots(figsize=(10, 6))
    for cohort in COHORTS:
        s = df[df["age_group"] == cohort][["year", "share_total"]].dropna()
        if not s.empty:
            ax.plot(s["year"], s["share_total"], lw=2, label=cohort)

    ax.set_xlabel("Year")
    ax.set_ylabel("Total Annual Time Cost (Share of Work-Year)")
    ax.yaxis.set_major_formatter(FuncFormatter(pctfmt))
    ax.set_xlim(1980, df["year"].max())
    ax.grid(True, alpha=0.3)
    ax.legend(frameon=False, ncol=2)
    ax.set_title("Total Annual Time Cost of Major Milestones by Working-Age Cohort")
    fig.tight_layout()
    fig.savefig(OUTDIR / "time_costs_total_share_by_cohort.png", dpi=250)
    fig.savefig(OUTDIR / "time_costs_total_share_by_cohort.pdf")
    plt.close(fig)
    print("Wrote", OUTDIR / "time_costs_total_share_by_cohort.pdf")

if __name__ == "__main__":
    main()
