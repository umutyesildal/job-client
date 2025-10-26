"""
Rippling Job Scraper
Scrapes job listings from Rippling ATS platform
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import logging
from datetime import datetime
from typing import List, Dict, Optional
import re

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RipplingScraper:
    """Scraper for Rippling job boards"""
    
    def __init__(self, delay: float = 2.0):
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
    
    def scrape_jobs(self, url: str, company_name: str = "", company_description: str = "", label: str = "") -> List[Dict]:
        """Scrape all jobs from Rippling job board"""
        logger.info(f"Scraping Rippling job board: {url}")
        jobs = []
        
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            job_items = soup.find_all(['a', 'div', 'li'], class_=re.compile(r'job|position|opening', re.I))
            
            logger.info(f"Found {len(job_items)} job postings")
            
            for item in job_items:
                try:
                    job = self._extract_job_data(item, url, company_name, company_description, label)
                    if job and job['Job Title']:
                        jobs.append(job)
                        time.sleep(self.delay)
                except Exception as e:
                    logger.error(f"Error extracting job: {e}")
                    continue
            
            logger.info(f"Successfully scraped {len(jobs)} jobs")
            
        except Exception as e:
            logger.error(f"Error scraping Rippling board: {e}")
        
        return jobs
    
    def _extract_job_data(self, item, base_url: str, company_name: str, company_description: str, label: str) -> Optional[Dict]:
        """Extract job data from a job item"""
        
        job = {
            'Job Title': '',
            'Job Description': '',
            'Job Type': '',
            'Company': company_name,
            'Company Description': company_description,
            'Job Link': '',
            'Location': '',
            'Department': '',
            'Salary Range': '',
            'Label': label,
            'Post Date': '',
            'Scraped Date': datetime.now().strftime('%Y-%m-%d')
        }
        
        title = item.find(['h2', 'h3', 'h4', 'span'], class_=re.compile(r'title|name', re.I))
        if title:
            job['Job Title'] = title.get_text(strip=True)
        elif item.name == 'a':
            job['Job Title'] = item.get_text(strip=True).split('\n')[0].strip()
        
        if item.name == 'a' and item.get('href'):
            href = item.get('href')
            job['Job Link'] = href if href.startswith('http') else requests.compat.urljoin(base_url, href)
        else:
            link = item.find('a', href=True)
            if link:
                href = link.get('href')
                job['Job Link'] = href if href.startswith('http') else requests.compat.urljoin(base_url, href)
        
        location = item.find(['span', 'div'], class_=re.compile(r'location', re.I))
        if location:
            job['Location'] = location.get_text(strip=True)
        
        dept = item.find(['span', 'div'], class_=re.compile(r'department|team', re.I))
        if dept:
            job['Department'] = dept.get_text(strip=True)
        
        return job
    
    def save_to_csv(self, jobs: List[Dict], output_file: str = 'rippling_jobs.csv'):
        """Save jobs to CSV file"""
        if not jobs:
            logger.warning("No jobs to save")
            return
        
        df = pd.DataFrame(jobs)
        df.to_csv(output_file, index=False)
        logger.info(f"Saved {len(jobs)} jobs to {output_file}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Scrape jobs from Rippling job board')
    parser.add_argument('url', help='Rippling job board URL')
    parser.add_argument('-c', '--company', default='', help='Company name')
    parser.add_argument('-d', '--description', default='', help='Company description')
    parser.add_argument('-l', '--label', default='', help='Company label')
    parser.add_argument('-o', '--output', default='rippling_jobs.csv', help='Output CSV file')
    
    args = parser.parse_args()
    
    scraper = RipplingScraper()
    jobs = scraper.scrape_jobs(args.url, args.company, args.description, args.label)
    scraper.save_to_csv(jobs, args.output)


if __name__ == '__main__':
    main()
