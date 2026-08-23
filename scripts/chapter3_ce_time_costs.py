#!/usr/bin/env python3
"""
chapter3_ce_time_costs.py

Redo the Chapter 3 / inflation-by-age "time cost" analysis using BLS Consumer
Expenditure Survey (CE) age-specific annual spending means instead of assigning
large asset purchases mechanically across age groups.

This replaces the stronger assumptions in the earlier Chapter 3 workflow:
  - No 1/4 of a new house price assigned to each working-age cohort.
  - No 4x annual college cost assigned only to ages 25--34.
  - No 1/4 of a new vehicle purchase assigned to each working-age cohort.
  - No ad hoc healthcare split across cohorts.

New design:
  1) Use 2024 CE published annual mean expenditures by age of reference person
     for four categories: Housing, Education, Transportation, Healthcare.
  2) Reprice those 2024 age-specific spending anchors backward/forward with
     category CPI indexes and convert to 2024 all-items dollars.
  3) Divide by age-specific median income in 2024 dollars to get years/hours of
     labor.

Interpretation:
  This is a fixed-2024-age-basket exercise. It asks: how many hours would a
  median person in age group a need to work in year y to buy the 2024 CE annual
  spending bundle for that same age group, after repricing each category by its
  category CPI and expressing the result in 2024 dollars?

Inputs expected in an EverydayEconomics project root:
  data/processed/chapter5/ce_items_by_age_2024.csv
      from scripts/chapter5_ce_age_weights.py

  figures/Chapter3/median_income_by_age.csv
      from figures/Chapter3/wages_by_age.py

Outputs:
  data/processed/chapter5/time_costs_ce_age_by_age_2024.csv
  data/processed/chapter5/time_costs_ce_age_latest_2024.csv
  data/processed/chapter5/time_costs_ce_age_summary_2024.txt
  figures/Chapter3/output/time_costs_ce_age_lines_by_cohort_2024.pdf/png
  figures/Chapter3/output/time_costs_ce_age_latest_stacked_hours_2024.pdf/png
  figures/Chapter3/output/time_costs_ce_age_25to34_breakdown_area_2024.pdf/png
  figures/Chapter3/output/time_costs_ce_age_education_spending_by_age_2024.pdf/png
  figures/Chapter3/output/time_costs_ce_age_latest_2024.tex

Run:
  python scripts/chapter3_ce_time_costs.py --anchor-year 2024 --start-year 1980
"""

from __future__ import annotations

import argparse
import math
import sys
import urllib.request
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

WORK_HOURS_PER_YEAR = 2000.0

# CE age labels produced by chapter5_ce_age_weights.py -> Census wage age labels.
AGE_MAP = {
    "25-34 years": "25 to 34 Years",
    "35-44 years": "35 to 44 Years",
    "45-54 years": "45 to 54 Years",
    "55-64 years": "55 to 64 Years",
    "65 years and older": "65 Years and Older",
}
COHORTS = list(AGE_MAP.values())

# Four-category replacement for the old Chapter 3 time-cost model.
# These are CE item labels on the spending side and CPI/FRED series on the price side.
CATEGORY_SPEC = {
    "housing": {
        "display": "Housing",
        "ce_items": ["Housing"],
        "fred_id": "CPIHOSSL",       # CPI-U: Housing, SA
    },
    "education": {
        "display": "Education",
        "ce_items": ["Education"],
        "fred_id": "CUSR0000SEEB",   # CPI-U: Tuition, other school fees, childcare, SA
    },
    "transport": {
        "display": "Transportation",
        "ce_items": ["Transportation"],
        "fred_id": "CPITRNSL",       # CPI-U: Transportation, SA
    },
    "health": {
        "display": "Healthcare",
        "ce_items": ["Healthcare", "Health care"],
        "fred_id": "CPIMEDSL",       # CPI-U: Medical care, SA
    },
}
ALL_ITEMS_ID = "CPIAUCSL"             # CPI-U: All items, SA


def find_repo_root() -> Path:
    """Find repo root from this script location or current working directory."""
    candidates = [Path.cwd(), Path(__file__).resolve().parent, Path(__file__).resolve().parent.parent]
    for start in candidates:
        p = start.resolve()
        for q in [p, *p.parents]:
            if (q / "main.tex").exists() and (q / "figures").exists():
                return q
    return Path.cwd().resolve()


def normalize_text(x: object) -> str:
    return " ".join(str(x).replace("\n", " ").split()).strip()


