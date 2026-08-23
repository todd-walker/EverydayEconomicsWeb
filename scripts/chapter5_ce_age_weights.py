#!/usr/bin/env python3
"""
Build Chapter 5 expenditure-allocation tables by age of reference person.

Source: BLS Consumer Expenditure Survey, calendar-year demographic table:
"Age of reference person: Annual expenditure means, shares, standard errors,
and relative standard errors."

Run from the EverydayEconomics repo root or put this file in scripts/ and run:

    python scripts/chapter5_ce_age_weights.py --year 2024

Outputs:
    data/raw/bls_cex/reference-person-age-ranges-2024.xlsx
    data/processed/chapter5/ce_items_by_age_2024.csv
    data/processed/chapter5/cpi_like_expenditure_weights_by_age_2024.csv
    data/processed/chapter5/cpi_like_expenditure_weights_by_age_wide_2024.csv
    data/processed/chapter5/cpi_like_expenditure_allocations_by_age_wide_2024.csv
    data/processed/chapter5/chapter5_ce_age_summary_2024.txt
    figures/Chapter5/ce_age_allocations_stacked_2024.pdf/.png
    figures/Chapter5/ce_age_selected_weights_2024.pdf/.png
    figures/Chapter5/ce_age_weights_2024.tex
    figures/Chapter5/ce_age_allocations_2024.tex

Important interpretation note:
These are CE expenditure shares by age of the reference person, not official
CPI relative-importance weights by age. They are useful for Chapter 5 teaching
and for showing how household spending baskets vary over the life cycle.
"""

from __future__ import annotations

import argparse
import math
import re
import textwrap
import urllib.request
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BLS_URL_TEMPLATE = (
    "https://www.bls.gov/cex/tables/calendar-year/"
    "mean-item-share-average-standard-error/"
    "reference-person-age-ranges-{year}.xlsx"
)

CATEGORY_ORDER = [
    "Food and beverages",
    "Housing",
    "Apparel",
    "Transportation",
    "Medical care",
    "Recreation",
    "Education and communication",
    "Other goods and services",
]

# Use non-overlapping age groups for figures and compact LaTeX tables.
AGE_GROUPS_NONOVERLAPPING = [
    "Under 25 years",
    "25-34 years",
    "35-44 years",
    "45-54 years",
    "55-64 years",
    "65 years and older",
]

# A CPI-like mapping built from the broad published CE table.
# This is intentionally transparent rather than pretending to be official CPI item-strata weights.
MAPPING_NOTE = """
CPI-like mapping from the published CE age table:
  Food and beverages = Food + Alcoholic beverages
  Housing = Housing - Telephone services - Postage and stationery
  Apparel = Apparel and services
  Transportation = Transportation
  Medical care = Healthcare
  Recreation = Entertainment + Reading
  Education and communication = Education + Telephone services + Postage and stationery
  Other goods and services = Average annual expenditures - sum(previous seven groups)
""".strip()


def find_repo_root() -> Path:
    """Find the EverydayEconomics repo root from this script location or cwd."""
    here = Path(__file__).resolve()
    candidates = [here.parent, *here.parents, Path.cwd(), *Path.cwd().parents]
    for p in candidates:
        if (p / "chapters").exists() and (p / "data").exists():
            return p
    # Fallback: when copied somewhere else, use the current working directory.
    return Path.cwd()


def ensure_dirs(root: Path) -> dict[str, Path]:
    dirs = {
        "raw": root / "data" / "raw" / "bls_cex",
        "processed": root / "data" / "processed" / "chapter5",
        "figures": root / "figures" / "Chapter5",
    }
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)
    return dirs


def download_if_needed(url: str, destination: Path, overwrite: bool = False) -> None:
    if destination.exists() and not overwrite:
        print(f"Using existing raw file: {destination}")
        return
    print(f"Downloading {url}")
    with urllib.request.urlopen(url) as response:
        destination.write_bytes(response.read())
    print(f"Saved raw file: {destination}")


def clean_cell_to_float(x) -> float:
    """Convert BLS table cells to float, handling suppression flags such as b/."""
    if pd.isna(x):
        return math.nan
    if isinstance(x, str):
        s = x.strip().replace(",", "")
        if s in {"", "b/", "a/", "-", "--", "N/A", "nan"}:
            return math.nan
        try:
            return float(s)
        except ValueError:
            return math.nan
    try:
        return float(x)
    except Exception:
        return math.nan


