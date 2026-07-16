import unittest
from unittest.mock import patch

from daily_jobs.data_controller import DataController


class GoogleSheetsJobOutputTests(unittest.TestCase):
    def test_job_rows_do_not_use_company_input_validation(self):
        values = [["Company Name", "Job Title", "Job Link"], ["Example", "Engineer", "https://example.com"]]

        with patch("daily_jobs.data_controller.CrawlerLogger.missing_column_warning") as warning:
            result = DataController()._values_to_dataframe(values, data_kind="jobs")

        warning.assert_not_called()
        self.assertEqual(result.iloc[0]["Company"], "Example")
        self.assertNotIn("Name", result.columns)
        self.assertNotIn("Career Page", result.columns)


if __name__ == "__main__":
    unittest.main()
