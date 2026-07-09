"""
Test script to verify the LinkedInScraper logic directly.
"""

import os
import sys
import logging

# Set up logging to stdout
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Add parent directories to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.done.linkedin_scraper import LinkedInScraper

def test_scrape():
    # We will query LinkedIn jobs for "Helsing" in Germany using the guest search URL
    url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=helsing&location=Almanya&geoId=101282230"
    
    # We use a 1.0s delay between requests to be safe
    scraper = LinkedInScraper(delay=1.0)
    
    # Scrape only a few jobs to test without getting rate-limited
    logger.info("Initializing test scrape for Helsing on LinkedIn...")
    
    # Let's temporarily override the internal limit of the scraper to 3 for fast testing
    # We can inject/modify the scraper's behavior or just let it run. Let's subclass or patch
    # to avoid pulling 50 jobs during testing.
    original_scrape = scraper.scrape_jobs
    
    # We can temporarily edit scrape_jobs inside this test script by setting a local limit
    # But since it paginates and page size is 10 or 25, we can just let it fetch one page.
    # Let's create a patched method or just write a small custom test loop
    
    # To keep it quick, we'll patch the scrape_jobs limit to 3:
    import unittest.mock as mock
    
    jobs = scraper.scrape_jobs(url, company_name="Helsing", label="linkedin")
    
    logger.info(f"Scraped {len(jobs)} jobs in total.")
    for i, job in enumerate(jobs[:5]):
        logger.info(f"\n--- Scraped Job {i+1} ---")
        logger.info(f"Title:           {job.get('Job Title')}")
        logger.info(f"Company Name:    {job.get('Company Name')}")
        logger.info(f"Location:        {job.get('Location')}")
        logger.info(f"Job Link:        {job.get('Job Link')}")
        logger.info(f"Remote Status:   {job.get('Remote')}")
        logger.info(f"Employment Type: {job.get('Employment Type')}")
        logger.info(f"Department:      {job.get('Department')}")
        logger.info(f"Description:     {job.get('Job Description')[:150]}...")

if __name__ == "__main__":
    test_scrape()