def first_existing_col(df: pd.DataFrame, candidates: Iterable[str]) -> str:
    lower = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in lower:
            return lower[cand.lower()]
    raise KeyError(f"None of these columns were found: {candidates}. Available: {list(df.columns)}")


def load_ce_anchors(processed_dir: Path, anchor_year: int) -> pd.DataFrame:
    """Return age_group x category CE annual mean spending anchors in anchor-year dollars."""
    ce_path = processed_dir / f"ce_items_by_age_{anchor_year}.csv"
    if not ce_path.exists():
        raise FileNotFoundError(
            f"Missing {ce_path}. Run: python scripts/chapter5_ce_age_weights.py --year {anchor_year}"
        )

    ce = pd.read_csv(ce_path)
    age_col = first_existing_col(ce, ["age_group", "Age Group"])
    item_col = first_existing_col(ce, ["item", "Item"])
    mean_col = first_existing_col(ce, ["mean", "Mean"])

    ce = ce[[age_col, item_col, mean_col]].copy()
    ce.columns = ["ce_age_group", "item", "mean_annual_spending_2024"]
    ce["ce_age_group"] = ce["ce_age_group"].map(normalize_text)
    ce["item"] = ce["item"].map(normalize_text)
    ce["mean_annual_spending_2024"] = pd.to_numeric(ce["mean_annual_spending_2024"], errors="coerce")

    ce = ce[ce["ce_age_group"].isin(AGE_MAP.keys())].copy()
    ce["age_group"] = ce["ce_age_group"].map(AGE_MAP)

    rows = []
    for _, age_row in ce[["ce_age_group", "age_group"]].drop_duplicates().iterrows():
        age_ce = age_row["ce_age_group"]
        age_out = age_row["age_group"]
        sub = ce[ce["ce_age_group"] == age_ce]
        lookup = {normalize_text(r["item"]).lower(): r["mean_annual_spending_2024"] for _, r in sub.iterrows()}
        for cat, spec in CATEGORY_SPEC.items():
            val = np.nan
            matched_item = None
            for item in spec["ce_items"]:
                key = normalize_text(item).lower()
                if key in lookup:
                    val = lookup[key]
                    matched_item = item
                    break
            if pd.isna(val):
                raise KeyError(f"Could not find CE item {spec['ce_items']} for age group {age_ce}")
            rows.append({
                "anchor_year": anchor_year,
                "age_group": age_out,
                "category": cat,
                "category_label": spec["display"],
                "ce_item": matched_item,
                "mean_annual_spending_anchor_dollars": float(val),
            })

    anchors = pd.DataFrame(rows)
    anchors["age_group"] = pd.Categorical(anchors["age_group"], COHORTS, ordered=True)
    anchors["category"] = pd.Categorical(anchors["category"], list(CATEGORY_SPEC.keys()), ordered=True)
    return anchors.sort_values(["age_group", "category"]).reset_index(drop=True)


def load_wages(wage_path: Path) -> pd.DataFrame:
    if not wage_path.exists():
        raise FileNotFoundError(f"Missing wage file: {wage_path}. Run figures/Chapter3/wages_by_age.py first.")
    w = pd.read_csv(wage_path)
    year_col = first_existing_col(w, ["year", "Year"])
    age_col = first_existing_col(w, ["age_group", "Age Group"])
    wage_col = first_existing_col(w, ["wage_annual_2024d", "Combined Median (2024 $)"])
    w = w[[year_col, age_col, wage_col]].copy()
    w.columns = ["year", "age_group", "wage_annual_2024d"]
    w["year"] = pd.to_numeric(w["year"], errors="coerce").astype("Int64")
    w["age_group"] = w["age_group"].map(normalize_text)
    w["wage_annual_2024d"] = pd.to_numeric(w["wage_annual_2024d"], errors="coerce")
    w = w[w["age_group"].isin(COHORTS)].copy()
    return w.dropna(subset=["year", "wage_annual_2024d"]).astype({"year": int})


def download_fred_csv(series_id: str, raw_dir: Path, overwrite: bool = False) -> Path:
    raw_dir.mkdir(parents=True, exist_ok=True)
    out = raw_dir / f"{series_id}.csv"
    if out.exists() and out.stat().st_size > 0 and not overwrite:
        return out
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
            "Accept": "text/csv,application/csv,*/*",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            content = resp.read()
    except Exception as exc:
        raise RuntimeError(f"Could not download FRED series {series_id} from {url}: {exc}") from exc
    out.write_bytes(content)
    return out


