# Value Investing Stock Ranker

A Graham-style intrinsic value calculator and stock screener for S&P 500 and Canadian stocks.

## Philosophy

This tool embodies Benjamin Graham's core principles:

- **Intrinsic value changes slowly** - Based on fundamentals, not sentiment
- **Market prices change daily** - Creating opportunities when they diverge
- **Margin of safety is paramount** - Only invest with a significant discount
- **Quality matters** - Filter out financially weak companies
- **No market timing** - Focus on value, not trading signals

## What This Tool Does

1. **Calculates intrinsic value** using three conservative methods:
   - Earnings Power Value (EPV)
   - Conservative Multiple Valuation
   - Discounted Cash Flow (when stable)

2. **Takes the minimum** of all three methods (most conservative estimate)

3. **Filters out poor quality stocks**:
   - Negative free cash flow
   - Interest coverage < 3x
   - Excessive leverage (D/E > 2.0)

4. **Ranks by margin of safety**:
   - MoS = (Intrinsic Value - Market Price) / Intrinsic Value
   - Higher = better opportunity

5. **Tracks opportunities** over time as prices fluctuate

## Installation

```bash
# Clone or download this repository
cd value_investor

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Quick Test (20 stocks from each market)
```bash
cd src
python main.py --quick
```

### Full Analysis (all S&P 500 + Canadian stocks)
```bash
cd src
python main.py
```

### Custom Sample Size
```bash
cd src
python main.py --sample 50  # Analyze 50 stocks from each market
```

## Output Files

All results are saved to the `outputs/` directory:

### CSV Files
- `us_stocks_YYYYMMDD_HHMMSS.csv` - All US stocks ranked by MoS
- `canadian_stocks_YYYYMMDD_HHMMSS.csv` - All Canadian stocks ranked by MoS
- `us_opportunities_YYYYMMDD_HHMMSS.csv` - US stocks with MoS > 20%
- `ca_opportunities_YYYYMMDD_HHMMSS.csv` - Canadian stocks with MoS > 20%
- `sector_summary_YYYYMMDD_HHMMSS.csv` - Sector-level statistics
- `excluded_stocks_YYYYMMDD_HHMMSS.csv` - Stocks filtered out with reasons

### Text Report
- `value_report_YYYYMMDD_HHMMSS.txt` - Comprehensive summary with:
  - Top opportunities
  - Detailed valuations for top 5 stocks
  - Sector analysis
  - Plain English explanations

## Understanding the Valuations

### Three Valuation Methods

**1. Earnings Power Value (EPV)**
```
EPV = Normalized EPS / 0.09
```
Assumes current earnings persist indefinitely with no growth. Very conservative.

**2. Conservative Multiple Valuation**
```
Value = Normalized EPS × Fair PE
Fair PE = min(10, Historical PE, Sector PE)
```
Uses the most conservative P/E ratio available.

**3. Conservative DCF**
```
Only used if FCF is stable (CV < 30%)
Growth capped at 3%
Discount rate = 9%
```

### Final Intrinsic Value
```
Intrinsic Value = min(EPV, Multiple, DCF)
```
We take the **minimum** of all methods - this is deliberately conservative.

### Margin of Safety Bands

- **>50%** - Exceptional opportunity (rare)
- **30-50%** - Strong value opportunity
- **20-30%** - Moderate opportunity
- **10-20%** - Slight discount
- **0-10%** - Minimal margin
- **<0%** - Overvalued

## Example Output

```
TICKER | MoS %    | COMPANY
-------|----------|------------------------------------------
XYZ    |   42.3%  | Example Corp
ABC    |   35.7%  | Another Company Inc
DEF    |   28.1%  | Third Company Ltd
```

### Detailed Stock Analysis
```
XYZ - Example Corp
==============================================================

Current Price: $45.00
Intrinsic Value: $78.00
Margin of Safety: 42.3% (Strong (30-50%))

