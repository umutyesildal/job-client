"""
Teamtailor Job Scraper
Scrapes job listings from Teamtailor ATS platform
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import logging
from datetime import datetime
from typing import List, Dict, Optional
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TeamtailorScraper:
    """Scraper for Teamtailor job boards"""
    
    def __init__(self, delay: float = 2.0):
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
    
    def scrape_jobs(self, url: str, company_name: str = "", company_description: str = "", label: str = "") -> List[Dict]:
        """Scrape all jobs from Teamtailor job board"""
        logger.info(f"Scraping Teamtailor job board: {url}")
        jobs = []
        
        try:
            # Try API endpoint first
            company_slug = url.rstrip('/').split('/')[-1]
            api_url = f"https://career.teamtailor.com/jobs.json?company={company_slug}"
            
            try:
                api_response = self.session.get(api_url, timeout=15)
                if api_response.status_code == 200:
                    return self._parse_api_response(api_response.json(), company_name, company_description, label)
            except:
                pass
            
            # Fall back to HTML parsing
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            job_items = soup.find_all(['a', 'li'], class_=lambda x: x and ('job' in x.lower() or 'position' in x.lower()))
            
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
            logger.error(f"Error scraping Teamtailor board: {e}")
        
        return jobs
    
    def _parse_api_response(self, data: dict, company_name: str, company_description: str, label: str) -> List[Dict]:
        """Parse jobs from Teamtailor API response"""
        jobs = []
        
        for job_data in data.get('jobs', []):
            job = {
                'Job Title': job_data.get('title', ''),
                'Job Description': '',
                'Job Type': '',
                'Company': company_name,
                'Company Description': company_description,
                'Job Link': job_data.get('links', {}).get('careersite_job_url', ''),
                'Location': ', '.join([loc.get('name', '') for loc in job_data.get('locations', [])]),
                'Department': job_data.get('department', {}).get('name', ''),
                'Salary Range': '',
                'Label': label,
                'Post Date': job_data.get('created_at', '')[:10] if job_data.get('created_at') else '',
                'Scraped Date': datetime.now().strftime('%Y-%m-%d')
            }
            jobs.append(job)
        
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
        
        title = item.find(['h2', 'h3', 'h4', 'span'], class_=lambda x: x and 'title' in x.lower())
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
        
        location = item.find(['span', 'div'], class_=lambda x: x and 'location' in x.lower())
        if location:
            job['Location'] = location.get_text(strip=True)
        
        dept = item.find(['span', 'div'], class_=lambda x: x and 'department' in x.lower())
        if dept:
            job['Department'] = dept.get_text(strip=True)
        
        return job
    
    def save_to_csv(self, jobs: List[Dict], output_file: str = 'teamtailor_jobs.csv'):
        """Save jobs to CSV file"""
        if not jobs:
            logger.warning("No jobs to save")
            return
        
        df = pd.DataFrame(jobs)
        df.to_csv(output_file, index=False)
        logger.info(f"Saved {len(jobs)} jobs to {output_file}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Scrape jobs from Teamtailor job board')
    parser.add_argument('url', help='Teamtailor job board URL')
    parser.add_argument('-c', '--company', default='', help='Company name')
    parser.add_argument('-d', '--description', default='', help='Company description')
    parser.add_argument('-l', '--label', default='', help='Company label')
    parser.add_argument('-o', '--output', default='teamtailor_jobs.csv', help='Output CSV file')
    
    args = parser.parse_args()
    
    scraper = TeamtailorScraper()
    jobs = scraper.scrape_jobs(args.url, args.company, args.description, args.label)
    scraper.save_to_csv(jobs, args.output)


if __name__ == '__main__':
    main()