def annual_fred(series_id: str, raw_dir: Path, overwrite: bool = False) -> pd.DataFrame:
    path = download_fred_csv(series_id, raw_dir, overwrite=overwrite)
    df = pd.read_csv(path)
    if "observation_date" in df.columns:
        date_col = "observation_date"
    else:
        date_col = df.columns[0]
    val_col = series_id if series_id in df.columns else df.columns[-1]
    df = df[[date_col, val_col]].copy()
    df.columns = ["date", series_id]
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df[series_id] = pd.to_numeric(df[series_id].replace(".", np.nan), errors="coerce")
    df = df.dropna(subset=["date", series_id])
    df["year"] = df["date"].dt.year
    out = df.groupby("year", as_index=False)[series_id].mean()
    out = out.rename(columns={series_id: "index_value"})
    out["fred_id"] = series_id
    return out[["year", "fred_id", "index_value"]]


def build_price_panel(raw_fred_dir: Path, start_year: int, end_year: int, anchor_year: int, overwrite: bool = False) -> pd.DataFrame:
    series_ids = [ALL_ITEMS_ID] + [spec["fred_id"] for spec in CATEGORY_SPEC.values()]
    pieces = [annual_fred(sid, raw_fred_dir, overwrite=overwrite) for sid in series_ids]
    idx = pd.concat(pieces, ignore_index=True)
    idx = idx[(idx["year"] >= start_year) & (idx["year"] <= end_year)].copy()

    # Build all-items deflator, CPI_anchor / CPI_y.
    all_items = idx[idx["fred_id"] == ALL_ITEMS_ID][["year", "index_value"]].rename(columns={"index_value": "all_items_cpi"})
    if anchor_year not in set(all_items["year"]):
        raise ValueError(f"All-items CPI does not contain anchor year {anchor_year}")
    all_anchor = float(all_items.loc[all_items["year"] == anchor_year, "all_items_cpi"].iloc[0])
    all_items["all_items_deflator_to_anchor"] = all_anchor / all_items["all_items_cpi"]

    rows = []
    for cat, spec in CATEGORY_SPEC.items():
        sid = spec["fred_id"]
        sub = idx[idx["fred_id"] == sid][["year", "index_value"]].copy()
        if anchor_year not in set(sub["year"]):
            raise ValueError(f"{sid} does not contain anchor year {anchor_year}")
        cat_anchor = float(sub.loc[sub["year"] == anchor_year, "index_value"].iloc[0])
        sub["category"] = cat
        sub["category_label"] = spec["display"]
        sub["fred_id"] = sid
        sub["category_price_relative_to_anchor"] = sub["index_value"] / cat_anchor
        sub = sub.merge(all_items, on="year", how="left")
        # Convert an anchor-year dollar amount into year-y price level, then express that in anchor-year dollars.
        sub["real_price_factor_anchor_dollars"] = (
            sub["category_price_relative_to_anchor"] * sub["all_items_deflator_to_anchor"]
        )
        rows.append(sub)
    price = pd.concat(rows, ignore_index=True)
    price = price.dropna(subset=["real_price_factor_anchor_dollars"])
    return price


