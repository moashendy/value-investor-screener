# PROJECT SUMMARY

## What You Have

A complete, production-ready value investing stock screener based on Benjamin Graham's principles.

## File Structure

```
value_investor/
│
├── README.md                  # Complete user guide and philosophy
├── QUICKSTART.md              # Get started in 5 minutes
├── TECHNICAL_OVERVIEW.md      # Deep dive into implementation
├── requirements.txt           # Python dependencies
├── .gitignore                 # Git ignore rules
│
├── src/                       # Source code
│   ├── __init__.py           # Package initialization
│   ├── config.py             # Configuration & constants
│   ├── data_fetcher.py       # Stock data retrieval (yfinance)
│   ├── valuations.py         # Core Graham-style valuation logic
│   ├── screener.py           # Ranking & report generation
│   ├── main.py               # Main execution script
│   └── demo.py               # Demo with example calculations
│
├── data/                      # Cached data (created at runtime)
└── outputs/                   # Results & reports (created at runtime)
```

## What It Does

### 1. Fetches Data
- S&P 500 stocks (from Wikipedia or fallback list)
- Canadian stocks (curated blue chips)
- 5 years of financial statements
- Current prices

### 2. Calculates Normalized Metrics
- 5-year average EPS
- 5-year average free cash flow
- Stability metrics

### 3. Applies Quality Filters
- ❌ Negative FCF → excluded
- ❌ Interest coverage < 3x → excluded
- ❌ Debt/Equity > 2.0 → excluded

### 4. Calculates Intrinsic Value (Three Methods)

**Earnings Power Value**
```
EPV = Normalized EPS / 0.09
```

**Conservative Multiple**
```
Value = Normalized EPS × min(10, Historical PE, Sector PE)
```

**Conservative DCF** (if FCF stable)
```
DCF with 3% growth cap, 9% discount rate
```

**Final Intrinsic Value**
```
IV = min(EPV, Multiple, DCF)  ← Most conservative wins
```

### 5. Calculates Margin of Safety
```
MoS = (Intrinsic Value - Current Price) / Intrinsic Value
```

### 6. Ranks & Reports
- Sorts all stocks by margin of safety
- Highlights opportunities (MoS > 20%)
- Generates detailed explanations
- Creates CSV files and text reports

## How to Use

### First Time Setup
```bash
cd value_investor
pip install -r requirements.txt
```

### Run Demo (no API calls)
```bash
cd src
python demo.py
```

### Quick Test (20 stocks, ~3 minutes)
```bash
cd src
python main.py --quick
```

### Full Analysis (500+ stocks, ~60 minutes)
```bash
cd src
python main.py
```

### Check Results
```bash
ls ../outputs/
cat ../outputs/value_report_*.txt
```

## Output Files

Every run creates timestamped files:

1. **us_stocks_YYYYMMDD_HHMMSS.csv**
   - All US stocks analyzed
   - Ranked by margin of safety
   - All valuation methods shown

2. **canadian_stocks_YYYYMMDD_HHMMSS.csv**
   - All Canadian stocks analyzed
   - Same format as US stocks

3. **us_opportunities_YYYYMMDD_HHMMSS.csv**
   - US stocks with MoS > 20%
   - Top candidates for research

4. **ca_opportunities_YYYYMMDD_HHMMSS.csv**
   - Canadian stocks with MoS > 20%

5. **sector_summary_YYYYMMDD_HHMMSS.csv**
   - Sector-level statistics
   - Opportunity counts by sector

6. **excluded_stocks_YYYYMMDD_HHMMSS.csv**
   - Stocks that failed quality filters
   - Reasons for exclusion

7. **value_report_YYYYMMDD_HHMMSS.txt**
   - Executive summary
   - Top 10 opportunities
   - Detailed analysis of top 5
   - Plain English explanations

## Customization

Edit `src/config.py`:

```python
# Make more conservative
DISCOUNT_RATE = 0.10          # Higher required return
CONSERVATIVE_PE = 8           # Lower P/E
MIN_INTEREST_COVERAGE = 5.0   # Stricter filter

# Make less conservative
DISCOUNT_RATE = 0.08
CONSERVATIVE_PE = 12
MIN_INTEREST_COVERAGE = 2.5
```

## Daily Workflow

```bash
# 1. Run analysis
python main.py --quick

# 2. Review top opportunities
grep -A 10 "TOP 10" ../outputs/value_report_*.txt

# 3. Research top 3-5 manually
# - Read annual reports
# - Understand business model
# - Assess competitive position

# 4. Make investment decision
# (Tool finds candidates, YOU decide to invest)
```

