import sys
import unittest
from pathlib import Path
from unittest.mock import patch


SRC_DIR = Path(__file__).resolve().parents[1] / "job_scraper" / "src"
sys.path.insert(0, str(SRC_DIR))

from data_controller import DataController  # noqa: E402


class GoogleSheetsJobOutputTests(unittest.TestCase):
    def test_job_rows_do_not_use_company_input_validation(self):
        values = [["Company Name", "Job Title", "Job Link"], ["Example", "Engineer", "https://example.com"]]

        with patch("data_controller.CrawlerLogger.missing_column_warning") as warning:
            result = DataController()._values_to_dataframe(values, data_kind="jobs")

        warning.assert_not_called()
        self.assertEqual(result.iloc[0]["Company"], "Example")
        self.assertNotIn("Name", result.columns)
        self.assertNotIn("Career Page", result.columns)


if __name__ == "__main__":
    unittest.main()
