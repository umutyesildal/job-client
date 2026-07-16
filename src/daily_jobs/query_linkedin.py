"""
query_linkedin.py - CLI tool to run dynamic LinkedIn guest job queries and option to score results.
"""

import os
import argparse
import logging
import pandas as pd
from urllib.parse import urlencode

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

from .scrapers.done.linkedin_guest_jobs import LinkedInGuestJobsClient

def main():
    parser = argparse.ArgumentParser(description="Query LinkedIn Guest Job Search API dynamically")
    parser.add_argument("--keywords", required=True, help="Job title or search keywords (e.g. 'software engineer')")
    parser.add_argument("--location", required=True, help="Search location (e.g. 'Berlin, Germany' or 'Munich')")
    parser.add_argument("--limit", type=int, default=50, help="Maximum number of jobs to retrieve (default: 50)")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between page/detail fetches in seconds (default: 1.0)")
    parser.add_argument("--output", default="data/linkedin_results.csv", help="Output CSV file path")
    parser.add_argument("--score", action="store_true", help="Apply early-career software engineering fit scoring")

    args = parser.parse_args()

    # Construct public guest API URL
    base_url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    query_params = {
        "keywords": args.keywords,
        "location": args.location
    }
    url = f"{base_url}?{urlencode(query_params)}"

    logger.info(f"Target URL: {url}")
    logger.info(f"Parameters: Keywords='{args.keywords}', Location='{args.location}', Limit={args.limit}, Delay={args.delay}s")

    client = LinkedInGuestJobsClient(delay=args.delay)
    
    jobs = client.scrape_jobs(url, company_name="Various", label="linkedin", limit=args.limit)

    if not jobs:
        logger.warning("No jobs were found.")
        return

    # Convert to DataFrame and normalize columns
    from .data_controller import DataController
    df = pd.DataFrame(jobs)
    df = DataController().normalize_jobs_dataframe(df)

    # Normalize folder path for saving
    output_path = os.path.abspath(args.output)
    output_dir = os.path.dirname(output_path)
    os.makedirs(output_dir, exist_ok=True)

    # Save raw results
    df.to_csv(output_path, index=False, encoding="utf-8")
    logger.info(f"Saved {len(df)} raw jobs to: {output_path}")

    # Optional scoring logic
    if args.score:
        logger.info("Applying early-career software engineering profile scoring...")
        try:
            from .post_process_jobs import filter_related_jobs
            
            # Run the scoring filter
            scored_df = filter_related_jobs(df)
            
            if scored_df.empty:
                logger.info("No collected jobs matched your early-career profile fit criteria.")
            else:
                scored_output_path = output_path.replace(".csv", "_scored.csv")
                scored_df.to_csv(scored_output_path, index=False, encoding="utf-8")
                logger.info(f"Saved {len(scored_df)} matched/scored jobs to: {scored_output_path}")
                
                logger.info(f"\n🎯 TOP FIT MATCHES ({len(scored_df)} found):")
                # Print the top 10 matches
                for idx, row in scored_df.head(10).iterrows():
                    logger.info(f"  • [{row.get('Fit Score')} pts] {row.get('Job Title')} at {row.get('Company Name')}")
                    logger.info(f"    Location: {row.get('Location')}")
                    logger.info(f"    Reasons:  {row.get('Fit Reasons')}")
                    logger.info(f"    Link:     {row.get('Job Link')}\n")
        except ImportError:
            logger.error("Could not import the daily_jobs post-processing module.")
        except Exception as e:
            logger.error(f"Error during scoring: {e}")

if __name__ == "__main__":
    main()
