import math
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import pandas as pd


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from screener import RunIntegrityError, ValueScreener
from data_fetcher import StockDataFetcher
from valuations import GrahamValuator, ReasonCode


def healthy_piotroski():
    return {
        "net_income_cy": 120.0,
        "net_income_py": 100.0,
        "operating_cf_cy": 150.0,
        "total_assets_cy": 1_000.0,
        "total_assets_py": 950.0,
        "long_term_debt_cy": 100.0,
        "long_term_debt_py": 120.0,
        "current_assets_cy": 500.0,
        "current_assets_py": 450.0,
        "current_liabilities_cy": 200.0,
        "current_liabilities_py": 220.0,
        "shares_cy": 100.0,
        "shares_py": 100.0,
        "gross_profit_cy": 400.0,
        "gross_profit_py": 350.0,
        "revenue_cy": 1_000.0,
        "revenue_py": 900.0,
        "retained_earnings_cy": 300.0,
        "total_liabilities_cy": 600.0,
    }


def financial_data(ticker="TEST", price=10.0, **overrides):
    now = datetime.now(timezone.utc)
    data = {
        "ticker": ticker,
        "company_name": "Test Company",
        "sector": "Industrials",
        "industry": "Specialty Industrial Machinery",
        "current_price": price,
        "market_cap": 1_000.0,
        "shares_outstanding": 100.0,
        "tax_rate": 0.21,
        "beta": 1.0,
        "risk_free_rate": 0.04,
        "annual_eps": [{"eps": 5.0}, {"eps": 5.0}, {"eps": 5.0}],
        "annual_fcf": [{"fcf": 100.0}, {"fcf": 100.0}, {"fcf": 100.0}],
        "total_debt": 100.0,
        "total_equity": 400.0,
        "cash": 50.0,
        "interest_expense": 10.0,
        "operating_income": 100.0,
        "current_pe": 8.0,
        "piotroski": healthy_piotroski(),
        "history_comparable": True,
        "corporate_action_flags": [],
        "earnings_quality_flags": [],
        "data_as_of": {
            "retrieved_at": now.isoformat(),
            "balance_sheet": now.date().isoformat(),
            "balance_sheet_frequency": "quarterly",
        },
        "source_identity": {
            "provider": "Test Provider",
            "symbol": ticker,
            "identity_key": f"TEST:{ticker}",
            "source_url": f"https://example.test/{ticker}",
        },
        "financial_metrics": {},
        "annual_ffo": [],
    }
    data.update(overrides)
    return data


def weak_piotroski():
    return {
        "net_income_cy": -100.0,
        "net_income_py": -50.0,
        "operating_cf_cy": -150.0,
        "total_assets_cy": 1_000.0,
        "total_assets_py": 900.0,
        "long_term_debt_cy": 200.0,
        "long_term_debt_py": 100.0,
        "current_assets_cy": 200.0,
        "current_assets_py": 300.0,
        "current_liabilities_cy": 200.0,
        "current_liabilities_py": 200.0,
        "shares_cy": 110.0,
        "shares_py": 100.0,
        "gross_profit_cy": 100.0,
        "gross_profit_py": 200.0,
        "revenue_cy": 1_000.0,
        "revenue_py": 900.0,
        "retained_earnings_cy": -100.0,
        "total_liabilities_cy": 700.0,
    }


