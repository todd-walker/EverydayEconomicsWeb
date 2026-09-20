#!/usr/bin/env python3
"""
combine_expenditures_dualaxes_2024d.py

Plots all major expenditures in 2024 dollars:
 - Housing (left y-axis, thousands of 2024 dollars)
 - Education, Transportation, Healthcare (right y-axis, thousands of 2024 dollars)

Inputs:
  - figures/Chapter3/output/housing_price_series.csv
  - figures/Chapter3/output/tuition_price_series.csv
  - figures/Chapter3/output/auto_price_series.csv
  - figures/Chapter3/output/health_price_series.csv

Outputs:
  - figures/Chapter3/output/expenditures_dualaxes_2024d.png
  - figures/Chapter3/output/expenditures_dualaxes_2024d.pdf
"""

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from pathlib import Path

OUTDIR = Path("figures/Chapter3/output")

def kfmt(x, _pos):
    return f"{x:,.0f}"

def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)

    # Load data
    housing = pd.read_csv(OUTDIR / "housing_price_series.csv", usecols=["year", "house_price_2024d"])
    edu     = pd.read_csv(OUTDIR / "tuition_price_series.csv", usecols=["year", "tuition_2024d"])
    auto    = pd.read_csv(OUTDIR / "auto_price_series.csv", usecols=["year", "auto_2024d"])
    health  = pd.read_csv(OUTDIR / "health_price_series.csv", usecols=["year", "health_2024d"])

    # Merge
    df = housing.merge(edu, on="year", how="outer") \
                .merge(auto, on="year", how="outer") \
                .merge(health, on="year", how="outer") \
                .sort_values("year")

    # --- Dual-axis plot ---
    fig, ax1 = plt.subplots(figsize=(10, 6))
    ax2 = ax1.twinx()

    # Left axis: housing (thousands of 2024 dollars)
    ax1.plot(df["year"], df["house_price_2024d"]/1000, color="tab:blue", linewidth=2, label="Housing (new homes)")
    ax1.set_ylabel("Housing (Thousands of 2024 Dollars)", color="tab:blue")
    ax1.tick_params(axis="y", labelcolor="tab:blue")
    ax1.yaxis.set_major_formatter(FuncFormatter(kfmt))

    # Right axis: education, autos, health (thousands)
    ax2.plot(df["year"], df["tuition_2024d"]/1000, color="tab:red", linewidth=2, label="Education (COA)")
    ax2.plot(df["year"], df["auto_2024d"]/1000, color="tab:green", linewidth=2, label="Transportation (New Vehicle)")
    ax2.plot(df["year"], df["health_2024d"]/1000, color="tab:purple", linewidth=2, label="Healthcare")
    ax2.set_ylabel("Education, Transportation, Healthcare\n(Thousands of 2024 Dollars)", color="tab:gray")
    ax2.tick_params(axis="y", labelcolor="tab:gray")
    ax2.yaxis.set_major_formatter(FuncFormatter(kfmt))

    ax1.set_xlabel("Year")
    ax1.set_title("Major Household Expenditures in 2024 Dollars (Dual Axes)")
    ax1.grid(True, alpha=0.3)

    # Combine legends from both axes
    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax2.legend(lines + lines2, labels + labels2, loc="upper left", frameon=False, fontsize=9)

    fig.tight_layout()
    plt.savefig(OUTDIR / "expenditures_dualaxes_2024d.png", dpi=250)
    plt.savefig(OUTDIR / "expenditures_dualaxes_2024d.pdf")
    plt.close()

    print("Wrote:")
    print(" -", OUTDIR / "expenditures_dualaxes_2024d.png")
    print(" -", OUTDIR / "expenditures_dualaxes_2024d.pdf")

if __name__ == "__main__":
    main()
