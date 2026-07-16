"""
Generic ATS Platform Scrapers
Template scrapers for: Gem, Join, Rippling, Softgarden, Teamtailor
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


class GenericATSScraper:
    """Generic scraper for ATS platforms"""
    
    def __init__(self, platform_name: str = "Generic", delay: float = 2.0):
        self.platform_name = platform_name
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
    
    def scrape_jobs(self, url: str, company_name: str = "", company_description: str = "", label: str = "") -> List[Dict]:
        """Scrape all jobs from job board"""
        logger.info(f"Scraping {self.platform_name} job board: {url}")
        jobs = []
        
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find job listings using common patterns
            job_elements = self._find_job_elements(soup)
            
            logger.info(f"Found {len(job_elements)} job postings")
            
            for element in job_elements:
                try:
                    job = self._extract_job_data(element, url, company_name, company_description, label)
                    if job and job['Job Title']:
                        jobs.append(job)
                        time.sleep(self.delay)
                except Exception as e:
                    logger.error(f"Error extracting job: {e}")
                    continue
            
            logger.info(f"Successfully scraped {len(jobs)} jobs")
            
        except Exception as e:
            logger.error(f"Error scraping job board: {e}")
        
        return jobs
    
    def _find_job_elements(self, soup):
        """Find job listing elements using common patterns"""
        # Try multiple selectors
        job_elements = []
        
        # Try common class patterns
        patterns = [
            {'class_': re.compile(r'job|posting|position|vacancy', re.I)},
            {'attrs': {'data-job': True}},
            {'attrs': {'data-posting': True}},
        ]
        
        for pattern in patterns:
            elements = soup.find_all(['div', 'li', 'a'], **pattern)
            if elements:
                job_elements.extend(elements)
                break
        
        # Remove duplicates
        seen = set()
        unique_elements = []
        for elem in job_elements:
            elem_id = id(elem)
            if elem_id not in seen:
                seen.add(elem_id)
                unique_elements.append(elem)
        
        return unique_elements
    
    def _extract_job_data(self, element, base_url: str, company_name: str, company_description: str, label: str) -> Optional[Dict]:
        """Extract job data from an element"""
        
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
        
        # Extract title
        title_elem = element.find(['h2', 'h3', 'h4', 'h5'], class_=re.compile(r'title|name|job', re.I))
        if title_elem:
            job['Job Title'] = title_elem.get_text(strip=True)
        elif element.name == 'a':
            job['Job Title'] = element.get_text(strip=True).split('\n')[0].strip()
        
        # Extract link
        if element.name == 'a' and element.get('href'):
            href = element.get('href')
            job['Job Link'] = href if href.startswith('http') else requests.compat.urljoin(base_url, href)
        else:
            link = element.find('a', href=True)
            if link:
                href = link.get('href')
                job['Job Link'] = href if href.startswith('http') else requests.compat.urljoin(base_url, href)
        
        # Extract location
        location_elem = element.find(['span', 'div', 'p'], class_=re.compile(r'location', re.I))
        if location_elem:
            job['Location'] = location_elem.get_text(strip=True)
        
        # Extract department
        dept_elem = element.find(['span', 'div', 'p'], class_=re.compile(r'department|team', re.I))
        if dept_elem:
            job['Department'] = dept_elem.get_text(strip=True)
        
        # Extract job type
        type_elem = element.find(['span', 'div', 'p'], class_=re.compile(r'type|commitment|employment', re.I))
        if type_elem:
            job['Job Type'] = type_elem.get_text(strip=True)
        
        return job
    
    def save_to_csv(self, jobs: List[Dict], output_file: str = 'jobs.csv'):
        """Save jobs to CSV file"""
        if not jobs:
            logger.warning("No jobs to save")
            return
        
        df = pd.DataFrame(jobs)
        df.to_csv(output_file, index=False)
        logger.info(f"Saved {len(jobs)} jobs to {output_file}")


# Create specific scrapers for each platform
class GemScraper(GenericATSScraper):
    def __init__(self, delay: float = 2.0):
        super().__init__("Gem", delay)


class JoinScraper(GenericATSScraper):
    def __init__(self, delay: float = 2.0):
        super().__init__("Join", delay)


class RipplingScraper(GenericATSScraper):
    def __init__(self, delay: float = 2.0):
        super().__init__("Rippling", delay)


class SoftgardenScraper(GenericATSScraper):
    def __init__(self, delay: float = 2.0):
        super().__init__("Softgarden", delay)


class TeamtailorScraper(GenericATSScraper):
    def __init__(self, delay: float = 2.0):
        super().__init__("Teamtailor", delay)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Scrape jobs from ATS platforms')
    parser.add_argument('platform', choices=['gem', 'join', 'rippling', 'softgarden', 'teamtailor'], 
                       help='ATS platform')
    parser.add_argument('url', help='Job board URL')
    parser.add_argument('-c', '--company', default='', help='Company name')
    parser.add_argument('-d', '--description', default='', help='Company description')
    parser.add_argument('-l', '--label', default='', help='Company label')
    parser.add_argument('-o', '--output', help='Output CSV file')
    
    args = parser.parse_args()
    
    # Select scraper based on platform
    scrapers = {
        'gem': GemScraper(),
        'join': JoinScraper(),
        'rippling': RipplingScraper(),
        'softgarden': SoftgardenScraper(),
        'teamtailor': TeamtailorScraper()
    }
    
    scraper = scrapers[args.platform]
    output_file = args.output or f'{args.platform}_jobs.csv'
    
    jobs = scraper.scrape_jobs(args.url, args.company, args.description, args.label)
    scraper.save_to_csv(jobs, output_file)


if __name__ == '__main__':
    main()
