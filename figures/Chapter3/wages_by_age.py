import pandas as pd
import re
import matplotlib.pyplot as plt

# Read the Excel file
file_path = "figures/Chapter3/p08ar.xlsx"
df = pd.read_excel(file_path, sheet_name='p08ar', header=None)

# Save raw spreadsheet as CSV
df.to_csv('figures/Chapter3/p08ar_raw.csv', index=False, header=False)

# Age groups and their header start rows (1-based)
age_groups = [
    ('25 to 34 Years', 149),
    ('35 to 44 Years', 233),
    ('45 to 54 Years', 317),
    ('55 to 64 Years', 401),
    ('65 Years and Older', 485),
]

# Extract data
new_data = []
for group, header_start in age_groups:
    data_iloc = header_start - 1 + 3  # header_iloc + 3
    i = data_iloc
    while i < len(df):
        year_str = str(df.iloc[i, 0])
        year_match = re.match(r'(\d{4})', year_str)
        if not year_match:
            break
        year = int(year_match.group(1))
        male_num = pd.to_numeric(df.iloc[i, 1], errors='coerce')
        male_2024 = pd.to_numeric(df.iloc[i, 3], errors='coerce')
        female_num = pd.to_numeric(df.iloc[i, 4], errors='coerce')
        female_2024 = pd.to_numeric(df.iloc[i, 6], errors='coerce')
        if any(pd.isna(x) for x in [male_num, male_2024, female_num, female_2024]):
            break
        total_num = male_num + female_num
        combined = (male_num * male_2024 + female_num * female_2024) / total_num if total_num > 0 else 0
        new_data.append({'Year': year, 'Age Group': group, 'Combined Median (2024 $)': combined})
        i += 1

# Create DataFrame and handle duplicates by keeping the last entry
result_df = pd.DataFrame(new_data).sort_values(['Year', 'Age Group'])
result_df = result_df.drop_duplicates(subset=['Year', 'Age Group'], keep='last')
result_df.to_csv('figures/Chapter3/median_income_by_age.csv', index=False)

# Pivot data for plotting
pivot_df = result_df.pivot(index='Year', columns='Age Group', values='Combined Median (2024 $)')

# Calculate and print percentage change for 1947-1972 and 1972-2024
print("\nPercentage Change in Median Income (2024 $):")
print(f"{'Age Group':<20} {'1947-1972':>15} {'1972-2024':>15}")
print("-" * 50)
for age_group in pivot_df.columns:
    income_1947 = pivot_df.loc[1947, age_group] if 1947 in pivot_df.index else None
    income_1972 = pivot_df.loc[1972, age_group] if 1972 in pivot_df.index else None
    income_2024 = pivot_df.loc[2024, age_group] if 2024 in pivot_df.index else None
    if all(x is not None for x in [income_1947, income_1972, income_2024]):
        pct_change_1947_1972 = ((income_1972 - income_1947) / income_1947 * 100) if income_1947 != 0 else 0
        pct_change_1972_2024 = ((income_2024 - income_1972) / income_1972 * 100) if income_1972 != 0 else 0
        print(f"{age_group:<20} {pct_change_1947_1972:>15.1f}% {pct_change_1972_2024:>14.1f}%")

# Create publication-quality plot
plt.style.use('seaborn-v0_8-whitegrid')
fig, ax = plt.subplots(figsize=(10, 6))

# Define colors and markers for each age group
styles = [
    ('25 to 34 Years', 'b', 'o'),
    ('35 to 44 Years', 'g', '^'),
    ('45 to 54 Years', 'r', 's'),
    ('55 to 64 Years', 'c', 'D'),
    ('65 Years and Older', 'm', '*'),
]

# Plot each age group
for age_group, color, marker in styles:
    ax.plot(pivot_df.index, pivot_df[age_group] / 1000, label=age_group,
            color=color, marker=marker, markersize=5, linewidth=2, markevery=5)

# Customize plot
ax.set_xlabel('Year', fontsize=12)
ax.set_ylabel('Combined Median Income (2024 $ Thousands)', fontsize=12)
ax.set_title('Median Income by Age Group in the U.S. (1947-2024)', fontsize=14, pad=10)
ax.legend(title='Age Group', fontsize=10, title_fontsize=11, loc='upper left', bbox_to_anchor=(0, 1))
ax.tick_params(axis='both', labelsize=10)
ax.set_xlim(1947, 2024)
ax.set_ylim(0, pivot_df.max().max() / 1000 * 1.1)  # Add 10% headroom

# Ensure layout is tight
plt.tight_layout()

# Save plot as high-resolution PNG
plt.savefig('figures/Chapter3/median_income_by_age_plot.png', dpi=300, bbox_inches='tight')
plt.close()