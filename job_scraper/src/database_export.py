"""
Database Integration Options for Job Crawler
Provides utilities for exporting to different database systems
"""

import pandas as pd
import logging
from typing import Optional
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseExporter:
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
    
    def export_to_postgresql(self, connection_string: str, table_name: str = 'jobs'):
        """
        Export jobs to PostgreSQL database
        
        Usage:
            pip install psycopg2-binary sqlalchemy
            connection_string = "postgresql://user:password@localhost:5432/jobsdb"
            exporter.export_to_postgresql(connection_string)
        """
        try:
            from sqlalchemy import create_engine
            
            if not self.df is not None or not self.load_csv():
                return False
            
            engine = create_engine(connection_string)
            
            # Write to database
            self.df.to_sql(table_name, engine, if_exists='replace', index=False)
            
            logger.info(f"✅ Successfully exported {len(self.df)} jobs to PostgreSQL")
            return True
            
        except ImportError:
            logger.error("Install required packages: pip install psycopg2-binary sqlalchemy")
            return False
        except Exception as e:
            logger.error(f"Error exporting to PostgreSQL: {e}")
            return False
    
    def export_to_airtable(self, api_key: str, base_id: str, table_name: str = 'Jobs'):
        """
        Export jobs to Airtable
        
        Usage:
            pip install pyairtable
            api_key = 'your_airtable_api_key'
            base_id = 'your_base_id'
            exporter.export_to_airtable(api_key, base_id)
        """
        try:
            from pyairtable import Table
            
            if not self.df is not None or not self.load_csv():
                return False
            
            table = Table(api_key, base_id, table_name)
            
            # Convert DataFrame to list of dicts
            records = self.df.to_dict('records')
            
            # Airtable has a 10-record limit per batch, so we batch it
            batch_size = 10
            total_uploaded = 0
            
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                # Format for Airtable (wrap in 'fields' key)
                airtable_batch = [{'fields': record} for record in batch]
                table.batch_create(airtable_batch)
                total_uploaded += len(batch)
                logger.info(f"Uploaded {total_uploaded}/{len(records)} jobs to Airtable")
            
            logger.info(f"✅ Successfully exported {len(records)} jobs to Airtable")
            return True
            
        except ImportError:
            logger.error("Install required package: pip install pyairtable")
            return False
        except Exception as e:
            logger.error(f"Error exporting to Airtable: {e}")
            return False
    
    def export_to_mongodb(self, connection_string: str, db_name: str = 'jobcrawler', 
                         collection_name: str = 'jobs'):
        """
        Export jobs to MongoDB
        
        Usage:
            pip install pymongo
            connection_string = "mongodb://localhost:27017/"
            exporter.export_to_mongodb(connection_string)
        """
        try:
            from pymongo import MongoClient
            
            if not self.df is not None or not self.load_csv():
                return False
            
            client = MongoClient(connection_string)
            db = client[db_name]
            collection = db[collection_name]
            
            # Convert DataFrame to list of dicts
            records = self.df.to_dict('records')
            
            # Clear existing data and insert new (or use update_many with upsert)
            collection.delete_many({})
            collection.insert_many(records)
            
            # Create indexes
            collection.create_index('Job Link')
            collection.create_index('Company')
            collection.create_index('Scraped Date')
            
            logger.info(f"✅ Successfully exported {len(records)} jobs to MongoDB")
            return True
            
        except ImportError:
            logger.error("Install required package: pip install pymongo")
            return False
        except Exception as e:
            logger.error(f"Error exporting to MongoDB: {e}")
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
    
    exporter = DatabaseExporter(args.csv)
    
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
