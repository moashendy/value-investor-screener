"""
Core valuation models based on Benjamin Graham's principles
All models are conservative by design
"""

import math
import numbers
import numpy as np
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from config import EARNINGS_OUTLIER_MULTIPLE, MAX_FUNDAMENTAL_AGE_DAYS


def is_finite_number(value, *, positive: bool = False, non_negative: bool = False) -> bool:
    """Return True only for finite real numbers in the requested domain."""
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, numbers.Real):
        return False
    number = float(value)
    if not math.isfinite(number):
        return False
    if positive and number <= 0:
        return False
    if non_negative and number < 0:
        return False
    return True


class ReasonCode(str, Enum):
    INVALID_PRICE = "invalid_price"
    INSUFFICIENT_EPS = "insufficient_eps_history"
    INSUFFICIENT_FCF = "insufficient_fcf_history"
    NON_POSITIVE_FCF = "non_positive_normalized_fcf"
    MISSING_INTEREST_COVERAGE = "missing_interest_coverage"
    LOW_INTEREST_COVERAGE = "low_interest_coverage"
    MISSING_DEBT = "missing_total_debt"
    MISSING_EQUITY = "missing_total_equity"
    NON_POSITIVE_EQUITY = "non_positive_equity"
    HIGH_LEVERAGE = "high_leverage"
    INCOMPLETE_F_SCORE = "incomplete_f_score"
    LOW_F_SCORE = "low_f_score"
    INVALID_INTRINSIC_VALUE = "invalid_intrinsic_value"
    INVALID_MARGIN_OF_SAFETY = "invalid_margin_of_safety"
    FETCH_FAILED = "fetch_failed"
    EVALUATION_ERROR = "evaluation_error"
    INCOMPARABLE_HISTORY = "incomparable_history"
    STALE_FUNDAMENTALS = "stale_fundamentals"
    MISSING_PROVENANCE = "missing_provenance"
    UNSUPPORTED_SECTOR_MODEL = "unsupported_sector_model"
    MISSING_SECTOR_INPUTS = "missing_sector_model_inputs"
    INSUFFICIENT_FFO = "insufficient_ffo_history"
    LOW_FINANCIAL_CAPITAL = "low_financial_equity_to_assets"
    HIGH_REIT_LEVERAGE = "high_reit_debt_to_ebitda"


