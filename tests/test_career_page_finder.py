import unittest
from unittest.mock import patch

from bs4 import BeautifulSoup

from career_page_finder.career_page_finder import CareerPageFinder
from career_page_finder.homepage_career_finder import HomepageCareerFinder


class CareerPageFinderTests(unittest.TestCase):
    def test_sitemap_does_not_treat_job_listing_as_career_root(self):
        finder = CareerPageFinder(delay=0)

        result = finder.find_career_page(
            [
                "https://vercel.com/careers/site-engineer-us-5732855004",
                "https://vercel.com/customers",
            ]
        )

        self.assertIsNone(result)

    def test_sitemap_accepts_career_root(self):
        finder = CareerPageFinder(delay=0)

        result = finder.find_career_page(
            [
                "https://example.com/careers/software-engineer-123456",
                "https://example.com/careers",
            ]
        )

        self.assertEqual(result, "https://example.com/careers")

    def test_homepage_link_text_can_find_external_ats(self):
        finder = HomepageCareerFinder(delay=0)
        page = BeautifulSoup(
            '<footer><a href="https://jobs.example-ats.com/acme">Careers</a></footer>',
            "html.parser",
        )

        links = finder._extract_career_links(page, "https://acme.example")

        self.assertEqual(links, [("https://jobs.example-ats.com/acme", 10)])

    @patch(
        "career_page_finder.career_page_finder.HomepageCareerFinder.process_company",
        return_value=("https://vercel.com/careers", "FOUND"),
    )
    @patch(
        "career_page_finder.career_page_finder.CareerPageFinder.find_sitemap",
        return_value=None,
    )
    def test_homepage_is_used_when_sitemap_is_unavailable(
        self, _find_sitemap, _process_homepage
    ):
        finder = CareerPageFinder(delay=0)

        result = finder.process_company("Vercel", "https://vercel.com")

        self.assertEqual(result, ("https://vercel.com/careers", "FOUND_HOMEPAGE"))


if __name__ == "__main__":
    unittest.main()
