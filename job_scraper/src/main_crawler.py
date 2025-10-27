"""
Main Job Crawler Controller
Reads company data and orchestrates scraping across different ATS platforms
"""

import pandas as pd
import logging
import time
from datetime import datetime
from typing import List, Dict
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import completed scrapers
from scrapers.done.ashby_scraper import AshbyScraper
from scrapers.done.bamboohr_scraper import BambooHRScraper
from scrapers.done.consider_scraper import ConsiderScraper
from scrapers.done.gem_scraper import GemScraper
from scrapers.done.getro_scraper import GetroScraper
from scrapers.done.greenhouse_scraper import GreenhouseScraper
from scrapers.done.hibob_scraper import HiBobScraper
from scrapers.done.join_scraper import JoinScraper
from scrapers.done.lever_scraper import LeverScraper
from scrapers.done.personio_scraper import PersonioScraper
from scrapers.done.recruitee_scraper import RecruiteeScraper
from scrapers.done.rippling_scraper import RipplingScraper
from scrapers.done.workable_scraper import WorkableScraper

# Import incomplete scrapers
from scrapers.undone.smartrecruiters_scraper import SmartRecruitarsScraper
from scrapers.undone.softgarden_scraper import SoftgardenScraper
from scrapers.undone.teamtailor_scraper import TeamtailorScraper
from scrapers.undone.workday_scraper import WorkdayScraper

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',  # Simplified format without timestamps
    handlers=[
        logging.FileHandler('job_crawler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class JobCrawlerController:
    """Main controller for orchestrating job scraping across ATS platforms"""
    
    # Map label names to scraper classes
    SCRAPER_MAP = {
        'ashbyhq': AshbyScraper,
        'ashby': AshbyScraper,
        'bamboohr': BambooHRScraper,
        'consider': ConsiderScraper,
        'gem': GemScraper,
        'getro': GetroScraper,
        'greenhouse': GreenhouseScraper,
        'hibob': HiBobScraper,
        'bob': HiBobScraper,
        'join': JoinScraper,
        'lever': LeverScraper,
        'myworkdayjobs': WorkdayScraper,
        'workday': WorkdayScraper,
        'personio': PersonioScraper,
        'recruitee': RecruiteeScraper,
        'rippling': RipplingScraper,
        'smartrecruiters': SmartRecruitarsScraper,
        'softgarden': SoftgardenScraper,
        'teamtailor': TeamtailorScraper,
        'workable': WorkableScraper,
    }
    
    def __init__(self, delay: float = 2.0, output_dir: str = '../../data'):
        self.delay = delay
        self.output_dir = output_dir
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
    
    def load_data_from_csv(self, csv_path: str) -> pd.DataFrame:
        """Load company data from CSV file"""
        df = pd.read_csv(csv_path)
        
        # Normalize column names to handle different schemas
        df = self._normalize_dataframe(df)
        
        return df
    
    def load_data_from_google_sheets(self, sheet_url: str) -> pd.DataFrame:
        """
        Load company data from Google Sheets
        Note: Requires gspread library and authentication
        """
        try:
            import gspread
            from google.oauth2.service_account import Credentials
            
            logger.info(f"Loading data from Google Sheets: {sheet_url}")
            
            # Setup credentials
            scope = ['https://spreadsheets.google.com/feeds',
                    'https://www.googleapis.com/auth/drive']
            
            # Load credentials from file
            creds = Credentials.from_service_account_file('credentials.json', scopes=scope)
            client = gspread.authorize(creds)
            
            # Open sheet
            sheet = client.open_by_url(sheet_url).sheet1
            data = sheet.get_all_records()
            
            df = pd.DataFrame(data)
            
            # Normalize column names to handle different schemas
            df = self._normalize_dataframe(df)
            
            logger.info(f"Loaded {len(df)} companies from Google Sheets")
            return df
            
        except ImportError:
            logger.error("gspread library not installed. Install with: pip install gspread google-auth")
            raise
        except FileNotFoundError:
            logger.error("credentials.json not found. Please provide Google Sheets API credentials")
            raise
        except Exception as e:
            logger.error(f"Error loading Google Sheets: {e}")
            raise
    
    def _normalize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize dataframe column names to handle different schemas
        Supports both old schema (Name, Website, Career Page) and new schema (Website, Career Page, Active)
        """
        # Create a copy to avoid modifying original
        df = df.copy()
        
        # If 'Website' exists but 'Name' doesn't, use Website as Name
        if 'Website' in df.columns and 'Name' not in df.columns:
            # Extract domain name from website URL for display
            df['Name'] = df['Website'].apply(self._extract_domain_name)
        
        # Ensure required columns exist
        required_columns = ['Name', 'Career Page', 'Label']
        for col in required_columns:
            if col not in df.columns:
                logger.warning(f"Missing required column: {col}")
                df[col] = 'N/A'
        
        # Add Description if missing
        if 'Description' not in df.columns:
            df['Description'] = 'N/A'
        
        # Filter by Active status if column exists
        if 'Active' in df.columns:
            # Filter only active entries
            active_count = len(df)
            df = df[df['Active'].str.lower() == 'active'].copy()
            logger.info(f"Filtered to {len(df)} active companies (out of {active_count} total)")
        
        return df
    
    def _extract_domain_name(self, url: str) -> str:
        """Extract clean domain name from URL for display"""
        if pd.isna(url) or not url:
            return 'Unknown'
        
        try:
            # Remove protocol
            domain = url.replace('https://', '').replace('http://', '')
            # Remove www.
            domain = domain.replace('www.', '')
            # Take first part before /
            domain = domain.split('/')[0]
            # Capitalize first letter
            domain = domain.split('.')[0].capitalize()
            return domain
        except:
            return url
    
    def get_scraper(self, label: str):
        """Get appropriate scraper based on label"""
        # Normalize label (lowercase, remove spaces)
        normalized_label = label.lower().strip().replace(' ', '').replace('-', '')
        
        # Try to find matching scraper
        for key, scraper_class in self.SCRAPER_MAP.items():
            if key in normalized_label or normalized_label in key:
                return scraper_class()
        
        return None
    
    def _load_existing_jobs(self) -> set:
        """Load existing job links from the CSV file"""
        all_jobs_file = os.path.join(self.output_dir, 'all_jobs.csv')
        existing_links = set()
        
        if os.path.exists(all_jobs_file):
            try:
                existing_df = pd.read_csv(all_jobs_file, encoding='utf-8')
                if 'Job Link' in existing_df.columns:
                    existing_links = set(existing_df['Job Link'].dropna().unique())
                logger.debug(f"Loaded {len(existing_links)} existing jobs from database")
            except Exception as e:
                logger.debug(f"Could not load existing jobs: {e}")
        
        return existing_links
    
    def scrape_company(self, row: pd.Series) -> List[Dict]:
        """
        Scrape jobs for a single company
        
        Args:
            row: DataFrame row with company data
            
        Returns:
            List of job dictionaries
        """
        name = row.get('Name', '')
        website = row.get('Website', '')
        career_page = row.get('Career Page', '')
        description = row.get('Description', '')
        label = row.get('Label', '')
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing: {name}")
        logger.info(f"Career Page: {career_page}")
        logger.info(f"Label: {label}")
        logger.info(f"{'='*60}")
        
        # Validate input
        if pd.isna(career_page) or not career_page:
            logger.warning(f"No career page URL for {name}, skipping...")
            return []
        
        if pd.isna(label) or not label:
            logger.warning(f"No label specified for {name}, skipping...")
            return []
        
        # Get appropriate scraper
        scraper = self.get_scraper(label)
        if not scraper:
            logger.error(f"Could not find scraper for label: {label}")
            return []
        
        # Scrape jobs
        try:
            jobs = scraper.scrape_jobs(
                url=career_page,
                company_name=name,
                company_description=description,
                label=label
            )
            
            logger.info(f"Found {len(jobs)} jobs for {name}")
            return jobs
            
        except Exception as e:
            logger.error(f"Error scraping {name}: {e}")
            return []
    
    def process_companies(self, df: pd.DataFrame, limit: int = None):
        """
        Process multiple companies from dataframe
        
        Args:
            df: DataFrame with company data
            limit: Optional limit on number of companies to process
        """
        all_jobs = []
        stats = {
            'total_companies': len(df) if limit is None else min(limit, len(df)),
            'successful': 0,
            'failed': 0,
            'total_jobs': 0,
            'new_jobs': 0
        }
        
        # Load existing jobs to detect new ones
        existing_jobs = self._load_existing_jobs()
        
        companies_to_process = df.head(limit) if limit else df
        
        logger.info("\n" + "="*80)
        logger.info("🚀 STARTING JOB CRAWLER")
        logger.info("="*80)
        logger.info(f"📊 Processing {stats['total_companies']} companies")
        logger.info(f"📦 Existing jobs: {len(existing_jobs)}")
        logger.info("="*80 + "\n")
        
        for idx, row in companies_to_process.iterrows():
            company_name = row.get('Name', 'Unknown')
            career_page = row.get('Career Page', '')
            description = row.get('Description', 'N/A')
            label = row.get('Label', 'unknown')
            
            logger.info(f"\n[{idx + 1}/{stats['total_companies']}] 🏢 {company_name} ({label})")
            
            # Validate input
            if pd.isna(career_page) or not career_page:
                logger.warning(f"  ⚠️  No career page - skipping")
                stats['failed'] += 1
                continue
            
            if pd.isna(label) or not label:
                logger.warning(f"  ⚠️  No ATS platform - skipping")
                stats['failed'] += 1
                continue
            
            # Get appropriate scraper
            scraper = self.get_scraper(label)
            
            if not scraper:
                logger.warning(f"  ⚠️  No scraper for {label} - skipping")
                stats['failed'] += 1
                continue
            
            try:
                start_time = time.time()
                
                # Scrape jobs
                jobs = scraper.scrape_jobs(
                    url=career_page,
                    company_name=company_name,
                    company_description=description,
                    label=label
                )
                
                elapsed_time = time.time() - start_time
                
                if jobs:
                    # Check for new jobs
                    new_jobs = [j for j in jobs if j.get('Job Link') not in existing_jobs]
                    
                    logger.info(f"  ✅ Found {len(jobs)} jobs ({len(new_jobs)} new) in {elapsed_time:.1f}s")
                    
                    if new_jobs:
                        # Show first 3 new jobs
                        for job in new_jobs[:3]:
                            logger.info(f"     • {job['Job Title']}")
                        if len(new_jobs) > 3:
                            logger.info(f"     ... and {len(new_jobs) - 3} more")
                        
                        # Add new jobs to tracking set
                        for job in new_jobs:
                            existing_jobs.add(job.get('Job Link'))
                        
                        stats['new_jobs'] += len(new_jobs)
                    
                    # Save jobs immediately after each company (incremental save)
                    self.save_jobs(jobs)
                    
                    stats['total_jobs'] += len(jobs)
                    stats['successful'] += 1
                else:
                    logger.warning(f"  ⚠️  No jobs found")
                    stats['failed'] += 1
                
                # Brief progress update
                logger.info(f"  📊 Progress: ✓{stats['successful']} ❌{stats['failed']} | Total: {stats['total_jobs']} jobs ({stats['new_jobs']} new)")
                
                # Delay between companies
                time.sleep(self.delay)
                
            except Exception as e:
                logger.error(f"  ❌ Error: {str(e)[:80]}")
                stats['failed'] += 1
                continue
        
        # Final summary
        logger.info("\n" + "="*80)
        logger.info("🎉 COMPLETED!")
        logger.info("="*80)
        logger.info(f"✓ Successful: {stats['successful']} | ❌ Failed: {stats['failed']}")
        logger.info(f"📦 Total jobs: {stats['total_jobs']} | 🆕 New: {stats['new_jobs']}")
        logger.info(f"💾 Saved to: {self.output_dir}/all_jobs.csv")
        logger.info("="*80)
        
        return all_jobs
    
    def save_jobs(self, jobs: List[Dict]):
        """
        Save jobs to a single consolidated CSV file
        Appends new jobs and handles deduplication
        """
        if not jobs:
            return
        
        output_path = os.path.join(self.output_dir, 'all_jobs.csv')
        new_jobs_df = pd.DataFrame(jobs)
        
        # If file exists, load it and append new jobs
        if os.path.exists(output_path):
            try:
                existing_df = pd.read_csv(output_path, encoding='utf-8')
                
                # Combine existing and new jobs
                combined_df = pd.concat([existing_df, new_jobs_df], ignore_index=True)
                
                # Remove duplicates based on Job Link (keep most recent = last occurrence)
                combined_df = combined_df.drop_duplicates(subset=['Job Link'], keep='last')
                
                # Save back
                combined_df.to_csv(output_path, index=False, encoding='utf-8')
                
                new_count = len(combined_df) - len(existing_df)
                logger.debug(f"Added {new_count} new jobs to database (total: {len(combined_df)})")
                
            except Exception as e:
                logger.error(f"Error updating jobs file: {e}")
                # Fallback: just append
                new_jobs_df.to_csv(output_path, mode='a', header=False, index=False, encoding='utf-8')
        else:
            # First time: create new file
            new_jobs_df.to_csv(output_path, index=False, encoding='utf-8')
            logger.debug(f"Created new jobs database with {len(jobs)} jobs")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Job Crawler - Scrape jobs from multiple ATS platforms')
    parser.add_argument('input', nargs='?', default='../../data/job_search.csv',
                       help='Input CSV file or Google Sheets URL (default: ../../data/job_search.csv)')
    parser.add_argument('-t', '--type', choices=['csv', 'sheets'], default='csv',
                       help='Input type: csv or sheets')
    parser.add_argument('-l', '--limit', type=int, help='Limit number of companies to process')
    parser.add_argument('-d', '--delay', type=float, default=2.0,
                       help='Delay between requests (seconds)')
    parser.add_argument('-o', '--output-dir', default='../data',
                       help='Output directory for job files')
    
    args = parser.parse_args()
    
    logger.info("\n� Job Crawler v1.0\n")
    
    # Initialize controller
    controller = JobCrawlerController(delay=args.delay, output_dir=args.output_dir)
    
    # Load data
    try:
        if args.type == 'csv':
            logger.info(f"📥 Loading from: {args.input}")
            df = controller.load_data_from_csv(args.input)
        else:
            logger.info(f"📥 Loading from: {args.input}")
            df = controller.load_data_from_google_sheets(args.input)
        
        logger.info(f"✓ Loaded {len(df)} companies\n")
        
    except Exception as e:
        logger.error(f"❌ Failed to load data: {e}")
        return
    
    # Process companies
    try:
        controller.process_companies(df, limit=args.limit)
            
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Interrupted - partial results saved")
    except Exception as e:
        logger.error(f"❌ Error: {e}")


if __name__ == '__main__':
    main()
