"""
Data fetching module for stock prices and fundamentals
Uses yfinance for free, reliable data
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import random
from typing import Dict, List, Optional, Tuple
import json
import os
import requests


class StockDataFetcher:
    """Fetches and caches stock price and fundamental data"""
    
    def __init__(self, cache_dir: str = "data"):
        self.cache_dir = cache_dir
        self.universes_dir = os.path.join(cache_dir, "universes")
        os.makedirs(cache_dir, exist_ok=True)
        os.makedirs(self.universes_dir, exist_ok=True)
    
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
            response = requests.get(href, headers=headers)
            tables = pd.read_html(response.text)
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
            return float(hist['Close'].iloc[-1])
        except: return None
        
    def get_financial_data(self, ticker: str) -> Optional[Dict]:
        cache_filename = f"{ticker}_finance.json"
        cached_data = self.load_cache(cache_filename, max_age_hours=24)
        if cached_data is not None: return cached_data
        
        time.sleep(random.uniform(0.5, 1.5))
        
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            if not info or 'symbol' not in info: raise ValueError("Empty Info")
            
            income_stmt = stock.financials
            balance_sheet = stock.balance_sheet
            cashflow = stock.cashflow
            
            data = {
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
                
                'annual_eps': [], 'annual_fcf': [], 'annual_revenue': [],
                'annual_net_income': [], 'annual_operating_income': [],
                
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
                    ni = income_stmt.loc['Net Income', y] if 'Net Income' in income_stmt.index else None
                    rev = income_stmt.loc['Total Revenue', y] if 'Total Revenue' in income_stmt.index else None
                    op = income_stmt.loc['Operating Income', y] if 'Operating Income' in income_stmt.index else None
                    
                    if pd.notna(ni) and data['shares_outstanding']:
                        data['annual_eps'].append({'year': y_str, 'eps': float(ni)/data['shares_outstanding']})
                    if pd.notna(rev): data['annual_revenue'].append({'year': y_str, 'revenue': float(rev)})
                    if pd.notna(op): data['annual_operating_income'].append({'year': y_str, 'operating_income': float(op)})
                
                if data['annual_operating_income']: data['operating_income'] = data['annual_operating_income'][0]['operating_income']
                if 'Interest Expense' in income_stmt.index: 
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

            if balance_sheet is not None and not balance_sheet.empty:
                latest = balance_sheet.columns[0]
                if 'Total Debt' in balance_sheet.index:
                    d = balance_sheet.loc['Total Debt', latest]
                    if pd.notna(d): data['total_debt'] = float(d)
                elif 'Long Term Debt' in balance_sheet.index:
                    d = balance_sheet.loc['Long Term Debt', latest]
                    if pd.notna(d): data['total_debt'] = float(d)
                
                if 'Stockholders Equity' in balance_sheet.index:
                    e = balance_sheet.loc['Stockholders Equity', latest]
                    if pd.notna(e): data['total_equity'] = float(e)
                if 'Cash And Cash Equivalents' in balance_sheet.index:
                    c = balance_sheet.loc['Cash And Cash Equivalents', latest]
                    if pd.notna(c): data['cash'] = float(c)

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
                    'shares_py': sh_py if sh_py else data['piotroski']['shares_cy'],
                    'retained_earnings_cy': re_cy,
                    'total_liabilities_cy': tl_cy
                })

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
