# Technical Overview

## Architecture

### Core Principles

1. **Modularity**: Each component handles one responsibility
2. **Clarity over optimization**: Readable code that can be audited
3. **Conservative by design**: Every choice errs on the side of caution
4. **No black boxes**: All calculations are transparent and traceable

### Components

```
┌──────────────────────────────────────────────────────────────┐
│                        main.py                               │
│                   (Orchestration Layer)                      │
└────────────┬─────────────────────────────────────────────────┘
             │
     ┌───────┴───────┬──────────────┬─────────────────┐
     │               │              │                 │
┌────▼─────┐  ┌─────▼──────┐  ┌───▼────────┐  ┌────▼──────┐
│  config  │  │data_fetcher│  │ valuations │  │ screener  │
│          │  │            │  │            │  │           │
│Constants │  │yfinance    │  │Graham      │  │Ranking    │
│Parameters│  │API calls   │  │Models      │  │Reporting  │
└──────────┘  └────────────┘  └────────────┘  └───────────┘
```

## Data Flow

```
1. Stock Universe
   ├─ S&P 500 constituents (Wikipedia/fallback list)
   └─ Canadian stocks (curated list)

2. Data Fetching (data_fetcher.py)
   ├─ Current prices
   ├─ Annual financials (5 years)
   ├─ Quarterly financials
   └─ Balance sheet data

3. Normalization (valuations.py)
   ├─ 5-year average EPS
   ├─ 5-year average FCF
   └─ Quality metric calculation

4. Quality Filters (valuations.py)
   ├─ Positive normalized FCF
   ├─ Interest coverage ≥ 3x
   └─ Debt/Equity ≤ 2.0

5. Valuation Methods (valuations.py)
   ├─ Earnings Power Value (EPV)
   ├─ Conservative Multiple
   └─ Conservative DCF (if stable FCF)

6. Conservative Selection (valuations.py)
   └─ Intrinsic Value = min(EPV, Multiple, DCF)

7. Margin of Safety (valuations.py)
   └─ MoS = (IV - Price) / IV

8. Ranking & Output (screener.py)
   ├─ Sort by MoS
   ├─ Generate tables
   └─ Create reports
```

## Valuation Models (Deep Dive)

### 1. Earnings Power Value (EPV)

**Formula**: `EPV = Normalized EPS / Discount Rate`

**Philosophy**: 
- Assumes current earnings persist indefinitely
- No growth assumption (ultra-conservative)
- Values the business as-is

**Why 9% discount rate?**
- Historical equity returns ~10%
- We use 9% as conservative estimate
- Accounts for equity risk premium

**When it works best**:
- Stable, mature businesses
- Consistent earnings
- Low reinvestment needs

**Limitations**:
- Ignores growth completely
- May undervalue growing businesses
- Assumes perpetual operation

### 2. Conservative Multiple Valuation

**Formula**: `Value = Normalized EPS × Fair PE`

**Fair PE Selection**: `min(10, Historical PE, Sector PE)`

**Philosophy**:
- Graham suggested P/E of 10 as conservative
- We take the LOWEST of three estimates
- Market-aware but not market-following

**Why P/E of 10?**
- Inverse is 10% earnings yield
- Slightly better than EPV (9%)
- Historical "fair value" benchmark

**When it works best**:
- When comparing to peers
- Market-cycle awareness
- Relative valuation checks

**Limitations**:
- Sector PE can be inflated
- Historical PE may not reflect changes
- Still relies on earnings multiples

### 3. Conservative DCF

**Formula**: Present value of future free cash flows

**Parameters**:
- Growth rate: Capped at 3% (GDP-like growth)
- Discount rate: 9%
- Growth period: 5 years, then perpetuity
- Stability requirement: CV < 30%

**Philosophy**:
- Only use when FCF is predictable
- Very conservative growth assumption
- Focus on cash, not earnings

**When it works best**:
- Stable cash flow businesses
- Capital-light models
- Predictable operations

**Limitations**:
- Requires FCF stability
- Terminal value is majority of value
- Growth cap may undervalue exceptional businesses

### Final Intrinsic Value

**Selection**: `min(EPV, Multiple, DCF)`

**Why minimum?**
- Most conservative estimate wins
- Protects against optimistic assumptions
- Creates built-in margin of safety

## Quality Filters

### Interest Coverage ≥ 3.0x

**Formula**: `Operating Income / Interest Expense`

**Rationale**:
- Graham's minimum: 2.0x for utilities, 3.0x for industrials
- We use 3.0x for all stocks
- Ensures debt serviceability

**What it catches**:
- Over-leveraged companies
- Businesses with thin margins
- Potential bankruptcy risks

### Debt/Equity ≤ 2.0

**Formula**: `Total Debt / Stockholders Equity`

**Rationale**:
- Graham suggested 50% debt to equity for industrials
- We allow up to 200% (2.0) for flexibility
- Still excludes highly leveraged plays

**What it catches**:
- Excessive leverage
- Financial engineering
- Bankruptcy risks

### Positive Normalized FCF

**Requirement**: 5-year average FCF > 0

**Rationale**:
- Cash is king
- Earnings can be manipulated
- FCF shows true cash generation

**What it catches**:
- Capital-intensive businesses
- Accounting gymnastics
- Unsustainable business models

## Data Sources

### Primary: yfinance (Yahoo Finance API)

**Advantages**:
- Free
- Comprehensive
- Historical data available
- Updated daily

