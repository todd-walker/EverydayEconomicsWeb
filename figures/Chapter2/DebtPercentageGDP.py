import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Set publication-ready style
plt.style.use('seaborn-v0_8-whitegrid')  # Clean, professional style
plt.rcParams.update({
    'font.family': 'Arial',  # Standard publication font
    'font.size': 12,         # Readable font size
    'axes.titlesize': 14,    # Title font size
    'axes.labelsize': 12,    # Axis label font size
    'xtick.labelsize': 10,   # X-tick font size
    'ytick.labelsize': 10,   # Y-tick font size
    'legend.fontsize': 10,   # Legend font size
    'figure.dpi': 300        # High resolution for publication
})

# Load the data from the provided CSV content
data = pd.read_csv('figures/Chapter2/DebtData.csv')

# Convert Date column to datetime format
data['Date'] = pd.to_datetime(data['Date'].str.replace(':Q', '-Q'))

# Set Date as the index
data.set_index('Date', inplace=True)

# Define debt components (excluding Total)
components = ['Mortgage', 'HE Revolving', 'Auto Loan', 'Credit Card', 'Student Loan', 'Other']

# Define a publication-friendly color palette (colorblind-friendly)
colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']

# Create figure and axis
fig, ax = plt.subplots(figsize=(8, 5))  # Standard size for publications

# Plot stacked bar chart for each date
bar_width = 0.8  # Slightly wider bars for clarity
dates = data.index
x = range(len(dates))

# Initialize bottom for stacking
bottom = pd.Series(0, index=dates)

# Plot each component
for component, color in zip(components, colors):
    ax.bar(x, data[component], bar_width, bottom=bottom, label=component, color=color, edgecolor='white', linewidth=0.5)
    bottom += data[component]

# Customize the plot
#ax.set_title('U.S. Household Debt by Category (Trillions of USD)', pad=15, weight='bold')
ax.set_ylabel('Debt (Trillions of USD)', labelpad=10)
ax.set_xlabel('Year', labelpad=10)

# Set x-ticks to show every 2 years for clarity
ax.set_xticks(x[::8])  # Show every 2 years (8 quarters)
ax.set_xticklabels(dates[::8].strftime('%Y'), rotation=0)

# Add subtle grid and remove top/right spines
ax.grid(True, axis='y', linestyle='--', alpha=0.7)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# Adjust legend
ax.legend(bbox_to_anchor=(0, 1), loc='upper left', frameon=True, edgecolor='black', framealpha=1)

# Add data source annotation
plt.text(0.01, -0.15, 'Source: Federal Reserve Bank of New York', transform=ax.transAxes, fontsize=8, color='gray')

# Adjust layout to prevent clipping
plt.tight_layout()

# Save the figure for publication (optional, uncomment to save)
# Save the figure for LaTeX (PDF for vector quality, PNG as backup)
plt.savefig('figures/Chapter2/household_debt.pdf', dpi=300, bbox_inches='tight', format='pdf')
plt.savefig('figures/Chapter2/household_debt.png', dpi=300, bbox_inches='tight', format='png')

# Show the plot
plt.show()




# Define debt components (excluding Mortgage and Total)
components = ['Auto Loan', 'Credit Card', 'Student Loan', 'Other']

# Define a publication-friendly color palette (colorblind-friendly)
colors = ['#2ca02c', '#d62728', '#9467bd', '#8c564b']

# Create figure and axis
fig, ax = plt.subplots(figsize=(8, 5))  # Standard size for publications

# Plot each component with shading
for component, color in zip(components, colors):
    ax.plot(data.index, data[component], label=component, color=color, linewidth=2)
    #ax.fill_between(data.index, data[component], alpha=0.1, color=color)  # Subtle shading

# Customize the plot
#ax.set_title('U.S. Non-Mortgage Household Debt by Category (Trillions of USD)', pad=20, weight='bold')
ax.set_ylabel('Debt (Trillions of USD)', labelpad=10)
ax.set_xlabel('Year', labelpad=10)

# Set x-ticks to show every 2 years for clarity
ax.set_xticks(data.index[::8])  # Show every 2 years (8 quarters)
ax.set_xticklabels(data.index[::8].strftime('%Y'), rotation=0)

# Add subtle grid and remove top/right spines
ax.grid(True, axis='y', linestyle='--', alpha=0.7)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# Adjust legend
ax.legend(bbox_to_anchor=(0, 1), loc='upper left', frameon=True, edgecolor='black', framealpha=1)

# Add data source annotation
plt.text(0.01, -0.15, 'Source: Federal Reserve Bank of New York', transform=ax.transAxes, fontsize=8, color='gray')

# Adjust layout to prevent clipping
fig.subplots_adjust(top=0.85, bottom=0.2, right=0.75, left=0.1)

# Save the figure for LaTeX (PDF for vector quality, PNG as backup)
plt.savefig('figures/Chapter2/non_mortgage_debt.pdf', dpi=300, bbox_inches='tight', format='pdf')
plt.savefig('figures/Chapter2/non_mortgage_debt.png', dpi=300, bbox_inches='tight', format='png')

# Show the plot
plt.show()