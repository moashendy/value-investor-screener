"""
Data fetching module for stock prices and fundamentals
Uses yfinance for free, reliable data
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
import time
import random
import math
from io import StringIO
from typing import Dict, List, Optional, Tuple
import json
import os
import requests
import re
import tempfile

from config import (
    FINANCIAL_DATA_SCHEMA_VERSION,
    UNUSUAL_ITEM_MATERIALITY,
)


class StockDataFetcher:
    """Fetches and caches stock price and fundamental data"""
    
    def __init__(self, cache_dir: str = "data"):
        self.cache_dir = cache_dir
        self.universes_dir = os.path.join(cache_dir, "universes")
        os.makedirs(cache_dir, exist_ok=True)
        os.makedirs(self.universes_dir, exist_ok=True)

    def start_isolated_provider_session(self) -> str:
        """Avoid stale Yahoo cookie/crumb state shared by unrelated runs."""
        session_dir = tempfile.mkdtemp(prefix="value-investor-yfinance-")
        yf.set_tz_cache_location(session_dir)
        return session_dir
    
    def get_sp500_tickers(self) -> List[str]:
        fallback_file = os.path.join(self.universes_dir, "sp500_fallback.json")
        default_fallback = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'BRK-B', 'LLY',
            'V', 'TSM', 'WMT', 'JPM', 'XOM', 'UNH', 'MA', 'JNJ', 'PG', 'HD',
            'COST', 'ABBV', 'NFLX', 'KO', 'MRK', 'BAC', 'PEP', 'CVX', 'ADBE',
            'CRM', 'TMO', 'CSCO', 'ACN', 'MCD', 'ABT', 'WFC', 'LIN', 'AMD',
            'AVGO', 'NKE', 'DIS', 'TXN', 'PM', 'ORCL', 'DHR', 'VZ', 'QCOM',
            'INTU', 'CMCSA', 'INTC', 'UPS', 'NEE'
        ]
        if not os.path.exists(fallback_file):
            with open(fallback_file, 'w') as f:
                json.dump(default_fallback, f, indent=2)
        try:
            import requests
            href = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(href, headers=headers, timeout=20)
            response.raise_for_status()
            tables = pd.read_html(StringIO(response.text))
            df = tables[0]
            tickers = df['Symbol'].tolist()
            tickers = [t.replace('.', '-') for t in tickers]
            return tickers
        except Exception as e:
            print(f"Could not fetch S&P 500 list from Wikipedia: {e}")
            print("Using fallback list of major S&P 500 stocks")
            with open(fallback_file, 'r') as f: return json.load(f)
            
    def get_canadian_tickers(self) -> List[str]:
        canadian_file = os.path.join(self.universes_dir, "tsx_major.json")
        default_canadian = [
            'RY.TO', 'TD.TO', 'BNS.TO', 'BMO.TO', 'CM.TO', 'ENB.TO', 'TRP.TO', 
            'CNQ.TO', 'SU.TO', 'IMO.TO', 'CNR.TO', 'CP.TO', 'BCE.TO', 'T.TO', 
            'SLF.TO', 'MFC.TO', 'SHOP.TO', 'BAM.TO', 'WCN.TO', 'QSR.TO', 
            'ABX.TO', 'NTR.TO', 'FNV.TO', 'MG.TO', 'WPM.TO'
        ]
        if not os.path.exists(canadian_file):
            with open(canadian_file, 'w') as f:
                json.dump(default_canadian, f, indent=2)
        with open(canadian_file, 'r') as f: return json.load(f)

    def load_sec_cik_map(self, max_age_days: int = 7) -> int:
        """Load SEC's ticker-to-CIK map once, avoiding one metadata call per stock."""
        cache_file = os.path.join(self.universes_dir, "sec_company_tickers.json")
        payload = None
        if os.path.exists(cache_file):
            age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(cache_file))
            if age <= timedelta(days=max_age_days):
                try:
                    with open(cache_file, 'r') as handle:
                        payload = json.load(handle)
                except Exception:
                    payload = None
        if payload is None:
            try:
                response = requests.get(
                    "https://www.sec.gov/files/company_tickers.json",
                    headers={"User-Agent": "value-investor research tool contact@example.com"},
                    timeout=30,
                )
                response.raise_for_status()
                payload = response.json()
                with open(cache_file, 'w') as handle:
                    json.dump(payload, handle)
            except Exception as exc:
                print(f"Could not refresh SEC issuer map: {str(exc)[:80]}")
                payload = {}

        self._sec_cik_by_ticker = {}
        for row in payload.values() if isinstance(payload, dict) else []:
            ticker = str(row.get('ticker', '')).replace('.', '-').upper()
            cik = row.get('cik_str')
            if ticker and cik is not None:
                self._sec_cik_by_ticker[ticker] = str(cik).lstrip('0') or '0'
        return len(self._sec_cik_by_ticker)

    def get_risk_free_rate(self) -> float:
        if hasattr(self, '_risk_free_rate') and self._risk_free_rate is not None:
            return self._risk_free_rate
        try:
            tnx = yf.Ticker('^TNX')
            rfr = float(tnx.history(period="1d")['Close'].iloc[-1]) / 100.0
            self._risk_free_rate = rfr
            return rfr
        except:
            self._risk_free_rate = 0.045
            return self._risk_free_rate

    def get_current_price(self, ticker: str) -> Optional[float]:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="5d")
            if hist.empty: return None
            price = float(hist['Close'].iloc[-1])
            if math.isfinite(price) and price > 0:
                if not hasattr(self, '_price_as_of'):
                    self._price_as_of = {}
                self._price_as_of[ticker] = pd.Timestamp(hist.index[-1]).isoformat()
            return price if math.isfinite(price) and price > 0 else None
        except: return None

    @staticmethod
    def _column_date(value) -> Optional[datetime]:
        """Normalize a statement column label to a naive UTC datetime."""
        try:
            parsed = pd.Timestamp(value)
            if pd.isna(parsed):
                return None
            if parsed.tzinfo is not None:
                parsed = parsed.tz_convert("UTC").tz_localize(None)
            return parsed.to_pydatetime()
        except Exception:
            return None

    @classmethod
    def _select_latest_statement(cls, annual: pd.DataFrame, quarterly: pd.DataFrame):
        """Return the statement whose newest reported period is most recent."""
        candidates = []
        for frequency, frame in (("annual", annual), ("quarterly", quarterly)):
            if frame is not None and not frame.empty and len(frame.columns):
                period = cls._column_date(frame.columns[0])
                if period is not None:
                    candidates.append((period, frequency, frame))
        if not candidates:
            return None, None, None
        period, frequency, frame = max(candidates, key=lambda item: item[0])
        return frame, period, frequency

    @staticmethod
    def _statement_value(frame: pd.DataFrame, column, *row_names):
        if frame is None or frame.empty or column is None:
            return None
        for row_name in row_names:
            if row_name in frame.index:
                value = frame.loc[row_name, column]
                if pd.notna(value):
                    return float(value)
        return None

    @classmethod
    def _ttm_value(cls, quarterly: pd.DataFrame, *row_names):
        if quarterly is None or quarterly.empty or len(quarterly.columns) < 4:
            return None
        values = [cls._statement_value(quarterly, col, *row_names) for col in quarterly.columns[:4]]
        if any(value is None for value in values):
            return None
        return float(sum(values))

    @staticmethod
    def _is_material_discontinued(value, continuing, total_income, revenue) -> bool:
        """Apply the same absolute-and-relative materiality gate everywhere."""
        if value is None or not np.isfinite(value) or value == 0:
            return False
        finite_income = [
            abs(float(candidate)) for candidate in (continuing, total_income)
            if candidate is not None and np.isfinite(candidate)
        ]
        income_base = max(finite_income + [1.0])
        income_material = abs(float(value)) / income_base >= 0.10
        revenue_material = (
            revenue is not None
            and np.isfinite(revenue)
            and revenue != 0
            and abs(float(value)) / abs(float(revenue)) >= 0.005
        )
        return income_material and (abs(float(value)) >= 50_000_000 or revenue_material)

    @classmethod
    def _detect_discontinued_operations(cls, frame: pd.DataFrame, frequency: str) -> List[str]:
        """Find recent, material discontinued operations that break comparability."""
        if frame is None or frame.empty:
            return []
        flags = []
        rows = ('Net Income Discontinuous Operations', 'Net Income From Discontinued Operations')
        limit = 8 if frequency == 'quarterly' else 3
        for row_name in rows:
            if row_name not in frame.index:
                continue
            for column in frame.columns[:limit]:
                value = cls._statement_value(frame, column, row_name)
                continuing = cls._statement_value(
                    frame, column,
                    'Net Income Continuous Operations',
                    'Net Income From Continuing Operation Net Minority Interest',
                )
                total_income = cls._statement_value(
                    frame, column,
                    'Net Income From Continuing And Discontinued Operation', 'Net Income'
                )
                revenue = cls._statement_value(frame, column, 'Total Revenue', 'Operating Revenue')
                if cls._is_material_discontinued(value, continuing, total_income, revenue):
                    period = cls._column_date(column)
                    label = period.date().isoformat() if period else str(column)
                    flags.append(
                        f"{label} {frequency}: material discontinued-operations income {value:,.0f}"
                    )
        return flags

    @staticmethod
    def _sec_cik_from_filings(filings) -> Optional[str]:
        """Extract the issuer CIK encoded at the end of Yahoo's EDGAR URL."""
        for filing in filings or []:
            match = re.search(r"_(\d+)(?:\?.*)?$", str(filing.get('edgarUrl', '')))
            if match:
                return match.group(1).lstrip('0') or '0'
        return None
        
    def get_financial_data(self, ticker: str) -> Optional[Dict]:
        cache_filename = f"{ticker}_finance.json"
        cached_data = self.load_cache(cache_filename, max_age_hours=24)
        if cached_data is not None:
            cached_price = cached_data.get('current_price')
            schema_current = cached_data.get('schema_version') == FINANCIAL_DATA_SCHEMA_VERSION
            price_valid = (
                isinstance(cached_price, (int, float))
                and not isinstance(cached_price, bool)
                and math.isfinite(float(cached_price))
                and cached_price > 0
            )
            if schema_current and price_valid:
                return cached_data
            reason = "outdated schema" if not schema_current else "invalid current price"
            print(f"Ignoring cached data for {ticker}: {reason}")
        
        time.sleep(random.uniform(0.5, 1.5))
        
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            if not info or 'symbol' not in info: raise ValueError("Empty Info")
            
            income_stmt = stock.financials
            balance_sheet = stock.balance_sheet
            cashflow = stock.cashflow
            quarterly_income = stock.quarterly_financials
            quarterly_balance = stock.quarterly_balance_sheet
            quarterly_cashflow = stock.quarterly_cashflow
            sec_cik = getattr(self, '_sec_cik_by_ticker', {}).get(ticker.upper())
            retrieved_at = datetime.now(timezone.utc).isoformat()
            latest_balance, balance_period, balance_frequency = self._select_latest_statement(
                balance_sheet, quarterly_balance
            )
            latest_income, income_period, income_frequency = self._select_latest_statement(
                income_stmt, quarterly_income
            )
            _, cashflow_period, cashflow_frequency = self._select_latest_statement(
                cashflow, quarterly_cashflow
            )
            
            data = {
                'schema_version': FINANCIAL_DATA_SCHEMA_VERSION,
                'ticker': ticker,
                'company_name': info.get('longName', ticker),
                'sector': info.get('sector', 'Unknown'),
                'industry': info.get('industry', 'Unknown'),
                'current_price': self.get_current_price(ticker),
                'market_cap': info.get('marketCap'),
                'shares_outstanding': info.get('sharesOutstanding'),
                'tax_rate': info.get('taxRate', 0.21),
                'beta': info.get('beta', 1.0),
                'risk_free_rate': self.get_risk_free_rate(),
                'dividend_rate': info.get('dividendRate'),
                'history_comparable': True,
                'corporate_action_flags': [],
                'earnings_quality_flags': [],
                'data_as_of': {
                    'retrieved_at': retrieved_at,
                    'price': getattr(self, '_price_as_of', {}).get(ticker, retrieved_at),
                    'balance_sheet': balance_period.date().isoformat() if balance_period else None,
                    'income_statement': income_period.date().isoformat() if income_period else None,
                    'cash_flow': cashflow_period.date().isoformat() if cashflow_period else None,
                    'balance_sheet_frequency': balance_frequency,
                    'income_statement_frequency': income_frequency,
                    'cash_flow_frequency': cashflow_frequency,
                },
                'source_identity': {
                    'provider': 'Yahoo Finance via yfinance',
                    'symbol': info.get('symbol', ticker),
                    'exchange': info.get('exchange'),
                    'quote_type': info.get('quoteType'),
                    'issuer_id': sec_cik or info.get('uuid') or f"{info.get('exchange', 'UNKNOWN')}:{info.get('symbol', ticker)}",
                    'issuer_id_kind': 'SEC CIK' if sec_cik else ('Yahoo UUID' if info.get('uuid') else 'exchange:symbol fallback'),
                    'identity_key': f"SEC-CIK:{sec_cik}" if sec_cik else f"{info.get('exchange', 'UNKNOWN')}:{info.get('symbol', ticker)}",
                    'source_url': f"https://finance.yahoo.com/quote/{ticker}",
                },
                
                'annual_eps': [], 'annual_fcf': [], 'annual_ffo': [], 'annual_revenue': [],
                'annual_net_income': [], 'annual_operating_income': [],
                'financial_metrics': {},
                
                'total_debt': None, 'total_equity': None, 'cash': None,
                'interest_expense': None, 'operating_income': None,
                'current_pe': info.get('trailingPE'), 'forward_pe': info.get('forwardPE'),
                
                'piotroski': {
                    'net_income_cy': None, 'net_income_py': None,
                    'operating_cf_cy': None,
                    'total_assets_cy': None, 'total_assets_py': None,
                    'long_term_debt_cy': None, 'long_term_debt_py': None,
                    'current_assets_cy': None, 'current_assets_py': None,
                    'current_liabilities_cy': None, 'current_liabilities_py': None,
                    'shares_cy': info.get('sharesOutstanding'), 'shares_py': None,
                    'gross_profit_cy': None, 'gross_profit_py': None,
                    'revenue_cy': None, 'revenue_py': None,
                }
            }

            for frame, frequency in ((income_stmt, 'annual'), (quarterly_income, 'quarterly')):
                for flag in self._detect_discontinued_operations(frame, frequency):
                    if flag not in data['corporate_action_flags']:
                        data['corporate_action_flags'].append(flag)
            if data['corporate_action_flags']:
                data['history_comparable'] = False
            
            def ext_fy(df, row_name):
                if df is not None and not df.empty and row_name in df.index:
                    vals = []
                    for y in df.columns[:2]:
                        v = df.loc[row_name, y]
                        vals.append(float(v) if pd.notna(v) else None)
                    if len(vals) == 1: vals.append(None)
                    return vals
                return [None, None]

            if income_stmt is not None and not income_stmt.empty:
                for y in income_stmt.columns:
                    y_str = str(y).split(" ")[0]
                    ni = self._statement_value(
                        income_stmt, y,
                        'Net Income Continuous Operations',
                        'Net Income From Continuing Operation Net Minority Interest',
                        'Net Income',
                    )
                    rev = income_stmt.loc['Total Revenue', y] if 'Total Revenue' in income_stmt.index else None
                    op = income_stmt.loc['Operating Income', y] if 'Operating Income' in income_stmt.index else None

                    diluted_shares = self._statement_value(
                        income_stmt, y, 'Diluted Average Shares', 'Basic Average Shares'
                    )
                    eps_shares = diluted_shares or data['shares_outstanding']
                    unusual = self._statement_value(
                        income_stmt, y,
                        'Total Unusual Items Excluding Goodwill',
                        'Special Income Charges',
                        'Other Non Operating Income Expenses',
                    )
                    discontinued = self._statement_value(
                        income_stmt, y,
                        'Net Income Discontinuous Operations',
                        'Net Income From Discontinued Operations',
                    )
                    total_income = self._statement_value(
                        income_stmt, y,
                        'Net Income From Continuing And Discontinued Operation', 'Net Income'
                    )
                    comparable = not self._is_material_discontinued(
                        discontinued, ni, total_income, float(rev) if pd.notna(rev) else None
                    )
                    quality_excluded = bool(
                        ni not in (None, 0)
                        and unusual is not None
                        and unusual > 0
                        and abs(unusual) / abs(ni) >= UNUSUAL_ITEM_MATERIALITY
                    )
                    if quality_excluded:
                        data['earnings_quality_flags'].append(
                            f"{y_str}: unusual items are {abs(unusual) / abs(ni):.0%} of continuing net income"
                        )

                    if ni is not None and eps_shares:
                        data['annual_eps'].append({
                            'year': y_str,
                            'eps': float(ni) / float(eps_shares),
                            'shares_basis': 'period_diluted' if diluted_shares else 'current_fallback',
                            'comparable': comparable,
                            'quality_excluded': quality_excluded,
                        })
                    if ni is not None:
                        data['annual_net_income'].append({'year': y_str, 'net_income': float(ni)})
                    if pd.notna(rev): data['annual_revenue'].append({'year': y_str, 'revenue': float(rev)})
                    if pd.notna(op): data['annual_operating_income'].append({'year': y_str, 'operating_income': float(op)})
                
                ttm_operating_income = self._ttm_value(quarterly_income, 'Operating Income')
                ttm_interest = self._ttm_value(quarterly_income, 'Interest Expense', 'Interest Expense Non Operating')
                if ttm_operating_income is not None:
                    data['operating_income'] = ttm_operating_income
                elif data['annual_operating_income']:
                    data['operating_income'] = data['annual_operating_income'][0]['operating_income']
                if ttm_interest is not None:
                    data['interest_expense'] = float(abs(ttm_interest))
                elif 'Interest Expense' in income_stmt.index:
                    ix = income_stmt.loc['Interest Expense', income_stmt.columns[0]]
                    if pd.notna(ix): data['interest_expense'] = float(abs(ix))
                
                ni_cy, ni_py = ext_fy(income_stmt, 'Net Income')
                rev_cy, rev_py = ext_fy(income_stmt, 'Total Revenue')
                gp_cy, gp_py = ext_fy(income_stmt, 'Gross Profit')
                data['piotroski']['net_income_cy'] = ni_cy
                data['piotroski']['net_income_py'] = ni_py
                data['piotroski']['revenue_cy'] = rev_cy
                data['piotroski']['revenue_py'] = rev_py
                data['piotroski']['gross_profit_cy'] = gp_cy
                data['piotroski']['gross_profit_py'] = gp_py

            if cashflow is not None and not cashflow.empty:
                for y in cashflow.columns:
                    y_str = str(y).split(" ")[0]
                    fcf = cashflow.loc['Free Cash Flow', y] if 'Free Cash Flow' in cashflow.index else None
                    if pd.notna(fcf): data['annual_fcf'].append({'year': y_str, 'fcf': float(fcf)})
                
                ocf_cy, _ = ext_fy(cashflow, 'Operating Cash Flow')
                data['piotroski']['operating_cf_cy'] = ocf_cy

            # Nareit-style FFO proxy: continuing common income plus D&A and
            # cash-flow-statement gains/losses on depreciable asset sales.
            if income_stmt is not None and not income_stmt.empty:
                for y in income_stmt.columns:
                    ni = self._statement_value(
                        income_stmt, y,
                        'Net Income Common Stockholders',
                        'Net Income From Continuing Operation Net Minority Interest',
                        'Net Income',
                    )
                    depreciation = self._statement_value(
                        cashflow, y,
                        'Depreciation Amortization Depletion',
                        'Depreciation And Amortization',
                    ) if cashflow is not None and y in cashflow.columns else None
                    sale_gain_loss = self._statement_value(
                        cashflow, y,
                        'Gain Loss On Sale Of Property Plant Equipment',
                        'Gain Loss On Sale Of PPE',
                        'Gain Loss On Sale Of Investment Property',
                    ) if cashflow is not None and y in cashflow.columns else None
                    if ni is not None and depreciation is not None:
                        ffo = ni + abs(depreciation) + (sale_gain_loss or 0.0)
                        data['annual_ffo'].append({
                            'year': str(y).split(' ')[0],
                            'ffo': float(ffo),
                            'basis': 'Nareit-style proxy; unconsolidated-JV adjustments unavailable',
                        })

            if latest_balance is not None and not latest_balance.empty:
                latest = latest_balance.columns[0]
                data['total_debt'] = self._statement_value(
                    latest_balance, latest, 'Total Debt', 'Long Term Debt And Capital Lease Obligation', 'Long Term Debt'
                )
                data['total_equity'] = self._statement_value(
                    latest_balance, latest, 'Stockholders Equity', 'Total Equity Gross Minority Interest'
                )
                data['cash'] = self._statement_value(
                    latest_balance, latest,
                    'Cash Cash Equivalents And Short Term Investments',
                    'Cash And Cash Equivalents',
                )
                latest_shares = self._statement_value(
                    latest_balance, latest, 'Ordinary Shares Number', 'Share Issued'
                )
                if latest_shares:
                    data['shares_outstanding'] = latest_shares
                total_assets = self._statement_value(latest_balance, latest, 'Total Assets')
                common_equity = self._statement_value(latest_balance, latest, 'Common Stock Equity', 'Stockholders Equity')
                tangible_book = self._statement_value(latest_balance, latest, 'Tangible Book Value', 'Net Tangible Assets')
                preferred_equity = self._statement_value(latest_balance, latest, 'Preferred Stock Equity', 'Preferred Stock')
                annual_column = income_stmt.columns[0] if income_stmt is not None and not income_stmt.empty else None
                normalized_ebitda = self._statement_value(income_stmt, annual_column, 'Normalized EBITDA', 'EBITDA')
                data['financial_metrics'] = {
                    'total_assets': total_assets,
                    'common_equity': common_equity,
                    'tangible_book_value': tangible_book,
                    'preferred_equity': preferred_equity or 0.0,
                    'equity_to_assets': (
                        common_equity / total_assets
                        if common_equity is not None and total_assets not in (None, 0)
                        else None
                    ),
                    'normalized_ebitda': normalized_ebitda,
                    'debt_to_ebitda': (
                        data['total_debt'] / normalized_ebitda
                        if data['total_debt'] is not None and normalized_ebitda not in (None, 0)
                        else None
                    ),
                }

            if balance_sheet is not None and not balance_sheet.empty:

                ta_cy, ta_py = ext_fy(balance_sheet, 'Total Assets')
                ca_cy, ca_py = ext_fy(balance_sheet, 'Current Assets')
                cl_cy, cl_py = ext_fy(balance_sheet, 'Current Liabilities')
                ltd_cy, ltd_py = ext_fy(balance_sheet, 'Long Term Debt')
                sh_cy, sh_py = ext_fy(balance_sheet, 'Ordinary Shares Number') 
                
                # Altman Z-Score components
                re_cy, _ = ext_fy(balance_sheet, 'Retained Earnings')
                tl_cy, _ = ext_fy(balance_sheet, 'Total Liabilities Net Minority Interest')
                if tl_cy is None: tl_cy, _ = ext_fy(balance_sheet, 'Total Liabilities')
                
                data['piotroski'].update({
                    'total_assets_cy': ta_cy, 'total_assets_py': ta_py,
                    'current_assets_cy': ca_cy, 'current_assets_py': ca_py,
                    'current_liabilities_cy': cl_cy, 'current_liabilities_py': cl_py,
                    'long_term_debt_cy': ltd_cy, 'long_term_debt_py': ltd_py,
                    'shares_py': sh_py,
                    'retained_earnings_cy': re_cy,
                    'total_liabilities_cy': tl_cy
                })

            # Do not turn a transient quote failure into a successful 24-hour
            # cache entry. Run-level integrity gates provide the final guard.
            price = data.get('current_price')
            if isinstance(price, (int, float)) and not isinstance(price, bool) and math.isfinite(float(price)) and price > 0:
                self.save_cache(data, cache_filename)
            return data
            
        except Exception as e:
            print(f"Error fetching financial data for {ticker}: {str(e)[:50]}")
            return None
            
    def get_historical_prices(self, ticker: str, years: int = 5) -> pd.DataFrame:
        try:
            stock = yf.Ticker(ticker)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=years*365)
            return stock.history(start=start_date, end=end_date)
        except Exception as e:
            return pd.DataFrame()
            
    def get_sector_pe_ratios(self, tickers: List[str]) -> Dict[str, float]:
        pes = {}
        for t in tickers:
            try:
                time.sleep(random.uniform(0.1, 0.4))
                stock = yf.Ticker(t)
                info = stock.info
                s, pe = info.get('sector'), info.get('trailingPE')
                if s and pe and pe > 0:
                    if s not in pes: pes[s] = []
                    pes[s].append(pe)
            except: pass
        return {s: np.median(p) for s, p in pes.items()}
        
    def save_cache(self, data: dict, filename: str):
        filepath = os.path.join(self.cache_dir, filename)
        with open(filepath, 'w') as f: json.dump(data, f, default=str, indent=2)
        
    def load_cache(self, filename: str, max_age_hours: int = None) -> Optional[dict]:
        filepath = os.path.join(self.cache_dir, filename)
        if os.path.exists(filepath):
            if max_age_hours:
                modified_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                if (datetime.now() - modified_time).total_seconds() > (max_age_hours * 3600): return None
            try:
                with open(filepath, 'r') as f: return json.load(f)
            except Exception: return None
        return None