class ValuationEligibilityTests(unittest.TestCase):
    def setUp(self):
        self.valuator = GrahamValuator()

    def value(self, **overrides):
        return self.valuator.valuate_stock(financial_data(**overrides), {})

    def test_healthy_company_is_eligible(self):
        result = self.value()
        self.assertTrue(result.data_valid)
        self.assertTrue(result.valuation_available)
        self.assertTrue(result.eligible)
        self.assertTrue(result.is_valid())
        self.assertEqual(result.reason_codes, [])

    def test_nan_price_is_never_rankable(self):
        result = self.value(price=float("nan"))
        self.assertFalse(result.is_valid())
        self.assertIsNone(result.current_price)
        self.assertIn(ReasonCode.INVALID_PRICE.value, result.reason_codes)
        self.assertIn(ReasonCode.INVALID_MARGIN_OF_SAFETY.value, result.reason_codes)

    def test_only_finite_positive_numeric_prices_are_rankable(self):
        invalid_prices = [
            None,
            float("nan"),
            float("inf"),
            float("-inf"),
            0.0,
            -1.0,
            "10.0",
            True,
        ]
        for price in invalid_prices:
            with self.subTest(price=price):
                result = self.value(price=price)
                self.assertFalse(result.is_valid())
                self.assertIsNone(result.current_price)
                self.assertIn(ReasonCode.INVALID_PRICE.value, result.reason_codes)

        self.assertTrue(self.value(price=10.0).is_valid())

    def test_low_interest_coverage_is_explicitly_ineligible(self):
        result = self.value(interest_expense=100.0)
        self.assertFalse(result.is_valid())
        self.assertIn(ReasonCode.LOW_INTEREST_COVERAGE.value, result.reason_codes)

    def test_high_leverage_is_explicitly_ineligible(self):
        result = self.value(total_debt=900.0)
        self.assertFalse(result.is_valid())
        self.assertIn(ReasonCode.HIGH_LEVERAGE.value, result.reason_codes)

    def test_zero_debt_is_valid_and_not_treated_as_missing(self):
        p = healthy_piotroski()
        p["long_term_debt_cy"] = 0.0
        result = self.value(total_debt=0.0, interest_expense=0.0, piotroski=p)
        self.assertTrue(result.is_valid())
        self.assertEqual(result.debt_to_equity, 0.0)
        self.assertTrue(math.isinf(result.interest_coverage))
        self.assertNotIn(ReasonCode.MISSING_DEBT.value, result.reason_codes)

    def test_negative_equity_stops_eligibility(self):
        result = self.value(total_equity=-10.0)
        self.assertFalse(result.is_valid())
        self.assertIsNone(result.debt_to_equity)
        self.assertIn(ReasonCode.NON_POSITIVE_EQUITY.value, result.reason_codes)

    def test_incomplete_f_score_is_not_scored_as_zero(self):
        result = self.value(piotroski={})
        self.assertFalse(result.is_valid())
        self.assertIsNone(result.f_score)
        self.assertIn(ReasonCode.INCOMPLETE_F_SCORE.value, result.reason_codes)
        self.assertNotIn(ReasonCode.LOW_F_SCORE.value, result.reason_codes)

    def test_complete_low_f_score_is_a_quality_failure(self):
        result = self.value(piotroski=weak_piotroski())
        self.assertEqual(result.f_score, 0)
        self.assertFalse(result.is_valid())
        self.assertIn(ReasonCode.LOW_F_SCORE.value, result.reason_codes)
        self.assertNotIn(ReasonCode.INCOMPLETE_F_SCORE.value, result.reason_codes)

    def test_corporate_action_makes_history_ineligible(self):
        result = self.value(
            history_comparable=False,
            corporate_action_flags=["2025: discontinued operations"],
        )
        self.assertFalse(result.is_valid())
        self.assertIn(ReasonCode.INCOMPARABLE_HISTORY.value, result.reason_codes)

    def test_upside_eps_spike_is_removed_from_normalization(self):
        result = self.value(annual_eps=[
            {"year": "2025", "eps": 30.0},
            {"year": "2024", "eps": 5.0},
            {"year": "2023", "eps": 5.0},
            {"year": "2022", "eps": 5.0},
        ])
        self.assertTrue(result.is_valid())
        self.assertEqual(result.normalized_eps, 5.0)
        self.assertTrue(any("upside spike" in flag for flag in result.earnings_quality_flags))

    def test_negative_eps_year_is_not_hidden_as_an_outlier(self):
        result = self.value(annual_eps=[
            {"year": "2025", "eps": -10.0},
            {"year": "2024", "eps": 5.0},
            {"year": "2023", "eps": 5.0},
            {"year": "2022", "eps": 5.0},
        ])
        self.assertEqual(result.normalized_eps, 1.25)
        self.assertFalse(any("2025" in flag for flag in result.earnings_quality_flags))

    def test_stale_fundamentals_stop_eligibility(self):
        result = self.value(data_as_of={
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "balance_sheet": "2000-01-01",
        })
        self.assertFalse(result.is_valid())
        self.assertIn(ReasonCode.STALE_FUNDAMENTALS.value, result.reason_codes)

    def test_missing_source_identity_stops_eligibility(self):
        result = self.value(source_identity={})
        self.assertFalse(result.is_valid())
        self.assertIn(ReasonCode.MISSING_PROVENANCE.value, result.reason_codes)

    def test_energy_policy_enforces_stricter_multiple_and_discount_floor(self):
        result = self.value(
            sector="Energy",
            current_pe=20.0,
            annual_eps=[{"eps": 2.0}, {"eps": 3.0}, {"eps": 8.0}, {"eps": 12.0}],
        )
        self.assertEqual(result.normalized_eps, 2.75)
        self.assertEqual(result.multiple_value, 22.0)
        self.assertGreaterEqual(result.wacc, 0.11)
        self.assertIn("PE cap 8.0x", result.valuation_policy)
        self.assertIn("normalization lower_quartile", result.valuation_policy)

    def test_other_financials_use_earnings_model_without_dcf(self):
        result = self.value(sector="Financial Services", industry="Financial Data & Stock Exchanges")
        self.assertIsNone(result.dcf_value)
        self.assertTrue(result.is_valid())
        self.assertEqual(result.sector_model, "financial_other")
        self.assertIn("sector-specific", result.verification_required)

    def test_bank_uses_tangible_book_and_earnings_cross_checks(self):
        result = self.value(
            sector="Financial Services", industry="Banks - Diversified",
            financial_metrics={
                "tangible_book_value": 500.0,
                "equity_to_assets": 0.08,
            },
        )
        self.assertTrue(result.is_valid())
        self.assertEqual(result.sector_model, "bank")
        self.assertEqual(result.multiple_value, 40.0)
        self.assertIsNotNone(result.epv_value)
        self.assertIn("CET1", result.verification_required)

    def test_reit_uses_ffo_proxy_and_leverage_gate(self):
        result = self.value(
            sector="Real Estate", industry="REIT - Industrial",
            annual_ffo=[{"ffo": 100.0}, {"ffo": 110.0}, {"ffo": 120.0}],
            financial_metrics={"debt_to_ebitda": 5.0},
        )
        self.assertTrue(result.is_valid())
        self.assertEqual(result.sector_model, "reit")
        self.assertEqual(result.normalized_ffo, 105.0)
        self.assertEqual(result.intrinsic_value, 8.4)
        self.assertIn("company-reported FFO/AFFO", result.verification_required)

    def test_reit_does_not_require_eps_when_ffo_is_complete(self):
        result = self.value(
            sector="Real Estate", industry="REIT - Industrial", annual_eps=[],
            annual_ffo=[{"ffo": 100.0}, {"ffo": 110.0}, {"ffo": 120.0}],
            financial_metrics={"debt_to_ebitda": 5.0},
        )
        self.assertTrue(result.is_valid())
        self.assertNotIn(ReasonCode.INSUFFICIENT_EPS.value, result.reason_codes)


