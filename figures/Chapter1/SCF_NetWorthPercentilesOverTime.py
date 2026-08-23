import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl

# ---------- File ----------
CSV = "NetWorthPercentilesOverTime.csv"  # put this script next to your CSV

# ---------- Read & prepare ----------
df = pd.read_csv(CSV)

# Expected columns:
#   year (int), Category (str with percentile group),
#   Net_Worth (levels in $ thousands; SCF summary convention)
# If your column names differ, tweak the three names below:
YEAR_COL = "year"
GROUP_COL = "Category"
VALUE_COL = "Net_Worth"

# Order percentile groups from lowest to highest
pct_order = ["Less than 25", "25-49.9", "50-74.9", "75-89.9", "90-100"]
df[GROUP_COL] = pd.Categorical(df[GROUP_COL], categories=pct_order, ordered=True)

# Pivot to: rows=year, cols=percentile groups, values=Net_Worth
pivot = df.pivot_table(index=YEAR_COL, columns=GROUP_COL, values=VALUE_COL)

# ---------- Plot settings (publication-friendly) ----------
mpl.rcParams.update({
    "font.size": 12,
    "font.family": "serif",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.3,
})

# ---------- Plot ----------
plt.figure(figsize=(9, 5.5))
for cat in pct_order:
    if cat in pivot.columns:
        plt.plot(pivot.index, pivot[cat], label=cat, linewidth=2)

plt.xlabel("Year")
plt.ylabel("Net Worth ($ thousands)")
plt.title("Household Net Worth by Percentile Group (SCF)")
plt.legend(title="Wealth Percentile", loc="upper left")
plt.tight_layout()
plt.savefig("scf_networth_percentiles_over_time.pdf", bbox_inches="tight")  # vector PDF
plt.savefig("scf_networth_percentiles_over_time.png", dpi=300, bbox_inches="tight")
plt.show()

print("Saved: scf_networth_percentiles_over_time.pdf")