**Limitations**:
- Delayed quotes (15-20 minutes)
- Occasional missing data
- API rate limits
- No guarantee of accuracy

**What we use**:
- Daily closing prices
- Annual income statements (5 years)
- Quarterly financials
- Balance sheets
- Cash flow statements
- Analyst estimates (P/E ratios)

### Fallback: Static lists

When APIs fail:
- Hardcoded major S&P 500 stocks
- Curated Canadian blue chips
- Ensures tool always runs

## Edge Cases & Handling

### Missing Data
```python
if financial_data is None:
    reasons_excluded.append("Failed to fetch data")
    # Create minimal valuation result
```

### Negative Metrics
```python
if normalized_fcf <= 0:
    reasons_excluded.append("Negative normalized FCF")
    # Exclude from analysis
```

### Unstable FCF
```python
cv = std(fcf) / mean(fcf)
if cv > 0.30:
    dcf_value = None  # Don't use DCF
```

### Zero Shares Outstanding
```python
if not shares or shares <= 0:
    dcf_value = None  # Can't calculate per-share value
```

## Performance Considerations

### Expected Runtime
- Quick mode (20 stocks): ~2-3 minutes
- Full S&P 500: ~30-45 minutes
- With Canadian stocks: ~45-60 minutes

### Bottlenecks
1. **Network I/O**: API calls to yfinance
2. **Rate limiting**: Yahoo Finance throttling
3. **Data parsing**: XML/JSON from financials

### Optimization Opportunities
- Caching (implemented)
- Parallel requests (not implemented - risky with free API)
- Database storage (not implemented - adds complexity)

### Why We Don't Optimize
- Clarity > speed
- Running overnight is fine
- Free APIs have limits anyway
- Manual review takes longer than computation

## Output Format

### CSV Files
```
us_stocks_YYYYMMDD_HHMMSS.csv
├─ All analyzable US stocks
├─ Sorted by margin of safety
└─ Includes all valuation methods

us_opportunities_YYYYMMDD_HHMMSS.csv
├─ Only stocks with MoS > 20%
└─ Ready for detailed research
```

### Text Report
```
value_report_YYYYMMDD_HHMMSS.txt
├─ Executive summary
├─ Top 10 opportunities per market
├─ Detailed analysis (top 5)
└─ Sector breakdown
```

## Testing Strategy

### Manual Testing
```bash
python demo.py  # Known inputs, predictable outputs
```

### Quick Mode
```bash
python main.py --quick  # Small sample, verify end-to-end
```

### Validation
- Compare valuations to manually calculated examples
- Cross-check with professional tools (FinBox, Gurufocus)
- Sanity checks (IV should be reasonable vs price)

## Extending the System

### Adding New Valuation Methods

1. Add to `GrahamValuator` class:
```python
def new_method(self, normalized_eps):
    return normalized_eps * some_factor
```

2. Update `valuate_stock()`:
```python
new_value = self.new_method(normalized_eps)
values.append(new_value)
```

3. Add to `ValuationResult`:
```python
@dataclass
class ValuationResult:
    new_value: Optional[float]
```

### Adding New Quality Filters

1. Calculate metric in `valuate_stock()`:
```python
new_metric = calculate_new_metric(financial_data)
```

2. Apply filter:
```python
if new_metric < threshold:
    reasons_excluded.append("Failed new filter")
```

3. Add to output:
```python
new_metric=new_metric  # In ValuationResult
```

### Adding New Data Sources

1. Create new fetcher method:
```python
def get_alternative_data(self, ticker):
    # Fetch from new source
    return data
```

2. Merge with existing data:
```python
primary_data = self.get_financial_data(ticker)
alternative_data = self.get_alternative_data(ticker)
merged = {**primary_data, **alternative_data}
```

## Maintenance & Updates

### Weekly
- Check if yfinance API still works
- Verify S&P 500 list is current

### Monthly
- Review excluded stocks for data issues
- Update Canadian stock list if needed

### Quarterly
- Compare results to earnings reports
- Validate calculation accuracy

### Annually
- Review discount rate (still appropriate?)
- Update PE ratios if market regime changed
- Audit overall methodology

## Known Issues & Limitations

### Data Quality
- Yahoo Finance occasionally has errors
- Delisted stocks may cause issues
- International stocks (Canadian) have less data

### Valuation Limitations
- Cannot predict business model changes
- Ignores management quality
- No assessment of competitive advantages
- Growth cap may undervalue tech/growth stocks

### Technical Debt
- No database (uses files)
- No caching of historical valuations
- Limited error recovery
- Single-threaded (slow but safe)

### Future Improvements
- Historical tracking database
- Price alerts when MoS improves
- Automated daily runs (cron)
- Web dashboard
- Portfolio tracking

## Philosophy Alignment

This tool embodies Graham's principles:

✅ **Conservative by design**
- Minimum of methods
- Strict quality filters
- 9% discount rate
- 3% growth cap

✅ **Margin of safety focus**
- Primary ranking metric
- Built into every calculation
- Clear bands for decision-making

✅ **Long-term oriented**
- 5-year normalization
- No trading signals
- Fundamental-only

✅ **Transparent & auditable**
- All calculations visible
- Detailed explanations
- No black boxes

✅ **Intellectually honest**
- Acknowledges limitations
- Conservative assumptions
- No false precision

---

This is a tool for **patient capital** and **thoughtful investors**.

It will not make you rich quickly.

It will help you avoid overpaying for businesses.

And over decades, that's what matters.