class PublicationGateTests(unittest.TestCase):
    def setUp(self):
        self.valuator = GrahamValuator()

    def test_price_coverage_failure_aborts_before_any_file_is_written(self):
        good_us = self.valuator.valuate_stock(financial_data(ticker="US1"), {})
        bad_ca = self.valuator.valuate_stock(
            financial_data(ticker="CA1", price=float("nan")), {}
        )
        with tempfile.TemporaryDirectory() as output_dir:
            screener = ValueScreener(output_dir=output_dir, min_price_coverage=0.95)
            tables = {
                "us_stocks": pd.DataFrame(),
                "canadian_stocks": pd.DataFrame(),
                "us_opportunities": pd.DataFrame(),
                "ca_opportunities": pd.DataFrame(),
                "sector_summary": pd.DataFrame(),
            }
            with self.assertRaisesRegex(RunIntegrityError, "no outputs were published"):
                screener.save_results(tables, [good_us], [bad_ca], "test")
            self.assertEqual(os.listdir(output_dir), [])

    def test_valid_markets_pass_and_rank_only_eligible_rows(self):
        us = self.valuator.valuate_stock(financial_data(ticker="US1"), {})
        ca = self.valuator.valuate_stock(financial_data(ticker="CA1"), {})
        excluded = self.valuator.valuate_stock(
            financial_data(ticker="US2", interest_expense=100.0), {}
        )
        with tempfile.TemporaryDirectory() as output_dir:
            screener = ValueScreener(output_dir=output_dir)
            screener.validate_run_integrity([us, excluded], [ca])
            ranked = screener.rank_stocks([us, excluded])
            self.assertEqual(ranked["Ticker"].tolist(), ["US1"])
            self.assertAlmostEqual(
                ranked.iloc[0]["Research Entry Price (20% MoS)"],
                ranked.iloc[0]["Intrinsic Value"] * 0.8,
            )
            self.assertIn(ranked.iloc[0]["Alert Status"], {"BUY-ZONE: verify filings", "NEAR: within 10% of entry", "WAIT"})
            self.assertIn("Verification Required", ranked.columns)


