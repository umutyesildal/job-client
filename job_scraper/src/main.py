"""
Main Job Crawler Controller
Reads company data and orchestrates scraping across different ATS platforms
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import logging
import argparse
from crawler_logger import CrawlerLogger
from data_controller import DataController
from client import JobCrawlerController

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',  # Simplified format without timestamps
    handlers=[
        logging.FileHandler('job_crawler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def main():
    
    # Get current directory and data directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_data_dir = os.path.join(script_dir, '..', '..', 'data')
    default_data_dir = os.path.abspath(default_data_dir)
    
    
    parser = argparse.ArgumentParser(description='Job Crawler - Scrape jobs from multiple ATS platforms')
    parser.add_argument('input', nargs='?', default='../../data/job_search.csv',
                    help='Input CSV file (default: ../../data/job_search.csv)')
    parser.add_argument('-l', '--limit', type=int, help='Limit number of companies to process')
    parser.add_argument('-d', '--delay', type=float, default=0.2,
                    help='Delay between requests (seconds)')
    parser.add_argument('-o', '--output-dir', default=default_data_dir,
                    help='Output directory for job files')
    
    args = parser.parse_args()
    
    CrawlerLogger.info_message("\n🤖 Job Crawler v1.0\n")
    
    # Initialize controller
    controller = JobCrawlerController(delay=args.delay, output_dir=args.output_dir)
    data_ctrl = DataController()
    # Load data
    try:
        CrawlerLogger.info_message(f"📥 Loading from: {args.input}")
        df = data_ctrl.load_data_from_csv(args.input)
        
        CrawlerLogger.info_message(f"✓ Loaded {len(df)} companies\n")
        
    except Exception as e:
        CrawlerLogger.error_message(f"❌ Failed to load data: {e}")
        return
    
    # Process companies
    try:
        controller.process_companies(df, limit=args.limit)
            
    except KeyboardInterrupt:
        CrawlerLogger.interrupted_warning()
    except Exception as e:
        CrawlerLogger.general_error(e)



if __name__ == '__main__':
    main()
