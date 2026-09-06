"""Point-in-time portfolio backtester for value-screen snapshots.

The live screener only represents today's information. This module intentionally
accepts externally prepared historical snapshots so that a backtest cannot
silently reconstruct old signals with data that was published later.
"""

from __future__ import annotations

import argparse
import json
import math
import os
from dataclasses import asdict, dataclass
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd


SIGNAL_COLUMNS = {
    "signal_date",
    "ticker",
    "current_price",
    "intrinsic_value",
    "eligible",
    "fundamentals_available_date",
    "universe_member",
}
PRICE_COLUMNS = {"date", "ticker", "adjusted_close"}


class BacktestIntegrityError(ValueError):
    """Raised when an input could introduce look-ahead or survivorship bias."""


@dataclass(frozen=True)
class BacktestConfig:
    margin_of_safety: float = 0.20
    max_positions: int = 20
    transaction_cost_bps: float = 10.0
    benchmark_ticker: Optional[str] = None

    def __post_init__(self) -> None:
        if not 0 <= self.margin_of_safety < 1:
            raise ValueError("margin_of_safety must be between 0 and 1")
        if self.max_positions < 1:
            raise ValueError("max_positions must be at least 1")
        if self.transaction_cost_bps < 0:
            raise ValueError("transaction_cost_bps cannot be negative")


@dataclass
class BacktestResult:
    summary: Dict[str, object]
    periods: pd.DataFrame
    holdings: pd.DataFrame


def _parse_boolean(series: pd.Series, name: str) -> pd.Series:
    mapping = {
        True: True,
        False: False,
        1: True,
        0: False,
        "1": True,
        "0": False,
        "true": True,
        "false": False,
        "yes": True,
        "no": False,
    }
    parsed = series.map(lambda value: mapping.get(value if isinstance(value, (bool, int)) else str(value).strip().lower()))
    if parsed.isna().any():
        bad = series[parsed.isna()].astype(str).unique()[:5]
        raise BacktestIntegrityError(f"{name} contains invalid boolean values: {', '.join(bad)}")
    return parsed.astype(bool)


