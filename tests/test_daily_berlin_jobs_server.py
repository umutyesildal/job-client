import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1] / "daily_berlin_jobs"
sys.path.insert(0, str(APP_DIR))

from server import build_update_command, normalize_keywords  # noqa: E402


class DailyBerlinJobsServerTests(unittest.TestCase):
    def test_normalize_keywords_dedupes_and_trims(self):
        result = normalize_keywords([" software engineer ", "Software Engineer", "", "backend engineer"])

        self.assertEqual(result, ["software engineer", "backend engineer"])

    def test_build_update_command_uses_linkedin_daily_settings(self):
        command = build_update_command({
            "includeLinkedIn": True,
            "profileFitOnly": True,
            "location": "Berlin, Germany",
            "limitPerQuery": 7,
            "postedWithinSeconds": 86400,
            "delay": 0.5,
            "skipUpload": True,
            "keywords": ["software engineer", "backend engineer"],
        })

        self.assertIn("--include-linkedin-daily", command)
        self.assertNotIn("--skip-upload", command)
        self.assertNotIn("--linkedin-raw-daily", command)
        self.assertEqual(command[command.index("--linkedin-limit-per-query") + 1], "7")
        self.assertEqual(command[command.index("--linkedin-keywords") + 1:], [
            "software engineer",
            "backend engineer",
        ])

    def test_build_update_command_can_include_raw_daily_rows(self):
        command = build_update_command({
            "includeLinkedIn": True,
            "profileFitOnly": False,
            "location": "Berlin, Germany",
            "limitPerQuery": 10,
            "postedWithinSeconds": 86400,
            "delay": 1,
            "skipUpload": False,
            "keywords": ["software engineer"],
        })

        self.assertIn("--linkedin-raw-daily", command)
        self.assertNotIn("--skip-upload", command)


if __name__ == "__main__":
    unittest.main()
