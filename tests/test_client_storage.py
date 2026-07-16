import tempfile
import unittest
from pathlib import Path

import pandas as pd


from daily_jobs.client import JobCrawlerController


class RawSnapshotTests(unittest.TestCase):
    def test_each_crawl_replaces_instead_of_appending_raw_history(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            controller = JobCrawlerController(delay=0, output_dir=temp_dir, max_workers=1)
            controller.save_jobs([{
                "Company Name": "Old Co", "Job Title": "Engineer", "Location": "Berlin",
                "Job Link": "https://example.com/old",
            }])
            controller.save_jobs([{
                "Company Name": "New Co", "Job Title": "Engineer", "Location": "Berlin",
                "Job Link": "https://example.com/new",
            }])

            result = pd.read_csv(Path(temp_dir) / "all_jobs.csv")
            self.assertEqual(result["Job Link"].tolist(), ["https://example.com/new"])

    def test_empty_crawl_clears_previous_raw_snapshot(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            controller = JobCrawlerController(delay=0, output_dir=temp_dir, max_workers=1)
            controller.save_jobs([{
                "Company Name": "Old Co", "Job Title": "Engineer", "Location": "Berlin",
                "Job Link": "https://example.com/old",
            }])
            controller.save_jobs([])

            result = pd.read_csv(Path(temp_dir) / "all_jobs.csv")
            self.assertTrue(result.empty)


if __name__ == "__main__":
    unittest.main()
