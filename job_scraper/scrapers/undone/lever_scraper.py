"""
Lever Job Scraper
Scrapes job listings from Lever ATS platform
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


class LeverScraper:
    """Scraper for Lever job boards"""
    
    def __init__(self, delay: float = 2.0):
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
    
    def scrape_jobs(self, url: str, company_name: str = "", company_description: str = "", label: str = "") -> List[Dict]:
        """
        Scrape all jobs from Lever job board
        
        Args:
            url: Lever job board URL (e.g., https://jobs.lever.co/company)
            company_name: Company name
            company_description: Company description
            label: Company label/category
            
        Returns:
            List of job dictionaries
        """
        logger.info(f"Scraping Lever job board: {url}")
        jobs = []
        
        try:
            # Extract company slug from URL
            company_slug = url.rstrip('/').split('/')[-1]
            
            # Try Lever's API endpoint
            api_url = f"https://api.lever.co/v0/postings/{company_slug}?mode=json"
            
            try:
                api_response = self.session.get(api_url, timeout=15)
                if api_response.status_code == 200:
                    return self._parse_api_response(api_response.json(), company_name, company_description, label)
            except Exception as e:
                logger.debug(f"API failed, falling back to HTML: {e}")
            
            # Fall back to HTML parsing
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Lever uses posting class for job listings
            job_postings = soup.find_all('div', class_='posting')
            
            logger.info(f"Found {len(job_postings)} job postings")
            
            for posting in job_postings:
                try:
                    job = self._extract_job_from_posting(posting, url, company_name, company_description, label)
                    if job:
                        jobs.append(job)
                        time.sleep(self.delay)
                except Exception as e:
                    logger.error(f"Error extracting job: {e}")
                    continue
            
            logger.info(f"Successfully scraped {len(jobs)} jobs")
            
        except Exception as e:
            logger.error(f"Error scraping Lever board: {e}")
        
        return jobs
    
    def _parse_api_response(self, data: List[Dict], company_name: str, company_description: str, label: str) -> List[Dict]:
        """Parse jobs from Lever API response"""
        jobs = []
        
        for job_data in data:
            job = {
                'Job Title': job_data.get('text', ''),
                'Job Description': job_data.get('description', '')[:500],  # Limit length
                'Job Type': job_data.get('categories', {}).get('commitment', ''),
                'Company': company_name,
                'Company Description': company_description,
                'Job Link': job_data.get('hostedUrl', ''),
                'Location': job_data.get('categories', {}).get('location', ''),
                'Department': job_data.get('categories', {}).get('team', ''),
                'Salary Range': '',
                'Label': label,
                'Post Date': job_data.get('createdAt', '')[:10] if job_data.get('createdAt') else '',
                'Scraped Date': datetime.now().strftime('%Y-%m-%d')
            }
            jobs.append(job)
        
        return jobs
    
    def _extract_job_from_posting(self, posting, base_url: str, company_name: str, company_description: str, label: str) -> Optional[Dict]:
        """Extract job data from a posting element"""
        
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
        
        # Get job title
        title = posting.find('h5')
        if not title:
            title = posting.find('a', class_='posting-title')
        if title:
            job['Job Title'] = title.get_text(strip=True)
        
        # Get job link
        link = posting.find('a', class_='posting-btn-submit')
        if not link:
            link = posting.find('a', href=True)
        if link and link.get('href'):
            href = link.get('href')
            job['Job Link'] = href if href.startswith('http') else requests.compat.urljoin(base_url, href)
        
        # Get location
        location = posting.find('span', class_='sort-by-location')
        if not location:
            location = posting.find('span', class_='location')
        if location:
            job['Location'] = location.get_text(strip=True)
        
        # Get department/team
        team = posting.find('span', class_='sort-by-team')
        if not team:
            team = posting.find('span', class_='department')
        if team:
            job['Department'] = team.get_text(strip=True)
        
        # Get commitment (job type)
        commitment = posting.find('span', class_='sort-by-commitment')
        if commitment:
            job['Job Type'] = commitment.get_text(strip=True)
        
        return job if job['Job Title'] else None
    
    def save_to_csv(self, jobs: List[Dict], output_file: str = 'lever_jobs.csv'):
        """Save jobs to CSV file"""
        if not jobs:
            logger.warning("No jobs to save")
            return
        
        df = pd.DataFrame(jobs)
        df.to_csv(output_file, index=False)
        logger.info(f"Saved {len(jobs)} jobs to {output_file}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Scrape jobs from Lever job board')
    parser.add_argument('url', help='Lever job board URL')
    parser.add_argument('-c', '--company', default='', help='Company name')
    parser.add_argument('-d', '--description', default='', help='Company description')
    parser.add_argument('-l', '--label', default='', help='Company label')
    parser.add_argument('-o', '--output', default='lever_jobs.csv', help='Output CSV file')
    
    args = parser.parse_args()
    
    scraper = LeverScraper()
    jobs = scraper.scrape_jobs(args.url, args.company, args.description, args.label)
    scraper.save_to_csv(jobs, args.output)


if __name__ == '__main__':
    main()
