"""
Core valuation models based on Benjamin Graham's principles
All models are conservative by design
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ValuationResult:
    """Container for valuation results"""
    ticker: str
    company_name: str
    current_price: float
    
    # Normalized metrics
    normalized_eps: Optional[float]
    normalized_fcf: Optional[float]
    years_of_data: int
    
    # Individual valuations
    epv_value: Optional[float]
    multiple_value: Optional[float]
    dcf_value: Optional[float]
    
    # Final valuation
    intrinsic_value: Optional[float]
    margin_of_safety: Optional[float]
    
    # Quality metrics
    interest_coverage: Optional[float]
    debt_to_equity: Optional[float]
    
    # Modern Quant Metrics
    roic: Optional[float]
    ev_fcf_yield: Optional[float]
    f_score: Optional[int]
    
    # Advanced Risk & Valuation
    wacc: Optional[float]
    altman_z_score: Optional[float]
    
    # Metadata
    sector: str
    reasons_excluded: List[str]
    
    def is_valid(self) -> bool:
        """Check if valuation is valid and stock passes quality filters"""
        return (
            self.intrinsic_value is not None and 
            self.margin_of_safety is not None
        )
    
    def get_mos_band(self) -> str:
        """Get margin of safety band description"""
        if self.margin_of_safety is None:
            return "N/A"
        
        from config import MOS_BANDS
        for threshold, label in MOS_BANDS:
            if self.margin_of_safety >= threshold:
                return label
        return "Overvalued"


class GrahamValuator:
    """
    Implements Graham-style valuation methods
    Conservative, margin-of-safety focused approach
    """
    
    def __init__(self, 
                 discount_rate: float = 0.09,
                 max_growth: float = 0.03,
                 conservative_pe: float = 10,
                 min_interest_coverage: float = 3.0,
                 max_debt_to_equity: float = 2.0):
        
        self.discount_rate = discount_rate
        self.max_growth = max_growth
        self.conservative_pe = conservative_pe
        self.min_interest_coverage = min_interest_coverage
        self.max_debt_to_equity = max_debt_to_equity
    
    def normalize_metric(self, 
                        annual_data: List[Dict],
                        metric_key: str,
                        min_years: int = 3) -> Optional[Tuple[float, int]]:
        if not annual_data or len(annual_data) < min_years:
            return None
        
        values = []
        for year_data in annual_data:
            if metric_key in year_data and year_data[metric_key] is not None:
                values.append(float(year_data[metric_key]))
        
        if len(values) < min_years:
            return None
        
        values = values[:5]
        normalized = np.mean(values)
        return normalized, len(values)
    
    def calculate_interest_coverage(self, operating_income: Optional[float], interest_expense: Optional[float]) -> Optional[float]:
        if not operating_income or not interest_expense or interest_expense == 0: return None
        return operating_income / interest_expense
    
    def calculate_debt_to_equity(self, total_debt: Optional[float], total_equity: Optional[float]) -> Optional[float]:
        if not total_equity or total_equity <= 0: return None
        if not total_debt: return 0.0
        return total_debt / total_equity
        
    def calculate_roic(self, operating_income: Optional[float], tax_rate: float, 
                       total_debt: Optional[float], total_equity: Optional[float], 
                       cash: Optional[float]) -> Optional[float]:
        if not operating_income or not total_equity: return None
        nopat = operating_income * (1 - tax_rate)
        invested_capital = (total_debt or 0) + total_equity - (cash or 0)
        if invested_capital <= 0: return None
        return nopat / invested_capital

    def calculate_ev_fcf_yield(self, market_cap: Optional[float], total_debt: Optional[float], 
                               cash: Optional[float], normalized_fcf: Optional[float]) -> Optional[float]:
        if not market_cap or not normalized_fcf: return None
        ev = market_cap + (total_debt or 0) - (cash or 0)
        if ev <= 0: return None
        return normalized_fcf / ev
        
    def calculate_wacc(self, beta: float, risk_free_rate: float, interest_expense: Optional[float], 
                       total_debt: Optional[float], market_cap: Optional[float], tax_rate: float) -> float:
        equity_risk_premium = 0.05
        cost_of_equity = risk_free_rate + (beta * equity_risk_premium)
        cost_of_equity = max(0.05, min(0.20, cost_of_equity))
        
        if not market_cap or market_cap <= 0: return cost_of_equity
        
        total_debt = total_debt or 0
        total_capital = market_cap + total_debt
        weight_equity = market_cap / total_capital
        weight_debt = total_debt / total_capital
        
        if total_debt > 0 and interest_expense:
            cost_of_debt = min(0.15, interest_expense / total_debt)
        else:
            cost_of_debt = 0.05
            
        wacc = (weight_equity * cost_of_equity) + (weight_debt * cost_of_debt * (1 - tax_rate))
        return max(0.05, wacc)
        
    def calculate_altman_z_score(self, p: dict, sector: str, market_cap: Optional[float], ebit: Optional[float]) -> Optional[float]:
        if not p or 'Financial' in sector or 'Bank' in sector or 'Insurance' in sector:
            return None
            
        ta = p.get('total_assets_cy')
        tl = p.get('total_liabilities_cy')
        if not ta or ta <= 0 or not tl or tl <= 0: return None
        
        ca = p.get('current_assets_cy') or 0
        cl = p.get('current_liabilities_cy') or 0
        working_capital = ca - cl
        
        re = p.get('retained_earnings_cy') or 0
        sales = p.get('revenue_cy') or 0
        ebit = ebit or 0
        market_cap = market_cap or 0
        
        A = working_capital / ta
        B = re / ta
        C = ebit / ta
        D = market_cap / tl
        E = sales / ta
        
        return (1.2 * A) + (1.4 * B) + (3.3 * C) + (0.6 * D) + (1.0 * E)
        
    def calculate_piotroski_f_score(self, p: dict) -> Optional[int]:
        score = 0
        roa_cy = (p['net_income_cy'] / p['total_assets_cy']) if p.get('net_income_cy') and p.get('total_assets_cy') else None
        roa_py = (p['net_income_py'] / p['total_assets_py']) if p.get('net_income_py') and p.get('total_assets_py') else None
        cfo_cy = p.get('operating_cf_cy')
        
        if roa_cy and roa_cy > 0: score += 1
        if cfo_cy and cfo_cy > 0: score += 1
        if roa_cy and roa_py and roa_cy > roa_py: score += 1
        if cfo_cy and p.get('net_income_cy') and cfo_cy > p['net_income_cy']: score += 1
        
        if p.get('long_term_debt_cy') is not None and p.get('total_assets_cy') and p.get('long_term_debt_py') is not None and p.get('total_assets_py'):
            ltd_asset_cy = p['long_term_debt_cy'] / p['total_assets_cy']
            ltd_asset_py = p['long_term_debt_py'] / p['total_assets_py']
            if ltd_asset_cy < ltd_asset_py: score += 1
        elif p.get('long_term_debt_cy') is None and p.get('long_term_debt_py') is None: score += 1
            
        if p.get('current_assets_cy') and p.get('current_liabilities_cy') and p.get('current_assets_py') and p.get('current_liabilities_py'):
            if (p['current_assets_cy'] / p['current_liabilities_cy']) > (p['current_assets_py'] / p['current_liabilities_py']): score += 1
            
        if p.get('shares_cy') and p.get('shares_py'):
            if p['shares_cy'] <= p['shares_py']: score += 1
            
        if p.get('gross_profit_cy') and p.get('revenue_cy') and p.get('gross_profit_py') and p.get('revenue_py'):
            if (p['gross_profit_cy'] / p['revenue_cy']) > (p['gross_profit_py'] / p['revenue_py']): score += 1
            
        if p.get('revenue_cy') and p.get('total_assets_cy') and p.get('revenue_py') and p.get('total_assets_py'):
            if (p['revenue_cy'] / p['total_assets_cy']) > (p['revenue_py'] / p['total_assets_py']): score += 1
            
        return score
    
    def earnings_power_value(self, normalized_eps: float) -> float:
        return normalized_eps / self.discount_rate
    
    def conservative_multiple_valuation(self, normalized_eps: float, historical_pe: Optional[float], sector_pe: Optional[float]) -> float:
        fair_pe = self.conservative_pe
        if historical_pe and historical_pe > 0: fair_pe = min(fair_pe, historical_pe)
        if sector_pe and sector_pe > 0: fair_pe = min(fair_pe, sector_pe)
        return normalized_eps * fair_pe
    
    def conservative_dcf(self, normalized_fcf: float, shares_outstanding: float, fcf_stability: float, dynamic_wacc: float = None) -> Optional[float]:
        if fcf_stability > 0.3: return None
        
        rate = dynamic_wacc if dynamic_wacc else self.discount_rate
        if rate <= self.max_growth: rate = self.max_growth + 0.01
        
        years_growth = 5
        present_value = 0
        for year in range(1, years_growth + 1):
            future_fcf = normalized_fcf * ((1 + self.max_growth) ** year)
            present_value += future_fcf / ((1 + rate) ** year)
        
        terminal_fcf = normalized_fcf * ((1 + self.max_growth) ** (years_growth + 1))
        terminal_value = terminal_fcf / (rate - self.max_growth)
        terminal_pv = terminal_value / ((1 + rate) ** years_growth)
        
        return (present_value + terminal_pv) / shares_outstanding
    
    def calculate_fcf_stability(self, annual_fcf: List[Dict]) -> float:
        if not annual_fcf or len(annual_fcf) < 3: return float('inf')
        fcf_values = [year_data['fcf'] for year_data in annual_fcf[:5]]
        mean_fcf = np.mean(fcf_values)
        if mean_fcf <= 0: return float('inf')
        return np.std(fcf_values) / abs(mean_fcf)
    
    def valuate_stock(self, financial_data: Dict, sector_pe_medians: Dict[str, float]) -> ValuationResult:
        ticker = financial_data['ticker']
        reasons_excluded = []
        
        current_price = financial_data.get('current_price')
        if not current_price or current_price <= 0: reasons_excluded.append("No valid current price")
        
        eps_result = self.normalize_metric(financial_data.get('annual_eps', []), 'eps', min_years=3)
        if eps_result: normalized_eps, eps_years = eps_result
        else: normalized_eps, eps_years = None, 0; reasons_excluded.append("Insufficient EPS history")
        
        fcf_result = self.normalize_metric(financial_data.get('annual_fcf', []), 'fcf', min_years=3)
        normalized_fcf, fcf_years = fcf_result if fcf_result else (None, 0)
        if normalized_fcf is not None and normalized_fcf <= 0:
            reasons_excluded.append("Negative normalized FCF")
            normalized_fcf = None
        
        interest_coverage = self.calculate_interest_coverage(financial_data.get('operating_income'), financial_data.get('interest_expense'))
        debt_to_equity = self.calculate_debt_to_equity(financial_data.get('total_debt'), financial_data.get('total_equity'))
        
        if interest_coverage and interest_coverage < self.min_interest_coverage:
            reasons_excluded.append(f"Low interest coverage ({interest_coverage:.1f}x)")
        if debt_to_equity and debt_to_equity > self.max_debt_to_equity:
            reasons_excluded.append(f"High leverage (D/E={debt_to_equity:.1f})")
            
        roic = self.calculate_roic(
            financial_data.get('operating_income'), financial_data.get('tax_rate', 0.21),
            financial_data.get('total_debt'), financial_data.get('total_equity'), financial_data.get('cash')
        )
        ev_fcf_yield = self.calculate_ev_fcf_yield(
            financial_data.get('market_cap'), financial_data.get('total_debt'),
            financial_data.get('cash'), normalized_fcf
        )
        f_score = self.calculate_piotroski_f_score(financial_data.get('piotroski', {}))
        
        if f_score is not None and f_score < 5:
            reasons_excluded.append(f"F-Score too low ({f_score}/9)")
        
        wacc = self.calculate_wacc(
            financial_data.get('beta', 1.0),
            financial_data.get('risk_free_rate', 0.045),
            financial_data.get('interest_expense'),
            financial_data.get('total_debt'),
            financial_data.get('market_cap'),
            financial_data.get('tax_rate', 0.21)
        )
        
        altman_z = self.calculate_altman_z_score(
            financial_data.get('piotroski', {}),
            financial_data.get('sector', 'Unknown'),
            financial_data.get('market_cap'),
            financial_data.get('operating_income')
        )
        
        epv_value, multiple_value, dcf_value = None, None, None
        if normalized_eps and normalized_eps > 0:
            epv_value = self.earnings_power_value(normalized_eps)
            multiple_value = self.conservative_multiple_valuation(normalized_eps, financial_data.get('current_pe'), sector_pe_medians.get(financial_data.get('sector', 'Unknown')))
            
            if normalized_fcf and normalized_fcf > 0:
                shares = financial_data.get('shares_outstanding')
                if shares and shares > 0:
                    dcf_value = self.conservative_dcf(
                        normalized_fcf, shares, 
                        self.calculate_fcf_stability(financial_data.get('annual_fcf', [])),
                        dynamic_wacc=wacc
                    )
        
        values = [v for v in [epv_value, multiple_value, dcf_value] if v is not None]
        intrinsic_value = min(values) if values else None
        if intrinsic_value is None and not reasons_excluded: reasons_excluded.append("Cannot calculate intrinsic value")
        
        margin_of_safety = ((intrinsic_value - current_price) / intrinsic_value) if intrinsic_value and current_price else None
        
        return ValuationResult(
            ticker=ticker,
            company_name=financial_data.get('company_name', ticker),
            current_price=current_price or 0,
            normalized_eps=normalized_eps,
            normalized_fcf=normalized_fcf,
            years_of_data=max(eps_years, fcf_years),
            epv_value=epv_value,
            multiple_value=multiple_value,
            dcf_value=dcf_value,
            intrinsic_value=intrinsic_value,
            margin_of_safety=margin_of_safety,
            interest_coverage=interest_coverage,
            debt_to_equity=debt_to_equity,
            roic=roic,
            ev_fcf_yield=ev_fcf_yield,
            f_score=f_score,
            wacc=wacc,
            altman_z_score=altman_z,
            sector=financial_data.get('sector', 'Unknown'),
            reasons_excluded=reasons_excluded
        )
