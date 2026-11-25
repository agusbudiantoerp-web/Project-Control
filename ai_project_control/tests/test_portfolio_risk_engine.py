import unittest

from portfolio_risk_engine import assess_project, rank_portfolio


class PortfolioRiskEngineTests(unittest.TestCase):
    def test_critical_project_from_schedule_and_cost(self):
        result = assess_project({"id": "P1", "name": "Mine A", "spi": 0.8, "cpi": 0.8})
        self.assertEqual(result["risk_status"], "CRITICAL")
        self.assertEqual(result["risk_score"], 100.0)

    def test_incomplete_data_is_not_scored(self):
        result = assess_project({"id": "P2", "name": "Mine B"})
        self.assertIsNone(result["risk_score"])
        self.assertEqual(result["risk_status"], "DATA_INCOMPLETE")

    def test_risk_exposure_requires_positive_capacity(self):
        result = assess_project({"risk_exposure": 100, "risk_capacity": 0})
        self.assertNotIn("risk", result["available_indicators"])

    def test_portfolio_sorted_highest_risk_first(self):
        rows = rank_portfolio([
            {"name": "Low", "spi": 0.99},
            {"name": "Critical", "spi": 0.7, "cpi": 0.8},
            {"name": "Unknown"},
        ])
        self.assertEqual([row["project_name"] for row in rows], ["Critical", "Low", "Unknown"])


if __name__ == "__main__":
    unittest.main()
