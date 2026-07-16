"""
Script to collect 250 Software Engineer jobs in Berlin from LinkedIn.
"""

import os
import logging
import pandas as pd

# Set up logging to stdout
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

from .scrapers.done.linkedin_guest_jobs import LinkedInGuestJobsClient

def run_large_collection():
    # LinkedIn Guest Search URL for Software Engineer in Berlin, Germany
    url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=software%20engineer&location=Berlin%2C%20Germany"
    
    # 0.5s delay to make it faster but still respectful to avoid blocking
    client = LinkedInGuestJobsClient(delay=0.5)
    
    logger.info("Initializing collection for 250 Software Engineer jobs in Berlin...")
    
    jobs = client.scrape_jobs(url, company_name="Various", label="linkedin", limit=250)
    
    logger.info(f"Collection complete. Successfully fetched {len(jobs)} jobs.")
    
    if not jobs:
        logger.warning("No jobs were collected.")
        return
        
    # Convert to DataFrame and save to data directory
    df = pd.DataFrame(jobs)
    
    # Ensure data directory exists
    output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, "linkedin_se_berlin.csv")
    df.to_csv(output_file, index=False, encoding="utf-8")
    
    logger.info(f"Successfully saved results to: {output_file}")
    
    # Show statistics
    logger.info(f"Total remote jobs: {len(df[df['Remote'] == 'Yes'])}")
    logger.info(f"Total hybrid jobs: {len(df[df['Remote'] == 'Hybrid'])}")
    logger.info(f"Total onsite jobs: {len(df[df['Remote'] == 'No'])}")
    
    # Display the first few jobs as sample
    logger.info("\nSample of collected jobs:")
    for i, job in enumerate(jobs[:5]):
        logger.info(f"  {i+1}. {job.get('Job Title')} at {job.get('Company Name')} ({job.get('Location')})")

if __name__ == "__main__":
    run_large_collection()
