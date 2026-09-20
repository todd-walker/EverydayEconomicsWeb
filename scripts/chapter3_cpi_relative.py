import json
from pathlib import Path
from urllib.request import Request, urlopen

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed" / "chapter3" / "cpi_relative_1983.csv"
OUT.parent.mkdir(parents=True, exist_ok=True)

# CPI-U, U.S. city average, not seasonally adjusted.
SERIES = {
    "All items": "CUUR0000SA0",
    "College tuition": "CUUR0000SEEB01",
    "Apparel": "CUUR0000SAA",
    "Household Energy": "CUUR0000SAH21",
    "Food": "CUUR0000SAF1",
    "Medical care": "CUUR0000SAM",
    "New vehicles": "CUUR0000SETA01",
    "Shelter": "CUUR0000SAH1",
}

API = "https://api.bls.gov/publicAPI/v2/timeseries/data/"


def fetch_window(start_year, end_year):
    payload = {
        "seriesid": list(SERIES.values()),
        "startyear": str(start_year),
        "endyear": str(end_year),
    }

    req = Request(
        API,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "EverydayEconomics/1.0",
        },
        method="POST",
    )

    with urlopen(req, timeout=60) as response:
        result = json.loads(response.read().decode("utf-8"))

    if result.get("status") != "REQUEST_SUCCEEDED":
        raise RuntimeError(
            f"BLS request failed for {start_year}-{end_year}: "
            f"{result.get('message')}"
        )

    if result.get("message"):
        print(f"BLS message {start_year}-{end_year}: {result['message']}")

    id_to_label = {sid: label for label, sid in SERIES.items()}
    rows = []

    for series in result["Results"]["series"]:
        sid = series["seriesID"]
        label = id_to_label.get(sid)

        if label is None:
            continue

        years_returned = sorted(
            {
                int(obs["year"])
                for obs in series["data"]
                if obs["period"].startswith("M")
                and obs["period"] != "M13"
            }
        )

        if years_returned:
            print(
                f"{label:18s} {start_year}-{end_year}: "
                f"{min(years_returned)}-{max(years_returned)}"
            )
        else:
            print(
                f"WARNING: {label} returned no data "
                f"for {start_year}-{end_year}"
            )

        for obs in series["data"]:
            period = obs["period"]

            if not period.startswith("M") or period == "M13":
                continue

            rows.append(
                {
                    "year": int(obs["year"]),
                    "month": int(period[1:]),
                    "category": label,
                    "series_id": sid,
                    "cpi": float(obs["value"]),
                }
            )

    return pd.DataFrame(rows)


# Unregistered BLS API requests are limited to 10 years.
windows = [
    (1983, 1992),
    (1993, 2002),
    (2003, 2012),
    (2013, 2020),
]

pieces = []

for start, end in windows:
    print(f"\nDownloading {start}-{end}")
    pieces.append(fetch_window(start, end))

monthly = pd.concat(pieces, ignore_index=True)

if monthly.empty:
    raise RuntimeError("BLS returned no observations.")

print("\nOverall returned range:")
print(monthly.groupby("category")["year"].agg(["min", "max", "nunique"]))


# Annual averages of monthly CPI observations.
annual = (
    monthly
    .groupby(["year", "category", "series_id"], as_index=False)["cpi"]
    .mean()
)


# Verify every requested category has a 1983 baseline.
base_1983 = (
    annual.loc[annual["year"] == 1983]
    .set_index("category")["cpi"]
)

missing_base = sorted(set(SERIES) - set(base_1983.index))

if missing_base:
    raise RuntimeError(
        "Missing 1983 baseline for: " + ", ".join(missing_base)
    )


# Growth of each component from its own 1983 value.
annual["component_growth_1983"] = annual.apply(
    lambda row: row["cpi"] / base_1983.loc[row["category"]],
    axis=1,
)


# Growth of the overall CPI from 1983.
all_items_growth = (
    annual.loc[annual["category"] == "All items"]
    .set_index("year")["component_growth_1983"]
)


# Relative price:
# component price growth / overall price-level growth.
#
# Thus every series = 1 in 1983.
annual["relative_index"] = annual.apply(
    lambda row: (
        row["component_growth_1983"]
        / all_items_growth.loc[row["year"]]
    ),
    axis=1,
)


annual = annual[
    [
        "year",
        "category",
        "series_id",
        "cpi",
        "component_growth_1983",
        "relative_index",
    ]
].sort_values(["year", "category"])


# Hard validation before writing.
check_2020 = annual.loc[annual["year"] == 2020]

if len(check_2020) != len(SERIES):
    raise RuntimeError(
        f"Expected {len(SERIES)} series in 2020; "
        f"found {len(check_2020)}."
    )

all_items_2020 = check_2020.loc[
    check_2020["category"] == "All items",
    "relative_index",
].iloc[0]

if abs(all_items_2020 - 1.0) > 1e-10:
    raise RuntimeError(
        f"All-items relative index should equal 1; got {all_items_2020}"
    )


annual.to_csv(OUT, index=False)

print(f"\nSaved: {OUT}")

print("\n2020 relative prices, 1983 = 1:")
print(
    check_2020[
        ["category", "relative_index"]
    ]
    .sort_values("relative_index", ascending=False)
    .to_string(index=False)
)
