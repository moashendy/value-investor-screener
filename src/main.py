"""
Main script to run the value investing stock screener
Orchestrates data fetching, valuation, and ranking
"""

import sys
from datetime import datetime
from typing import List
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import *
from data_fetcher import StockDataFetcher
from valuations import GrahamValuator, ValuationResult
from screener import ValueScreener


def analyze_stocks(tickers: List[str], 
                   fetcher: StockDataFetcher,
                   valuator: GrahamValuator,
                   sector_pes: dict,
                   market_name: str,
                   max_workers: int = 5) -> List[ValuationResult]:
    """
    Analyze a list of stocks and return valuations using concurrency
    """
    valuations = []
    total = len(tickers)
    fetched_data = {}
    
    print(f"\nFetching data for {total} {market_name} stocks (max_workers={max_workers})...")
    print("-" * 60)
    
    # Pre-fetch a single stock synchronously to securely cache the Yahoo Finance Crumb/Cookies 
    # This completely eliminates the 401 threading spam ban when 20+ workers hit concurrently
    try:
        import yfinance as yf
        yf.Ticker("MSFT").info
    except Exception:
        pass
    
    # 1. Fetch data concurrently
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(fetcher.get_financial_data, ticker): ticker 
            for ticker in tickers
        }
        
        completed = 0
        for future in as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            completed += 1
            print(f"[{completed}/{total}] Fetched {ticker}")
            try:
                data = future.result()
                fetched_data[ticker] = data
            except Exception as e:
                print(f"❌ Error fetching {ticker}: {e}")
                fetched_data[ticker] = None

    print(f"\nEvaluating valuations for {market_name} stocks...")
    print("-" * 60)
    
    # 2. Evaluate sequentially to maintain orderly reporting
    for ticker in tickers:
        financial_data = fetched_data.get(ticker)
        
        if financial_data is None:
            valuations.append(ValuationResult(
                ticker=ticker,
                company_name=ticker,
                current_price=0,
                normalized_eps=None,
                normalized_fcf=None,
                years_of_data=0,
                epv_value=None,
                multiple_value=None,
                dcf_value=None,
                intrinsic_value=None,
                margin_of_safety=None,
                interest_coverage=None,
                debt_to_equity=None,
                sector="Unknown",
                roic=None,
                ev_fcf_yield=None,
                f_score=None,
                wacc=None,
                altman_z_score=None,
                reasons_excluded=["Failed to fetch network data"]
            ))
            continue
            
        try:
            # Valuate the stock
            valuation = valuator.valuate_stock(financial_data, sector_pes)
            valuations.append(valuation)
            
            # Print status
            if valuation.is_valid():
                mos_pct = valuation.margin_of_safety * 100
                print(f"{ticker:>6s}: ✓ MoS: {mos_pct:>6.1f}%\t(IV: ${valuation.intrinsic_value:.2f})")
            else:
                print(f"{ticker:>6s}: ⊗ Excluded: {valuation.reasons_excluded[0]}")
                
        except Exception as e:
            valuations.append(ValuationResult(
                ticker=ticker,
                company_name=ticker,
                current_price=0,
                normalized_eps=None,
                normalized_fcf=None,
                years_of_data=0,
                epv_value=None,
                multiple_value=None,
                dcf_value=None,
                intrinsic_value=None,
                margin_of_safety=None,
                interest_coverage=None,
                debt_to_equity=None,
                sector="Unknown",
                roic=None,
                ev_fcf_yield=None,
                f_score=None,
                wacc=None,
                altman_z_score=None,
                reasons_excluded=[f"Evaluation Error: {str(e)[:30]}"]
            ))
            
    return valuations


