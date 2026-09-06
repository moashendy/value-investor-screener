import os
import sys
import unittest

import pandas as pd


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from historical_signals import (
    HistoricalDataError,
    SecCompanyFactsClient,
    annual_instant_facts,
    annual_facts,
    build_signals,
    prepare_membership,
    summarize_coverage,
)


def company_facts(entries):
    return {
        "entityName": "Example Company",
        "facts": {
            "us-gaap": {
                "EarningsPerShareDiluted": {
                    "units": {"USD/shares": entries}
                }
            }
        },
    }


class HistoricalSignalTests(unittest.TestCase):
    def test_future_restatement_does_not_rewrite_an_older_signal(self):
        payload = company_facts([
            {
                "start": "2019-01-01", "end": "2019-12-31", "val": 4.0,
                "filed": "2020-02-15", "form": "10-K", "accn": "old",
            },
            {
                "start": "2019-01-01", "end": "2019-12-31", "val": 9.0,
                "filed": "2022-02-15", "form": "10-K", "accn": "restated",
            },
        ])
        old_view = annual_facts(payload, "eps", "2021-01-01")
        new_view = annual_facts(payload, "eps", "2023-01-01")
        self.assertEqual(old_view[0].value, 4.0)
        self.assertEqual(new_view[0].value, 9.0)

    def test_quarterly_duration_is_not_mistaken_for_annual_data(self):
        payload = company_facts([
            {
                "start": "2020-01-01", "end": "2020-03-31", "val": 1.0,
                "filed": "2020-05-01", "form": "10-Q", "accn": "quarter",
            }
        ])
        self.assertEqual(annual_facts(payload, "eps", "2021-01-01"), [])

    def test_piotroski_balance_history_uses_annual_instants(self):
        payload = {
            "facts": {"us-gaap": {"Assets": {"units": {"USD": [
                {"end": "2019-12-31", "val": 90, "filed": "2020-02-01", "form": "10-K", "accn": "a"},
                {"end": "2020-03-31", "val": 95, "filed": "2020-05-01", "form": "10-Q", "accn": "b"},
                {"end": "2020-12-31", "val": 100, "filed": "2021-02-01", "form": "10-K", "accn": "c"},
            ]}}}},
        }
        rows = annual_instant_facts(payload, "assets", "2021-03-01")
        self.assertEqual([row.value for row in rows], [100, 90])

    def test_membership_requires_stable_cik_and_unique_snapshot_rows(self):
        frame = pd.DataFrame([{
            "signal_date": "2020-01-01", "ticker": "abc", "cik": "123",
            "sector": "Industrials", "industry": "Tools", "universe_member": "true",
        }])
        prepared = prepare_membership(frame)
        self.assertEqual(prepared.iloc[0]["ticker"], "ABC")
        self.assertEqual(prepared.iloc[0]["cik"], "0000000123")
        self.assertTrue(prepared.iloc[0]["universe_member"])

    def test_offline_mode_refuses_missing_companyfacts(self):
        import tempfile
        with tempfile.TemporaryDirectory() as cache_dir:
            client = SecCompanyFactsClient(cache_dir)
            with self.assertRaisesRegex(HistoricalDataError, "missing cached"):
                client.get("123", offline=True)

    def test_end_to_end_signal_records_filing_availability(self):
        years = [2017, 2018, 2019]

        def durations(values):
            return [
                {"start": f"{year}-01-01", "end": f"{year}-12-31", "val": value,
                 "filed": f"{year + 1}-02-15", "form": "10-K", "accn": str(year)}
                for year, value in zip(years, values)
            ]

        def instants(values):
            return [
                {"end": f"{year}-12-31", "val": value,
                 "filed": f"{year + 1}-02-15", "form": "10-K", "accn": str(year)}
                for year, value in zip(years, values)
            ]

        usd_duration = {
            "NetCashProvidedByUsedInOperatingActivities": durations([100, 130, 150]),
            "PaymentsToAcquirePropertyPlantAndEquipment": durations([20, 20, 20]),
            "NetIncomeLoss": durations([80, 100, 120]),
            "OperatingIncomeLoss": durations([100, 120, 140]),
            "InterestExpenseNonOperating": durations([10, 10, 10]),
            "Revenues": durations([800, 900, 1000]),
            "GrossProfit": durations([300, 350, 400]),
        }
        usd_instant = {
            "Assets": instants([800, 900, 1000]),
            "Liabilities": instants([400, 420, 430]),
            "StockholdersEquity": instants([400, 480, 570]),
            "AssetsCurrent": instants([300, 350, 400]),
            "LiabilitiesCurrent": instants([220, 210, 200]),
            "LongTermDebt": instants([150, 120, 100]),
            "CashAndCashEquivalentsAtCarryingValue": instants([50, 60, 70]),
            "RetainedEarningsAccumulatedDeficit": instants([200, 260, 330]),
        }
        facts = {
            name: {"units": {"USD": rows}}
            for name, rows in {**usd_duration, **usd_instant}.items()
        }
        facts["EarningsPerShareDiluted"] = {"units": {"USD/shares": durations([4, 5, 6])}}
        facts["WeightedAverageNumberOfDilutedSharesOutstanding"] = {
            "units": {"shares": durations([100, 100, 100])}
        }
        facts["EntityCommonStockSharesOutstanding"] = {
            "units": {"shares": instants([100, 100, 100])}
        }
        payload = {"entityName": "Example Company", "facts": {"us-gaap": facts}}

        class StubClient:
            def get(self, cik, offline=False):
                return payload

        membership = pd.DataFrame([{
            "signal_date": "2020-04-01", "ticker": "AAA", "cik": "123",
            "sector": "Industrials", "industry": "Tools", "universe_member": True,
        }])
        prices = pd.DataFrame([
            {"date": "2020-04-01", "ticker": "AAA", "adjusted_close": 10},
        ])
        result = build_signals(membership, prices, StubClient(), offline=True)
        self.assertEqual(len(result), 1)
        self.assertTrue(result.iloc[0]["eligible"])
        self.assertEqual(result.iloc[0]["fundamentals_available_date"], "2020-02-15")
        self.assertEqual(result.iloc[0]["issuer_identity"], "SEC:0000000123")
        coverage = summarize_coverage(result)
        self.assertEqual(coverage["member_rows"], 1)
        self.assertEqual(coverage["usable_coverage"], 1.0)
        self.assertEqual(coverage["by_sector"][0]["sector"], "Industrials")


if __name__ == "__main__":
    unittest.main()
