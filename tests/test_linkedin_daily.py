import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse


SRC_DIR = Path(__file__).resolve().parents[1] / "job_scraper" / "src"
sys.path.insert(0, str(SRC_DIR))

from linkedin_daily import build_linkedin_search_url, collect_daily_linkedin_jobs  # noqa: E402


class LinkedInDailyTests(unittest.TestCase):
    def test_build_url_uses_last_24_hour_filter(self):
        url = build_linkedin_search_url("software engineer", "Berlin, Germany")
        params = parse_qs(urlparse(url).query)

        self.assertEqual(params["keywords"], ["software engineer"])
        self.assertEqual(params["location"], ["Berlin, Germany"])
        self.assertEqual(params["f_TPR"], ["r86400"])

    def test_collect_daily_dedupes_across_keyword_queries(self):
        duplicate_job = {
            "Company Name": "Example",
            "Job Title": "Software Engineer",
            "Location": "Berlin, Berlin, Germany",
            "Job Link": "https://de.linkedin.com/jobs/view/123",
            "ATS": "LinkedIn",
        }
        unique_job = {
            "Company Name": "Example",
            "Job Title": "Backend Engineer",
            "Location": "Berlin, Berlin, Germany",
            "Job Link": "https://de.linkedin.com/jobs/view/456",
            "ATS": "LinkedIn",
        }

        with patch("linkedin_daily.LinkedInGuestJobsClient") as client_class:
            client = client_class.return_value
            client.scrape_jobs.side_effect = [[duplicate_job], [duplicate_job, unique_job]]

            result = collect_daily_linkedin_jobs(
                keywords=["software engineer", "backend engineer"],
                location="Berlin, Germany",
                limit_per_query=2,
                delay=0,
            )

        self.assertEqual(len(result), 2)
        self.assertEqual(result["Job Link"].tolist(), [
            "https://de.linkedin.com/jobs/view/123",
            "https://de.linkedin.com/jobs/view/456",
        ])


if __name__ == "__main__":
    unittest.main()
