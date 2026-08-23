#!/usr/bin/env bash
set -euo pipefail

ANCHOR_YEAR="${1:-2024}"
START_YEAR="${2:-1980}"

PROJECT_ROOT="/media/todd/402c0fe4-be1d-4a58-95cd-a759825c1b6f/School/EverydayEconomics"
cd "$PROJECT_ROOT"

echo "==> Project root: $PROJECT_ROOT"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

echo "==> Installing/updating Python dependencies"
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install pandas numpy matplotlib openpyxl jinja2

RAW_FRED="data/raw/fred"
mkdir -p "$RAW_FRED"

download_fred() {
  SID="$1"
  OUTFILE="${RAW_FRED}/${SID}.csv"
  TMPFILE="${OUTFILE}.tmp"
  URL="https://fred.stlouisfed.org/graph/fredgraph.csv?id=${SID}"

  echo "==> Downloading ${SID}"

  rm -f "$TMPFILE"

  curl --http1.1 -L --fail --compressed \
    --retry 10 --retry-delay 5 --retry-all-errors \
    --connect-timeout 30 --max-time 240 \
    -A "Mozilla/5.0 (X11; Linux x86_64; rv:152.0) Gecko/20100101 Firefox/152.0" \
    -H "Accept: text/csv,*/*" \
    -o "$TMPFILE" \
    "$URL"

  if ! head -n 1 "$TMPFILE" | tr -d '\r' | grep -q "observation_date"; then
    echo "ERROR: ${SID} did not download as a valid FRED CSV."
    echo "First five lines:"
    head -n 5 "$TMPFILE"
    exit 1
  fi

  mv "$TMPFILE" "$OUTFILE"
}

download_fred CPIAUCSL
download_fred CPIHOSSL
download_fred CUSR0000SEEB
download_fred CPITRNSL
download_fred CPIMEDSL

echo
echo "==> FRED files available"
ls -lh data/raw/fred/CPIAUCSL.csv \
       data/raw/fred/CPIHOSSL.csv \
       data/raw/fred/CUSR0000SEEB.csv \
       data/raw/fred/CPITRNSL.csv \
       data/raw/fred/CPIMEDSL.csv

echo
echo "==> Running CE-based time-cost redo"
.venv/bin/python scripts/chapter5_ce_time_costs.py \
  --anchor-year "$ANCHOR_YEAR" \
  --start-year "$START_YEAR"

echo
echo "==> Processed outputs"
ls -lh data/processed/chapter5/time_costs_ce_age_* || true

echo
echo "==> Figure/table outputs"
ls -lh figures/Chapter5/time_costs_ce_age_* || true

echo
echo "Done."