def compute_time_costs(
    anchors: pd.DataFrame,
    wages: pd.DataFrame,
    price: pd.DataFrame,
    start_year: int,
    end_year: int,
) -> pd.DataFrame:
    years = pd.DataFrame({"year": list(range(start_year, end_year + 1))})
    ages = pd.DataFrame({"age_group": COHORTS})
    cats = pd.DataFrame({"category": list(CATEGORY_SPEC.keys())})
    panel = years.merge(ages, how="cross").merge(cats, how="cross")

    panel = panel.merge(anchors, on=["age_group", "category"], how="left")
    panel = panel.merge(price[["year", "category", "fred_id", "real_price_factor_anchor_dollars"]], on=["year", "category"], how="left")
    panel = panel.merge(wages, on=["year", "age_group"], how="left")

    panel["category_cost_2024d"] = (
        panel["mean_annual_spending_anchor_dollars"] * panel["real_price_factor_anchor_dollars"]
    )
    panel["time_years_category"] = panel["category_cost_2024d"] / panel["wage_annual_2024d"]
    panel["time_hours_category"] = panel["time_years_category"] * WORK_HOURS_PER_YEAR
    panel["hourly_2024d"] = panel["wage_annual_2024d"] / WORK_HOURS_PER_YEAR

    totals = (
        panel.groupby(["year", "age_group"], observed=True)
        .agg(
            wage_annual_2024d=("wage_annual_2024d", "first"),
            hourly_2024d=("hourly_2024d", "first"),
            time_years_total=("time_years_category", "sum"),
            time_hours_total=("time_hours_category", "sum"),
            total_cost_2024d=("category_cost_2024d", "sum"),
        )
        .reset_index()
    )
    wide_cost = panel.pivot_table(
        index=["year", "age_group"], columns="category", values="category_cost_2024d", aggfunc="sum", observed=True
    ).reset_index()
    wide_years = panel.pivot_table(
        index=["year", "age_group"], columns="category", values="time_years_category", aggfunc="sum", observed=True
    ).reset_index()
    wide_hours = panel.pivot_table(
        index=["year", "age_group"], columns="category", values="time_hours_category", aggfunc="sum", observed=True
    ).reset_index()

    def prefix_cols(df: pd.DataFrame, prefix: str) -> pd.DataFrame:
        return df.rename(columns={c: f"{prefix}_{c}" for c in CATEGORY_SPEC if c in df.columns})

    out = totals.merge(prefix_cols(wide_cost, "cost_2024d"), on=["year", "age_group"], how="left")
    out = out.merge(prefix_cols(wide_years, "time_years"), on=["year", "age_group"], how="left")
    out = out.merge(prefix_cols(wide_hours, "time_hours"), on=["year", "age_group"], how="left")

    out["age_group"] = pd.Categorical(out["age_group"], COHORTS, ordered=True)
    out = out.sort_values(["year", "age_group"]).reset_index(drop=True)
    return out


def dollar_fmt(x: float) -> str:
    if pd.isna(x):
        return ""
    return f"${x:,.0f}"


def write_latex_latest(latest: pd.DataFrame, fig_dir: Path, anchor_year: int) -> None:
    table = latest.copy()
    table = table[[
        "age_group", "wage_annual_2024d", "total_cost_2024d", "time_hours_total",
        "time_hours_housing", "time_hours_education", "time_hours_transport", "time_hours_health",
    ]]
    table = table.rename(columns={
        "age_group": "Age group",
        "wage_annual_2024d": "Median income",
        "total_cost_2024d": "CE basket cost",
        "time_hours_total": "Total hours",
        "time_hours_housing": "Housing",
        "time_hours_education": "Education",
        "time_hours_transport": "Transportation",
        "time_hours_health": "Healthcare",
    })
    for col in ["Median income", "CE basket cost"]:
        table[col] = table[col].map(dollar_fmt)
    for col in ["Total hours", "Housing", "Education", "Transportation", "Healthcare"]:
        table[col] = table[col].map(lambda x: "" if pd.isna(x) else f"{x:,.0f}")
    tex = table.to_latex(index=False, escape=False, caption=(
        f"Time cost of selected CE expenditures by age group, {anchor_year}. "
        "Spending amounts are CE annual means by age of reference person; hours use median income by age."
    ), label="tab:ce-time-costs-age")
    (fig_dir / f"time_costs_ce_age_latest_{anchor_year}.tex").write_text(tex)


def yfmt(x, _pos):
    return f"{x:,.2f}"


def hfmt(x, _pos):
    return f"{x:,.0f}"


