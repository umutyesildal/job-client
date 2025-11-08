"""
Database Integration Options for Job Crawler
Provides utilities for exporting to different database systems
"""

import pandas as pd
import logging
from typing import Optional
import os
from crawler_logger import CrawlerLogger

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataController:
    """Handle exporting jobs to different database systems"""
    
    def __init__(self, csv_path: str = 'output/all_jobs.csv'):
        self.csv_path = csv_path
        self.df = None
    
    def load_csv(self):
        """Load jobs from CSV"""
        if not os.path.exists(self.csv_path):
            logger.error(f"CSV file not found: {self.csv_path}")
            return False
        
        self.df = pd.read_csv(self.csv_path, encoding='utf-8')
        logger.info(f"Loaded {len(self.df)} jobs from {self.csv_path}")
        return True
    
    
    def load_data_from_csv(self, csv_path: str) -> pd.DataFrame:
        """Load company data from CSV file"""
        df = pd.read_csv(csv_path, low_memory=False, dtype=str)
        
        # Normalize column names to handle different schemas
        df = self.normalize_dataframe(df)
        
        return df
    
    def normalize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize dataframe column names to handle different schemas
        Supports both old schema (Name, Website, Career Page) and new schema (Website, Career Page, Active)
        """
        # Create a copy to avoid modifying original
        df = df.copy()
        
        # If 'Website' exists but 'Name' doesn't, use Website as Name
        if 'Website' in df.columns and 'Name' not in df.columns:
            # Extract domain name from website URL for display
            df['Name'] = self.extract_domain_name(df['Website'])
        
        # Ensure required columns exist
        required_columns = ['Name', 'Career Page', 'Label']
        for col in required_columns:
            if col not in df.columns:
                CrawlerLogger.missing_column_warning(col)
                df[col] = 'N/A'
        
        # Add Description if missing
        if 'Description' not in df.columns:
            df['Description'] = 'N/A'
        
        # Filter by Active status if column exists
        if 'Active' in df.columns:
            # Filter only active entries
            active_count = len(df)
            df = df[df['Active'].str.lower() == 'active'].copy()
            CrawlerLogger.info_message(f"Filtered to {len(df)} active companies (out of {active_count} total)")
        
        return df

    def extract_domain_name(url: str) -> str:
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
    
    def export_to_sqlite(self, db_path: str = 'jobs.db', table_name: str = 'jobs'):
        """
        Export jobs to SQLite database
        
        Usage:
            pip install sqlite3  # (usually comes with Python)
            exporter.export_to_sqlite('jobs.db')
        """
        try:
            import sqlite3
            
            if not self.df is not None or not self.load_csv():
                return False
            
            conn = sqlite3.connect(db_path)
            
            # Create table and insert data
            self.df.to_sql(table_name, conn, if_exists='replace', index=False)
            
            # Create index on Job Link for faster lookups
            conn.execute(f"CREATE INDEX IF NOT EXISTS idx_job_link ON {table_name} ([Job Link])")
            conn.execute(f"CREATE INDEX IF NOT EXISTS idx_company ON {table_name} (Company)")
            conn.execute(f"CREATE INDEX IF NOT EXISTS idx_scraped_date ON {table_name} ([Scraped Date])")
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Successfully exported {len(self.df)} jobs to SQLite: {db_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting to SQLite: {e}")
            return False
    
    def get_stats(self):
        """Get statistics about the jobs database"""
        if self.df is None:
            if not self.load_csv():
                return
        
        logger.info("\n" + "="*60)
        logger.info("📊 JOB DATABASE STATISTICS")
        logger.info("="*60)
        logger.info(f"Total jobs: {len(self.df)}")
        logger.info(f"Unique companies: {self.df['Company'].nunique()}")
        logger.info(f"Unique locations: {self.df['Location'].nunique()}")
        
        logger.info("\n📦 Jobs by ATS Platform:")
        platform_counts = self.df['Label'].value_counts()
        for platform, count in platform_counts.head(10).items():
            logger.info(f"   {platform}: {count}")
        
        logger.info("\n🏢 Top Companies by Job Count:")
        company_counts = self.df['Company'].value_counts()
        for company, count in company_counts.head(10).items():
            logger.info(f"   {company}: {count}")
        
        logger.info("="*60 + "\n")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Export jobs to different database systems')
    parser.add_argument('--csv', default='output/all_jobs.csv', help='Path to jobs CSV file')
    parser.add_argument('--stats', action='store_true', help='Show database statistics')
    parser.add_argument('--sqlite', metavar='DB_PATH', help='Export to SQLite database')
    parser.add_argument('--postgresql', metavar='CONNECTION_STRING', 
                       help='Export to PostgreSQL (e.g., postgresql://user:pass@localhost/db)')
    parser.add_argument('--mongodb', metavar='CONNECTION_STRING',
                       help='Export to MongoDB (e.g., mongodb://localhost:27017/)')
    parser.add_argument('--airtable', nargs=2, metavar=('API_KEY', 'BASE_ID'),
                       help='Export to Airtable (requires API key and base ID)')
    
    args = parser.parse_args()
    
    exporter = DataController(args.csv)
    
    if args.stats:
        exporter.get_stats()
    
    if args.sqlite:
        exporter.export_to_sqlite(args.sqlite)
    
    if args.postgresql:
        exporter.export_to_postgresql(args.postgresql)
    
    if args.mongodb:
        exporter.export_to_mongodb(args.mongodb)
    
    if args.airtable:
        api_key, base_id = args.airtable
        exporter.export_to_airtable(api_key, base_id)


if __name__ == '__main__':
    main()
