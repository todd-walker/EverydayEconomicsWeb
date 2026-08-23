from pathlib import Path
import re
import urllib.request

import pandas as pd
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
CH2 = ROOT / "figures" / "Chapter2"
RAW_FRED = ROOT / "data" / "raw" / "fred"
PROCESSED = ROOT / "data" / "processed"

RAW_FRED.mkdir(parents=True, exist_ok=True)
PROCESSED.mkdir(parents=True, exist_ok=True)
CH2.mkdir(parents=True, exist_ok=True)

DEBT_CSV = CH2 / "DebtData.csv"
GDP_CSV = RAW_FRED / "GDP.csv"
OUT_CSV = PROCESSED / "chapter2_household_debt_pct_gdp.csv"

FRED_GDP_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=GDP"


def download_fred_gdp() -> None:
    if GDP_CSV.exists():
        print(f"Using existing {GDP_CSV}")
        return

    print(f"Downloading FRED GDP data to {GDP_CSV}")
    urllib.request.urlretrieve(FRED_GDP_URL, GDP_CSV)


def parse_debt_quarter(x) -> pd.Period:
    """
    Handles labels like 2003:Q1, 2003-Q1, 2003Q1, or 03:Q1.
    """
    s = str(x).strip()
    m = re.search(r"(\d{2,4})\s*[:\-]?\s*Q([1-4])", s, flags=re.IGNORECASE)

    if not m:
        raise ValueError(f"Could not parse quarter label: {x}")

    year = int(m.group(1))
    quarter = int(m.group(2))

    if year < 100:
        year = 2000 + year if year < 70 else 1900 + year

    return pd.Period(f"{year}Q{quarter}", freq="Q")


def load_and_merge() -> pd.DataFrame:
    debt = pd.read_csv(DEBT_CSV)

    if "Date" not in debt.columns:
        raise ValueError(f"{DEBT_CSV} must contain a Date column.")

    debt["quarter"] = debt["Date"].apply(parse_debt_quarter)

    gdp = pd.read_csv(GDP_CSV)

    if "observation_date" in gdp.columns:
        gdp = gdp.rename(columns={"observation_date": "DATE"})

    if "DATE" not in gdp.columns:
        gdp = gdp.rename(columns={gdp.columns[0]: "DATE"})

    if "GDP" not in gdp.columns:
        raise ValueError(f"{GDP_CSV} must contain a GDP column.")

    gdp["quarter"] = pd.to_datetime(gdp["DATE"]).dt.to_period("Q")
    gdp["GDP_billions"] = pd.to_numeric(gdp["GDP"], errors="coerce")
    gdp["GDP_trillions"] = gdp["GDP_billions"] / 1000.0

    data = debt.merge(
        gdp[["quarter", "GDP_trillions"]],
        on="quarter",
        how="left",
    )

    debt_components = [
        "Mortgage",
        "HE Revolving",
        "Auto Loan",
        "Credit Card",
        "Student Loan",
        "Other",
        "Total",
    ]

    missing = [c for c in debt_components if c not in data.columns]
    if missing:
        raise ValueError(f"Missing debt columns in {DEBT_CSV}: {missing}")

    for c in debt_components:
        data[f"{c}_pct_gdp"] = 100.0 * data[c] / data["GDP_trillions"]

    data["date"] = data["quarter"].dt.to_timestamp()
    data = data.sort_values("date").reset_index(drop=True)

    data.to_csv(OUT_CSV, index=False)
    print(f"Saved processed data to {OUT_CSV}")

    return data


def set_style() -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    plt.rcParams.update({
        "font.family": "Arial",
        "font.size": 12,
        "axes.titlesize": 14,
        "axes.labelsize": 12,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 10,
        "figure.dpi": 300,
    })


def plot_household_debt_pct_gdp(data: pd.DataFrame) -> None:
    components = [
        "Mortgage_pct_gdp",
        "HE Revolving_pct_gdp",
        "Auto Loan_pct_gdp",
        "Credit Card_pct_gdp",
        "Student Loan_pct_gdp",
        "Other_pct_gdp",
    ]

    labels = [
        "Mortgage",
        "HE Revolving",
        "Auto Loan",
        "Credit Card",
        "Student Loan",
        "Other",
    ]

    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]

    fig, ax = plt.subplots(figsize=(8, 5))

    x = range(len(data))
    bottom = pd.Series(0.0, index=data.index)

    for component, label, color in zip(components, labels, colors):
        ax.bar(
            x,
            data[component],
            0.8,
            bottom=bottom,
            label=label,
            color=color,
            edgecolor="white",
            linewidth=0.5,
        )
        bottom += data[component]

    ax.set_ylabel("Debt (% of GDP)", labelpad=10)
    ax.set_xlabel("Year", labelpad=10)

    ax.set_xticks(list(x)[::8])
    ax.set_xticklabels(data["date"].dt.strftime("%Y").iloc[::8], rotation=0)

    ax.grid(True, axis="y", linestyle="--", alpha=0.7)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax.legend(
        bbox_to_anchor=(0, 1),
        loc="upper left",
        frameon=True,
        edgecolor="black",
        framealpha=1,
    )

    ax.text(
        0.01,
        -0.15,
        "Sources: Federal Reserve Bank of New York; FRED, Federal Reserve Bank of St. Louis",
        transform=ax.transAxes,
        fontsize=8,
        color="gray",
    )

    plt.tight_layout()

    fig.savefig(CH2 / "household_debt_pct_gdp.pdf", dpi=300, bbox_inches="tight")
    fig.savefig(CH2 / "household_debt_pct_gdp.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_non_mortgage_debt_pct_gdp(data: pd.DataFrame) -> None:
    components = [
        "Auto Loan_pct_gdp",
        "Credit Card_pct_gdp",
        "Student Loan_pct_gdp",
        "Other_pct_gdp",
    ]

    labels = [
        "Auto Loan",
        "Credit Card",
        "Student Loan",
        "Other",
    ]

    colors = ["#2ca02c", "#d62728", "#9467bd", "#8c564b"]

    fig, ax = plt.subplots(figsize=(8, 5))

    for component, label, color in zip(components, labels, colors):
        ax.plot(
            data["date"],
            data[component],
            label=label,
            color=color,
            linewidth=2,
        )

    ax.set_ylabel("Debt (% of GDP)", labelpad=10)
    ax.set_xlabel("Year", labelpad=10)

    ticks = data["date"].iloc[::8]
    ax.set_xticks(ticks)
    ax.set_xticklabels(ticks.dt.strftime("%Y"), rotation=0)

    ax.grid(True, axis="y", linestyle="--", alpha=0.7)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax.legend(
        bbox_to_anchor=(0, 1.04),
        loc="upper left",
        frameon=True,
        edgecolor="black",
        framealpha=1,
    )


    fig.subplots_adjust(top=0.85, bottom=0.2, right=0.75, left=0.1)

    fig.savefig(CH2 / "non_mortgage_debt_pct_gdp.pdf", dpi=300, bbox_inches="tight")
    fig.savefig(CH2 / "non_mortgage_debt_pct_gdp.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    download_fred_gdp()
    data = load_and_merge()
    set_style()
    plot_household_debt_pct_gdp(data)
    plot_non_mortgage_debt_pct_gdp(data)

    print("Done.")
    print(f"Raw FRED GDP saved to: {GDP_CSV}")
    print(f"Processed data saved to: {OUT_CSV}")
    print(f"Figures saved to: {CH2}")


if __name__ == "__main__":
    main()
