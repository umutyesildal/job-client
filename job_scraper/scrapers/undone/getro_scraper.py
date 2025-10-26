"""
Getro ATS Scraper
Scrapes job listings from Getro career pages.
"""

import requests
from bs4 import BeautifulSoup
import logging
import time
from datetime import datetime
from typing import List, Dict, Optional
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GetroScraper:
    """Scraper for Getro ATS platform"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def scrape_jobs(self, url: str, company_name: str, company_description: str, label: str) -> List[Dict]:
        """
        Scrape jobs from a Getro career page
        
        Args:
            url: URL of the career page
            company_name: Name of the company
            company_description: Description of the company
            label: Label/ATS platform identifier
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        
        try:
            logger.info(f"Scraping Getro jobs from: {url}")
            
            # Getro URLs can be:
            # - https://jobs.getro.com/company-name
            # - https://app.getro.com/companies/company-name/jobs
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try API endpoint first (if available)
            api_jobs = self._try_api_scrape(url, company_name, company_description, label)
            if api_jobs:
                return api_jobs
            
            # Method 1: Look for job cards/items with common Getro patterns
            job_elements = soup.find_all(['div', 'a'], class_=re.compile(r'job|position|opening|role', re.I))
            
            if not job_elements:
                # Method 2: Look for links containing job/position/role
                job_elements = soup.find_all('a', href=re.compile(r'/(job|position|opening|role)', re.I))
            
            if not job_elements:
                # Method 3: Look for specific Getro structure
                job_elements = soup.find_all(['div', 'article'], attrs={'data-job-id': True})
            
            logger.info(f"Found {len(job_elements)} potential job elements")
            
            for element in job_elements:
                try:
                    job_data = self._extract_job_data(element, url, company_name, company_description, label)
                    if job_data and job_data.get('Job Title'):
                        jobs.append(job_data)
                        logger.info(f"Extracted job: {job_data['Job Title']}")
                except Exception as e:
                    logger.warning(f"Error extracting job data: {e}")
                    continue
            
            # Remove duplicates based on job link
            seen_links = set()
            unique_jobs = []
            for job in jobs:
                if job['Job Link'] not in seen_links:
                    seen_links.add(job['Job Link'])
                    unique_jobs.append(job)
            
            logger.info(f"Successfully scraped {len(unique_jobs)} unique jobs from {url}")
            return unique_jobs
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Getro page {url}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error scraping Getro jobs: {e}")
            return []
    
    def _try_api_scrape(self, url: str, company_name: str, company_description: str, label: str) -> List[Dict]:
        """Try to scrape using Getro API if available"""
        try:
            # Extract company identifier from URL
            company_id = None
            if 'jobs.getro.com/' in url:
                company_id = url.split('jobs.getro.com/')[-1].strip('/')
            elif 'app.getro.com/companies/' in url:
                parts = url.split('app.getro.com/companies/')[-1].split('/')
                if parts:
                    company_id = parts[0]
            
            if not company_id:
                return []
            
            # Try Getro API endpoint
            api_url = f"https://api.getro.com/v1/companies/{company_id}/jobs"
            response = self.session.get(api_url, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                jobs = []
                
                job_list = data if isinstance(data, list) else data.get('jobs', [])
                
                for job in job_list:
                    job_data = {
                        'Job Title': job.get('title', 'N/A'),
                        'Job Description': self._clean_description(job.get('description', 'N/A')),
                        'Job Type': job.get('employment_type', 'N/A'),
                        'Company': company_name,
                        'Company Description': company_description,
                        'Job Link': job.get('url', job.get('apply_url', url)),
                        'Location': self._extract_location(job),
                        'Department': job.get('department', job.get('team', 'N/A')),
                        'Salary Range': self._extract_salary(job),
                        'Label': label,
                        'Post Date': job.get('posted_at', job.get('created_at', 'N/A')),
                        'Scraped Date': datetime.now().strftime('%Y-%m-%d')
                    }
                    jobs.append(job_data)
                
                if jobs:
                    logger.info(f"Successfully scraped {len(jobs)} jobs from Getro API")
                    return jobs
        
        except Exception as e:
            logger.debug(f"API scraping not available: {e}")
        
        return []
    
    def _extract_job_data(self, element, base_url: str, company_name: str, 
                         company_description: str, label: str) -> Optional[Dict]:
        """Extract job data from an HTML element"""
        
        # Extract title
        title_element = element.find(['h2', 'h3', 'h4', 'a'], class_=re.compile(r'title|name', re.I))
        if not title_element:
            title_element = element.find('a')
        
        if not title_element:
            return None
        
        title = title_element.get_text(strip=True)
        
        # Skip if title is too short or looks like navigation
        if len(title) < 3 or title.lower() in ['jobs', 'careers', 'openings', 'back', 'home']:
            return None
        
        # Extract link
        link_element = element if element.name == 'a' else element.find('a')
        job_link = link_element.get('href', '') if link_element else ''
        
        if job_link and not job_link.startswith('http'):
            if job_link.startswith('/'):
                from urllib.parse import urljoin
                job_link = urljoin(base_url, job_link)
            else:
                job_link = f"{base_url.rstrip('/')}/{job_link}"
        
        if not job_link:
            job_link = base_url
        
        # Extract location
        location = 'N/A'
        location_element = element.find(['span', 'div', 'p'], class_=re.compile(r'location|city|place', re.I))
        if location_element:
            location = location_element.get_text(strip=True)
        else:
            # Look for location in text
            text = element.get_text()
            location_match = re.search(r'(?:Location|City|Office):\s*([^|•\n]+)', text, re.I)
            if location_match:
                location = location_match.group(1).strip()
        
        # Extract department
        department = 'N/A'
        dept_element = element.find(['span', 'div', 'p'], class_=re.compile(r'department|team|category', re.I))
        if dept_element:
            department = dept_element.get_text(strip=True)
        
        # Extract job type
        job_type = 'N/A'
        type_element = element.find(['span', 'div', 'p'], class_=re.compile(r'type|employment', re.I))
        if type_element:
            job_type = type_element.get_text(strip=True)
        
        # Extract description
        description = 'N/A'
        desc_element = element.find(['div', 'p'], class_=re.compile(r'description|summary|content', re.I))
        if desc_element:
            description = self._clean_description(desc_element.get_text(strip=True))
        
        job_data = {
            'Job Title': title,
            'Job Description': description,
            'Job Type': job_type,
            'Company': company_name,
            'Company Description': company_description,
            'Job Link': job_link,
            'Location': location,
            'Department': department,
            'Salary Range': 'N/A',
            'Label': label,
            'Post Date': 'N/A',
            'Scraped Date': datetime.now().strftime('%Y-%m-%d')
        }
        
        return job_data
    
    def _extract_location(self, job: Dict) -> str:
        """Extract location from job data"""
        location = job.get('location', job.get('office_location', ''))
        
        if isinstance(location, dict):
            city = location.get('city', '')
            country = location.get('country', '')
            return f"{city}, {country}".strip(', ') if city or country else 'N/A'
        
        return location if location else 'N/A'
    
    def _extract_salary(self, job: Dict) -> str:
        """Extract salary information from job data"""
        if 'salary' in job:
            salary = job['salary']
            if isinstance(salary, dict):
                min_sal = salary.get('min', '')
                max_sal = salary.get('max', '')
                currency = salary.get('currency', '')
                if min_sal and max_sal:
                    return f"{currency} {min_sal} - {max_sal}".strip()
        
        if 'salary_range' in job:
            return str(job['salary_range'])
        
        return 'N/A'
    
    def _clean_description(self, description: str) -> str:
        """Clean and truncate job description"""
        if not description or description == 'N/A':
            return 'N/A'
        
        # Remove extra whitespace
        description = re.sub(r'\s+', ' ', description)
        
        # Truncate if too long
        max_length = 500
        if len(description) > max_length:
            description = description[:max_length] + '...'
        
        return description.strip()


if __name__ == "__main__":
    # Test the scraper
    scraper = GetroScraper()
    
    # Example URL (replace with actual Getro URL)
    test_url = "https://jobs.getro.com/example-company"
    test_company = "Example Company"
    test_description = "A test company"
    
    jobs = scraper.scrape_jobs(test_url, test_company, test_description, "getro")
    
    print(f"\nFound {len(jobs)} jobs")
    for job in jobs:
        print(f"- {job['Job Title']} | {job['Location']} | {job['Job Link']}")