## Core Philosophy

✅ **Conservative by design**
- Minimum of three valuation methods
- Strict quality filters
- Low growth assumptions
- High discount rate

✅ **Margin of safety focus**
- Primary ranking metric
- Price must be well below intrinsic value
- Protection against mistakes

✅ **Long-term oriented**
- 5-year normalization period
- No short-term trading signals
- Fundamentals-only approach

✅ **Transparent & auditable**
- All calculations visible
- Detailed explanations
- No black boxes or ML magic

✅ **Intellectually honest**
- Acknowledges limitations
- Conservative assumptions
- Clear about what it can't do

## What This Tool Is NOT

❌ Not a buy signal generator
❌ Not market timing advice
❌ Not a replacement for due diligence
❌ Not suitable for day trading
❌ Not predictive of future stock prices

## What This Tool IS

✅ A systematic screening process
✅ A conservative valuation calculator
✅ A starting point for research
✅ A tool for patient capital
✅ A Graham-inspired framework

## Key Features

### Intellectual Honesty
- Based on proven value investing principles
- Conservative at every decision point
- Transparent methodology
- Acknowledges limitations

### Anti-Fragile Design
- Works in bull and bear markets
- Finds opportunities when others panic
- Immune to market trends
- Based on fundamentals, not sentiment

### Practical Implementation
- Uses free data sources (yfinance)
- Runs on any computer
- No subscription fees
- Modular, hackable code

### Trust-Worthy in Crashes
- More stocks pass filters when markets crash
- Higher margins of safety appear
- Counter-cyclical by design
- Built for contrarian investors

## Example Use Cases

### 1. Daily Screening
Run quick mode daily, track top 10 opportunities over time

### 2. Monthly Deep Dive
Run full analysis monthly, research top 5 in detail

### 3. Crash Opportunism
Run after market crashes to find quality at distressed prices

### 4. Portfolio Monitoring
Track your holdings to see if they're still undervalued

### 5. Sector Rotation
Use sector summary to find undervalued sectors

## Next Steps

1. **Read the docs**
   - README.md for complete guide
   - TECHNICAL_OVERVIEW.md for deep dive
   - QUICKSTART.md for immediate action

2. **Run the demo**
   ```bash
   python src/demo.py
   ```

3. **Test with quick mode**
   ```bash
   python src/main.py --quick
   ```

4. **Review first results**
   - Check the text report
   - Look at CSV files
   - Understand the output format

5. **Customize to your taste**
   - Adjust filters in config.py
   - Add your own watchlist
   - Modify quality standards

6. **Set up automation** (optional)
   - Cron job for daily runs
   - Email top opportunities
   - Track changes over time

## Common Questions

**Q: How often should I run this?**
A: Daily for quick mode, weekly for full analysis. Intrinsic value changes slowly.

**Q: Should I buy every stock with high MoS?**
A: No! This finds candidates. You must still research the business.

**Q: What if no opportunities show up?**
A: Market may be overvalued. Be patient. True value investors wait.

**Q: Can I use this for day trading?**
A: Absolutely not. This is for long-term value investing only.

**Q: Is the data accurate?**
A: Uses Yahoo Finance (free). Always verify from official sources.

**Q: Why are great companies sometimes excluded?**
A: Quality filters are strict. You can relax them in config.py.

**Q: Should I trust the intrinsic values?**
A: They're conservative estimates. Use as a guide, not gospel.

## Final Thoughts

This tool embodies Warren Buffett's advice:

> "Price is what you pay. Value is what you get."

It helps you find situations where you can pay less and get more.

But it requires three things from YOU:

1. **Patience** - Wait for the right price
2. **Research** - Understand the business
3. **Discipline** - Don't chase performance

The tool handles the math.

You handle the judgment.

Together, you can build a rational, value-focused portfolio.

---

**Good investing is boring.** This tool is deliberately boring.

**Good investing is patient.** This tool rewards patience.

**Good investing is conservative.** This tool is obsessively conservative.

Use it well. 📊

---

## Support & Contact

This is a personal tool for educational purposes.

For issues or questions:
1. Read TECHNICAL_OVERVIEW.md for implementation details
2. Check config.py for customization options
3. Review the code - it's designed to be readable

The best support is understanding how it works.

Happy value investing!
