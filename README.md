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
   - Stale balance-sheet data (>190 days)
   - Detected discontinued operations or non-comparable history
   - Missing provider, issuer identity, or as-of provenance

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
- `us_watchlist_YYYYMMDD_HHMMSS.csv` - Top 20 eligible US names with research entry prices and alerts
- `ca_watchlist_YYYYMMDD_HHMMSS.csv` - Top 10 eligible Canadian names with research entry prices and alerts
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
Fair PE = min(Sector policy cap, Current PE, optional precomputed Sector PE)
```
Uses the most conservative P/E ratio available.

**3. Conservative DCF**
```
Only used if FCF is stable (CV < 30%)
Growth capped at 0-3% according to sector
Discount rate floor = 9-11% according to sector
DCF is disabled for Financial Services and REITs; sector-specific models are used instead
```

The cash-flow input is an FCFE proxy (operating cash flow less capital expenditure),
so net debt is not subtracted a second time. The output records this basis explicitly.

### Sector-specific models

- Banks and insurers use the lower of a tangible-book/normalized-return estimate and an
  8x normalized-earnings cross-check. A common-equity/assets floor is only a preliminary
  safety gate; CET1 or insurer risk-based capital must be checked in official filings.
- REITs use a three-year lower-quartile FFO proxy, apply a 20% AFFO haircut, and use an
  8x-10x multiple. Debt/EBITDA above 7x is excluded. Company-reported FFO/AFFO, recurring
  capital expenditure, occupancy, and debt maturities still require manual verification.
- Other financial companies use conservative normalized earnings without a DCF and carry
  an explicit sector-risk verification warning.

### Data and comparability safeguards

- Cached records are schema-versioned; older records are automatically refetched.
- The newest available annual or quarterly balance sheet supplies cash, debt, equity,
  and shares, and records its reporting period and frequency.
- EPS uses each period's diluted average shares when available instead of today's share count.
- Material recent discontinued operations block ranking until a comparable history can be
  rebuilt; immaterial presentation-only amounts do not stop the line.
- Material unusual gains and isolated upside EPS spikes are excluded from normalization;
  losses are retained.
- Energy and Materials use lower-quartile rather than mean normalization, an 8× earnings cap,
  an 11% discount floor, and zero perpetual growth to reduce cycle-peak false positives.
- Ranked and excluded CSVs include provider, stable issuer key (SEC CIK when available),
  source URL, fundamentals date, quality flags, valuation policy, DCF basis, sector model,
  research entry price, alert status, and any filing verification still required.

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

### Point-in-time backtesting

The live output is a current research watchlist, not evidence that the strategy
has worked historically. The repository includes a backtest engine that only
runs on explicit point-in-time snapshots:

```bash
python src/backtest.py \
  --signals path/to/historical_signals.csv \
  --prices path/to/adjusted_prices.csv \
  --benchmark SPY \
  --output outputs/backtest
```

The signal file must contain one full historical universe snapshot per rebalance
date with these columns:

- `signal_date`, `ticker`, `current_price`, `intrinsic_value`
- `eligible`, `universe_member`
- `fundamentals_available_date` — the date the inputs were publicly available,
  not the fiscal period end

The price file requires `date`, `ticker`, and `adjusted_close`, including the
benchmark ticker when one is requested. Orders are simulated on the first
trading session after each signal. Missing selected-stock prices, future-dated
fundamentals, duplicate observations, and malformed inputs stop the run.

Outputs include period returns, security-level holdings, CAGR, annualized
rebalance-period volatility, drawdown observed at rebalance endpoints, turnover,
transaction costs, hit rate, and benchmark-relative CAGR. Daily volatility and
intra-period drawdown require a separate daily mark-to-market equity curve and
are intentionally not inferred from sparse snapshots. No historical performance
is claimed until a survivorship-bias-free, filing-date-aware dataset is supplied.

SEC Company Facts can be converted into valuation snapshots after obtaining a
historical membership file and adjusted-price history:

```bash
export SEC_USER_AGENT="Your Name or Organization your-email@example.com"
python src/historical_signals.py \
  --membership path/to/historical_membership.csv \
  --prices path/to/adjusted_prices.csv \
  --output data/historical_signals.csv
```

The downloader caches responses, stays below the SEC's published request ceiling,
uses stable CIK identifiers, and excludes facts filed after each signal date.
See `docs/HISTORICAL_DATA.md` for the data contract and known coverage limits.

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
