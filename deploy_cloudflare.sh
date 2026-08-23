#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

python scripts/chapter2_household_debt_gdp.py

cd web
quarto render

npx wrangler pages deploy _book --project-name todd-everyday-economics --branch main
