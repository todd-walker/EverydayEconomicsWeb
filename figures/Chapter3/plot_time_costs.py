#!/usr/bin/env python3
"""
plot_time_costs.py  (representative-agent, amortized)

Reads time_costs_repagent_by_age.csv (from compute_time_costs.py) and produces:

1) time_costs_workyear_share_25to34.pdf/png
   25-34 cohort: stacked area of work-year share by category, 1980-2024.

2) time_costs_compare_1980_2024.pdf/png
   Grouped bars: work-year share by category, 1980 vs 2024, headline cohort.

3) time_costs_total_share_by_cohort.pdf/png
   Lines of total work-year share by cohort over time.

Also writes a brief text summary.

Inputs : figures/Chapter3/output/time_costs_repagent_by_age.csv
Outputs: figures/Chapter3/output/
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from pathlib import Path

OUTDIR = Path("figures/Chapter3/output")
INFILE = OUTDIR / "time_costs_repagent_by_age.csv"

COHORTS = [
    "25 to 34 Years",
    "35 to 44 Years",
    "45 to 54 Years",
    "55 to 64 Years",
    "65 Years and Older",
]
HEADLINE = "25 to 34 Years"
COMPARE_YEARS = [1980, 2024]

# milestone keys in the new schema (share_* / hours_* columns)
CATS = ["house", "degree", "car", "health"]
CAT_LABEL = {"house": "Housing", "degree": "Education",
             "car": "Transportation", "health": "Healthcare"}
COLORS = {"house": "#1f77b4", "degree": "#d62728",
          "car": "#2ca02c", "health": "#9467bd"}


def pctfmt(x, _pos):
    return f"{x*100:,.0f}%"


def yrfmt(x, _pos):
    return f"{x:,.2f}"


def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(INFILE).sort_values(["year", "age_group"]).reset_index(drop=True)
    df = df[df["year"] >= 1980].copy()

    # ---------- (1) 25-34 stacked area: work-year share by category ----------
    young = df[df["age_group"] == HEADLINE].sort_values("year")
    if not young.empty:
        fig, ax = plt.subplots(figsize=(10, 6))
        stacks = [young[f"share_{c}"].fillna(0).values for c in CATS]
        ax.stackplot(young["year"].values, stacks,
                     labels=[CAT_LABEL[c] for c in CATS],
                     colors=[COLORS[c] for c in CATS], alpha=0.85)
        ax.set_xlabel("Year")
        ax.set_ylabel("Share of a 2,000-Hour Work-Year")
        ax.yaxis.set_major_formatter(FuncFormatter(pctfmt))
        ax.set_xlim(1980, young["year"].max())
        ax.grid(True, alpha=0.3)
        ax.legend(frameon=False, ncol=4, loc="upper left")
        ax.set_title("Representative 25\u201334 Worker: Annual Time Cost of Major Milestones")
        fig.tight_layout()
        fig.savefig(OUTDIR / "time_costs_workyear_share_25to34.png", dpi=250)
        fig.savefig(OUTDIR / "time_costs_workyear_share_25to34.pdf")
        plt.close(fig)

    # ---------- (2) 1980 vs 2024 grouped bars (headline cohort) ----------
    cmp = df[(df["age_group"] == HEADLINE) & (df["year"].isin(COMPARE_YEARS))]
    cmp = cmp.set_index("year").reindex(COMPARE_YEARS)
    if not cmp[["share_total"]].isna().all().all():
        fig, ax = plt.subplots(figsize=(10, 6))
        x = np.arange(len(CATS))
        width = 0.38
        for i, yr in enumerate(COMPARE_YEARS):
            vals = [cmp.loc[yr, f"share_{c}"] for c in CATS]
            ax.bar(x + (i - 0.5) * width, vals, width, label=str(yr),
                   color=["#9ecae1" if i == 0 else "#1f77b4"][0] if False else None,
                   edgecolor="black", alpha=0.85)
        ax.set_xticks(x)
        ax.set_xticklabels([CAT_LABEL[c] for c in CATS])
        ax.set_ylabel("Share of a 2,000-Hour Work-Year")
        ax.yaxis.set_major_formatter(FuncFormatter(pctfmt))
        ax.grid(axis="y", alpha=0.3)
        ax.legend(frameon=False, title="Year")
        t80 = cmp.loc[1980, "share_total"]
        t24 = cmp.loc[2024, "share_total"]
        ax.set_title(f"Annual Time Cost of Milestones, 25\u201334 Worker: "
                     f"1980 ({t80*100:,.0f}% of work-year) vs 2024 ({t24*100:,.0f}%)")
        fig.tight_layout()
        fig.savefig(OUTDIR / "time_costs_compare_1980_2024.png", dpi=250)
        fig.savefig(OUTDIR / "time_costs_compare_1980_2024.pdf")
        plt.close(fig)

    # ---------- (3) Total work-year share, lines by cohort ----------
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
    ax.set_title("Total Annual Time Cost of Major Milestones by Age Cohort")
    fig.tight_layout()
    fig.savefig(OUTDIR / "time_costs_total_share_by_cohort.png", dpi=250)
    fig.savefig(OUTDIR / "time_costs_total_share_by_cohort.pdf")
    plt.close(fig)

    # ---------- (4) Summary ----------
    lines = []
    latest = int(df["year"].max())
    lines.append(f"Latest year in panel: {latest}\n")
    for cohort in COHORTS:
        sub = df[df["age_group"] == cohort].dropna(subset=["share_total"])
        if sub.empty:
            continue
        peak = sub.loc[sub["share_total"].idxmax()]
        curr = sub[sub["year"] == latest]
        curr = curr.iloc[0] if not curr.empty else peak
        base = sub[sub["year"] == 1980]
        base_str = ""
        if not base.empty and base.iloc[0]["share_total"] > 0:
            ch = (curr["share_total"] - base.iloc[0]["share_total"]) / base.iloc[0]["share_total"] * 100
            base_str = f" vs 1980: {ch:+.1f}%"
        denom = curr["share_total"] if curr["share_total"] > 0 else np.nan
        comp = ", ".join(
            f"{CAT_LABEL[c]}:{curr[f'share_{c}']/denom*100:,.0f}%"
            for c in CATS if denom == denom)
        lines.append(
            f"{cohort:>18s} \u2014 peak {peak['share_total']*100:,.0f}% in {int(peak['year'])}; "
            f"latest {curr['share_total']*100:,.0f}% ({curr['share_total']:.2f} work-years){base_str}; "
            f"composition: {comp}")

    cmp_rows = df[(df["age_group"] == HEADLINE) & (df["year"].isin(COMPARE_YEARS))]
    if not cmp_rows.empty:
        lines.append("\n25\u201334 headline comparison:")
        for _, r in cmp_rows.iterrows():
            lines.append(
                f"  {int(r['year'])}: total {r['share_total']*100:,.0f}% of work-year "
                f"({r['hours_total']:,.0f} hours), mortgage rate {r['mortgage_rate']*100:,.1f}%")

    (OUTDIR / "time_costs_summary.txt").write_text("\n".join(lines))
    print("Wrote figures and summary to", OUTDIR)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