def make_plots(panel: pd.DataFrame, anchors: pd.DataFrame, fig_dir: Path, anchor_year: int, plot_start_year: int) -> None:
    fig_dir.mkdir(parents=True, exist_ok=True)
    df = panel[panel["year"] >= plot_start_year].copy()

    # 1) Total time years by cohort.
    fig, ax = plt.subplots(figsize=(10, 6))
    for cohort in COHORTS:
        s = df[df["age_group"] == cohort][["year", "time_years_total"]].dropna()
        if not s.empty:
            ax.plot(s["year"], s["time_years_total"], lw=2, label=cohort)
    ax.set_xlabel("Year")
    ax.set_ylabel("Years of labor")
    ax.yaxis.set_major_formatter(FuncFormatter(yfmt))
    ax.grid(True, alpha=0.3)
    ax.legend(frameon=False, ncol=2)
    ax.set_title("Time cost of CE age-specific expenditure basket")
    fig.tight_layout()
    fig.savefig(fig_dir / f"time_costs_ce_age_lines_by_cohort_{anchor_year}.pdf")
    fig.savefig(fig_dir / f"time_costs_ce_age_lines_by_cohort_{anchor_year}.png", dpi=300)
    plt.close(fig)

    # 2) Latest-year stacked bars in hours.
    latest_year = int(df["year"].dropna().max())
    latest = df[df["year"] == latest_year].copy().set_index("age_group").reindex(COHORTS)
    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(len(COHORTS))
    bottom = np.zeros(len(COHORTS))
    for cat, spec in CATEGORY_SPEC.items():
        vals = latest[f"time_hours_{cat}"].fillna(0).to_numpy()
        ax.bar(x, vals, bottom=bottom, label=spec["display"])
        bottom += vals
    ax.set_xticks(x)
    ax.set_xticklabels([c.replace(" Years", "").replace(" and Older", "+") for c in COHORTS], rotation=0)
    ax.set_ylabel("Hours of labor")
    ax.yaxis.set_major_formatter(FuncFormatter(hfmt))
    ax.set_title(f"Latest year ({latest_year}): time cost by category")
    ax.legend(frameon=False, ncol=4, loc="upper left")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(fig_dir / f"time_costs_ce_age_latest_stacked_hours_{anchor_year}.pdf")
    fig.savefig(fig_dir / f"time_costs_ce_age_latest_stacked_hours_{anchor_year}.png", dpi=300)
    plt.close(fig)

    # 3) 25--34 category breakdown over time.
    young = df[df["age_group"] == "25 to 34 Years"].sort_values("year")
    if not young.empty:
        fig, ax = plt.subplots(figsize=(10, 6))
        stacks = [young[f"time_years_{cat}"].fillna(0).to_numpy() for cat in CATEGORY_SPEC]
        ax.stackplot(young["year"].to_numpy(), stacks, labels=[spec["display"] for spec in CATEGORY_SPEC.values()], alpha=0.85)
        ax.set_xlabel("Year")
        ax.set_ylabel("Years of labor")
        ax.yaxis.set_major_formatter(FuncFormatter(yfmt))
        ax.set_title("25--34 cohort: time cost by category")
        ax.legend(frameon=False, ncol=4, loc="upper left")
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(fig_dir / f"time_costs_ce_age_25to34_breakdown_area_{anchor_year}.pdf")
        fig.savefig(fig_dir / f"time_costs_ce_age_25to34_breakdown_area_{anchor_year}.png", dpi=300)
        plt.close(fig)

    # 4) Education spending anchor by age: shows where college/education enters CE budgets.
    edu = anchors[anchors["category"] == "education"].copy()
    edu = edu.set_index("age_group").reindex(COHORTS).reset_index()
    fig, ax = plt.subplots(figsize=(9, 5.5))
    x = np.arange(len(edu))
    ax.bar(x, edu["mean_annual_spending_anchor_dollars"].to_numpy())
    ax.set_xticks(x)
    ax.set_xticklabels([c.replace(" Years", "").replace(" and Older", "+") for c in COHORTS], rotation=0)
    ax.set_ylabel(f"Annual CE education spending ({anchor_year} dollars)")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v:,.0f}"))
    ax.set_title("Where education spending appears in household budgets")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(fig_dir / f"time_costs_ce_age_education_spending_by_age_{anchor_year}.pdf")
    fig.savefig(fig_dir / f"time_costs_ce_age_education_spending_by_age_{anchor_year}.png", dpi=300)
    plt.close(fig)


