#!/usr/bin/env python3
"""
compute_time_costs.py  (representative-agent, fully amortized)

Every major life milestone is converted to an ANNUAL financed payment, then
divided by the representative cohort worker's annual income to express it as a
share of a 2,000-hour work-year. Headline cohort: 25-34. Comparison: 1980 vs 2024.

Financing assumptions (all rates from FRED where available):
  house  : 20% down (down payment amortized over term), 30-yr at MORTGAGE30US
  degree : 4 x tuition, 10-yr loan at federal Direct Loan statutory rate
  car    : 1 x new-vehicle price, financed over CAR_LIFE_YEARS at TERMCBAUTO48NS
  health : annual benchmark, used directly (already a flow)

Inputs:
  figures/Chapter3/output/expenditures_2024d.csv
      year, house_price_2024d, tuition_2024d, auto_2024d, health_2024d
  figures/Chapter3/median_income_by_age.csv
      Year, Age Group, Combined Median (2024 $)
  data/raw/fred/MORTGAGE30US.csv      (year, 30yr_fixed_mortgage)   [pct]
  data/raw/fred/TERMCBAUTO48NS.csv    (year, auto_loan_48m)         [pct]

Outputs:
  figures/Chapter3/output/time_costs_repagent_by_age.csv
  figures/Chapter3/output/time_costs_repagent_compare_1980_2024.csv
"""

from pathlib import Path
import numpy as np
import pandas as pd

OUTDIR = Path("figures/Chapter3/output")
FRED = Path("data/raw/fred")
EXP_FILE = OUTDIR / "expenditures_2024d.csv"
WAGE_FILE = Path("figures/Chapter3/median_income_by_age.csv")

WORK_HOURS_PER_YEAR = 2000.0
COMPARE_YEARS = [1980, 2024]
HEADLINE_COHORT = "25 to 34 Years"
COHORTS = ["25 to 34 Years", "35 to 44 Years", "45 to 54 Years",
           "55 to 64 Years", "65 Years and Older"]

# Financing terms
DOWN_FRAC = 0.20
MORTGAGE_TERM = 30
DEGREE_MULT = 4.0
DEGREE_LOAN_TERM = 10
CAR_LIFE_YEARS = 8       # finance/replace cycle for one new vehicle

# Federal Direct Loan statutory rate (annual, decimal). Source: Finaid /
# Higher Education Act statutory schedule. Pre-2006 Stafford ~ variable; we use
# a fixed 0.08 backstop before 2006 where statutory fixed rates did not exist.
STUDENT_RATE = {2006: .0680, 2013: .0386, 2014: .0466, 2015: .0429, 2016: .0376,
                2017: .0445, 2018: .0505, 2019: .0453, 2020: .0275, 2021: .0373,
                2022: .0499, 2023: .0550, 2024: .0653}
STUDENT_RATE_BACKSTOP = 0.08


def amort_payment(principal, annual_rate, term):
    principal = np.asarray(principal, dtype=float)
    r = np.asarray(annual_rate, dtype=float)
    out = np.where(r > 0,
                   principal * r / (1.0 - (1.0 + r) ** (-term)),
                   principal / term)
    return out


def load_rate(fname, col):
    df = pd.read_csv(FRED / fname)
    df["year"] = df["year"].astype(int)
    df[col] = pd.to_numeric(df[col], errors="coerce") / 100.0
    return df[["year", col]]


def interp_to_years(years, rate_df, col, backfill_to=1963):
    yrs = np.arange(min(backfill_to, years.min()), years.max() + 1)
    xs = rate_df["year"].to_numpy()
    ys = rate_df[col].to_numpy()
    full = np.interp(yrs, xs, ys)  # flat extrapolation outside range
    return dict(zip(yrs, full))


def student_rate_for(year):
    if year in STUDENT_RATE:
        return STUDENT_RATE[year]
    keys = sorted(STUDENT_RATE)
    if year < keys[0]:
        return STUDENT_RATE_BACKSTOP
    prior = max(k for k in keys if k <= year)
    return STUDENT_RATE[prior]


