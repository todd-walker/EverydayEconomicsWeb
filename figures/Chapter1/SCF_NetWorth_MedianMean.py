import pandas as pd
import matplotlib.pyplot as plt
import re
from typing import Optional, List

# ---------- Config ----------
MEAN_CSV = "NetWorthMean.csv"
MEDIAN_CSV = "NetWorthMedian.csv"
AGE_ORDER = ["Less than 35", "35-44", "45-54", "55-64", "65-74", "75 or older"]

# ---------- Helpers ----------
def find_column(candidates: List[str], df: pd.DataFrame, pattern: str) -> Optional[str]:
    """Return the first column whose name matches the regex pattern (case-insensitive)."""
    rx = re.compile(pattern, flags=re.I)
    for c in candidates:
        if c in df.columns:
            return c
    for c in df.columns:
        if rx.search(c):
            return c
    return None

def enforce_age_order(frame: pd.DataFrame, age_col: str = "Category") -> pd.DataFrame:
    frame = frame.copy()
    frame[age_col] = pd.Categorical(frame[age_col], categories=AGE_ORDER, ordered=True)
    return frame.sort_values(age_col)

# ---------- Load data ----------
mean_df = pd.read_csv(MEAN_CSV)
median_df = pd.read_csv(MEDIAN_CSV)

# Core columns
YEAR_COL = "year"
AGE_COL = "Category"

# Find Net Worth column (exact in your files)
NW_COL = find_column(["Net_Worth"], mean_df, r"^net[_\s-]*worth$")
if NW_COL is None:
    raise ValueError("Could not find a Net Worth column (e.g., 'Net_Worth'). Check your CSV headers.")

# Find Retirement column (be flexible with names)
RET_COL = find_column(["Retirement_Accounts"], mean_df, r"retire")
if RET_COL is None:
    raise ValueError("Could not find a retirement accounts column. "
                     "Look for a column containing 'retire' (e.g., 'Retirement_Accounts').")

# ---------- Build Net Worth merged table ----------
mean_nw = mean_df[[YEAR_COL, AGE_COL, NW_COL]].rename(columns={NW_COL: "Net_Worth_Mean"})
median_nw = median_df[[YEAR_COL, AGE_COL, NW_COL]].rename(columns={NW_COL: "Net_Worth_Median"})
merged_nw = pd.merge(mean_nw, median_nw, on=[YEAR_COL, AGE_COL])
latest_year = merged_nw[YEAR_COL].max()
merged_nw_latest = enforce_age_order(merged_nw[merged_nw[YEAR_COL] == latest_year])

# ---------- Build Retirement merged table ----------
mean_ret = mean_df[[YEAR_COL, AGE_COL, RET_COL]].rename(columns={RET_COL: "Retirement_Mean"})
median_ret = median_df[[YEAR_COL, AGE_COL, RET_COL]].rename(columns={RET_COL: "Retirement_Median"})
merged_ret = pd.merge(mean_ret, median_ret, on=[YEAR_COL, AGE_COL])
merged_ret["Gap"] = merged_ret["Retirement_Mean"] - merged_ret["Retirement_Median"]
latest_year_ret = merged_ret[YEAR_COL].max()
merged_ret_latest = enforce_age_order(merged_ret[merged_ret[YEAR_COL] == latest_year_ret])

# ---------- Plot styles for publication ----------
import matplotlib as mpl
mpl.rcParams.update({
    "font.size": 12,
    "font.family": "serif",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.3,
})

# ---------- Plot 1: Net Worth (Mean vs Median) ----------
x = range(len(merged_nw_latest))
bar_width = 0.35

plt.figure(figsize=(8,5))
plt.bar([i - bar_width/2 for i in x], merged_nw_latest["Net_Worth_Median"],
        width=bar_width, label="Median", color="C0")
plt.bar([i + bar_width/2 for i in x], merged_nw_latest["Net_Worth_Mean"],
        width=bar_width, label="Mean", color="C1")
plt.xticks(x, merged_nw_latest[AGE_COL], rotation=30)
plt.ylabel("Net Worth ($ thousands)")  # your data are in thousands
plt.xlabel("Age") 
plt.legend(loc="upper left")
plt.tight_layout()
plt.savefig("scf_networth_mean_vs_median.pdf", bbox_inches="tight")
plt.savefig("scf_networth_mean_vs_median.png", dpi=300, bbox_inches="tight")
plt.close()

# ---------- Plot 2: Retirement (Mean vs Median) ----------
x = range(len(merged_ret_latest))
plt.figure(figsize=(8,5))
plt.bar([i - bar_width/2 for i in x], merged_ret_latest["Retirement_Median"],
        width=bar_width, label="Median", color="C0")
plt.bar([i + bar_width/2 for i in x], merged_ret_latest["Retirement_Mean"],
        width=bar_width, label="Mean", color="C1")
plt.xticks(x, merged_ret_latest[AGE_COL], rotation=30)
plt.ylabel("Retirement Savings ($ thousands)")
plt.title(f"Mean vs. Median Retirement Savings by Age Group (U.S., SCF {latest_year_ret})")
plt.legend(loc="upper left")
plt.tight_layout()
plt.savefig("scf_retirement_mean_vs_median.pdf", bbox_inches="tight")
plt.close()

# ---------- Plot 3: Retirement Gap (Mean – Median) ----------
plt.figure(figsize=(8,5))
plt.plot(merged_ret_latest[AGE_COL], merged_ret_latest["Gap"],
         marker="o", linestyle="-", color="C1", linewidth=2)
plt.xlabel("Age Group of Household Head")
plt.ylabel("Mean – Median Retirement Savings ($ thousands)")
plt.title(f"Difference Between Mean and Median Retirement Savings by Age Group (U.S., SCF {latest_year_ret})")
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("scf_retirement_gap.pdf", bbox_inches="tight")
plt.close()

print("Saved figures: scf_networth_mean_vs_median.pdf, scf_retirement_mean_vs_median.pdf, scf_retirement_gap.pdf")
