"""Build filing-date-aware historical valuation signals from SEC Company Facts.

This module does not invent historical index membership or delisted prices. It
requires those two datasets as inputs, keyed by stable SEC CIK where possible.
Only facts filed on or before a signal date can enter that date's valuation.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np
import pandas as pd
import requests

from valuations import GrahamValuator
from backtest import prepare_prices


MEMBERSHIP_COLUMNS = {
    "signal_date", "ticker", "cik", "sector", "industry", "universe_member"
}


CONCEPTS = {
    "eps": ["EarningsPerShareDiluted", "EarningsPerShareBasicAndDiluted"],
    "operating_cf": ["NetCashProvidedByUsedInOperatingActivities"],
    "capex": [
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsForAdditionsToPropertyPlantAndEquipment",
    ],
    "net_income": ["NetIncomeLoss", "ProfitLoss"],
    "operating_income": ["OperatingIncomeLoss"],
    "interest_expense": [
        "InterestExpenseNonOperating", "InterestAndDebtExpense", "InterestExpense"
    ],
    "revenue": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues", "SalesRevenueNet",
    ],
    "gross_profit": ["GrossProfit"],
    "assets": ["Assets"],
    "liabilities": ["Liabilities"],
    "equity": [
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ],
    "current_assets": ["AssetsCurrent"],
    "current_liabilities": ["LiabilitiesCurrent"],
    "long_term_debt": [
        "LongTermDebtAndFinanceLeaseObligations",
        "LongTermDebtAndCapitalLeaseObligations",
        "LongTermDebt",
    ],
    "cash": [
        "CashAndCashEquivalentsAtCarryingValue",
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
    ],
    "shares": ["EntityCommonStockSharesOutstanding", "CommonStockSharesOutstanding"],
    "diluted_shares": ["WeightedAverageNumberOfDilutedSharesOutstanding"],
    "retained_earnings": ["RetainedEarningsAccumulatedDeficit"],
}

UNITS = {
    "eps": ("USD/shares",),
    "shares": ("shares",),
    "diluted_shares": ("shares",),
}


class HistoricalDataError(ValueError):
    """Raised when source data cannot support a point-in-time observation."""


@dataclass(frozen=True)
class FactObservation:
    value: float
    start: Optional[pd.Timestamp]
    end: pd.Timestamp
    filed: pd.Timestamp
    form: str
    accession: str


class SecCompanyFactsClient:
    """Small cached client that follows the SEC fair-access request ceiling."""

    def __init__(self, cache_dir: str, user_agent: Optional[str] = None, pause_seconds: float = 0.12):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.user_agent = user_agent or os.environ.get("SEC_USER_AGENT")
        self.pause_seconds = max(0.11, pause_seconds)

    @staticmethod
    def normalize_cik(cik) -> str:
        try:
            number = float(str(cik).strip())
            if not np.isfinite(number) or not number.is_integer() or number < 0:
                raise ValueError
            return f"{int(number):010d}"
        except (TypeError, ValueError):
            raise HistoricalDataError(f"invalid SEC CIK: {cik}")

    def get(self, cik, offline: bool = False) -> Dict:
        normalized = self.normalize_cik(cik)
        path = self.cache_dir / f"CIK{normalized}.json"
        if path.exists():
            with path.open("r", encoding="utf-8") as handle:
                return json.load(handle)
        if offline:
            raise HistoricalDataError(f"missing cached Company Facts for CIK {normalized}")
        if not self.user_agent:
            raise HistoricalDataError(
                "SEC_USER_AGENT is required for downloads; identify the application and a contact email"
            )
        response = requests.get(
            f"https://data.sec.gov/api/xbrl/companyfacts/CIK{normalized}.json",
            headers={"User-Agent": self.user_agent, "Accept-Encoding": "gzip, deflate"},
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        temporary = path.with_suffix(".tmp")
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle)
        temporary.replace(path)
        time.sleep(self.pause_seconds)
        return payload


def _boolean(value) -> bool:
    if isinstance(value, bool):
        return value
    label = str(value).strip().lower()
    if label in {"true", "1", "yes"}:
        return True
    if label in {"false", "0", "no"}:
        return False
    raise HistoricalDataError(f"invalid universe_member value: {value}")


def prepare_membership(frame: pd.DataFrame) -> pd.DataFrame:
    missing = MEMBERSHIP_COLUMNS - set(frame.columns)
    if missing:
        raise HistoricalDataError(f"membership data is missing columns: {', '.join(sorted(missing))}")
    result = frame.copy()
    result["signal_date"] = pd.to_datetime(result["signal_date"], errors="coerce").dt.normalize()
    if result["signal_date"].isna().any():
        raise HistoricalDataError("membership signal dates must be valid")
    result["ticker"] = result["ticker"].astype(str).str.strip().str.upper()
    result["sector"] = result["sector"].fillna("Unknown").astype(str).str.strip()
    result["industry"] = result["industry"].fillna("Unknown").astype(str).str.strip()
    if result["ticker"].isin({"", "NAN"}).any():
        raise HistoricalDataError("membership data contains an invalid ticker")
    result["cik"] = result["cik"].map(SecCompanyFactsClient.normalize_cik)
    result["universe_member"] = result["universe_member"].map(_boolean)
    if result.duplicated(["signal_date", "ticker"]).any():
        raise HistoricalDataError("membership data contains duplicate ticker/date rows")
    return result.sort_values(["signal_date", "ticker"]).reset_index(drop=True)


def _fact_units(payload: Dict, concept_names: Sequence[str]) -> List[Dict]:
    facts = payload.get("facts", {}).get("us-gaap", {})
    for concept in concept_names:
        fact = facts.get(concept)
        if not fact:
            continue
        units = fact.get("units", {})
        preferred = UNITS.get(next((key for key, value in CONCEPTS.items() if concept in value), ""), ("USD",))
        for unit in preferred:
            if units.get(unit):
                return units[unit]
        for values in units.values():
            if values:
                return values
    return []


def _observations(payload: Dict, concept_key: str, as_of, duration: bool) -> List[FactObservation]:
    cutoff = pd.Timestamp(as_of).normalize()
    rows: List[FactObservation] = []
    for raw in _fact_units(payload, CONCEPTS[concept_key]):
        try:
            filed = pd.Timestamp(raw["filed"]).normalize()
            end = pd.Timestamp(raw["end"]).normalize()
            value = float(raw["val"])
        except (KeyError, TypeError, ValueError):
            continue
        if filed > cutoff or end > cutoff or not np.isfinite(value):
            continue
        form = str(raw.get("form", ""))
        if form not in {"10-K", "10-K/A", "10-Q", "10-Q/A"}:
            continue
        start = pd.Timestamp(raw["start"]).normalize() if raw.get("start") else None
        if duration:
            if start is None or form not in {"10-K", "10-K/A"}:
                continue
            days = (end - start).days
            if days < 270 or days > 400:
                continue
        else:
            if start is not None:
                continue
        rows.append(FactObservation(value, start, end, filed, form, str(raw.get("accn", ""))))

    # Later filings can restate an older period. They are valid only after their
    # own filed date, so choose the latest version known at the cutoff.
    by_period: Dict[pd.Timestamp, FactObservation] = {}
    for row in rows:
        current = by_period.get(row.end)
        if current is None or (row.filed, row.accession) > (current.filed, current.accession):
            by_period[row.end] = row
    return sorted(by_period.values(), key=lambda row: row.end, reverse=True)


def annual_facts(payload: Dict, concept_key: str, as_of, limit: int = 5) -> List[FactObservation]:
    return _observations(payload, concept_key, as_of, duration=True)[:limit]


def instant_facts(payload: Dict, concept_key: str, as_of, limit: int = 2) -> List[FactObservation]:
    return _observations(payload, concept_key, as_of, duration=False)[:limit]


def annual_instant_facts(
    payload: Dict, concept_key: str, as_of, limit: int = 2
) -> List[FactObservation]:
    """Return year-end balance facts, excluding misleading quarter-to-quarter comparisons."""
    rows = _observations(payload, concept_key, as_of, duration=False)
    return [row for row in rows if row.form in {"10-K", "10-K/A"}][:limit]


def _value(rows: List[FactObservation], index: int = 0) -> Optional[float]:
    return rows[index].value if len(rows) > index else None


def _latest_price(prices: pd.DataFrame, ticker: str, signal_date: pd.Timestamp) -> Optional[float]:
    rows = prices[(prices["ticker"] == ticker) & (prices["date"] <= signal_date)]
    if rows.empty:
        return None
    value = float(rows.iloc[-1]["adjusted_close"])
    return value if np.isfinite(value) and value > 0 else None


def build_financial_data(payload: Dict, member, prices: pd.DataFrame) -> Dict:
    as_of = member.signal_date
    annual = {key: annual_facts(payload, key, as_of) for key in (
        "eps", "operating_cf", "capex", "net_income", "operating_income",
        "interest_expense", "revenue", "gross_profit", "diluted_shares"
    )}
    instant = {key: instant_facts(payload, key, as_of) for key in (
        "assets", "liabilities", "equity", "current_assets", "current_liabilities",
        "long_term_debt", "cash", "shares", "retained_earnings"
    )}
    annual_instant = {key: annual_instant_facts(payload, key, as_of) for key in (
        "assets", "liabilities", "current_assets", "current_liabilities",
        "long_term_debt", "retained_earnings"
    )}

    eps = [{"year": row.end.year, "eps": row.value} for row in annual["eps"]]
    cfo_by_end = {row.end: row for row in annual["operating_cf"]}
    capex_by_end = {row.end: row for row in annual["capex"]}
    fcf = [
        {"year": end.year, "fcf": cfo_by_end[end].value - abs(capex_by_end[end].value)}
        for end in sorted(set(cfo_by_end) & set(capex_by_end), reverse=True)
    ]
    balance_end = instant["assets"][0].end if instant["assets"] else None
    used = [rows[0] for rows in list(annual.values()) + list(instant.values()) if rows]
    available_date = max((row.filed for row in used), default=None)
    price = _latest_price(prices, member.ticker, as_of)
    shares = _value(instant["shares"]) or _value(annual["diluted_shares"])
    latest_eps = _value(annual["eps"])
    total_assets = _value(instant["assets"])
    total_equity = _value(instant["equity"])

    piotroski = {
        "net_income_cy": _value(annual["net_income"]),
        "net_income_py": _value(annual["net_income"], 1),
        "operating_cf_cy": _value(annual["operating_cf"]),
        "total_assets_cy": _value(annual_instant["assets"]),
        "total_assets_py": _value(annual_instant["assets"], 1),
        "long_term_debt_cy": _value(annual_instant["long_term_debt"]),
        "long_term_debt_py": _value(annual_instant["long_term_debt"], 1),
        "current_assets_cy": _value(annual_instant["current_assets"]),
        "current_assets_py": _value(annual_instant["current_assets"], 1),
        "current_liabilities_cy": _value(annual_instant["current_liabilities"]),
        "current_liabilities_py": _value(annual_instant["current_liabilities"], 1),
        "shares_cy": _value(annual["diluted_shares"]),
        "shares_py": _value(annual["diluted_shares"], 1),
        "gross_profit_cy": _value(annual["gross_profit"]),
        "gross_profit_py": _value(annual["gross_profit"], 1),
        "revenue_cy": _value(annual["revenue"]),
        "revenue_py": _value(annual["revenue"], 1),
        "retained_earnings_cy": _value(annual_instant["retained_earnings"]),
        "total_liabilities_cy": _value(annual_instant["liabilities"]),
    }
    return {
        "ticker": member.ticker,
        "company_name": payload.get("entityName", member.ticker),
        "sector": member.sector,
        "industry": member.industry,
        "current_price": price,
        "market_cap": price * shares if price and shares else None,
        "shares_outstanding": shares,
        "tax_rate": 0.21,
        "beta": 1.0,
        "risk_free_rate": 0.045,
        "annual_eps": eps,
        "annual_fcf": fcf,
        "annual_ffo": [],
        "total_debt": _value(instant["long_term_debt"]),
        "total_equity": total_equity,
        "cash": _value(instant["cash"]),
        "interest_expense": (
            abs(_value(annual["interest_expense"]))
            if _value(annual["interest_expense"]) is not None else None
        ),
        "operating_income": _value(annual["operating_income"]),
        "current_pe": price / latest_eps if price and latest_eps and latest_eps > 0 else None,
        "piotroski": piotroski,
        "history_comparable": True,
        "corporate_action_flags": [],
        "earnings_quality_flags": [],
        "valuation_as_of": as_of.date().isoformat(),
        "data_as_of": {
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "balance_sheet": balance_end.date().isoformat() if balance_end is not None else None,
            "fundamentals_available_date": available_date.date().isoformat() if available_date is not None else None,
        },
        "source_identity": {
            "provider": "SEC EDGAR Company Facts",
            "symbol": member.ticker,
            "identity_key": f"SEC:{member.cik}",
            "source_url": f"https://data.sec.gov/api/xbrl/companyfacts/CIK{member.cik}.json",
        },
        "financial_metrics": {
            "equity_to_assets": total_equity / total_assets if total_equity and total_assets else None,
        },
    }


def build_signals(
    membership: pd.DataFrame,
    prices: pd.DataFrame,
    client: SecCompanyFactsClient,
    offline: bool = False,
) -> pd.DataFrame:
    members = prepare_membership(membership)
    prices = prepare_prices(prices).sort_values(["ticker", "date"])

    valuator = GrahamValuator()
    payloads = {cik: client.get(cik, offline=offline) for cik in members.loc[members["universe_member"], "cik"].unique()}
    records = []
    for member in members.itertuples(index=False):
        if not member.universe_member:
            records.append({
                "signal_date": member.signal_date.date().isoformat(), "ticker": member.ticker,
                "current_price": None, "intrinsic_value": None, "eligible": False,
                "fundamentals_available_date": member.signal_date.date().isoformat(),
                "universe_member": False, "reason_codes": "not_historical_member",
                "data_valid": False, "valuation_available": False,
                "sector": member.sector, "industry": member.industry,
            })
            continue
        financial_data = build_financial_data(payloads[member.cik], member, prices)
        result = valuator.valuate_stock(financial_data, {})
        records.append({
            "signal_date": member.signal_date.date().isoformat(),
            "ticker": member.ticker,
            "current_price": result.current_price,
            "intrinsic_value": result.intrinsic_value,
            "eligible": result.eligible,
            "fundamentals_available_date": financial_data["data_as_of"].get("fundamentals_available_date"),
            "universe_member": True,
            "margin_of_safety": result.margin_of_safety,
            "reason_codes": ";".join(result.reason_codes),
            "data_valid": result.data_valid,
            "valuation_available": result.valuation_available,
            "sector": member.sector,
            "industry": member.industry,
            "fundamentals_period_end": financial_data["data_as_of"].get("balance_sheet"),
            "data_provider": "SEC EDGAR Company Facts",
            "issuer_identity": f"SEC:{member.cik}",
            "sector_model": result.sector_model,
        })
    return pd.DataFrame(records).sort_values(["signal_date", "ticker"]).reset_index(drop=True)


def summarize_coverage(signals: pd.DataFrame) -> Dict:
    """Describe usable valuation coverage without confusing it with stock quality."""
    members = signals[signals["universe_member"].map(_boolean)].copy()
    if members.empty:
        raise HistoricalDataError("no historical universe members were supplied")
    members["signal_date"] = pd.to_datetime(members["signal_date"])
    members["year"] = members["signal_date"].dt.year
    members["usable"] = (
        members["data_valid"].map(_boolean)
        & members["valuation_available"].map(_boolean)
    )

    def grouped(column: str) -> List[Dict]:
        rows = []
        for label, group in members.groupby(column, dropna=False):
            rows.append({
                column: str(label),
                "member_rows": int(len(group)),
                "usable_rows": int(group["usable"].sum()),
                "usable_coverage": float(group["usable"].mean()),
                "eligible_rows": int(group["eligible"].map(_boolean).sum()),
            })
        return rows

    reasons = (
        members.loc[~members["usable"], "reason_codes"]
        .fillna("").str.split(";").explode().str.strip()
    )
    reasons = reasons[reasons != ""].value_counts().to_dict()
    membership_sets = {
        date: set(group["ticker"])
        for date, group in members.groupby("signal_date")
    }
    membership_churn = []
    previous_date = None
    previous_set = None
    for date, tickers in sorted(membership_sets.items()):
        if previous_set is not None:
            membership_churn.append({
                "from_date": previous_date.date().isoformat(),
                "to_date": date.date().isoformat(),
                "additions": len(tickers - previous_set),
                "deletions": len(previous_set - tickers),
            })
        previous_date, previous_set = date, tickers
    warnings = []
    date_span = (members["signal_date"].max() - members["signal_date"].min()).days
    if date_span >= 365 and membership_churn and not any(
        row["additions"] or row["deletions"] for row in membership_churn
    ):
        warnings.append(
            "No membership changes appear in a multi-year sample; verify that today's survivors were not backfilled."
        )
    return {
        "member_rows": int(len(members)),
        "usable_rows": int(members["usable"].sum()),
        "usable_coverage": float(members["usable"].mean()),
        "eligible_rows": int(members["eligible"].map(_boolean).sum()),
        "by_year": grouped("year"),
        "by_sector": grouped("sector"),
        "membership_churn": membership_churn,
        "unusable_reason_counts": {str(key): int(value) for key, value in reasons.items()},
        "warnings": warnings,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build point-in-time SEC valuation signals")
    parser.add_argument("--membership", required=True, help="Historical constituent snapshots CSV")
    parser.add_argument("--prices", required=True, help="Adjusted prices including delisted securities")
    parser.add_argument("--companyfacts-cache", default="data/companyfacts")
    parser.add_argument("--output", required=True)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    signals = build_signals(
        pd.read_csv(args.membership),
        pd.read_csv(args.prices),
        SecCompanyFactsClient(args.companyfacts_cache),
        offline=args.offline,
    )
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    signals.to_csv(args.output, index=False)
    coverage_path = f"{args.output}.coverage.json"
    with open(coverage_path, "w", encoding="utf-8") as handle:
        json.dump(summarize_coverage(signals), handle, indent=2, allow_nan=False)
    print(f"Wrote {len(signals)} point-in-time signal rows to {args.output}")
    print(f"Wrote coverage audit to {coverage_path}")


if __name__ == "__main__":
    main()
