# Historical Backtest Data Contract

## Why this is separate from the live screen

Today's S&P 500 list and today's normalized financial history cannot be used to
reconstruct old portfolios. Doing so would retain companies that survived and
can also expose an old signal to later restatements. The historical pipeline
therefore joins three independently dated inputs:

1. Historical membership snapshots, including deletions and former tickers.
2. SEC Company Facts selected by their actual `filed` date.
3. Split- and distribution-adjusted prices that retain delisted securities.

## Membership input

CSV columns:

| Column | Meaning |
| --- | --- |
| `signal_date` | Date the screen was calculated |
| `ticker` | Tradable symbol on that date |
| `cik` | Stable SEC Central Index Key |
| `sector` | Classification known on that date |
| `industry` | Classification known on that date |
| `universe_member` | Whether the security belonged to the tested universe |

Each signal date must represent the full historical universe. Repeating the
current constituent list across old dates is invalid. CIK is required because
tickers can change and can later be reused by another issuer.

## Price input

CSV columns: `date`, `ticker`, `adjusted_close`.

The history must include acquired, bankrupt, and delisted companies. A selected
holding without an entry or exit price stops the run; the engine will not quietly
drop it. The benchmark ticker must be present when `--benchmark` is used.

## Filing-date treatment

`historical_signals.py` reads SEC Company Facts and:

- accepts 10-K and 10-K/A annual-duration facts for normalized annual values;
- accepts 10-K, 10-Q, and amendments for balance-sheet instants;
- rejects facts whose `filed` or period-end date is after the signal date;
- selects the latest version of a period that was public at that time;
- records the latest filing availability date used by the valuation;
- evaluates balance-sheet staleness relative to the historical signal date.

Every signal export also writes a `.coverage.json` audit with usable valuation
coverage by year and sector plus counts for each exclusion reason. “Usable” means
the required data and valuation were available; it is deliberately distinct from
“eligible,” which can be low because a company failed the strategy's quality
rules. The audit also reports additions and deletions between snapshots and warns
when a multi-year membership file shows no churn, a common sign that today's
survivors were copied backward.

The SEC endpoint is free and requires no key, but automated downloads must use a
declared `SEC_USER_AGENT`. Set it to an application or organization name plus a
real contact email. Cached files are stored under `data/companyfacts/`.

## Important remaining limitations

- SEC XBRL coverage and tagging consistency vary by issuer and are weaker in
  earlier years. Missing required concepts exclude a row instead of being filled.
- The free SEC facts do not provide historical S&P membership or delisted return
  histories. Those must come from a licensed or independently audited dataset.
- Current code supports the generic company model. Banks, insurers, other
  financials, and REITs normally fail closed because their historical regulatory
  capital or FFO/AFFO inputs are not available in the generic Company Facts map.
- The pipeline uses a fixed 4.5% risk-free assumption and beta of 1.0 for this
  first historical implementation. Sensitivity tests are required before drawing
  investment conclusions.
- Company Facts alone cannot reliably identify every historical spin-off,
  discontinued operation, or ticker mapping. Corporate-action coverage must be
  audited against the price/vendor dataset.

## Required acceptance checks before trusting results

- Reconcile a sample of at least 25 signals to the filing available on that date.
- Confirm membership changes and effective dates against the index source.
- Confirm delisting returns and merger consideration are represented.
- Report eligible-row coverage by year and sector; reject years with poor coverage.
- Run transaction-cost, entry-lag, threshold, and rebalance-frequency sensitivity.
- Compare against SPY total return and simple equal-weight/value baselines.

Authoritative references:

- [SEC EDGAR data APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
- [SEC automated-access guidance](https://www.sec.gov/about/webmaster-frequently-asked-questions)
- [S&P U.S. Indices methodology](https://www.spglobal.com/spdji/en/methodology/article/sp-us-indices-methodology/)