def clean_label(x) -> str:
    return re.sub(r"\s+", " ", str(x).replace("\n", " ")).strip()


def read_ce_age_table(xlsx_path: Path) -> tuple[pd.DataFrame, list[str]]:
    """
    Parse the BLS Excel table into a long data frame.

    BLS table structure is hierarchical: an item row is followed by statistic rows
    such as Mean, Share, SE, and RSE. We turn that into one row per item-age group.
    """
    raw = pd.read_excel(xlsx_path, sheet_name=0, header=None)

    item_col = raw.iloc[:, 0].astype(str).map(clean_label)
    header_matches = item_col[item_col.eq("Item")]
    if header_matches.empty:
        raise ValueError("Could not find the table header row containing 'Item'.")
    header_row = int(header_matches.index[0])

    age_groups = [clean_label(x) for x in raw.iloc[header_row, 1:].tolist()]
    records: list[dict] = []

    for i in range(header_row + 1, len(raw) - 4):
        item = clean_label(raw.iloc[i, 0])
        if not item or item.lower() == "nan":
            continue
        next_row_label = clean_label(raw.iloc[i + 1, 0])
        if next_row_label != "Mean":
            continue

        stat_rows = {}
        for k in range(1, 5):
            stat_label = clean_label(raw.iloc[i + k, 0])
            if stat_label in {"Mean", "Share", "SE", "RSE"}:
                stat_rows[stat_label] = i + k

        for j, age_group in enumerate(age_groups, start=1):
            records.append(
                {
                    "source_row": i + 1,  # one-index-ish for easier checking against Excel
                    "item": item,
                    "age_group": age_group,
                    "mean": clean_cell_to_float(raw.iloc[stat_rows["Mean"], j]),
                    "share_reported": clean_cell_to_float(raw.iloc[stat_rows["Share"], j])
                    if "Share" in stat_rows
                    else math.nan,
                    "se": clean_cell_to_float(raw.iloc[stat_rows["SE"], j])
                    if "SE" in stat_rows
                    else math.nan,
                    "rse": clean_cell_to_float(raw.iloc[stat_rows["RSE"], j])
                    if "RSE" in stat_rows
                    else math.nan,
                }
            )

    out = pd.DataFrame.from_records(records)
    return out, age_groups


def get_item(wide: pd.DataFrame, candidates: str | Iterable[str], required: bool = True) -> pd.Series:
    """Fetch an expenditure item from a wide item table, allowing name aliases."""
    if isinstance(candidates, str):
        candidates = [candidates]
    candidates = list(candidates)

    for name in candidates:
        if name in wide.columns:
            return wide[name]

    lower_map = {str(c).lower(): c for c in wide.columns}
    for name in candidates:
        key = name.lower()
        if key in lower_map:
            return wide[lower_map[key]]

    if required:
        raise KeyError(f"Could not find any of these CE items: {candidates}")
    return pd.Series(0.0, index=wide.index)


