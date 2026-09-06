import os
import sys
import tempfile
import unittest

import pandas as pd


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from backtest import BacktestConfig, BacktestIntegrityError, run_backtest, save_result


def valid_signals():
    return pd.DataFrame([
        {"signal_date": "2020-01-01", "ticker": "AAA", "current_price": 70, "intrinsic_value": 100,
         "eligible": True, "fundamentals_available_date": "2019-12-20", "universe_member": True},
        {"signal_date": "2020-01-01", "ticker": "BBB", "current_price": 90, "intrinsic_value": 100,
         "eligible": True, "fundamentals_available_date": "2019-12-20", "universe_member": True},
        {"signal_date": "2021-01-01", "ticker": "AAA", "current_price": 80, "intrinsic_value": 100,
         "eligible": True, "fundamentals_available_date": "2020-12-20", "universe_member": True},
        {"signal_date": "2021-01-01", "ticker": "BBB", "current_price": 70, "intrinsic_value": 100,
         "eligible": True, "fundamentals_available_date": "2020-12-20", "universe_member": True},
        {"signal_date": "2022-01-01", "ticker": "AAA", "current_price": 90, "intrinsic_value": 100,
         "eligible": True, "fundamentals_available_date": "2021-12-20", "universe_member": True},
        {"signal_date": "2022-01-01", "ticker": "BBB", "current_price": 75, "intrinsic_value": 100,
         "eligible": True, "fundamentals_available_date": "2021-12-20", "universe_member": True},
    ])


def valid_prices():
    return pd.DataFrame([
        {"date": "2020-01-02", "ticker": "AAA", "adjusted_close": 100},
        {"date": "2020-01-02", "ticker": "BBB", "adjusted_close": 100},
        {"date": "2020-01-02", "ticker": "SPY", "adjusted_close": 100},
        {"date": "2021-01-04", "ticker": "AAA", "adjusted_close": 120},
        {"date": "2021-01-04", "ticker": "BBB", "adjusted_close": 90},
        {"date": "2021-01-04", "ticker": "SPY", "adjusted_close": 110},
        {"date": "2022-01-03", "ticker": "AAA", "adjusted_close": 130},
        {"date": "2022-01-03", "ticker": "BBB", "adjusted_close": 108},
        {"date": "2022-01-03", "ticker": "SPY", "adjusted_close": 121},
    ])


class BacktestTests(unittest.TestCase):
    def test_selects_only_qualifying_names_and_uses_next_session(self):
        result = run_backtest(
            valid_signals(), valid_prices(),
            BacktestConfig(max_positions=1, transaction_cost_bps=0, benchmark_ticker="SPY"),
        )
        self.assertEqual(result.periods["tickers"].tolist(), ["AAA", "BBB"])
        self.assertEqual(result.periods["positions"].tolist(), [1, 1])
        self.assertEqual(result.periods.iloc[0]["entry_date"], pd.Timestamp("2020-01-02"))
        self.assertAlmostEqual(result.periods.iloc[0]["net_return"], 0.20)
        self.assertAlmostEqual(result.periods.iloc[1]["net_return"], 0.20)
        self.assertAlmostEqual(result.summary["total_return"], 0.44)
        self.assertAlmostEqual(result.summary["cagr"], 0.20, places=3)
        self.assertIn("benchmark", result.summary)

    def test_transaction_cost_is_applied_to_turnover(self):
        result = run_backtest(
            valid_signals(), valid_prices(),
            BacktestConfig(max_positions=1, transaction_cost_bps=100),
        )
        self.assertAlmostEqual(result.periods.iloc[0]["turnover"], 1.0)
        self.assertAlmostEqual(result.periods.iloc[0]["transaction_cost"], 0.01)
        self.assertAlmostEqual(result.periods.iloc[0]["net_return"], 1.2 * 0.99 - 1)
        self.assertAlmostEqual(result.periods.iloc[1]["turnover"], 1.0)

    def test_future_fundamentals_are_rejected(self):
        signals = valid_signals()
        signals.loc[0, "fundamentals_available_date"] = "2020-01-03"
        with self.assertRaisesRegex(BacktestIntegrityError, "look-ahead detected"):
            run_backtest(signals, valid_prices())

    def test_missing_holding_exit_price_is_rejected(self):
        prices = valid_prices()
        prices = prices[~((prices["ticker"] == "AAA") & (prices["date"] == "2021-01-04"))]
        with self.assertRaisesRegex(BacktestIntegrityError, "lack entry/exit prices"):
            run_backtest(valid_signals(), prices, BacktestConfig(max_positions=1))

    def test_current_nonmember_cannot_enter_historical_portfolio(self):
        signals = valid_signals()
        signals.loc[(signals["signal_date"] == "2020-01-01") & (signals["ticker"] == "AAA"), "universe_member"] = False
        result = run_backtest(signals, valid_prices(), BacktestConfig(max_positions=1, transaction_cost_bps=0))
        self.assertEqual(result.periods.iloc[0]["positions"], 0)
        self.assertEqual(result.periods.iloc[0]["tickers"], "")
        self.assertEqual(result.periods.iloc[0]["net_return"], 0)

    def test_results_are_saved_as_auditable_files(self):
        result = run_backtest(valid_signals(), valid_prices(), BacktestConfig(transaction_cost_bps=0))
        with tempfile.TemporaryDirectory() as output_dir:
            save_result(result, output_dir)
            self.assertEqual(set(os.listdir(output_dir)), {"summary.json", "periods.csv", "holdings.csv"})


if __name__ == "__main__":
    unittest.main()
