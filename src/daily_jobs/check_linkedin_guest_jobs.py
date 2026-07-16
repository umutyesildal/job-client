"""
Test script to verify the LinkedIn guest jobs client directly.
"""

import logging

# Set up logging to stdout
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

from .scrapers.done.linkedin_guest_jobs import LinkedInGuestJobsClient

def test_collect():
    # We will query LinkedIn jobs for "Helsing" in Germany using the guest search URL
    url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=helsing&location=Almanya&geoId=101282230"
    
    # We use a 1.0s delay between requests to be safe
    client = LinkedInGuestJobsClient(delay=1.0)
    
    logger.info("Initializing test query for Helsing on LinkedIn...")
    
    jobs = client.scrape_jobs(url, company_name="Helsing", label="linkedin", limit=3)
    
    logger.info(f"Collected {len(jobs)} jobs in total.")
    for i, job in enumerate(jobs[:5]):
        logger.info(f"\n--- Collected Job {i+1} ---")
        logger.info(f"Title:           {job.get('Job Title')}")
        logger.info(f"Company Name:    {job.get('Company Name')}")
        logger.info(f"Location:        {job.get('Location')}")
        logger.info(f"Job Link:        {job.get('Job Link')}")
        logger.info(f"Remote Status:   {job.get('Remote')}")
        logger.info(f"Employment Type: {job.get('Employment Type')}")
        logger.info(f"Department:      {job.get('Department')}")
        logger.info(f"Description:     {job.get('Job Description')[:150]}...")

if __name__ == "__main__":
    test_collect()
