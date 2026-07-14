import sys
import unittest
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[1] / "job_scraper" / "src"
sys.path.insert(0, str(SRC_DIR))

from job_taxonomy import CLASSIFICATION_VERSION, classify_job, classify_role  # noqa: E402


class JobTaxonomyTests(unittest.TestCase):
    def test_classifies_generic_engineering_role_and_normalized_fields(self):
        result = classify_job({
            "Job Title": "Senior Software Engineer",
            "Department": "Product Engineering",
            "Location": "Berlin (Hybrid)",
            "Remote": "Hybrid",
            "Job Description": "Build services with Python, AWS and PostgreSQL.",
        })

        self.assertEqual(result["Role"], "Software Engineering")
        self.assertEqual(result["Level"], "Senior")
        self.assertEqual(result["Work Mode"], "Hybrid")
        self.assertEqual(result["Tech Stack"], "Python, AWS, SQL")
        self.assertIn("Software Engineering", result["Keywords"])
        self.assertEqual(result["Classification Version"], CLASSIFICATION_VERSION)

    def test_classifies_engineering_areas_before_generic_software(self):
        self.assertEqual(classify_role({"Job Title": "Senior Backend Software Engineer"}), "Backend")
        self.assertEqual(classify_role({"Job Title": "Machine Learning Engineer"}), "Data / AI / ML")
        self.assertEqual(classify_role({"Job Title": "Site Reliability Engineer"}), "Platform / DevOps / SRE")

    def test_keeps_scope_engineering_only(self):
        self.assertEqual(classify_role({"Job Title": "Technical Product Manager"}), "")
        self.assertEqual(classify_role({"Job Title": "Sales Engineer"}), "")
        self.assertEqual(classify_role({"Job Title": "Technical Support Engineer"}), "")
        self.assertEqual(classify_role({"Job Title": "Mechanical Engineer"}), "")
        self.assertEqual(classify_role({"Job Title": "Electrical Engineer"}), "")
        self.assertEqual(classify_role({"Job Title": "Civil Engineer"}), "")
        self.assertEqual(classify_role({"Job Title": "Founder's Associate (CTO Office)"}), "")
        self.assertEqual(classify_role({"Job Title": "Working Student Content und Frontend Plattformen"}), "")

    def test_classifies_engineering_beyond_software(self):
        examples = {
            "Embedded Firmware Engineer": "Embedded / Firmware / Robotics",
            "Robotics Software Engineer": "Embedded / Firmware / Robotics",
            "Machine Learning Engineer": "Data / AI / ML",
            "Cloud Engineer": "Platform / DevOps / SRE",
            "Security Engineer": "Security",
        }

        for title, expected in examples.items():
            with self.subTest(title=title):
                self.assertEqual(classify_role({"Job Title": title}), expected)

    def test_classifies_engineering_leadership(self):
        result = classify_job({"Job Title": "Director of Engineering", "Location": "Berlin"})

        self.assertEqual(result["Role"], "Engineering Leadership")
        self.assertEqual(result["Level"], "Manager / Head / Director")


if __name__ == "__main__":
    unittest.main()
