import sys
import tempfile
import unittest
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[1] / "job_scraper" / "src"
sys.path.insert(0, str(SRC_DIR))

from data_controller import DataController  # noqa: E402


class CompanyCatalogTests(unittest.TestCase):
    def test_example_catalog_loads(self):
        path = Path(__file__).resolve().parents[1] / "catalog" / "companies.example.yaml"
        result = DataController().load_data_from_yaml(str(path))
        self.assertEqual(result.iloc[0]["Label"], "greenhouse")

    def test_duplicate_source_is_rejected(self):
        content = """companies:
  - {name: Example, career_page: https://example.com/jobs, ats: lever}
  - {name: example, career_page: https://example.com/jobs/, ats: lever}
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "companies.yaml"
            path.write_text(content, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Duplicate company source"):
                DataController().load_data_from_yaml(str(path))

    def test_unknown_ats_is_rejected(self):
        content = """companies:
  - {name: Example, career_page: https://example.com/jobs, ats: unknown-ats}
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "companies.yaml"
            path.write_text(content, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unsupported ATS"):
                DataController().load_data_from_yaml(str(path))


if __name__ == "__main__":
    unittest.main()
