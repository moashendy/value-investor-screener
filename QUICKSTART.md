# Quick Start Guide

Get up and running in 5 minutes.

## Setup (one time)

```bash
# 1. Navigate to project
cd value_investor

# 2. Install dependencies
pip install -r requirements.txt
```

## Run Your First Analysis

```bash
# Quick test with 20 stocks
cd src
python main.py --quick
```

This will:
- Fetch data for 20 S&P 500 stocks and 20 Canadian stocks
- Calculate intrinsic values using Graham's methods
- Rank by margin of safety
- Generate reports in `../outputs/`

## Check Results

```bash
# List output files
ls ../outputs/

# Read the main report
cat ../outputs/value_report_*.txt
```

## Understanding Your First Results

Look for these sections in the report:

### Top Opportunities
```
TOP 10 OPPORTUNITIES (US STOCKS)
----------------------------------------------------------------------
TICKER | MoS %    | COMPANY
XYZ    |   42.3%  | Example Corp
ABC    |   35.7%  | Another Company
```

**What this means**: These stocks are trading significantly below their calculated intrinsic value.

### Margin of Safety Bands
- **>30%** = Strong opportunity worth researching
- **20-30%** = Moderate opportunity
- **<20%** = Marginal or overvalued

## Run Full Analysis

```bash
# All S&P 500 + Canadian stocks (takes 30-60 minutes)
python main.py
```

## Daily Workflow

```bash
# 1. Run quick analysis daily
python main.py --quick

# 2. Review opportunities
cat ../outputs/value_report_*.txt | grep -A 50 "TOP 10"

# 3. Research top 3-5 stocks manually
# Read annual reports, understand the business, etc.

# 4. Track over time
# Compare today's results to previous runs
# Look for stocks where IV is stable but price dropped
```

## Customizing Your Screen

Edit `config.py` to be more or less conservative:

```python
# More conservative (higher standards)
MIN_INTEREST_COVERAGE = 5.0  # Instead of 3.0
MAX_DEBT_TO_EQUITY = 1.0     # Instead of 2.0
CONSERVATIVE_PE = 8          # Instead of 10

# Less conservative (more opportunities)
MIN_INTEREST_COVERAGE = 2.5
MAX_DEBT_TO_EQUITY = 3.0
CONSERVATIVE_PE = 12
```

## Common Issues

### "No module named 'yfinance'"
```bash
pip install -r requirements.txt
```

### "No opportunities found"
- Market might be overvalued overall
- Try less strict filters in config.py
- Run full analysis instead of quick mode

### Network/timeout errors
- yfinance uses Yahoo Finance API (free)
- Some stocks may timeout or be missing data
- This is normal - the tool continues with available stocks

## Next Steps

1. Read the full [README.md](../README.md) for methodology
2. Run the demo: `python demo.py`
3. Check the sector summary CSV for market overview
4. Set up a cron job for daily analysis

## Pro Tips

1. **Don't chase high MoS alone** - Always understand WHY a stock is cheap
2. **Look for patterns** - Compare multiple days to see stability
3. **Use as a filter** - Narrow 500 stocks → 20 worth researching
4. **Track excluded stocks** - Sometimes they improve and become opportunities
5. **Be patient** - Value investing requires waiting for the right price

---

**Remember**: This tool finds candidates. You still need to:
- Read the annual reports
- Understand the business model
- Assess competitive position
- Consider qualitative factors

Happy value investing! 📈
