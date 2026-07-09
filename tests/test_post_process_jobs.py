import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd


SRC_DIR = Path(__file__).resolve().parents[1] / "job_scraper" / "src"
sys.path.insert(0, str(SRC_DIR))

from post_process_jobs import find_daily_new_jobs  # noqa: E402


class DailyNewJobsTests(unittest.TestCase):
    def _find_new(self, previous_rows, current_rows):
        with tempfile.TemporaryDirectory() as temp_dir:
            previous_path = Path(temp_dir) / "previous.csv"
            pd.DataFrame(previous_rows).to_csv(previous_path, index=False)
            return find_daily_new_jobs(pd.DataFrame(current_rows), previous_path)

    def test_changed_url_does_not_make_existing_role_new(self):
        previous = [{
            "Company Name": "München Labs",
            "Job Title": "Junior Software Engineer (m/f/d)",
            "Location": "Berlin, Germany",
            "Job Link": "https://example.com/old",
        }]
        current = [{
            "Company Name": "Munchen Labs",
            "Job Title": "Junior Software Engineer - m/f/d",
            "Location": "Berlin Germany",
            "Job Link": "https://example.com/new",
        }]

        self.assertTrue(self._find_new(previous, current).empty)

    def test_same_title_in_different_location_is_new(self):
        previous = [{
            "Company Name": "Example",
            "Job Title": "Software Engineer",
            "Location": "Munich",
            "Job Link": "https://example.com/old",
        }]
        current = [{
            "Company Name": "Example",
            "Job Title": "Software Engineer",
            "Location": "Berlin",
            "Job Link": "https://example.com/new",
        }]

        self.assertEqual(len(self._find_new(previous, current)), 1)

    def test_real_new_role_is_kept_once(self):
        previous = [{
            "Company Name": "Example",
            "Job Title": "Data Engineer",
            "Location": "Berlin",
            "Job Link": "https://example.com/old",
        }]
        current = [
            {
                "Company Name": "Example",
                "Job Title": "Backend Engineer",
                "Location": "Berlin",
                "Job Link": "https://example.com/new-1",
            },
            {
                "Company Name": "Example",
                "Job Title": "Backend Engineer",
                "Location": "Berlin",
                "Job Link": "https://example.com/new-2",
            },
        ]

        result = self._find_new(previous, current)
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["Job Link"], "https://example.com/new-1")


if __name__ == "__main__":
    unittest.main()