def write_summary(panel: pd.DataFrame, anchors: pd.DataFrame, out_path: Path, anchor_year: int, plot_start_year: int) -> None:
    latest_year = int(panel["year"].dropna().max())
    latest = panel[panel["year"] == latest_year].copy()
    lines = []
    lines.append(f"Chapter 3 CE-based time-cost redo, anchor year {anchor_year}")
    lines.append("")
    lines.append("This replaces the earlier big-ticket allocation rules with CE annual means by age of reference person.")
    lines.append("Interpretation: fixed 2024 CE age-specific annual spending bundle, repriced by category CPI and expressed in 2024 dollars.")
    lines.append("")
    lines.append("2024 CE annual spending anchors used:")
    a = anchors.pivot(index="age_group", columns="category", values="mean_annual_spending_anchor_dollars").reindex(COHORTS)
    for cohort, row in a.iterrows():
        parts = []
        for cat, spec in CATEGORY_SPEC.items():
            parts.append(f"{spec['display']}=${row[cat]:,.0f}")
        lines.append(f"  {cohort}: " + "; ".join(parts))
    lines.append("")
    lines.append(f"Latest year in time-cost panel: {latest_year}")
    for cohort in COHORTS:
        sub = panel[(panel["age_group"] == cohort) & (panel["year"] >= plot_start_year)].dropna(subset=["time_years_total"])
        if sub.empty:
            continue
        curr = sub[sub["year"] == latest_year]
        curr_row = curr.iloc[0] if not curr.empty else sub.iloc[-1]
        peak = sub.loc[sub["time_years_total"].idxmax()]
        pieces = []
        for cat, spec in CATEGORY_SPEC.items():
            val = curr_row.get(f"time_hours_{cat}", np.nan)
            pieces.append(f"{spec['display']}={val:,.0f}h")
        lines.append(
            f"  {cohort}: latest {curr_row['time_years_total']:.2f} years "
            f"({curr_row['time_hours_total']:,.0f} hours); peak {peak['time_years_total']:.2f} years in {int(peak['year'])}; "
            + ", ".join(pieces)
        )
    lines.append("")
    lines.append("Important limitation: this is not historical actual CE spending by age. It fixes the 2024 age-specific CE bundle and reprices it with CPI category indexes.")
    lines.append("That is deliberately weaker than assigning a full home/college/car purchase to a cohort, but still transparent enough for a teaching chapter.")
    out_path.write_text("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--anchor-year", type=int, default=2024)
    parser.add_argument("--start-year", type=int, default=1980)
    parser.add_argument("--end-year", type=int, default=2024)
    parser.add_argument("--plot-start-year", type=int, default=1980)
    parser.add_argument("--overwrite-fred", action="store_true")
    args = parser.parse_args()

    root = find_repo_root()
    processed = root / "data" / "processed" / "chapter3"
    fig_dir = root / "figures" / "Chapter3/output"
    raw_fred = root / "data" / "raw" / "fred"
    wage_path = root / "figures" / "Chapter3" / "median_income_by_age.csv"

    processed.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)

    anchors = load_ce_anchors(processed, args.anchor_year)
    wages = load_wages(wage_path)
    price = build_price_panel(raw_fred, args.start_year, args.end_year, args.anchor_year, overwrite=args.overwrite_fred)

    # Use only years with complete wage coverage and CPI coverage.
    min_price_year = int(price.groupby("category", observed=True)["year"].min().max())
    max_price_year = int(price.groupby("category", observed=True)["year"].max().min())
    start = max(args.start_year, min_price_year, int(wages["year"].min()))
    end = min(args.end_year, max_price_year, int(wages["year"].max()))
    if start > end:
        raise RuntimeError(f"No overlapping years after merging CE anchors, CPI, and wages: start={start}, end={end}")

    if start > args.start_year:
        print(f"NOTE: Starting at {start} because that is the first complete overlap across CPI category indexes and wages.")

    panel = compute_time_costs(anchors, wages, price, start, end)
    panel = panel[(panel["year"] >= start) & (panel["year"] <= end)].copy()

    panel.to_csv(processed / f"time_costs_ce_age_by_age_{args.anchor_year}.csv", index=False)
    latest = panel[panel["year"] == int(panel["year"].max())].copy()
    latest.to_csv(processed / f"time_costs_ce_age_latest_{args.anchor_year}.csv", index=False)
    anchors.to_csv(processed / f"time_costs_ce_age_anchors_{args.anchor_year}.csv", index=False)

    make_plots(panel, anchors, fig_dir, args.anchor_year, max(args.plot_start_year, start))
    write_latex_latest(latest, fig_dir, args.anchor_year)
    write_summary(panel, anchors, processed / f"time_costs_ce_age_summary_{args.anchor_year}.txt", args.anchor_year, max(args.plot_start_year, start))

    print("Wrote:")
    print(" -", processed / f"time_costs_ce_age_by_age_{args.anchor_year}.csv")
    print(" -", processed / f"time_costs_ce_age_latest_{args.anchor_year}.csv")
    print(" -", processed / f"time_costs_ce_age_summary_{args.anchor_year}.txt")
    print(" -", fig_dir / f"time_costs_ce_age_lines_by_cohort_{args.anchor_year}.pdf")
    print(" -", fig_dir / f"time_costs_ce_age_latest_stacked_hours_{args.anchor_year}.pdf")
    print(" -", fig_dir / f"time_costs_ce_age_25to34_breakdown_area_{args.anchor_year}.pdf")
    print(" -", fig_dir / f"time_costs_ce_age_education_spending_by_age_{args.anchor_year}.pdf")
    print(" -", fig_dir / f"time_costs_ce_age_latest_{args.anchor_year}.tex")


if __name__ == "__main__":
    main()
