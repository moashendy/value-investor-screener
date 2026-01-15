"""
Configuration for Value Investing Stock Ranker
"""

# Valuation parameters
DISCOUNT_RATE = 0.09  # 9% - conservative required return
MAX_GROWTH_RATE = 0.03  # 3% - conservative perpetual growth
CONSERVATIVE_PE = 10  # Graham's conservative multiple

# Quality filters
MIN_INTEREST_COVERAGE = 3.0  # Times interest earned
MAX_DEBT_TO_EQUITY = 2.0  # Conservative leverage limit

# Data parameters
YEARS_FOR_NORMALIZATION = 5  # Years to average for normalized metrics
MIN_YEARS_REQUIRED = 3  # Minimum years of data to include stock

# Margin of Safety bands
MOS_BANDS = [
    (0.50, "Exceptional (>50%)"),
    (0.30, "Strong (30-50%)"),
    (0.20, "Moderate (20-30%)"),
    (0.10, "Slight (10-20%)"),
    (0.00, "Minimal (0-10%)"),
    (-float('inf'), "Overvalued")
]

# Stock universes
SP500_TICKER = "^GSPC"  # For reference only
# Will fetch actual S&P 500 constituents
CANADIAN_EXCHANGES = ['TO', 'V']  # TSX and TSXV

# Output settings
OUTPUT_DIR = "outputs"
DATA_DIR = "data"
RESULTS_FILE = "stock_rankings_{date}.csv"
CHARTS_DIR = "charts"