def prepare_signals(signals: pd.DataFrame) -> pd.DataFrame:
    missing = SIGNAL_COLUMNS - set(signals.columns)
    if missing:
        raise BacktestIntegrityError(f"signal data is missing columns: {', '.join(sorted(missing))}")

    frame = signals.copy()
    frame["signal_date"] = pd.to_datetime(frame["signal_date"], errors="coerce").dt.normalize()
    frame["fundamentals_available_date"] = pd.to_datetime(
        frame["fundamentals_available_date"], errors="coerce"
    ).dt.normalize()
    if frame["signal_date"].isna().any():
        raise BacktestIntegrityError("signal dates must be valid")

    frame["ticker"] = frame["ticker"].astype(str).str.strip().str.upper()
    if (frame["ticker"] == "").any():
        raise BacktestIntegrityError("signal data contains an empty ticker")
    if frame.duplicated(["signal_date", "ticker"]).any():
        raise BacktestIntegrityError("signal data contains duplicate ticker/date rows")

    frame["eligible"] = _parse_boolean(frame["eligible"], "eligible")
    frame["universe_member"] = _parse_boolean(frame["universe_member"], "universe_member")
    for column in ("current_price", "intrinsic_value"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    candidates = frame["eligible"] & frame["universe_member"]
    if frame.loc[candidates, "fundamentals_available_date"].isna().any():
        raise BacktestIntegrityError("eligible members require valid fundamentals availability dates")
    future_fundamentals = candidates & (
        frame["fundamentals_available_date"] > frame["signal_date"]
    )
    if future_fundamentals.any():
        examples = frame.loc[future_fundamentals, ["signal_date", "ticker"]].head(5)
        labels = ", ".join(f"{row.ticker}@{row.signal_date.date()}" for row in examples.itertuples())
        raise BacktestIntegrityError(f"look-ahead detected: fundamentals were not public for {labels}")

    invalid_values = candidates & (
        ~np.isfinite(frame["current_price"])
        | ~np.isfinite(frame["intrinsic_value"])
        | (frame["current_price"] <= 0)
        | (frame["intrinsic_value"] <= 0)
    )
    if invalid_values.any():
        raise BacktestIntegrityError("eligible universe members require finite positive price and intrinsic value")

    if frame["signal_date"].nunique() < 2:
        raise BacktestIntegrityError("at least two signal dates are required")
    return frame.sort_values(["signal_date", "ticker"]).reset_index(drop=True)


def prepare_prices(prices: pd.DataFrame) -> pd.DataFrame:
    missing = PRICE_COLUMNS - set(prices.columns)
    if missing:
        raise BacktestIntegrityError(f"price data is missing columns: {', '.join(sorted(missing))}")

    frame = prices.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.normalize()
    frame["ticker"] = frame["ticker"].astype(str).str.strip().str.upper()
    frame["adjusted_close"] = pd.to_numeric(frame["adjusted_close"], errors="coerce")
    if frame[["date", "ticker", "adjusted_close"]].isna().any().any():
        raise BacktestIntegrityError("price rows require a valid date, ticker, and adjusted close")
    if (frame["ticker"] == "").any() or (frame["adjusted_close"] <= 0).any():
        raise BacktestIntegrityError("price tickers must be non-empty and adjusted closes positive")
    if frame.duplicated(["date", "ticker"]).any():
        raise BacktestIntegrityError("price data contains duplicate ticker/date rows")
    return frame.sort_values(["date", "ticker"]).reset_index(drop=True)


def _execution_dates(signal_dates: Iterable[pd.Timestamp], prices: pd.DataFrame) -> Dict[pd.Timestamp, pd.Timestamp]:
    trading_dates = prices["date"].drop_duplicates().sort_values().to_numpy()
    result: Dict[pd.Timestamp, pd.Timestamp] = {}
    for signal_date in signal_dates:
        later = trading_dates[trading_dates > np.datetime64(signal_date)]
        if not len(later):
            raise BacktestIntegrityError(f"no next-session prices after signal date {signal_date.date()}")
        result[signal_date] = pd.Timestamp(later[0])
    return result


def _weights(tickers: List[str]) -> Dict[str, float]:
    if not tickers:
        return {"CASH": 1.0}
    weight = 1.0 / len(tickers)
    return {ticker: weight for ticker in tickers}


def _turnover(previous: Dict[str, float], current: Dict[str, float]) -> float:
    names = set(previous) | set(current)
    return 0.5 * sum(abs(current.get(name, 0.0) - previous.get(name, 0.0)) for name in names)


def _price_lookup(prices: pd.DataFrame) -> Dict[Tuple[pd.Timestamp, str], float]:
    return {
        (row.date, row.ticker): float(row.adjusted_close)
        for row in prices.itertuples(index=False)
    }


def _performance_summary(
    returns: pd.Series,
    dates: pd.Series,
    start_date: pd.Timestamp,
) -> Dict[str, float]:
    if returns.empty:
        raise BacktestIntegrityError("the backtest produced no holding periods")
    equity = (1.0 + returns).cumprod()
    total_return = float(equity.iloc[-1] - 1.0)
    elapsed_days = int((dates.iloc[-1] - start_date).days)
    years = elapsed_days / 365.25
    cagr = float(equity.iloc[-1] ** (1.0 / years) - 1.0) if years > 0 and equity.iloc[-1] > 0 else -1.0
    periods_per_year = len(returns) / years if years > 0 else 1.0
    volatility = float(returns.std(ddof=1) * math.sqrt(periods_per_year)) if len(returns) > 1 else 0.0
    path = pd.concat([pd.Series([1.0]), equity.reset_index(drop=True)], ignore_index=True)
    drawdown = path / path.cummax() - 1.0
    return {
        "total_return": total_return,
        "cagr": cagr,
        "annualized_period_volatility": volatility,
        "max_drawdown_at_rebalances": float(drawdown.min()),
        "positive_period_rate": float((returns > 0).mean()),
    }


def run_backtest(
    signals: pd.DataFrame,
    prices: pd.DataFrame,
    config: Optional[BacktestConfig] = None,
) -> BacktestResult:
    config = config or BacktestConfig()
    signals = prepare_signals(signals)
    prices = prepare_prices(prices)
    signal_dates = list(signals["signal_date"].drop_duplicates().sort_values())
    execution_dates = _execution_dates(signal_dates, prices)
    lookup = _price_lookup(prices)

    period_rows: List[Dict[str, object]] = []
    holding_rows: List[Dict[str, object]] = []
    previous_weights = {"CASH": 1.0}
    cost_rate = config.transaction_cost_bps / 10_000.0

    for index, signal_date in enumerate(signal_dates[:-1]):
        exit_signal_date = signal_dates[index + 1]
        entry_date = execution_dates[signal_date]
        exit_date = execution_dates[exit_signal_date]
        snapshot = signals[signals["signal_date"] == signal_date].copy()
        snapshot["margin_of_safety"] = (
            snapshot["intrinsic_value"] - snapshot["current_price"]
        ) / snapshot["intrinsic_value"]
        selected = snapshot[
            snapshot["eligible"]
            & snapshot["universe_member"]
            & (snapshot["margin_of_safety"] >= config.margin_of_safety)
        ].sort_values(["margin_of_safety", "ticker"], ascending=[False, True]).head(config.max_positions)
        tickers = selected["ticker"].tolist()
        current_weights = _weights(tickers)
        turnover = _turnover(previous_weights, current_weights)

        gross_return = 0.0
        end_values: Dict[str, float] = {}
        missing_prices = []
        for row in selected.itertuples():
            entry_price = lookup.get((entry_date, row.ticker))
            exit_price = lookup.get((exit_date, row.ticker))
            if entry_price is None or exit_price is None:
                missing_prices.append(row.ticker)
                continue
            security_return = exit_price / entry_price - 1.0
            weight = current_weights[row.ticker]
            gross_return += weight * security_return
            end_values[row.ticker] = weight * (1.0 + security_return)
            holding_rows.append({
                "signal_date": signal_date,
                "entry_date": entry_date,
                "exit_date": exit_date,
                "ticker": row.ticker,
                "weight": weight,
                "signal_price": float(row.current_price),
                "intrinsic_value": float(row.intrinsic_value),
                "margin_of_safety": float(row.margin_of_safety),
                "entry_adjusted_close": entry_price,
                "exit_adjusted_close": exit_price,
                "security_return": security_return,
            })
        if missing_prices:
            raise BacktestIntegrityError(
                f"selected holdings lack entry/exit prices for {signal_date.date()}: "
                + ", ".join(sorted(missing_prices))
            )

        transaction_cost = turnover * cost_rate
        net_return = (1.0 + gross_return) * (1.0 - transaction_cost) - 1.0
        row: Dict[str, object] = {
            "signal_date": signal_date,
            "entry_date": entry_date,
            "exit_date": exit_date,
            "positions": len(tickers),
            "tickers": ";".join(tickers),
            "turnover": turnover,
            "transaction_cost": transaction_cost,
            "gross_return": gross_return,
            "net_return": net_return,
        }
        if config.benchmark_ticker:
            benchmark = config.benchmark_ticker.upper()
            benchmark_entry = lookup.get((entry_date, benchmark))
            benchmark_exit = lookup.get((exit_date, benchmark))
            if benchmark_entry is None or benchmark_exit is None:
                raise BacktestIntegrityError(
                    f"benchmark {benchmark} lacks a price on {entry_date.date()} or {exit_date.date()}"
                )
            row["benchmark_return"] = benchmark_exit / benchmark_entry - 1.0
        period_rows.append(row)
        gross_factor = 1.0 + gross_return
        previous_weights = (
            {ticker: value / gross_factor for ticker, value in end_values.items()}
            if end_values and gross_factor > 0
            else {"CASH": 1.0}
        )

    periods = pd.DataFrame(period_rows)
    holdings = pd.DataFrame(holding_rows)
    first_entry_date = periods.iloc[0]["entry_date"]
    performance = _performance_summary(periods["net_return"], periods["exit_date"], first_entry_date)
    summary: Dict[str, object] = {
        **performance,
        "periods": len(periods),
        "start_date": periods.iloc[0]["entry_date"].date().isoformat(),
        "end_date": periods.iloc[-1]["exit_date"].date().isoformat(),
        "average_positions": float(periods["positions"].mean()),
        "average_turnover": float(periods["turnover"].mean()),
        "config": asdict(config),
        "integrity_guards": [
            "fundamentals_available_date <= signal_date",
            "historical universe membership required",
            "execution uses the first trading session after each signal",
            "selected holdings require complete entry and exit prices",
            "adjusted prices required for corporate actions",
        ],
    }
    if config.benchmark_ticker:
        benchmark_performance = _performance_summary(
            periods["benchmark_return"], periods["exit_date"], first_entry_date
        )
        summary["benchmark"] = {"ticker": config.benchmark_ticker.upper(), **benchmark_performance}
        summary["cagr_vs_benchmark"] = performance["cagr"] - benchmark_performance["cagr"]
    return BacktestResult(summary=summary, periods=periods, holdings=holdings)


def save_result(result: BacktestResult, output_dir: str) -> None:
    os.makedirs(output_dir, exist_ok=True)
    result.periods.to_csv(os.path.join(output_dir, "periods.csv"), index=False)
    result.holdings.to_csv(os.path.join(output_dir, "holdings.csv"), index=False)
    with open(os.path.join(output_dir, "summary.json"), "w", encoding="utf-8") as handle:
        json.dump(result.summary, handle, indent=2, allow_nan=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a point-in-time value-screen backtest")
    parser.add_argument("--signals", required=True, help="CSV of point-in-time screen snapshots")
    parser.add_argument("--prices", required=True, help="CSV of adjusted historical prices")
    parser.add_argument("--output", default="outputs/backtest", help="Directory for backtest results")
    parser.add_argument("--margin-of-safety", type=float, default=0.20)
    parser.add_argument("--max-positions", type=int, default=20)
    parser.add_argument("--transaction-cost-bps", type=float, default=10.0)
    parser.add_argument("--benchmark", help="Optional benchmark ticker included in the prices CSV")
    args = parser.parse_args()
    config = BacktestConfig(
        margin_of_safety=args.margin_of_safety,
        max_positions=args.max_positions,
        transaction_cost_bps=args.transaction_cost_bps,
        benchmark_ticker=args.benchmark,
    )
    result = run_backtest(pd.read_csv(args.signals), pd.read_csv(args.prices), config)
    save_result(result, args.output)
    print(json.dumps(result.summary, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