class UniverseLoadingTests(unittest.TestCase):
    def test_provider_session_uses_isolated_temporary_cache(self):
        with tempfile.TemporaryDirectory() as cache_dir, patch(
            "data_fetcher.yf.set_tz_cache_location"
        ) as configure:
            session_dir = StockDataFetcher(cache_dir).start_isolated_provider_session()
            self.assertTrue(os.path.isdir(session_dir))
            configure.assert_called_once_with(session_dir)

    def test_sec_ticker_map_is_loaded_once_from_cache(self):
        with tempfile.TemporaryDirectory() as cache_dir:
            fetcher = StockDataFetcher(cache_dir)
            path = os.path.join(fetcher.universes_dir, "sec_company_tickers.json")
            with open(path, "w") as handle:
                json.dump({"0": {"ticker": "BRK.B", "cik_str": 1067983}}, handle)
            with patch("data_fetcher.requests.get") as request:
                self.assertEqual(fetcher.load_sec_cik_map(), 1)
                request.assert_not_called()
            self.assertEqual(fetcher._sec_cik_by_ticker["BRK-B"], "1067983")

    def test_sec_cik_is_extracted_as_stable_issuer_key(self):
        filings = [{"edgarUrl": "https://finance.yahoo.com/sec-filing/CMCSA/abc_001166691"}]
        self.assertEqual(StockDataFetcher._sec_cik_from_filings(filings), "1166691")

    def test_quarterly_discontinued_operations_are_detected(self):
        quarterly = pd.DataFrame(
            {
                pd.Timestamp("2026-06-30"): [-50.0, 100.0, 1_000.0],
                pd.Timestamp("2026-03-31"): [float("nan"), 100.0, 1_000.0],
            },
            index=["Net Income Discontinuous Operations", "Net Income Continuous Operations", "Total Revenue"],
        )
        flags = StockDataFetcher._detect_discontinued_operations(quarterly, "quarterly")
        self.assertEqual(len(flags), 1)
        self.assertIn("2026-06-30 quarterly", flags[0])

    def test_immaterial_discontinued_operations_do_not_block_history(self):
        annual = pd.DataFrame(
            {pd.Timestamp("2025-12-31"): [1.0, 1_000.0, 10_000.0]},
            index=["Net Income Discontinuous Operations", "Net Income Continuous Operations", "Total Revenue"],
        )
        self.assertEqual(StockDataFetcher._detect_discontinued_operations(annual, "annual"), [])

    def test_discontinued_materiality_helper_rejects_small_presentation_amount(self):
        self.assertFalse(
            StockDataFetcher._is_material_discontinued(
                3_000_000, 1_000_000, 4_000_000, 50_000_000_000
            )
        )
        self.assertTrue(
            StockDataFetcher._is_material_discontinued(
                60_000_000, 100_000_000, 160_000_000, 1_000_000_000
            )
        )

    def test_latest_statement_selection_prefers_newer_quarter(self):
        annual = pd.DataFrame({pd.Timestamp("2025-12-31"): [1.0]}, index=["Total Debt"])
        quarterly = pd.DataFrame({pd.Timestamp("2026-06-30"): [2.0]}, index=["Total Debt"])
        frame, period, frequency = StockDataFetcher._select_latest_statement(annual, quarterly)
        self.assertIs(frame, quarterly)
        self.assertEqual(period.date().isoformat(), "2026-06-30")
        self.assertEqual(frequency, "quarterly")

    def test_downloaded_html_is_parsed_as_content(self):
        class Response:
            text = "<html><table><tr><th>Symbol</th></tr></table></html>"

            @staticmethod
            def raise_for_status():
                return None

        def parse_html(source):
            self.assertTrue(hasattr(source, "read"))
            return [pd.DataFrame({"Symbol": ["MMM", "BRK.B"]})]

        with tempfile.TemporaryDirectory() as cache_dir:
            fetcher = StockDataFetcher(cache_dir)
            with patch("data_fetcher.requests.get", return_value=Response()), patch(
                "data_fetcher.pd.read_html", side_effect=parse_html
            ):
                self.assertEqual(fetcher.get_sp500_tickers(), ["MMM", "BRK-B"])


if __name__ == "__main__":
    unittest.main()
