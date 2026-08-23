#!/usr/bin/env bash
set -euo pipefail

YEAR="${1:-2024}"

PROJECT_ROOT="/media/todd/402c0fe4-be1d-4a58-95cd-a759825c1b6f/School/EverydayEconomics"
cd "$PROJECT_ROOT"

echo "==> Project root:"
pwd

echo "==> Creating/using virtual environment"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

echo "==> Installing Python dependencies"
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install pandas numpy matplotlib openpyxl jinja2

RAW_DIR="data/raw/bls_cex"
RAW_FILE="${RAW_DIR}/reference-person-age-ranges-${YEAR}.xlsx"
URL="https://www.bls.gov/cex/tables/calendar-year/mean-item-share-average-standard-error/reference-person-age-ranges-${YEAR}.xlsx"

mkdir -p "$RAW_DIR" "data/processed/chapter5" "figures/Chapter5"

echo "==> Downloading CE age table if needed"
if [ ! -s "$RAW_FILE" ]; then
  curl -L --fail --compressed \
    -A "Mozilla/5.0 (X11; Linux x86_64; rv:152.0) Gecko/20100101 Firefox/152.0" \
    -e "https://www.bls.gov/cex/tables/calendar-year/mean-item-share-average-standard-error.htm" \
    -o "$RAW_FILE" \
    "$URL"
else
  echo "Using existing raw file: $RAW_FILE"
fi

echo "==> Verifying downloaded file"
file "$RAW_FILE"

if file "$RAW_FILE" | grep -qi "HTML"; then
  echo "ERROR: Downloaded file appears to be HTML, not Excel."
  echo "Open the BLS page manually and save the Excel file here:"
  echo "  $RAW_FILE"
  exit 1
fi

echo "==> Running Chapter 5 CE age-weight script"
.venv/bin/python scripts/chapter5_ce_age_weights.py --year "$YEAR"

echo
echo "==> Processed outputs"
ls -lh data/processed/chapter5 || true

echo
echo "==> Figure/table outputs"
ls -lh figures/Chapter5 || true

echo
echo "Done."
