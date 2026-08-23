#!/usr/bin/env python3
"""
Professional-grade amortization analysis and publication-quality figures.

This script:
1. Computes daily-compounded amortization schedules.
2. Compares extra monthly payments and an early-payment timing scenario.
3. Saves a clean CSV summary for replication.
4. Saves publication-ready PDF and PNG figures under figures/Chapter2/.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib as mpl

# Use noninteractive backend so the script works cleanly from bash/CI.
mpl.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter


# ---------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "figures" / "Chapter2"
FIG_DIR.mkdir(parents=True, exist_ok=True)

CSV_PATH = FIG_DIR / "amortization_scenarios_summary.csv"

FIG1_PNG = FIG_DIR / "cumulative_interest_duration.png"
FIG1_PDF = FIG_DIR / "cumulative_interest_duration.pdf"

FIG2_PNG = FIG_DIR / "interest_savings_bar.png"
FIG2_PDF = FIG_DIR / "interest_savings_bar.pdf"


# ---------------------------------------------------------------------
# Loan assumptions
# ---------------------------------------------------------------------

principal = 350_000
annual_rate = 0.08
days_per_month = 30
days_per_year = 365
term_years = 30
months = term_years * 12

extras = [0, 100, 200, 300, 400, 500]

# In this setup, early_days=14 means the payment is made 14 days before
# the assumed 30-day month-end payment date, i.e. on day 16.
early_days = 14


# ---------------------------------------------------------------------
# Publication style
# ---------------------------------------------------------------------

mpl.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "font.size": 10,
    "axes.labelsize": 10,
    "axes.titlesize": 11,
    "legend.fontsize": 8.5,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.linewidth": 0.8,
    "axes.edgecolor": "0.2",
    "grid.color": "0.86",
    "grid.linewidth": 0.6,
    "grid.linestyle": "-",
})


def dollars_k(x, pos=None):
    """Compact dollar labels for plot axes."""
    if abs(x) >= 1_000_000:
        return f"${x / 1_000_000:,.1f}m"
    if abs(x) >= 1_000:
        return f"${x / 1_000:,.0f}k"
    return f"${x:,.0f}"


usd_k = FuncFormatter(dollars_k)


# ---------------------------------------------------------------------
# Core calculations
# ---------------------------------------------------------------------

daily_rate = annual_rate / days_per_year
effective_monthly_rate = (1 + daily_rate) ** days_per_month - 1


def monthly_payment_from_effective_rate(P, r_m, n_months):
    """Fixed-payment formula using the effective monthly rate."""
    if r_m == 0:
        return P / n_months
    return P * (r_m * (1 + r_m) ** n_months) / ((1 + r_m) ** n_months - 1)


base_monthly_payment = monthly_payment_from_effective_rate(
    principal,
    effective_monthly_rate,
    months,
)


def daily_amortization_schedule(
    P,
    daily_r,
    n_months,
    monthly_pmt,
    *,
    extra_payment=0.0,
    early_days=0,
    dpm=30,
):
    """
    Simulate a daily-compounded loan with one monthly payment.

    early_days=0 means payment on the final day of the assumed month.
    early_days=14 with dpm=30 means payment on day 16.
    """
    payment_day = max(1, min(dpm, dpm - early_days))

    balance = P
    total_interest = 0.0
    cumulative_interest = 0.0

    cum_interest_by_month = []
    balances_by_month = []

    for m in range(1, n_months + 1):
        month_interest = 0.0

        for day in range(1, dpm + 1):
            daily_int = balance * daily_r
            balance += daily_int

            month_interest += daily_int
            total_interest += daily_int

            if day == payment_day:
                payment = monthly_pmt + extra_payment
                payment = min(payment, balance)
                balance -= payment

        cumulative_interest += month_interest
        cum_interest_by_month.append(cumulative_interest)
        balances_by_month.append(balance)

        if balance <= 1e-8:
            break

    return (
        np.array(balances_by_month, dtype=float),
        np.array(cum_interest_by_month, dtype=float),
        float(total_interest),
        int(m),
    )


# Run extra-payment scenarios
cum_int_dict = {}
months_dict = {}
total_int_dict = {}

for extra in extras:
    _, cum_int, total_int, months_rem = daily_amortization_schedule(
        principal,
        daily_rate,
        months,
        base_monthly_payment,
        extra_payment=extra,
        early_days=0,
        dpm=days_per_month,
    )

    cum_int_dict[extra] = cum_int
    months_dict[extra] = months_rem
    total_int_dict[extra] = total_int


# Run early-payment scenario
_, cum_int_early, total_int_early, months_early = daily_amortization_schedule(
    principal,
    daily_rate,
    months,
    base_monthly_payment,
    extra_payment=0.0,
    early_days=early_days,
    dpm=days_per_month,
)

baseline_interest = total_int_dict[0]
savings_dict = {
    extra: baseline_interest - total_int_dict[extra]
    for extra in extras[1:]
}
savings_early = baseline_interest - total_int_early


# ---------------------------------------------------------------------
# Save tabular summary
# ---------------------------------------------------------------------

rows = []

for extra in extras:
    rows.append({
        "Scenario": "No extra payment" if extra == 0 else f"Extra ${extra}/month",
        "Principal": principal,
        "Annual Rate": annual_rate,
        "Base Monthly Payment": base_monthly_payment,
        "Extra Monthly Payment": extra,
        "Payment Timing": "Month end",
        "Total Monthly Payment": base_monthly_payment + extra,
        "Total Interest": total_int_dict[extra],
        "Interest Savings vs Baseline": (
            baseline_interest - total_int_dict[extra]
            if extra > 0
            else 0.0
        ),
        "Months to Payoff": months_dict[extra],
        "Years to Payoff": months_dict[extra] / 12,
    })

rows.append({
    "Scenario": f"Pay {early_days} days early",
    "Principal": principal,
    "Annual Rate": annual_rate,
    "Base Monthly Payment": base_monthly_payment,
    "Extra Monthly Payment": 0,
    "Payment Timing": f"{early_days} days early",
    "Total Monthly Payment": base_monthly_payment,
    "Total Interest": total_int_early,
    "Interest Savings vs Baseline": savings_early,
    "Months to Payoff": months_early,
    "Years to Payoff": months_early / 12,
})

summary_df = pd.DataFrame(rows)
summary_df.to_csv(CSV_PATH, index=False)


# ---------------------------------------------------------------------
# Figure 1: cumulative interest paths
# ---------------------------------------------------------------------

fig, ax = plt.subplots(figsize=(6.6, 4.0))

line_colors = plt.cm.viridis(np.linspace(0.12, 0.88, len(extras)))

for extra, color in zip(extras, line_colors):
    y = cum_int_dict[extra]
    x_years = np.arange(1, len(y) + 1) / 12

    label = "No extra payment" if extra == 0 else f"+${extra}/month"
    linewidth = 2.2 if extra == 0 else 1.7
    alpha = 1.0 if extra == 0 else 0.9

    ax.plot(
        x_years,
        y,
        linewidth=linewidth,
        color=color,
        alpha=alpha,
        label=label,
    )

x_early = np.arange(1, len(cum_int_early) + 1) / 12

ax.plot(
    x_early,
    cum_int_early,
    linewidth=1.8,
    linestyle="--",
    color="0.25",
    label=f"Pay {early_days} days early",
)

ax.set_xlabel("Years since origination")
ax.set_ylabel("Cumulative interest paid")
ax.yaxis.set_major_formatter(usd_k)

ax.set_xlim(0, term_years)
ax.set_ylim(bottom=0)
ax.set_xticks(np.arange(0, term_years + 1, 5))

ax.grid(True, axis="y")
ax.grid(False, axis="x")

ax.legend(
    loc="upper left",
    ncol=2,
    frameon=True,
    framealpha=0.95,
    edgecolor="0.75",
    handlelength=2.4,
    columnspacing=1.2,
    borderpad=0.6,
)

ax.text(
    0.98,
    0.04,
    "Lines end at payoff",
    transform=ax.transAxes,
    ha="right",
    va="bottom",
    fontsize=8.5,
    color="0.35",
)

fig.tight_layout()
fig.savefig(FIG1_PNG, bbox_inches="tight", pad_inches=0.03)
fig.savefig(FIG1_PDF, bbox_inches="tight", pad_inches=0.03)
plt.close(fig)


# ---------------------------------------------------------------------
# Figure 2: interest savings relative to baseline
# ---------------------------------------------------------------------

savings_rows = []

for extra in extras[1:]:
    savings_rows.append({
        "Scenario": f"+${extra}/month",
        "Interest Savings": savings_dict[extra],
        "Months to Payoff": months_dict[extra],
    })

savings_rows.append({
    "Scenario": f"Pay {early_days} days early",
    "Interest Savings": savings_early,
    "Months to Payoff": months_early,
})

savings_plot = pd.DataFrame(savings_rows)
savings_plot = savings_plot.sort_values("Interest Savings", ascending=True)

fig, ax = plt.subplots(figsize=(6.2, 3.5))

bars = ax.barh(
    savings_plot["Scenario"],
    savings_plot["Interest Savings"],
    color="0.35",
    edgecolor="0.15",
    linewidth=0.5,
)

ax.set_xlabel("Interest savings relative to no extra payment")
ax.set_ylabel("")
ax.xaxis.set_major_formatter(usd_k)

ax.grid(True, axis="x")
ax.grid(False, axis="y")

ax.spines["left"].set_visible(False)
ax.tick_params(axis="y", length=0)

max_savings = savings_plot["Interest Savings"].max()
ax.set_xlim(0, max_savings * 1.18)

for bar, value in zip(bars, savings_plot["Interest Savings"]):
    ax.text(
        value + max_savings * 0.015,
        bar.get_y() + bar.get_height() / 2,
        dollars_k(value),
        va="center",
        ha="left",
        fontsize=8.5,
        color="0.2",
    )

fig.tight_layout()
fig.savefig(FIG2_PNG, bbox_inches="tight", pad_inches=0.03)
fig.savefig(FIG2_PDF, bbox_inches="tight", pad_inches=0.03)
plt.close(fig)


# ---------------------------------------------------------------------
# Terminal output
# ---------------------------------------------------------------------

print("Done.")
print(f"Base monthly payment: ${base_monthly_payment:,.2f}")
print(f"Saved summary: {CSV_PATH}")
print(f"Saved figure:  {FIG1_PDF}")
print(f"Saved figure:  {FIG1_PNG}")
print(f"Saved figure:  {FIG2_PDF}")
print(f"Saved figure:  {FIG2_PNG}")