def build_cpi_like_table(items: pd.DataFrame, age_groups: list[str]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build a CPI-like eight-category table by age group."""
    dedup = items.drop_duplicates(["age_group", "item"], keep="first")
    mean_wide = dedup.pivot(index="age_group", columns="item", values="mean")
    mean_wide = mean_wide.reindex(age_groups)

    total = get_item(mean_wide, "Average annual expenditures")
    telephone = get_item(mean_wide, "Telephone services", required=False)
    postage = get_item(mean_wide, "Postage and stationery", required=False)

    amounts = pd.DataFrame(index=mean_wide.index)
    amounts["Food and beverages"] = get_item(mean_wide, "Food") + get_item(
        mean_wide, "Alcoholic beverages", required=False
    )
    amounts["Housing"] = get_item(mean_wide, "Housing") - telephone - postage
    amounts["Apparel"] = get_item(mean_wide, "Apparel and services")
    amounts["Transportation"] = get_item(mean_wide, "Transportation")
    amounts["Medical care"] = get_item(mean_wide, ["Healthcare", "Health care"])
    amounts["Recreation"] = get_item(mean_wide, "Entertainment") + get_item(mean_wide, "Reading", required=False)
    amounts["Education and communication"] = get_item(mean_wide, "Education", required=False) + telephone + postage

    amounts["Other goods and services"] = total - amounts.sum(axis=1)
    amounts = amounts[CATEGORY_ORDER]

    weights = amounts.div(total, axis=0) * 100.0
    allocations = weights * 10.0  # dollars out of $1,000

    long = (
        amounts.reset_index(names="age_group")
        .melt(id_vars="age_group", var_name="category", value_name="mean_annual_spending")
        .merge(
            weights.reset_index(names="age_group").melt(
                id_vars="age_group", var_name="category", value_name="weight_percent"
            ),
            on=["age_group", "category"],
        )
        .merge(
            allocations.reset_index(names="age_group").melt(
                id_vars="age_group", var_name="category", value_name="allocation_out_of_1000"
            ),
            on=["age_group", "category"],
        )
    )
    long["category"] = pd.Categorical(long["category"], CATEGORY_ORDER, ordered=True)
    long["age_group"] = pd.Categorical(long["age_group"], age_groups, ordered=True)
    long = long.sort_values(["age_group", "category"]).reset_index(drop=True)

    return long, weights, allocations


def save_latex_tables(weights: pd.DataFrame, allocations: pd.DataFrame, fig_dir: Path, year: int) -> None:
    compact_ages = [age for age in AGE_GROUPS_NONOVERLAPPING if age in weights.index]

    weights_table = weights.loc[compact_ages, CATEGORY_ORDER].T.round(1)
    weights_table.index.name = "Category"
    weights_table.columns.name = None
    weights_tex = weights_table.to_latex(
        float_format="%.1f",
        index_names=False,
        caption=(
            f"Approximate expenditure shares by age of reference person, {year}. "
            "Shares are based on BLS Consumer Expenditure Survey means, not official CPI weights."
        ),
        label="tab:ce-age-weights",
    )
    (fig_dir / f"ce_age_weights_{year}.tex").write_text(weights_tex)

    alloc_table = allocations.loc[compact_ages, CATEGORY_ORDER].T.round(2)
    alloc_table.index.name = "Category"
    alloc_table.columns.name = None
    alloc_tex = alloc_table.to_latex(
        float_format="%.2f",
        index_names=False,
        caption=(
            f"Hypothetical allocation of \\$1,000 by age of reference person, {year}. "
            "Allocations are based on approximate CE expenditure shares."
        ),
        label="tab:ce-age-allocations",
    )
    (fig_dir / f"ce_age_allocations_{year}.tex").write_text(alloc_tex)


def make_figures(weights: pd.DataFrame, allocations: pd.DataFrame, fig_dir: Path, year: int) -> None:
    plot_ages = [age for age in AGE_GROUPS_NONOVERLAPPING if age in weights.index]

    alloc_plot = allocations.loc[plot_ages, CATEGORY_ORDER]
    fig, ax = plt.subplots(figsize=(10, 6))
    bottom = np.zeros(len(alloc_plot))
    x = np.arange(len(alloc_plot.index))
    for category in CATEGORY_ORDER:
        vals = alloc_plot[category].to_numpy()
        ax.bar(x, vals, bottom=bottom, label=category)
        bottom += vals
    ax.set_xticks(x)
    ax.set_xticklabels(alloc_plot.index, rotation=30, ha="right")
    ax.set_ylabel("Dollars out of $1,000")
    ax.set_title(f"Hypothetical $1,000 spending basket by age, {year}")
    ax.legend(loc="center left", bbox_to_anchor=(1.0, 0.5), frameon=False)
    fig.tight_layout()
    fig.savefig(fig_dir / f"ce_age_allocations_stacked_{year}.pdf", bbox_inches="tight")
    fig.savefig(fig_dir / f"ce_age_allocations_stacked_{year}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    selected = ["Housing", "Transportation", "Medical care", "Food and beverages"]
    wt_plot = weights.loc[plot_ages, selected]
    fig, ax = plt.subplots(figsize=(9, 5.5))
    x = np.arange(len(wt_plot.index))
    for category in selected:
        ax.plot(x, wt_plot[category].to_numpy(), marker="o", label=category)
    ax.set_xticks(x)
    ax.set_xticklabels(wt_plot.index, rotation=30, ha="right")
    ax.set_ylabel("Percent of annual expenditures")
    ax.set_title(f"Selected expenditure shares by age, {year}")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(fig_dir / f"ce_age_selected_weights_{year}.pdf", bbox_inches="tight")
    fig.savefig(fig_dir / f"ce_age_selected_weights_{year}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def write_summary(weights: pd.DataFrame, items: pd.DataFrame, processed_dir: Path, year: int) -> None:
    compact_ages = [age for age in AGE_GROUPS_NONOVERLAPPING if age in weights.index]
    wt = weights.loc[compact_ages, CATEGORY_ORDER]
    ranges = (wt.max(axis=0) - wt.min(axis=0)).sort_values(ascending=False)
    largest = ranges.index[0]

    totals = (
        items[(items["item"] == "Average annual expenditures") & (items["age_group"].isin(compact_ages))]
        .set_index("age_group")["mean"]
        .reindex(compact_ages)
    )
    max_total_age = totals.idxmax()
    min_total_age = totals.idxmin()

    age65 = "65 years and older"
    under25 = "Under 25 years"
    lines = [
        f"Chapter 5 CE age-spending summary, {year}",
        "",
        "Interpretation: age means age of the BLS CE reference person, not every member of the household.",
        "These are CE expenditure shares, not official CPI relative-importance weights by age.",
        "",
        MAPPING_NOTE,
        "",
        f"Highest average annual expenditures among compact age groups: {max_total_age} (${totals[max_total_age]:,.0f}).",
        f"Lowest average annual expenditures among compact age groups: {min_total_age} (${totals[min_total_age]:,.0f}).",
        f"Largest across-age category range: {largest} ({ranges[largest]:.1f} percentage points).",
        "",
        f"65+ minus Under 25 differences, percentage points:",
    ]
    if age65 in wt.index and under25 in wt.index:
        diffs = (wt.loc[age65] - wt.loc[under25]).sort_values(ascending=False)
        for category, value in diffs.items():
            lines.append(f"  {category}: {value:+.1f}")

    (processed_dir / f"chapter5_ce_age_summary_{year}.txt").write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=2024)
    parser.add_argument("--overwrite", action="store_true", help="Re-download the BLS Excel file.")
    args = parser.parse_args()

    root = find_repo_root()
    dirs = ensure_dirs(root)

    url = BLS_URL_TEMPLATE.format(year=args.year)
    raw_xlsx = dirs["raw"] / f"reference-person-age-ranges-{args.year}.xlsx"
    download_if_needed(url, raw_xlsx, overwrite=args.overwrite)

    items, age_groups = read_ce_age_table(raw_xlsx)
    long, weights, allocations = build_cpi_like_table(items, age_groups)

    processed = dirs["processed"]
    fig_dir = dirs["figures"]

    items.to_csv(processed / f"ce_items_by_age_{args.year}.csv", index=False)
    long.to_csv(processed / f"cpi_like_expenditure_weights_by_age_{args.year}.csv", index=False)
    weights.round(6).to_csv(processed / f"cpi_like_expenditure_weights_by_age_wide_{args.year}.csv")
    allocations.round(2).to_csv(processed / f"cpi_like_expenditure_allocations_by_age_wide_{args.year}.csv")

    save_latex_tables(weights, allocations, fig_dir, args.year)
    make_figures(weights, allocations, fig_dir, args.year)
    write_summary(weights, items, processed, args.year)

    print("\nDone. Key outputs:")
    for p in [
        processed / f"cpi_like_expenditure_weights_by_age_{args.year}.csv",
        processed / f"cpi_like_expenditure_allocations_by_age_wide_{args.year}.csv",
        processed / f"chapter5_ce_age_summary_{args.year}.txt",
        fig_dir / f"ce_age_allocations_stacked_{args.year}.pdf",
        fig_dir / f"ce_age_weights_{args.year}.tex",
        fig_dir / f"ce_age_allocations_{args.year}.tex",
    ]:
        print(f"  {p.relative_to(root)}")


if __name__ == "__main__":
    main()
