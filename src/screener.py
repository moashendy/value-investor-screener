"""
Stock screening and ranking module
Filters, ranks, and presents value opportunities
"""

import pandas as pd
from typing import List, Dict
from datetime import datetime
import os

from valuations import ValuationResult


class ValueScreener:
    """
    Screens and ranks stocks based on margin of safety
    Tracks changes in price vs intrinsic value
    """
    
    def __init__(self, output_dir: str = "outputs"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def rank_stocks(self, valuations: List[ValuationResult]) -> pd.DataFrame:
        valid_valuations = [v for v in valuations if v.is_valid()]
        
        if not valid_valuations:
            return pd.DataFrame()
        
        records = []
        for val in valid_valuations:
            records.append({
                'Ticker': val.ticker,
                'Company': val.company_name,
                'Sector': val.sector,
                'Current Price': val.current_price,
                'Intrinsic Value': val.intrinsic_value,
                'Margin of Safety': val.margin_of_safety,
                'MoS %': f"{val.margin_of_safety * 100:.1f}%",
                'MoS Band': val.get_mos_band(),
                'Piotroski F-Score': val.f_score if val.f_score is not None else 'N/A',
                'Altman Z-Score': f"{val.altman_z_score:.2f}" if val.altman_z_score is not None else 'N/A',
                'WACC': f"{val.wacc * 100:.1f}%" if val.wacc is not None else 'N/A',
                'ROIC': f"{val.roic * 100:.1f}%" if val.roic is not None else 'N/A',
                'EV/FCF Yield': f"{val.ev_fcf_yield * 100:.1f}%" if val.ev_fcf_yield is not None else 'N/A',
                'Normalized EPS': val.normalized_eps,
                'EPV Value': val.epv_value,
                'Multiple Value': val.multiple_value,
                'DCF Value': val.dcf_value if val.dcf_value else 'N/A',
                'Interest Coverage': f"{val.interest_coverage:.1f}x" if val.interest_coverage else 'N/A',
                'Debt/Equity': f"{val.debt_to_equity:.2f}" if val.debt_to_equity else 'N/A',
                'Years of Data': val.years_of_data
            })
        
        df = pd.DataFrame(records)
        df = df.sort_values('Margin of Safety', ascending=False)
        return df
    
    def create_summary_tables(self, us_valuations: List[ValuationResult], ca_valuations: List[ValuationResult]) -> Dict[str, pd.DataFrame]:
        us_df = self.rank_stocks(us_valuations)
        ca_df = self.rank_stocks(ca_valuations)
        
        tables = {
            'us_stocks': us_df,
            'canadian_stocks': ca_df
        }
        
        if not us_df.empty: tables['us_opportunities'] = us_df[us_df['Margin of Safety'] > 0.20].copy()
        else: tables['us_opportunities'] = pd.DataFrame()
        
        if not ca_df.empty: tables['ca_opportunities'] = ca_df[ca_df['Margin of Safety'] > 0.20].copy()
        else: tables['ca_opportunities'] = pd.DataFrame()
        
        all_valid = us_valuations + ca_valuations
        all_valid = [v for v in all_valid if v.is_valid()]
        
        if all_valid:
            sector_data = {}
            for val in all_valid:
                sector = val.sector
                if sector not in sector_data: sector_data[sector] = {'count': 0, 'avg_mos': [], 'opportunities': 0}
                sector_data[sector]['count'] += 1
                sector_data[sector]['avg_mos'].append(val.margin_of_safety)
                if val.margin_of_safety > 0.20: sector_data[sector]['opportunities'] += 1
            
            sector_records = []
            for sector, data in sector_data.items():
                sector_records.append({
                    'Sector': sector,
                    'Stocks Analyzed': data['count'],
                    'Avg Margin of Safety': f"{(sum(data['avg_mos']) / len(data['avg_mos']) * 100):.1f}%",
                    'Opportunities (>20% MoS)': data['opportunities']
                })
            tables['sector_summary'] = pd.DataFrame(sector_records).sort_values('Opportunities (>20% MoS)', ascending=False)
        else:
            tables['sector_summary'] = pd.DataFrame()
        
        return tables
    
    def create_excluded_report(self, valuations: List[ValuationResult]) -> pd.DataFrame:
        excluded = [v for v in valuations if not v.is_valid()]
        if not excluded: return pd.DataFrame()
        
        records = []
        for val in excluded:
            records.append({
                'Ticker': val.ticker,
                'Company': val.company_name,
                'Sector': val.sector,
                'Reasons Excluded': '; '.join(val.reasons_excluded),
                'Current Price': val.current_price,
                'F-Score': val.f_score if val.f_score is not None else 'N/A',
                'Altman Z-Score': f"{val.altman_z_score:.2f}" if val.altman_z_score is not None else 'N/A',
                'Normalized EPS': val.normalized_eps if val.normalized_eps else 'N/A'
            })
        
        return pd.DataFrame(records)
    
    def generate_stock_explanation(self, val: ValuationResult) -> str:
        if not val.is_valid():
            return f"{val.ticker}: Excluded - {', '.join(val.reasons_excluded)}"
        
        epv_str = f"${val.epv_value:.2f}" if val.epv_value is not None else "N/A"
        multiple_str = f"${val.multiple_value:.2f}" if val.multiple_value is not None else "N/A"
        eps_str = f"${val.normalized_eps:.2f}" if val.normalized_eps is not None else "N/A"
        ic_str = f"{val.interest_coverage:.1f}x" if val.interest_coverage is not None else "N/A (No interest exp)"
        de_str = f"{val.debt_to_equity:.2f}" if val.debt_to_equity is not None else "N/A (No debt)"
        
        de_str = f"{val.debt_to_equity:.2f}" if val.debt_to_equity is not None else "N/A (No debt)"
        
        f_score_str = f"{val.f_score}/9" if val.f_score is not None else "N/A"
        altman_str = f"{val.altman_z_score:.2f}" if val.altman_z_score is not None else "N/A"
        wacc_str = f"{val.wacc * 100:.1f}%" if val.wacc is not None else "N/A"
        roic_str = f"{val.roic * 100:.1f}%" if val.roic is not None else "N/A"
        ev_fcf_str = f"{val.ev_fcf_yield * 100:.1f}%" if val.ev_fcf_yield is not None else "N/A"

        explanation = f"""
{val.ticker} - {val.company_name}
{'=' * 60}

Current Price: ${val.current_price:.2f}
Intrinsic Value: ${val.intrinsic_value:.2f}
Margin of Safety: {val.margin_of_safety * 100:.1f}% ({val.get_mos_band()})

MODERN QUANT METRICS:
- Piotroski F-Score: {f_score_str} (Financial health score out of 9)
- Altman Z-Score: {altman_str} (Bankruptcy risk. >2.99 is Safe)
- ROIC: {roic_str} (Capital efficiency, >10% is good)
- EV/FCF Yield: {ev_fcf_str} (Enterprise value to cash flow, >5% is good)
- True WACC: {wacc_str} (Dynamic market cost of capital used in DCF)

GRAHAM VALUATION METHODS:
- Earnings Power Value: {epv_str}
  (Based on {val.years_of_data} years of normalized EPS: {eps_str})
  
- Conservative Multiple: {multiple_str}
  (Using conservative P/E ratio)
"""
        
        if val.dcf_value:
            explanation += f"- DCF Value: ${val.dcf_value:.2f}\n  (Free cash flow is sufficiently stable)\n"
        else:
            explanation += "- DCF Value: Not calculated (FCF too volatile or unavailable)\n"
        
        explanation += f"""
INTRINSIC VALUE = ${val.intrinsic_value:.2f}
(Minimum of all methods - most conservative estimate)

QUALITY METRICS:
- Interest Coverage: {ic_str} (minimum 3.0x required)
- Debt/Equity: {de_str} (maximum 2.0 required)

"""
        
        if val.margin_of_safety > 0.30: interpretation = "STRONG VALUE: Significant margin of safety. Worth detailed research."
        elif val.margin_of_safety > 0.20: interpretation = "MODERATE VALUE: Decent margin of safety. Consider for portfolio."
        elif val.margin_of_safety > 0.10: interpretation = "SLIGHT VALUE: Small margin of safety. Watch for price drops."
        elif val.margin_of_safety > 0: interpretation = "MINIMAL VALUE: Very small margin of safety. Wait for better entry."
        else: interpretation = "OVERVALUED: Price exceeds intrinsic value. Avoid."
        
        explanation += f"INTERPRETATION: {interpretation}\n"
        
        return explanation
    
    def save_results(self, tables: Dict[str, pd.DataFrame], us_valuations: List[ValuationResult], ca_valuations: List[ValuationResult], timestamp: str = None):
        if timestamp is None: timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        for name, df in tables.items():
            if not df.empty:
                filepath = os.path.join(self.output_dir, f"{name}_{timestamp}.csv")
                df.to_csv(filepath, index=False)
                print(f"Saved: {filepath}")
        
        all_valuations = us_valuations + ca_valuations
        excluded_df = self.create_excluded_report(all_valuations)
        if not excluded_df.empty:
            filepath = os.path.join(self.output_dir, f"excluded_stocks_{timestamp}.csv")
            excluded_df.to_csv(filepath, index=False)
            print(f"Saved: {filepath}")
        
        report_lines = [
            "VALUE INVESTING STOCK RANKING REPORT WITH MODERN QUANTS",
            "=" * 70,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "SUMMARY",
            "-" * 70
        ]
        
        if not tables['us_stocks'].empty:
            us_count = len(tables['us_stocks'])
            us_opps = len(tables['us_opportunities'])
            report_lines.append(f"US Stocks: {us_count} analyzed, {us_opps} opportunities (>20% MoS)")
        
        if not tables['canadian_stocks'].empty:
            ca_count = len(tables['canadian_stocks'])
            ca_opps = len(tables['ca_opportunities'])
            report_lines.append(f"Canadian Stocks: {ca_count} analyzed, {ca_opps} opportunities (>20% MoS)")
        
        report_lines.extend(["", "TOP 10 OPPORTUNITIES (US STOCKS)", "-" * 70])
        if not tables['us_opportunities'].empty:
            for _, row in tables['us_opportunities'].head(10).iterrows():
                report_lines.append(f"{row['Ticker']:6s} | MoS: {row['MoS %']:>8s} | F-Score: {str(row['Piotroski F-Score'])+'/9':>3s} | {row['Company'][:30]}")
        else: report_lines.append("No opportunities found.")
        
        report_lines.extend(["", "TOP 10 OPPORTUNITIES (CANADIAN STOCKS)", "-" * 70])
        if not tables['ca_opportunities'].empty:
            for _, row in tables['ca_opportunities'].head(10).iterrows():
                report_lines.append(f"{row['Ticker']:8s} | MoS: {row['MoS %']:>8s} | F-Score: {str(row['Piotroski F-Score'])+'/9':>3s} | {row['Company'][:30]}")
        else: report_lines.append("No opportunities found.")
        
        all_valid = [v for v in all_valuations if v.is_valid()]
        all_valid.sort(key=lambda v: v.margin_of_safety, reverse=True)
        if all_valid:
            report_lines.extend(["", "", "DETAILED ANALYSIS - TOP 5 OPPORTUNITIES", "=" * 70])
            for val in all_valid[:5]: report_lines.append(self.generate_stock_explanation(val))
        
        report_filepath = os.path.join(self.output_dir, f"value_report_{timestamp}.txt")
        with open(report_filepath, 'w') as f: f.write('\n'.join(report_lines))
        print(f"Saved: {report_filepath}")
        return report_filepath
