#!/bin/bash

# Value Investor Backend Automated Refresher
# Set this to run via cron

# 1. Clear old cache so it pulls completely fresh data
echo "Clearing 24-Hour Cache..."
rm -f /home/mhendy/ML_projects/from_wsl/value_investor/data/*_finance.json

# 2. Source conda and activate environment
source /home/mhendy/miniforge3/etc/profile.d/conda.sh
conda activate value_investor

# 3. Navigate to workspace
cd /home/mhendy/ML_projects/from_wsl/value_investor

# 4. Run the full analysis (Remove --quick to run all 500 stocks)
echo "Running full quant analysis..."
python src/main.py

# 5. Push newest data to frontend
echo "Copying latest data to frontend..."
LATEST_CSV=$(ls -t outputs/us_stocks_*.csv | head -1)
cp "$LATEST_CSV" frontend/public/data/latest_screener.csv

echo "Done! Fresh data is ready in the outputs/ folder and served to the frontend dashboard."
