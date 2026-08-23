#!/usr/bin/env python3
import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

SERIES = [
    "CPIAUCSL",
    "CPIHOSSL",
    "CUSR0000SEEB",
    "CPITRNSL",
    "CPIMEDSL",
]

def download_json(url, tries=5):
    last_err = None
    for attempt in range(1, tries + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "EverydayEconomics/1.0",
                    "Accept": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=90) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            last_err = exc
            print(f"    attempt {attempt}/{tries} failed: {exc}")
            time.sleep(3 * attempt)
    raise RuntimeError(last_err)

def main():
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        raise SystemExit("ERROR: FRED_API_KEY is not set.")

    raw_dir = Path("data/raw/fred")
    raw_dir.mkdir(parents=True, exist_ok=True)

    base = "https://api.stlouisfed.org/fred/series/observations"

    for sid in SERIES:
        print(f"==> Downloading {sid} from FRED API")

        params = {
            "series_id": sid,
            "api_key": api_key,
            "file_type": "json",
            "observation_start": "1947-01-01",
        }
        url = base + "?" + urllib.parse.urlencode(params)
        payload = download_json(url)

        if "observations" not in payload:
            raise RuntimeError(f"Bad FRED response for {sid}: {payload}")

        rows = []
        for obs in payload["observations"]:
            value = obs.get("value")
            rows.append({
                "observation_date": obs["date"],
                sid: pd.NA if value in (None, "", ".") else float(value),
            })

        out = raw_dir / f"{sid}.csv"
        pd.DataFrame(rows).to_csv(out, index=False)
        print(f"    wrote {out}")

if __name__ == "__main__":
    main()
