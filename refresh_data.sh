#!/bin/bash
set -euo pipefail

# Value Investor Backend Automated Refresher
# Set this to run via cron

# Valid 24-hour cache entries are intentionally preserved. The Python fetcher
# invalidates stale records and old schema versions itself, allowing interrupted
# or provider-limited runs to resume safely.

# 1. Source conda and activate environment
source /home/mhendy/miniforge3/etc/profile.d/conda.sh
conda activate value_investor

# 2. Navigate to workspace
PROJECT_DIR=/home/mhendy/ML_projects/from_wsl/value_investor
cd "$PROJECT_DIR"

# 3. Run the full analysis. set -e prevents frontend publication if the
# run-integrity gate rejects incomplete provider data.
echo "Running full quant analysis..."
python src/main.py

# 4. Publish the newest validated US ranking atomically.
echo "Copying latest data to frontend..."
LATEST_CSV=$(ls -t outputs/us_stocks_*.csv | head -1)
FRONTEND_TMP=frontend/public/data/latest_screener.csv.tmp
cp "$LATEST_CSV" "$FRONTEND_TMP"
mv "$FRONTEND_TMP" frontend/public/data/latest_screener.csv

echo "Done! Fresh data is ready in the outputs/ folder and served to the frontend dashboard."