def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)

    exp = pd.read_csv(EXP_FILE)
    exp["year"] = pd.to_numeric(exp["year"], errors="coerce").astype("Int64")
    exp = exp.dropna(subset=["year"]).astype({"year": int})

    w = pd.read_csv(WAGE_FILE).rename(columns={
        "Year": "year", "Age Group": "age_group",
        "Combined Median (2024 $)": "wage_annual_2024d"})
    w["year"] = pd.to_numeric(w["year"], errors="coerce").astype("Int64")
    w["wage_annual_2024d"] = pd.to_numeric(w["wage_annual_2024d"], errors="coerce")
    w = w.dropna(subset=["year"]).astype({"year": int})
    w = w[w["age_group"].isin(COHORTS)]

    mort = load_rate("MORTGAGE30US.csv", "30yr_fixed_mortgage")
    auto = load_rate("TERMCBAUTO48NS.csv", "auto_loan_48m")

    exp = exp[exp["year"] <= int(w["year"].max())]
    years = np.array(sorted(exp["year"].unique()))
    mort_map = interp_to_years(years, mort, "30yr_fixed_mortgage")
    auto_map = interp_to_years(years, auto, "auto_loan_48m")

    panel = (pd.DataFrame({"year": years})
             .merge(pd.DataFrame({"age_group": COHORTS}), how="cross")
             .merge(exp, on="year", how="left")
             .merge(w, on=["year", "age_group"], how="left"))

    panel["mortgage_rate"] = panel["year"].map(mort_map)
    panel["auto_rate"] = panel["year"].map(auto_map)
    panel["student_rate"] = panel["year"].map(student_rate_for)

    # --- Annual financed payments (2024$) ---
    # House: down payment amortized over term + mortgage payment on the balance.
    house_price = panel["house_price_2024d"].to_numpy()
    down = DOWN_FRAC * house_price
    bal = (1 - DOWN_FRAC) * house_price
    panel["pay_house"] = down / MORTGAGE_TERM + amort_payment(
        bal, panel["mortgage_rate"].to_numpy(), MORTGAGE_TERM)

    # Degree: 4x tuition as a 10-yr student loan.
    degree_principal = DEGREE_MULT * panel["tuition_2024d"].to_numpy()
    panel["pay_degree"] = amort_payment(
        degree_principal, panel["student_rate"].to_numpy(), DEGREE_LOAN_TERM)

    # Car: one new vehicle financed/replaced over its service life.
    panel["pay_car"] = amort_payment(
        panel["auto_2024d"].to_numpy(), panel["auto_rate"].to_numpy(), CAR_LIFE_YEARS)

    # Health: annual flow, used directly.
    panel["pay_health"] = panel["health_2024d"].astype(float)

    pay_cols = ["pay_house", "pay_degree", "pay_car", "pay_health"]
    panel["pay_total"] = panel[pay_cols].sum(axis=1, min_count=1)

    # --- Work-year shares and hours ---
    for c in pay_cols + ["pay_total"]:
        share = panel[c] / panel["wage_annual_2024d"]
        panel[c.replace("pay_", "share_")] = share
        panel[c.replace("pay_", "hours_")] = share * WORK_HOURS_PER_YEAR

    panel = panel.sort_values(["year", "age_group"]).reset_index(drop=True)
    out = OUTDIR / "time_costs_repagent_by_age.csv"
    panel.to_csv(out, index=False)

    cmp = panel[(panel["age_group"] == HEADLINE_COHORT)
                & (panel["year"].isin(COMPARE_YEARS))].copy()
    keep = (["year", "wage_annual_2024d", "mortgage_rate", "auto_rate", "student_rate"]
            + pay_cols + ["pay_total"]
            + [f"share_{k}" for k in ["house", "degree", "car", "health", "total"]]
            + [f"hours_{k}" for k in ["house", "degree", "car", "health", "total"]])
    cmp = cmp[keep]
    out_cmp = OUTDIR / "time_costs_repagent_compare_1980_2024.csv"
    cmp.to_csv(out_cmp, index=False)

    print("Wrote:\n -", out, "\n -", out_cmp)
    print(f"\nRepresentative {HEADLINE_COHORT}, {COMPARE_YEARS[0]} vs {COMPARE_YEARS[-1]}")
    show = ["year", "wage_annual_2024d", "mortgage_rate",
            "share_house", "share_degree", "share_car", "share_health", "share_total",
            "hours_total"]
    print(cmp[show].to_string(index=False, float_format=lambda x: f"{x:,.4f}"))


if __name__ == "__main__":
    main()
