import pandas as pd

# --- Load your SCF summary tables ---
mean_df = pd.read_csv("NetWorthMean.csv")
median_df = pd.read_csv("NetWorthMedian.csv")

# Core columns
YEAR_COL = "year"
AGE_COL = "Category"
VAL_COL = "Net_Worth"   # change if the column is named differently

# Merge mean and median
mean = mean_df[[YEAR_COL, AGE_COL, VAL_COL]].rename(columns={VAL_COL: "Mean"})
median = median_df[[YEAR_COL, AGE_COL, VAL_COL]].rename(columns={VAL_COL: "Median"})
merged = pd.merge(mean, median, on=[YEAR_COL, AGE_COL])

# Latest year only (e.g., 2022)
latest_year = merged[YEAR_COL].max()
latest = merged[merged[YEAR_COL] == latest_year].copy()

# Compute constant of proportionality
latest["c = Mean/Median"] = latest["Mean"] / latest["Median"]

print(f"SCF {latest_year} — Mean/Median Net Worth by Age Group")
print(latest[[AGE_COL, "Mean", "Median", "c = Mean/Median"]])