def main(quick_mode: bool = False, sample_size: int = None):
    """
    Main execution function
    
    Args:
        quick_mode: If True, only analyze a small sample for testing
        sample_size: Number of stocks to analyze (for quick testing)
    """
    print("\n" + "=" * 70)
    print("VALUE INVESTING STOCK RANKER")
    print("Graham-Style Intrinsic Value Analysis")
    print("=" * 70)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Initialize components
    print("\n📊 Initializing components...")
    fetcher = StockDataFetcher(cache_dir=DATA_DIR)
    valuator = GrahamValuator(
        discount_rate=DISCOUNT_RATE,
        max_growth=MAX_GROWTH_RATE,
        conservative_pe=CONSERVATIVE_PE,
        min_interest_coverage=MIN_INTEREST_COVERAGE,
        max_debt_to_equity=MAX_DEBT_TO_EQUITY
    )
    screener = ValueScreener(output_dir=OUTPUT_DIR)
    
    # Get stock universes
    print("\n📋 Fetching stock lists...")
    us_tickers = fetcher.get_sp500_tickers()
    ca_tickers = fetcher.get_canadian_tickers()
    
    # Apply quick mode if requested
    if quick_mode or sample_size:
        n = sample_size if sample_size else 20
        print(f"\n⚡ Quick mode: analyzing {n} stocks from each market")
        us_tickers = us_tickers[:n]
        ca_tickers = ca_tickers[:min(n, len(ca_tickers))]
    
    print(f"  • US stocks: {len(us_tickers)}")
    print(f"  • Canadian stocks: {len(ca_tickers)}")
    
    # Calculate sector PE medians (for context)
    print("\n📈 Calculating sector PE ratios...")
    all_tickers = us_tickers + ca_tickers
    sector_pes = fetcher.get_sector_pe_ratios(all_tickers)
    print(f"  • Found PE data for {len(sector_pes)} sectors")
    
    # Analyze US stocks
    us_valuations = analyze_stocks(
        us_tickers, 
        fetcher, 
        valuator, 
        sector_pes,
        "US"
    )
    
    # Analyze Canadian stocks
    ca_valuations = analyze_stocks(
        ca_tickers,
        fetcher,
        valuator,
        sector_pes,
        "Canadian"
    )
    
    # Generate rankings and reports
    print("\n" + "=" * 70)
    print("GENERATING REPORTS")
    print("=" * 70)
    
    tables = screener.create_summary_tables(us_valuations, ca_valuations)
    
    # Print summary statistics
    us_valid = len([v for v in us_valuations if v.is_valid()])
    ca_valid = len([v for v in ca_valuations if v.is_valid()])
    us_opps = len(tables.get('us_opportunities', []))
    ca_opps = len(tables.get('ca_opportunities', []))
    
    print(f"\n✅ Analysis complete!")
    print(f"  • US: {us_valid}/{len(us_valuations)} passed filters, {us_opps} opportunities")
    print(f"  • CA: {ca_valid}/{len(ca_valuations)} passed filters, {ca_opps} opportunities")
    
    # Show top opportunities
    if not tables['us_opportunities'].empty:
        print("\n🎯 Top 5 US Opportunities:")
        top5_us = tables['us_opportunities'].head(5)[['Ticker', 'Company', 'MoS %', 'Current Price', 'Intrinsic Value']]
        print(top5_us.to_string(index=False))
    
    if not tables['ca_opportunities'].empty:
        print("\n🎯 Top 5 Canadian Opportunities:")
        top5_ca = tables['ca_opportunities'].head(5)[['Ticker', 'Company', 'MoS %', 'Current Price', 'Intrinsic Value']]
        print(top5_ca.to_string(index=False))
    
    # Save results
    print("\n💾 Saving results...")
    report_path = screener.save_results(tables, us_valuations, ca_valuations, timestamp)
    
    print("\n" + "=" * 70)
    print(f"✅ Complete! Results saved to: {OUTPUT_DIR}/")
    print(f"📄 Main report: {report_path}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Value Investing Stock Ranker - Graham-style analysis"
    )
    parser.add_argument(
        '--quick',
        action='store_true',
        help='Quick mode: analyze only 20 stocks from each market'
    )
    parser.add_argument(
        '--sample',
        type=int,
        metavar='N',
        help='Analyze N stocks from each market (for testing)'
    )
    
    args = parser.parse_args()
    
    try:
        main(quick_mode=args.quick, sample_size=args.sample)
    except KeyboardInterrupt:
        print("\n\n⚠️  Analysis interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
