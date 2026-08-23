# professional_amortization.py
import os
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

# ------------------------ Config ------------------------
principal = 400_000          # July 2026 avg mortgage size (MBA ~$402k)
annual_rate = 0.065          # July 2026 avg 30-yr fixed (Freddie Mac 6.49%)
days_per_month = 30
days_per_year = 365
term_years = 30
months = term_years * 12

extras = [0, 100, 200, 300, 400, 500]
early_days = 29

FIG_DIR = "figures/Chapter2"
CSV_PATH = os.path.join(FIG_DIR, "amortization_scenarios_summary.csv")
FIG1_PATH = os.path.join(FIG_DIR, "cumulative_interest_duration.png")
FIG2_PATH = os.path.join(FIG_DIR, "total_interest_bar.png")
os.makedirs(FIG_DIR, exist_ok=True)

mpl.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
    "font.size": 10, "axes.labelsize": 10, "axes.titlesize": 12,
    "legend.fontsize": 9, "xtick.labelsize": 9, "ytick.labelsize": 9,
    "figure.dpi": 300, "savefig.dpi": 300,
    "axes.spines.top": False, "axes.spines.right": False,
})

def dollars(x, pos):
    return f"${x:,.0f}"
usd0 = FuncFormatter(dollars)

daily_rate = annual_rate / days_per_year
eff_mr = (1 + daily_rate) ** days_per_month - 1

def monthly_payment_from_effective_rate(P, r_m, n_months):
    if r_m == 0:
        return P / n_months
    return P * (r_m * (1 + r_m) ** n_months) / ((1 + r_m) ** n_months - 1)

base_monthly_payment = monthly_payment_from_effective_rate(principal, eff_mr, months)

def daily_amortization_schedule(P, daily_r, months, monthly_pmt, *, extra_payment=0.0, early_days=0, dpm=30):
    payment_day = max(1, min(dpm, dpm - early_days))
    balance = P
    total_interest = 0.0
    cum_interest_by_month = []
    balances_by_month = []
    current_cum_interest = 0.0
    m = 0
    for m in range(1, months + 1):
        month_interest = 0.0
        for day in range(1, dpm + 1):
            daily_int = balance * daily_r
            balance += daily_int
            month_interest += daily_int
            total_interest += daily_int
            if day == payment_day:
                p = monthly_pmt + extra_payment
                p = min(p, balance)
                balance -= p
        current_cum_interest += month_interest
        cum_interest_by_month.append(current_cum_interest)
        balances_by_month.append(balance)
        if balance <= 1e-8:
            break
    return balances_by_month, cum_interest_by_month, total_interest, m

cum_int_dict, months_dict, total_int_dict = {}, {}, {}
for extra in extras:
    _, cum_int, total_int, months_rem = daily_amortization_schedule(
        principal, daily_rate, months, base_monthly_payment,
        extra_payment=extra, early_days=0, dpm=days_per_month)
    cum_int_dict[extra] = np.array(cum_int, dtype=float)
    months_dict[extra] = int(months_rem)
    total_int_dict[extra] = float(total_int)

_, cum_int_early, total_int_early, months_early = daily_amortization_schedule(
    principal, daily_rate, months, base_monthly_payment,
    extra_payment=0.0, early_days=early_days, dpm=days_per_month)
cum_int_early = np.array(cum_int_early, dtype=float)
baseline_interest = total_int_dict[0]
savings_dict = {extra: baseline_interest - total_int_dict[extra] for extra in extras[1:]}
savings_early = baseline_interest - total_int_early

rows = []
for extra in extras:
    rows.append({
        "Scenario": f"Extra ${extra}/mo",
        "Monthly Payment": base_monthly_payment + extra,
        "Total Interest": total_int_dict[extra],
        "Months to Payoff": months_dict[extra],
        "Interest Savings vs Baseline": (baseline_interest - total_int_dict[extra]) if extra > 0 else 0.0
    })
rows.append({
    "Scenario": f"Pay {early_days} days early",
    "Monthly Payment": base_monthly_payment,
    "Total Interest": total_int_early,
    "Months to Payoff": months_early,
    "Interest Savings vs Baseline": savings_early
})
summary_df = pd.DataFrame(rows)
summary_df.to_csv(CSV_PATH, index=False)

# ---------------------- Figure 1 ------------------------
plt.figure(figsize=(5.0, 3.2))
ax = plt.gca()
for extra in extras:
    y = cum_int_dict[extra]
    x = np.arange(1, len(y) + 1)
    ax.plot(x, y, linewidth=1.6, label=f"Extra ${extra}/mo")
    ax.text(x[-1] + 2, y[-1], f"{months_dict[extra]}", va="center", fontsize=8)
x_e = np.arange(1, len(cum_int_early) + 1)
ax.plot(x_e, cum_int_early, linewidth=1.6, linestyle="-", label=f"{early_days} days early")
ax.text(x_e[-1] + 2, cum_int_early[-1], f"{months_early}", va="center", fontsize=8)
savings_lines = [f"${extra}/mo: ${savings_dict[extra]:,.0f}" for extra in extras[1:]]
savings_lines.append(f"Early: ${savings_early:,.0f}")
ax.text(0.98, 0.02, "\n".join(savings_lines), transform=ax.transAxes,
        ha="right", va="bottom", fontsize=8,
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="0.3", alpha=0.95))
ax.set_xlabel("Month")
ax.set_ylabel("Cumulative Interest (USD)")
ax.yaxis.set_major_formatter(usd0)
ax.set_title("Cumulative Interest and Payoff Month by Scenario")
ax.grid(True, linestyle="--", alpha=0.5)
ax.legend(loc="upper left", bbox_to_anchor=(1.0, 1.0), frameon=False)
plt.tight_layout()
plt.savefig(FIG1_PATH, bbox_inches="tight")
plt.savefig("figures/Chapter2/cumulative_interest_duration.pdf", bbox_inches="tight")
plt.close()

# ---------------------- Figure 2 ------------------------
plt.figure(figsize=(3.7, 2.8))
ax = plt.gca()
scenarios = [f"${extra}/mo" for extra in extras] + [f"{early_days}-days early"]
interest_totals = [total_int_dict[extra] for extra in extras] + [total_int_early]
bars = ax.bar(scenarios, interest_totals, edgecolor="black", linewidth=0.6)
ax.set_ylabel("Total Interest (USD)")
ax.yaxis.set_major_formatter(usd0)
ax.set_title("Total Interest by Scenario")
ax.grid(True, axis="y", linestyle="--", alpha=0.5)
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
plt.savefig(FIG2_PATH, bbox_inches="tight")
plt.close()