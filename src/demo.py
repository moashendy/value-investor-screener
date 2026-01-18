"""
Demo script showing manual valuation calculations
Demonstrates the core valuation logic without API calls
"""

from valuations import GrahamValuator


def demo_manual_valuation():
    """
    Demonstrate manual valuation with example data
    This shows how the valuation logic works
    """
    
    print("\n" + "=" * 70)
    print("VALUATION DEMO - Manual Calculation Example")
    print("=" * 70)
    
    # Initialize valuator
    valuator = GrahamValuator(
        discount_rate=0.09,
        max_growth=0.03,
        conservative_pe=10
    )
    
    # Example company data
    example_company = {
        'ticker': 'DEMO',
        'company_name': 'Demo Value Company',
        'sector': 'Technology',
        'current_price': 50.00,
        'shares_outstanding': 100_000_000,
        
        # 5 years of EPS data (most recent first)
        'annual_eps': [
            {'year': '2024', 'eps': 5.20},
            {'year': '2023', 'eps': 4.80},
            {'year': '2022', 'eps': 5.00},
            {'year': '2021', 'eps': 4.50},
            {'year': '2020', 'eps': 4.70},
        ],
        
        # 5 years of FCF data
        'annual_fcf': [
            {'year': '2024', 'fcf': 450_000_000},
            {'year': '2023', 'fcf': 420_000_000},
            {'year': '2022', 'fcf': 480_000_000},
            {'year': '2021', 'fcf': 410_000_000},
            {'year': '2020', 'fcf': 440_000_000},
        ],
        
        # Balance sheet
        'total_debt': 500_000_000,
        'total_equity': 1_000_000_000,
        'cash': 200_000_000,
        
        # Income statement
        'operating_income': 600_000_000,
        'interest_expense': 25_000_000,
        
        # Valuation multiples
        'current_pe': 12.5,
    }
    
    print("\nCOMPANY DATA:")
    print("-" * 70)
    print(f"Company: {example_company['company_name']}")
    print(f"Ticker: {example_company['ticker']}")
    print(f"Current Price: ${example_company['current_price']:.2f}")
    print(f"Shares Outstanding: {example_company['shares_outstanding']:,}")
    
    print("\nEARNINGS HISTORY:")
    for year_data in example_company['annual_eps']:
        print(f"  {year_data['year']}: ${year_data['eps']:.2f}")
    
    # Calculate normalized EPS
    eps_result = valuator.normalize_metric(example_company['annual_eps'], 'eps')
    normalized_eps, years = eps_result
    
    print(f"\n→ Normalized EPS (5-year average): ${normalized_eps:.2f}")
    
    # Calculate quality metrics
    interest_coverage = valuator.calculate_interest_coverage(
        example_company['operating_income'],
        example_company['interest_expense']
    )
    
    debt_to_equity = valuator.calculate_debt_to_equity(
        example_company['total_debt'],
        example_company['total_equity']
    )
    
    print("\nQUALITY METRICS:")
    print("-" * 70)
    print(f"Interest Coverage: {interest_coverage:.1f}x (minimum required: 3.0x)")
    print(f"Debt to Equity: {debt_to_equity:.2f} (maximum allowed: 2.0)")
    
    if interest_coverage >= 3.0:
        print("✓ Passes interest coverage filter")
    else:
        print("✗ Fails interest coverage filter")
    
    if debt_to_equity <= 2.0:
        print("✓ Passes leverage filter")
    else:
        print("✗ Fails leverage filter")
    
    # Calculate valuations
    print("\nVALUATION METHODS:")
    print("-" * 70)
    
    # 1. EPV
    epv = valuator.earnings_power_value(normalized_eps)
    print(f"\n1. Earnings Power Value (EPV)")
    print(f"   Formula: Normalized EPS / Discount Rate")
    print(f"   Calculation: ${normalized_eps:.2f} / 0.09 = ${epv:.2f}")
    
    # 2. Conservative Multiple
    sector_pe_example = 15.0
    multiple_value = valuator.conservative_multiple_valuation(
        normalized_eps,
        example_company['current_pe'],
        sector_pe_example
    )
    fair_pe = min(10, example_company['current_pe'], sector_pe_example)
    print(f"\n2. Conservative Multiple Valuation")
    print(f"   Formula: Normalized EPS × Fair PE")
    print(f"   Fair PE = min(10, Current PE {example_company['current_pe']}, Sector PE {sector_pe_example})")
    print(f"   Fair PE = {fair_pe:.1f}")
    print(f"   Calculation: ${normalized_eps:.2f} × {fair_pe:.1f} = ${multiple_value:.2f}")
    
    # 3. DCF
    fcf_result = valuator.normalize_metric(example_company['annual_fcf'], 'fcf')
    normalized_fcf, _ = fcf_result
    fcf_stability = valuator.calculate_fcf_stability(example_company['annual_fcf'])
    
    dcf_value = valuator.conservative_dcf(
        normalized_fcf,
        example_company['shares_outstanding'],
        fcf_stability
    )
    
    print(f"\n3. Discounted Cash Flow (DCF)")
    print(f"   Normalized FCF: ${normalized_fcf:,.0f}")
    print(f"   FCF per share: ${normalized_fcf/example_company['shares_outstanding']:.2f}")
    print(f"   FCF Stability (CV): {fcf_stability:.2%}")
    if dcf_value:
        print(f"   DCF Value: ${dcf_value:.2f}")
    else:
        print(f"   DCF Value: Not calculated (FCF too volatile)")
    
    # Final intrinsic value
    values = [v for v in [epv, multiple_value, dcf_value] if v is not None]
    intrinsic_value = min(values)
    
    print("\n" + "=" * 70)
    print("FINAL VALUATION")
    print("=" * 70)
    print(f"\nIntrinsic Value = min(EPV, Multiple, DCF)")
    dcf_str = f"${dcf_value:.2f}" if dcf_value else "N/A"
    print(f"Intrinsic Value = min(${epv:.2f}, ${multiple_value:.2f}, {dcf_str})")
    print(f"\n→ INTRINSIC VALUE: ${intrinsic_value:.2f}")
    
    # Margin of safety
    current_price = example_company['current_price']
    margin_of_safety = (intrinsic_value - current_price) / intrinsic_value
    
    print("\n" + "=" * 70)
    print("MARGIN OF SAFETY")
    print("=" * 70)
    print(f"\nCurrent Price: ${current_price:.2f}")
    print(f"Intrinsic Value: ${intrinsic_value:.2f}")
    print(f"\nMargin of Safety = (IV - Price) / IV")
    print(f"Margin of Safety = (${intrinsic_value:.2f} - ${current_price:.2f}) / ${intrinsic_value:.2f}")
    print(f"\n→ MARGIN OF SAFETY: {margin_of_safety:.1%}")
    
    # Interpretation
    print("\n" + "=" * 70)
    print("INVESTMENT INTERPRETATION")
    print("=" * 70)
    
    if margin_of_safety > 0.30:
        interpretation = "STRONG VALUE"
        recommendation = "Significant margin of safety. Worth detailed research."
    elif margin_of_safety > 0.20:
        interpretation = "MODERATE VALUE"
        recommendation = "Decent margin of safety. Consider for portfolio."
    elif margin_of_safety > 0.10:
        interpretation = "SLIGHT VALUE"
        recommendation = "Small margin of safety. Watch for price drops."
    elif margin_of_safety > 0:
        interpretation = "MINIMAL VALUE"
        recommendation = "Very small margin of safety. Wait for better entry."
    else:
        interpretation = "OVERVALUED"
        recommendation = "Price exceeds intrinsic value. Avoid."
    
    print(f"\nRating: {interpretation}")
    print(f"Recommendation: {recommendation}")
    
    print("\n" + "=" * 70)
    print()


if __name__ == "__main__":
    demo_manual_valuation()