@dataclass
class ValuationResult:
    """Container for valuation results"""
    ticker: str
    company_name: str
    current_price: Optional[float]
    
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
    reason_codes: List[str] = field(default_factory=list)
    data_valid: bool = False
    valuation_available: bool = False
    eligible: bool = False
    data_as_of: Dict = field(default_factory=dict)
    source_identity: Dict = field(default_factory=dict)
    corporate_action_flags: List[str] = field(default_factory=list)
    earnings_quality_flags: List[str] = field(default_factory=list)
    valuation_policy: str = ""
    dcf_basis: str = ""
    sector_model: str = "generic"
    normalized_ffo: Optional[float] = None
    verification_required: str = ""
    
    def is_valid(self) -> bool:
        """Compatibility alias for explicit, finite ranking eligibility."""
        return (
            self.eligible
            and self.data_valid
            and self.valuation_available
            and is_finite_number(self.current_price, positive=True)
            and is_finite_number(self.intrinsic_value, positive=True)
            and is_finite_number(self.margin_of_safety)
        )
    
    def get_mos_band(self) -> str:
        """Get margin of safety band description"""
        if not is_finite_number(self.margin_of_safety):
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

    SECTOR_POLICIES = {
        'Energy': {'pe_cap': 8.0, 'discount_floor': 0.11, 'growth_cap': 0.0, 'max_fcf_cv': 0.20, 'normalization': 'lower_quartile'},
        'Basic Materials': {'pe_cap': 8.0, 'discount_floor': 0.11, 'growth_cap': 0.0, 'max_fcf_cv': 0.20, 'normalization': 'lower_quartile'},
        'Materials': {'pe_cap': 8.0, 'discount_floor': 0.11, 'growth_cap': 0.0, 'max_fcf_cv': 0.20, 'normalization': 'lower_quartile'},
        'Consumer Cyclical': {'pe_cap': 10.0, 'discount_floor': 0.10, 'growth_cap': 0.02, 'max_fcf_cv': 0.25},
        'Industrials': {'pe_cap': 10.0, 'discount_floor': 0.10, 'growth_cap': 0.02, 'max_fcf_cv': 0.25},
        'Communication Services': {'pe_cap': 10.0, 'discount_floor': 0.095, 'growth_cap': 0.02, 'max_fcf_cv': 0.25},
        'Technology': {'pe_cap': 10.0, 'discount_floor': 0.10, 'growth_cap': 0.025, 'max_fcf_cv': 0.25},
        'Healthcare': {'pe_cap': 10.0, 'discount_floor': 0.095, 'growth_cap': 0.02, 'max_fcf_cv': 0.25},
        'Utilities': {'pe_cap': 10.0, 'discount_floor': 0.09, 'growth_cap': 0.015, 'max_fcf_cv': 0.20},
        'Financial Services': {'pe_cap': 9.0, 'discount_floor': 0.11, 'growth_cap': 0.0, 'max_fcf_cv': 0.0, 'dcf_allowed': False},
        'Real Estate': {'pe_cap': 10.0, 'discount_floor': 0.10, 'growth_cap': 0.0, 'max_fcf_cv': 0.0, 'dcf_allowed': False},
    }
    
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
                        min_years: int = 3,
                        method: str = 'mean') -> Optional[Tuple[float, int]]:
        if not annual_data or len(annual_data) < min_years:
            return None
        
        values = []
        for year_data in annual_data:
            if year_data.get('comparable', True) is False or year_data.get('quality_excluded', False):
                continue
            if metric_key in year_data and year_data[metric_key] is not None:
                value = year_data[metric_key]
                if is_finite_number(value):
                    values.append(float(value))
        
        if len(values) < min_years:
            return None
        
        values = values[:5]
        if method == 'lower_quartile':
            normalized = np.percentile(values, 25)
        elif method == 'median':
            normalized = np.median(values)
        else:
            normalized = np.mean(values)
        return normalized, len(values)

    def remove_upside_outliers(self, annual_data: List[Dict], metric_key: str):
        """Exclude isolated positive spikes without hiding losses or down-cycles."""
        rows = [dict(row) for row in (annual_data or [])]
        comparable = [
            row for row in rows[:5]
            if row.get('comparable', True) is not False
            and is_finite_number(row.get(metric_key))
        ]
        positives = [float(row[metric_key]) for row in comparable if float(row[metric_key]) > 0]
        flags = []
        if len(comparable) >= 4 and len(positives) >= 3:
            median_positive = float(np.median(positives))
            if median_positive > 0:
                candidates = [
                    row for row in comparable
                    if not row.get('quality_excluded', False)
                    if float(row[metric_key]) > median_positive * EARNINGS_OUTLIER_MULTIPLE
                ]
                for candidate in candidates:
                    candidate['quality_excluded'] = True
                    flags.append(
                        f"{candidate.get('year', 'unknown period')}: {metric_key} upside spike "
                        f"{float(candidate[metric_key]):.2f} vs median {median_positive:.2f}"
                    )
        return rows, flags

    def sector_policy(self, sector: str) -> Dict:
        policy = {
            'pe_cap': self.conservative_pe,
            'discount_floor': self.discount_rate,
            'growth_cap': self.max_growth,
            'max_fcf_cv': 0.30,
            'dcf_allowed': True,
            'supported': True,
            'normalization': 'mean',
        }
        policy.update(self.SECTOR_POLICIES.get(sector, {}))
        policy['pe_cap'] = min(float(policy['pe_cap']), self.conservative_pe)
        policy['discount_floor'] = max(float(policy['discount_floor']), self.discount_rate)
        policy['growth_cap'] = min(float(policy['growth_cap']), self.max_growth)
        return policy

    @staticmethod
    def sector_model_type(sector: str, industry: str) -> str:
        industry = industry or ''
        if sector == 'Financial Services':
            if industry.startswith('Banks -'):
                return 'bank'
            if industry.startswith('Insurance -'):
                return 'insurance'
            return 'financial_other'
        if sector == 'Real Estate' and industry.startswith('REIT -'):
            return 'reit'
        return 'generic'

    @staticmethod
    def fundamentals_age_days(data_as_of: Dict, reference_date=None) -> Optional[int]:
        raw = (data_as_of or {}).get('balance_sheet')
        if not raw:
            return None
        try:
            point = datetime.fromisoformat(str(raw).replace('Z', '+00:00'))
            if point.tzinfo is None:
                point = point.replace(tzinfo=timezone.utc)
            if reference_date is None:
                reference = datetime.now(timezone.utc)
            else:
                reference = datetime.fromisoformat(str(reference_date).replace('Z', '+00:00'))
                if reference.tzinfo is None:
                    reference = reference.replace(tzinfo=timezone.utc)
            return (reference - point).days
        except (TypeError, ValueError):
            return None
    
    def calculate_interest_coverage(self, operating_income: Optional[float], interest_expense: Optional[float]) -> Optional[float]:
        if not is_finite_number(operating_income) or not is_finite_number(interest_expense, non_negative=True):
            return None
        if float(interest_expense) == 0:
            return float('inf') if float(operating_income) > 0 else None
        return float(operating_income) / float(interest_expense)
    
    def calculate_debt_to_equity(self, total_debt: Optional[float], total_equity: Optional[float]) -> Optional[float]:
        if not is_finite_number(total_equity, positive=True): return None
        if not is_finite_number(total_debt, non_negative=True): return None
        return float(total_debt) / float(total_equity)
        
    def calculate_roic(self, operating_income: Optional[float], tax_rate: float, 
                       total_debt: Optional[float], total_equity: Optional[float], 
                       cash: Optional[float]) -> Optional[float]:
        if not is_finite_number(operating_income) or not is_finite_number(total_equity, positive=True): return None
        if not is_finite_number(tax_rate): return None
        debt = float(total_debt) if is_finite_number(total_debt, non_negative=True) else 0.0
        cash_value = float(cash) if is_finite_number(cash, non_negative=True) else 0.0
        nopat = float(operating_income) * (1 - float(tax_rate))
        invested_capital = debt + float(total_equity) - cash_value
        if not is_finite_number(invested_capital, positive=True): return None
        return nopat / invested_capital

    def calculate_ev_fcf_yield(self, market_cap: Optional[float], total_debt: Optional[float], 
                               cash: Optional[float], normalized_fcf: Optional[float]) -> Optional[float]:
        if not is_finite_number(market_cap, positive=True) or not is_finite_number(normalized_fcf, positive=True): return None
        debt = float(total_debt) if is_finite_number(total_debt, non_negative=True) else 0.0
        cash_value = float(cash) if is_finite_number(cash, non_negative=True) else 0.0
        ev = float(market_cap) + debt - cash_value
        if not is_finite_number(ev, positive=True): return None
        return float(normalized_fcf) / ev
        
    def calculate_wacc(self, beta: float, risk_free_rate: float, interest_expense: Optional[float], 
                       total_debt: Optional[float], market_cap: Optional[float], tax_rate: float,
                       discount_floor: Optional[float] = None) -> float:
        beta = float(beta) if is_finite_number(beta) else 1.0
        risk_free_rate = float(risk_free_rate) if is_finite_number(risk_free_rate, non_negative=True) else 0.045
        tax_rate = float(tax_rate) if is_finite_number(tax_rate) else 0.21
        equity_risk_premium = 0.05
        cost_of_equity = risk_free_rate + (beta * equity_risk_premium)
        cost_of_equity = max(0.05, min(0.20, cost_of_equity))
        
        if not is_finite_number(market_cap, positive=True): return cost_of_equity
        
        total_debt = float(total_debt) if is_finite_number(total_debt, non_negative=True) else 0.0
        total_capital = market_cap + total_debt
        weight_equity = market_cap / total_capital
        weight_debt = total_debt / total_capital
        
        if total_debt > 0 and is_finite_number(interest_expense, non_negative=True):
            cost_of_debt = min(0.15, interest_expense / total_debt)
        else:
            cost_of_debt = 0.05
            
        wacc = (weight_equity * cost_of_equity) + (weight_debt * cost_of_debt * (1 - tax_rate))
        floor = self.discount_rate if discount_floor is None else max(self.discount_rate, discount_floor)
        return max(floor, wacc)
        
    def calculate_altman_z_score(self, p: dict, sector: str, market_cap: Optional[float], ebit: Optional[float]) -> Optional[float]:
        if not p or 'Financial' in sector or 'Bank' in sector or 'Insurance' in sector:
            return None
            
        ta = p.get('total_assets_cy')
        tl = p.get('total_liabilities_cy')
        if not is_finite_number(ta, positive=True) or not is_finite_number(tl, positive=True): return None
        required = ['current_assets_cy', 'current_liabilities_cy', 'retained_earnings_cy', 'revenue_cy']
        if any(not is_finite_number(p.get(key)) for key in required): return None
        if not is_finite_number(ebit) or not is_finite_number(market_cap, non_negative=True): return None
        
        ca = p.get('current_assets_cy')
        cl = p.get('current_liabilities_cy')
        working_capital = ca - cl
        
        re = p.get('retained_earnings_cy')
        sales = p.get('revenue_cy')
        
        A = working_capital / ta
        B = re / ta
        C = ebit / ta
        D = market_cap / tl
        E = sales / ta
        
        return (1.2 * A) + (1.4 * B) + (3.3 * C) + (0.6 * D) + (1.0 * E)
        
    def calculate_piotroski_f_score(self, p: dict) -> Optional[int]:
        required = (
            'net_income_cy', 'net_income_py', 'operating_cf_cy',
            'total_assets_cy', 'total_assets_py', 'long_term_debt_cy',
            'long_term_debt_py', 'current_assets_cy', 'current_assets_py',
            'current_liabilities_cy', 'current_liabilities_py', 'shares_cy',
            'shares_py', 'gross_profit_cy', 'gross_profit_py',
            'revenue_cy', 'revenue_py'
        )
        if not p or any(not is_finite_number(p.get(key)) for key in required):
            return None
        if p['total_assets_cy'] <= 0 or p['total_assets_py'] <= 0:
            return None
        if p['current_liabilities_cy'] <= 0 or p['current_liabilities_py'] <= 0:
            return None
        if p['revenue_cy'] <= 0 or p['revenue_py'] <= 0:
            return None
        score = 0
        roa_cy = p['net_income_cy'] / p['total_assets_cy']
        roa_py = p['net_income_py'] / p['total_assets_py']
        cfo_cy = p.get('operating_cf_cy')
        
        if roa_cy > 0: score += 1
        if cfo_cy > 0: score += 1
        if roa_cy > roa_py: score += 1
        if cfo_cy > p['net_income_cy']: score += 1
        
        ltd_asset_cy = p['long_term_debt_cy'] / p['total_assets_cy']
        ltd_asset_py = p['long_term_debt_py'] / p['total_assets_py']
        if ltd_asset_cy < ltd_asset_py: score += 1
            
        if (p['current_assets_cy'] / p['current_liabilities_cy']) > (p['current_assets_py'] / p['current_liabilities_py']): score += 1
            
        if p['shares_cy'] <= p['shares_py']: score += 1
            
        if (p['gross_profit_cy'] / p['revenue_cy']) > (p['gross_profit_py'] / p['revenue_py']): score += 1
            
        if (p['revenue_cy'] / p['total_assets_cy']) > (p['revenue_py'] / p['total_assets_py']): score += 1
            
        return score
    
    def earnings_power_value(self, normalized_eps: float) -> float:
        return normalized_eps / self.discount_rate
    
    def conservative_multiple_valuation(self, normalized_eps: float, historical_pe: Optional[float], sector_pe: Optional[float], pe_cap: Optional[float] = None) -> float:
        fair_pe = min(self.conservative_pe, pe_cap) if pe_cap else self.conservative_pe
        if historical_pe and historical_pe > 0: fair_pe = min(fair_pe, historical_pe)
        if sector_pe and sector_pe > 0: fair_pe = min(fair_pe, sector_pe)
        return normalized_eps * fair_pe
    
    def conservative_dcf(self, normalized_fcf: float, shares_outstanding: float, fcf_stability: float,
                         dynamic_wacc: float = None, min_discount_rate: Optional[float] = None,
                         growth_cap: Optional[float] = None, max_fcf_cv: float = 0.30) -> Optional[float]:
        if (
            not is_finite_number(normalized_fcf, positive=True)
            or not is_finite_number(shares_outstanding, positive=True)
            or not is_finite_number(fcf_stability, non_negative=True)
            or fcf_stability > max_fcf_cv
        ):
            return None
        
        rate = dynamic_wacc if dynamic_wacc else self.discount_rate
        if min_discount_rate is not None:
            rate = max(rate, min_discount_rate)
        growth = self.max_growth if growth_cap is None else min(self.max_growth, growth_cap)
        if rate <= growth: rate = growth + 0.01
        
        years_growth = 5
        present_value = 0
        for year in range(1, years_growth + 1):
            future_fcf = normalized_fcf * ((1 + growth) ** year)
            present_value += future_fcf / ((1 + rate) ** year)
        
        terminal_fcf = normalized_fcf * ((1 + growth) ** (years_growth + 1))
        terminal_value = terminal_fcf / (rate - growth)
        terminal_pv = terminal_value / ((1 + rate) ** years_growth)
        
        return (present_value + terminal_pv) / shares_outstanding
    
    def calculate_fcf_stability(self, annual_fcf: List[Dict]) -> float:
        if not annual_fcf or len(annual_fcf) < 3: return float('inf')
        fcf_values = [
            float(year_data['fcf']) for year_data in annual_fcf[:5]
            if is_finite_number(year_data.get('fcf'))
        ]
        if len(fcf_values) < 3: return float('inf')
        mean_fcf = np.mean(fcf_values)
        if not is_finite_number(mean_fcf, positive=True): return float('inf')
        return np.std(fcf_values) / abs(mean_fcf)
    
    def valuate_stock(self, financial_data: Dict, sector_pe_medians: Dict[str, float]) -> ValuationResult:
        ticker = financial_data['ticker']
        reasons_excluded = []
        reason_codes = []
        sector = financial_data.get('sector', 'Unknown')
        industry = financial_data.get('industry', 'Unknown')
        sector_model = self.sector_model_type(sector, industry)
        policy = self.sector_policy(sector)
        data_as_of = financial_data.get('data_as_of', {})
        source_identity = financial_data.get('source_identity', {})
        corporate_action_flags = list(financial_data.get('corporate_action_flags', []))
        earnings_quality_flags = list(financial_data.get('earnings_quality_flags', []))
        verification_required = ""
        if sector_model == 'bank':
            verification_required = (
                "Verify CET1 capital, asset quality, credit-loss reserves, and deposit funding "
                "in the latest regulatory and SEC filings"
            )
        elif sector_model == 'insurance':
            verification_required = (
                "Verify risk-based capital, reserve adequacy, underwriting results, and investment "
                "portfolio risk in the latest statutory and SEC filings"
            )
        elif sector_model == 'reit':
            verification_required = (
                "Replace the calculated FFO proxy with company-reported FFO/AFFO and verify recurring "
                "capital expenditure, occupancy, lease expiries, and debt maturities"
            )
        elif sector_model == 'financial_other':
            verification_required = (
                "Verify sector-specific balance-sheet, regulatory, and transaction-volume risks in "
                "the latest filings"
            )

        def exclude(code: ReasonCode, message: str):
            reason_codes.append(code.value)
            reasons_excluded.append(message)
        
        current_price = financial_data.get('current_price')
        if not is_finite_number(current_price, positive=True):
            exclude(ReasonCode.INVALID_PRICE, "Missing, non-finite, or non-positive current price")

        if financial_data.get('history_comparable') is False or corporate_action_flags:
            detail = corporate_action_flags[0] if corporate_action_flags else "corporate action detected"
            exclude(ReasonCode.INCOMPARABLE_HISTORY, f"Historical statements are not comparable ({detail})")

        fundamentals_age = self.fundamentals_age_days(
            data_as_of, financial_data.get('valuation_as_of')
        )
        if fundamentals_age is None or fundamentals_age < 0 or fundamentals_age > MAX_FUNDAMENTAL_AGE_DAYS:
            label = "missing" if fundamentals_age is None else f"{fundamentals_age} days old"
            exclude(ReasonCode.STALE_FUNDAMENTALS, f"Latest balance-sheet period is {label}")

        if (
            not source_identity.get('provider')
            or not source_identity.get('symbol')
            or not source_identity.get('identity_key')
            or not data_as_of.get('retrieved_at')
        ):
            exclude(ReasonCode.MISSING_PROVENANCE, "Provider, issuer identity key, symbol, or retrieval timestamp is missing")

        adjusted_eps, detected_outliers = self.remove_upside_outliers(
            financial_data.get('annual_eps', []), 'eps'
        )
        earnings_quality_flags.extend(detected_outliers)
        eps_result = self.normalize_metric(
            adjusted_eps, 'eps', min_years=3, method=policy['normalization']
        )
        if eps_result:
            normalized_eps, eps_years = eps_result
        else:
            normalized_eps, eps_years = None, 0
            if sector_model != 'reit':
                exclude(ReasonCode.INSUFFICIENT_EPS, "Insufficient finite EPS history")
        
        fcf_result = self.normalize_metric(
            financial_data.get('annual_fcf', []), 'fcf', min_years=3,
            method=policy['normalization'],
        )
        normalized_fcf, fcf_years = fcf_result if fcf_result else (None, 0)
        if fcf_result is None and sector_model == 'generic':
            exclude(ReasonCode.INSUFFICIENT_FCF, "Insufficient finite FCF history")
        if normalized_fcf is not None and normalized_fcf <= 0 and sector_model == 'generic':
            exclude(ReasonCode.NON_POSITIVE_FCF, "Non-positive normalized FCF")
            normalized_fcf = None

        ffo_result = self.normalize_metric(
            financial_data.get('annual_ffo', []), 'ffo', min_years=3,
            method='lower_quartile',
        )
        normalized_ffo, ffo_years = ffo_result if ffo_result else (None, 0)
        if sector_model == 'reit' and not is_finite_number(normalized_ffo, positive=True):
            exclude(ReasonCode.INSUFFICIENT_FFO, "REIT requires three years of positive FFO-proxy history")
        
        interest_coverage = self.calculate_interest_coverage(financial_data.get('operating_income'), financial_data.get('interest_expense'))
        debt_to_equity = self.calculate_debt_to_equity(financial_data.get('total_debt'), financial_data.get('total_equity'))
        
        if sector_model == 'generic' and interest_coverage is None:
            exclude(ReasonCode.MISSING_INTEREST_COVERAGE, "Interest coverage is missing or not meaningful")
        elif sector_model == 'generic' and interest_coverage < self.min_interest_coverage:
            exclude(ReasonCode.LOW_INTEREST_COVERAGE, f"Low interest coverage ({interest_coverage:.1f}x)")
        elif sector_model == 'reit' and interest_coverage is not None and interest_coverage < 2.0:
            exclude(ReasonCode.LOW_INTEREST_COVERAGE, f"REIT interest coverage is low ({interest_coverage:.1f}x)")

        total_debt = financial_data.get('total_debt')
        total_equity = financial_data.get('total_equity')
        if sector_model in ('generic', 'reit') and not is_finite_number(total_debt, non_negative=True):
            exclude(ReasonCode.MISSING_DEBT, "Total debt is missing or invalid")
        if not is_finite_number(total_equity):
            exclude(ReasonCode.MISSING_EQUITY, "Total equity is missing or invalid")
        elif float(total_equity) <= 0:
            exclude(ReasonCode.NON_POSITIVE_EQUITY, "Total equity is zero or negative")
        elif sector_model == 'generic' and debt_to_equity is not None and debt_to_equity > self.max_debt_to_equity:
            exclude(ReasonCode.HIGH_LEVERAGE, f"High leverage (D/E={debt_to_equity:.1f})")

        metrics = financial_data.get('financial_metrics', {})
        shares = financial_data.get('shares_outstanding')
        tangible_book = metrics.get('tangible_book_value')
        equity_to_assets = metrics.get('equity_to_assets')
        debt_to_ebitda = metrics.get('debt_to_ebitda')
        if sector_model in ('bank', 'insurance'):
            if not is_finite_number(tangible_book, positive=True) or not is_finite_number(shares, positive=True):
                exclude(ReasonCode.MISSING_SECTOR_INPUTS, "Financial model requires positive tangible book value and shares")
            if not is_finite_number(equity_to_assets, positive=True):
                exclude(ReasonCode.MISSING_SECTOR_INPUTS, "Financial model requires equity-to-assets data")
            elif equity_to_assets < 0.04:
                exclude(ReasonCode.LOW_FINANCIAL_CAPITAL, f"Common equity/assets is only {equity_to_assets:.1%}")
        if sector_model == 'reit':
            if not is_finite_number(shares, positive=True) or not is_finite_number(debt_to_ebitda, positive=True):
                exclude(ReasonCode.MISSING_SECTOR_INPUTS, "REIT model requires shares and positive debt/EBITDA")
            elif debt_to_ebitda > 7.0:
                exclude(ReasonCode.HIGH_REIT_LEVERAGE, f"REIT debt/EBITDA is {debt_to_ebitda:.1f}x")
            
        roic = self.calculate_roic(
            financial_data.get('operating_income'), financial_data.get('tax_rate', 0.21),
            financial_data.get('total_debt'), financial_data.get('total_equity'), financial_data.get('cash')
        )
        ev_fcf_yield = self.calculate_ev_fcf_yield(
            financial_data.get('market_cap'), financial_data.get('total_debt'),
            financial_data.get('cash'), normalized_fcf
        )
        f_score = self.calculate_piotroski_f_score(financial_data.get('piotroski', {}))
        
        if sector_model == 'generic' and f_score is None:
            exclude(ReasonCode.INCOMPLETE_F_SCORE, "Piotroski F-Score inputs are incomplete")
        elif sector_model == 'generic' and f_score < 5:
            exclude(ReasonCode.LOW_F_SCORE, f"F-Score too low ({f_score}/9)")
        
        wacc = self.calculate_wacc(
            financial_data.get('beta', 1.0),
            financial_data.get('risk_free_rate', 0.045),
            financial_data.get('interest_expense'),
            financial_data.get('total_debt'),
            financial_data.get('market_cap'),
            financial_data.get('tax_rate', 0.21),
            discount_floor=policy['discount_floor']
        )
        
        altman_z = self.calculate_altman_z_score(
            financial_data.get('piotroski', {}),
            sector,
            financial_data.get('market_cap'),
            financial_data.get('operating_income')
        )
        
        epv_value, multiple_value, dcf_value = None, None, None
        if sector_model in ('bank', 'insurance') and is_finite_number(normalized_eps, positive=True):
            if is_finite_number(tangible_book, positive=True) and is_finite_number(shares, positive=True):
                tangible_book_per_share = tangible_book / shares
                return_on_tangible_equity = normalized_eps / tangible_book_per_share
                justified_multiple = max(0.5, min(1.5, (return_on_tangible_equity - 0.02) / (0.12 - 0.02)))
                epv_value = tangible_book_per_share * justified_multiple
                multiple_value = normalized_eps * 8.0
        elif sector_model == 'reit':
            if is_finite_number(normalized_ffo, positive=True) and is_finite_number(shares, positive=True):
                affo_haircut = 0.80
                reit_multiple = 8.0 if industry in ('REIT - Office', 'REIT - Hotel & Motel') else 10.0
                multiple_value = (normalized_ffo * affo_haircut / shares) * reit_multiple
        elif is_finite_number(normalized_eps, positive=True):
            epv_value = self.earnings_power_value(normalized_eps)
            multiple_value = self.conservative_multiple_valuation(
                normalized_eps,
                financial_data.get('current_pe'),
                sector_pe_medians.get(sector),
                pe_cap=policy['pe_cap'],
            )
            
            if policy['dcf_allowed'] and is_finite_number(normalized_fcf, positive=True):
                if is_finite_number(shares, positive=True):
                    dcf_value = self.conservative_dcf(
                        normalized_fcf, shares, 
                        self.calculate_fcf_stability(financial_data.get('annual_fcf', [])),
                        dynamic_wacc=wacc,
                        min_discount_rate=policy['discount_floor'],
                        growth_cap=policy['growth_cap'],
                        max_fcf_cv=policy['max_fcf_cv'],
                    )
        
        values = [v for v in [epv_value, multiple_value, dcf_value] if is_finite_number(v, positive=True)]
        intrinsic_value = min(values) if values else None
        if intrinsic_value is None:
            exclude(ReasonCode.INVALID_INTRINSIC_VALUE, "Cannot calculate a finite positive intrinsic value")

        margin_of_safety = None
        if is_finite_number(intrinsic_value, positive=True) and is_finite_number(current_price, positive=True):
            candidate_mos = (float(intrinsic_value) - float(current_price)) / float(intrinsic_value)
            if is_finite_number(candidate_mos):
                margin_of_safety = candidate_mos
        if margin_of_safety is None:
            exclude(ReasonCode.INVALID_MARGIN_OF_SAFETY, "Cannot calculate a finite margin of safety")

        data_blockers = {
            ReasonCode.INVALID_PRICE.value, ReasonCode.INSUFFICIENT_EPS.value,
            ReasonCode.INSUFFICIENT_FCF.value, ReasonCode.MISSING_INTEREST_COVERAGE.value,
            ReasonCode.MISSING_DEBT.value, ReasonCode.MISSING_EQUITY.value,
            ReasonCode.NON_POSITIVE_EQUITY.value, ReasonCode.INCOMPLETE_F_SCORE.value,
            ReasonCode.INCOMPARABLE_HISTORY.value, ReasonCode.STALE_FUNDAMENTALS.value,
            ReasonCode.MISSING_PROVENANCE.value,
            ReasonCode.UNSUPPORTED_SECTOR_MODEL.value,
            ReasonCode.MISSING_SECTOR_INPUTS.value, ReasonCode.INSUFFICIENT_FFO.value,
            ReasonCode.LOW_FINANCIAL_CAPITAL.value, ReasonCode.HIGH_REIT_LEVERAGE.value,
        }
        data_valid = not any(code in data_blockers for code in reason_codes)
        valuation_available = (
            is_finite_number(intrinsic_value, positive=True)
            and is_finite_number(margin_of_safety)
        )
        eligible = data_valid and valuation_available and not reason_codes
        
        return ValuationResult(
            ticker=ticker,
            company_name=financial_data.get('company_name', ticker),
            current_price=float(current_price) if is_finite_number(current_price, positive=True) else None,
            normalized_eps=normalized_eps,
            normalized_fcf=normalized_fcf,
            years_of_data=max(eps_years, fcf_years, ffo_years),
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
            sector=sector,
            reasons_excluded=reasons_excluded,
            reason_codes=reason_codes,
            data_valid=data_valid,
            valuation_available=valuation_available,
            eligible=eligible,
            data_as_of=data_as_of,
            source_identity=source_identity,
            corporate_action_flags=corporate_action_flags,
            earnings_quality_flags=earnings_quality_flags,
            valuation_policy=(
                f"{sector_model}: PE cap {policy['pe_cap']:.1f}x, discount floor "
                f"{policy['discount_floor']:.1%}, growth cap {policy['growth_cap']:.1%}, "
                f"normalization {policy['normalization']}, "
                f"DCF {'enabled' if policy['dcf_allowed'] else 'disabled'}, "
                f"sector model enabled"
            ),
            dcf_basis=(
                "Nareit-style FFO proxy with 20% AFFO haircut" if sector_model == 'reit'
                else "Tangible-book/normalized-earnings cross-check; verify regulatory capital" if sector_model in ('bank', 'insurance')
                else "FCFE proxy (operating cash flow less capex); no net-debt subtraction"
            ),
            sector_model=sector_model,
            normalized_ffo=normalized_ffo,
            verification_required=verification_required,
        )