VALUATION METHODS:
- Earnings Power Value: $82.00
  (Based on 5 years of normalized EPS: $7.38)
  
- Conservative Multiple: $78.00
  (Using conservative P/E ratio)

- DCF Value: Not calculated (FCF too volatile)

INTRINSIC VALUE = $78.00
(Minimum of all methods - most conservative estimate)

QUALITY METRICS:
- Interest Coverage: 5.2x (minimum 3.0x required)
- Debt/Equity: 0.85 (maximum 2.0 required)

INTERPRETATION: STRONG VALUE: Significant margin of safety. 
Worth detailed research.
```

## Customization

Edit `src/config.py` to adjust parameters:

```python
DISCOUNT_RATE = 0.09         # Required return
MAX_GROWTH_RATE = 0.03       # Maximum growth assumption
CONSERVATIVE_PE = 10         # Base P/E ratio
MIN_INTEREST_COVERAGE = 3.0  # Minimum times interest earned
MAX_DEBT_TO_EQUITY = 2.0     # Maximum leverage
```

## How to Use This Tool

### For Daily Screening
1. Run the analysis daily or weekly
2. Review the opportunities tables (>20% MoS)
3. Read detailed reports for top-ranked stocks
4. Do your own due diligence before investing

### For Tracking
1. Save outputs with dates in filename
2. Compare rankings over time
3. Look for stocks where:
   - Price dropped but intrinsic value unchanged
   - Margin of safety increased significantly

### What This Tool Is NOT
- ❌ Not a buy signal generator
- ❌ Not market timing advice
- ❌ Not a replacement for research
- ❌ Not suitable for day trading

### What This Tool IS
- ✅ A conservative valuation calculator
- ✅ A systematic screening process
- ✅ A starting point for research
- ✅ A long-term value investor's tool

## Important Disclaimers

1. **Do your own research** - This tool provides valuations, not recommendations
2. **Markets can be irrational** - Low prices may be justified by factors not in the model
3. **Past performance ≠ future results** - Historical financials don't guarantee future earnings
4. **Not financial advice** - This is an educational tool for personal use
5. **Check the data** - Always verify fundamentals from official sources

## Limitations

- Uses free data (yfinance) which may have delays or inaccuracies
- Cannot predict business model disruption
- Does not account for:
  - Management quality
  - Competitive advantages (moats)
  - Industry disruption
  - Qualitative factors
  - Future growth opportunities

## Advanced Usage

### Adding Your Own Stocks
Edit `data_fetcher.py` and add tickers to the lists:

```python
def get_custom_watchlist(self):
    return ['TICKER1', 'TICKER2', 'TICKER3']
```

### Adjusting Filters
In `valuations.py`, modify quality thresholds:

```python
if interest_coverage and interest_coverage < 5.0:  # Stricter
    reasons_excluded.append(...)
```

## Project Structure

```
value_investor/
├── src/
│   ├── config.py          # Configuration and constants
│   ├── data_fetcher.py    # Stock data retrieval
│   ├── valuations.py      # Core valuation logic
│   ├── screener.py        # Ranking and reporting
│   └── main.py            # Main execution script
├── data/                  # Cached data (created at runtime)
├── outputs/               # Results and reports (created at runtime)
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Contributing

This is a personal tool, but suggestions for improvement are welcome:
- More conservative valuation methods
- Better quality filters
- Improved data sources
- Canadian stock list improvements

## Philosophy Check

Before using this tool, ask yourself:

1. **Am I willing to hold for years?** This finds long-term value, not trades.
2. **Can I ignore daily volatility?** Prices fluctuate; intrinsic value doesn't.
3. **Will I do my own research?** This is a starting point, not the end.
4. **Do I understand the business?** Never invest in what you don't understand.

If you answered "yes" to all four, this tool is for you.

## License

This tool is provided as-is for educational and personal use.
Not financial advice. Use at your own risk.

---

**Remember**: The goal isn't to find the "best" stocks. The goal is to find **good businesses at great prices** and have the patience to wait.
