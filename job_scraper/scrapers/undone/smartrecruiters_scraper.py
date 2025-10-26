"""
SmartRecruiters ATS Scraper
Scrapes job listings from SmartRecruiters career pages.
"""

import requests
from bs4 import BeautifulSoup
import logging
import time
from datetime import datetime
from typing import List, Dict, Optional
import re
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SmartRecruitarsScraper:
    """Scraper for SmartRecruiters ATS platform"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*'
        })
    
    def scrape_jobs(self, url: str, company_name: str, company_description: str, label: str) -> List[Dict]:
        """
        Scrape jobs from a SmartRecruiters career page
        
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
            logger.info(f"Scraping SmartRecruiters jobs from: {url}")
            
            # SmartRecruiters URLs are typically:
            # - https://careers.smartrecruiters.com/CompanyName
            # - https://jobs.smartrecruiters.com/CompanyName
            # - https://company-name.smartrecruiters.com
            
            # Try API endpoint first
            api_jobs = self._try_api_scrape(url, company_name, company_description, label)
            if api_jobs:
                return api_jobs
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try to find embedded JSON data
            json_jobs = self._extract_json_data(soup, url, company_name, company_description, label)
            if json_jobs:
                return json_jobs
            
            # Method 1: Look for SmartRecruiters-specific job containers
            job_elements = soup.find_all(['li', 'div', 'article'], class_=re.compile(r'job|position|opening|posting', re.I))
            
            if not job_elements:
                # Method 2: Look for data attributes
                job_elements = soup.find_all(attrs={'data-job-id': True})
            
            if not job_elements:
                # Method 3: Look for links containing smartrecruiters job URLs
                job_elements = soup.find_all('a', href=re.compile(r'smartrecruiters\.com/.*/job/', re.I))
            
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
            logger.error(f"Error fetching SmartRecruiters page {url}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error scraping SmartRecruiters jobs: {e}")
            return []
    
    def _try_api_scrape(self, url: str, company_name: str, company_description: str, label: str) -> List[Dict]:
        """Try to scrape using SmartRecruiters API if available"""
        try:
            # Extract company identifier from URL
            company_id = None
            
            if 'smartrecruiters.com/' in url:
                # Extract from URL like careers.smartrecruiters.com/CompanyName
                parts = url.split('smartrecruiters.com/')
                if len(parts) > 1:
                    company_id = parts[1].strip('/').split('/')[0]
            
            if not company_id:
                return []
            
            # Try SmartRecruiters public API
            api_url = f"https://api.smartrecruiters.com/v1/companies/{company_id}/postings"
            
            # Add query parameters for pagination
            params = {
                'limit': 100,
                'offset': 0
            }
            
            response = self.session.get(api_url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                jobs = []
                
                # SmartRecruiters returns content array
                postings = data.get('content', [])
                
                for posting in postings:
                    # Extract location
                    location = 'N/A'
                    job_location = posting.get('location', {})
                    if isinstance(job_location, dict):
                        city = job_location.get('city', '')
                        country = job_location.get('country', '')
                        location = f"{city}, {country}".strip(', ') if city or country else 'N/A'
                    
                    # Extract department
                    department = 'N/A'
                    dept = posting.get('department', {})
                    if isinstance(dept, dict):
                        department = dept.get('label', dept.get('name', 'N/A'))
                    
                    # Build job link
                    job_id = posting.get('id', '')
                    ref_number = posting.get('refNumber', '')
                    job_link = posting.get('applyUrl', '')
                    
                    if not job_link and job_id:
                        job_link = f"https://jobs.smartrecruiters.com/{company_id}/{job_id}"
                    if not job_link:
                        job_link = url
                    
                    # Extract employment type
                    employment_type = 'N/A'
                    type_code = posting.get('typeCode', '')
                    if type_code:
                        employment_type = posting.get('type', {}).get('label', type_code) if isinstance(posting.get('type'), dict) else type_code
                    
                    job_data = {
                        'Job Title': posting.get('name', posting.get('title', 'N/A')),
                        'Job Description': self._clean_description(posting.get('jobAd', {}).get('sections', {}).get('jobDescription', {}).get('text', 'N/A')),
                        'Job Type': employment_type,
                        'Company': company_name,
                        'Company Description': company_description,
                        'Job Link': job_link,
                        'Location': location,
                        'Department': department,
                        'Salary Range': 'N/A',
                        'Label': label,
                        'Post Date': posting.get('releasedDate', posting.get('updatedDate', 'N/A')),
                        'Scraped Date': datetime.now().strftime('%Y-%m-%d')
                    }
                    jobs.append(job_data)
                
                if jobs:
                    logger.info(f"Successfully scraped {len(jobs)} jobs from SmartRecruiters API")
                    return jobs
        
        except Exception as e:
            logger.debug(f"API scraping not available: {e}")
        
        return []
    
    def _extract_json_data(self, soup, base_url: str, company_name: str, 
                          company_description: str, label: str) -> List[Dict]:
        """Extract job data from JSON-LD or embedded JSON"""
        jobs = []
        
        try:
            # Look for JSON-LD structured data
            json_scripts = soup.find_all('script', type='application/ld+json')
            
            for script in json_scripts:
                try:
                    data = json.loads(script.string)
                    
                    # Handle different JSON-LD structures
                    job_postings = []
                    if isinstance(data, list):
                        job_postings = [item for item in data if item.get('@type') == 'JobPosting']
                    elif data.get('@type') == 'JobPosting':
                        job_postings = [data]
                    
                    for job in job_postings:
                        title = job.get('title', job.get('name', 'N/A'))
                        
                        # Extract location
                        location = 'N/A'
                        job_location = job.get('jobLocation', {})
                        if isinstance(job_location, dict):
                            address = job_location.get('address', {})
                            if isinstance(address, dict):
                                city = address.get('addressLocality', '')
                                country = address.get('addressCountry', '')
                                location = f"{city}, {country}".strip(', ') if city or country else 'N/A'
                        
                        # Extract salary
                        salary = 'N/A'
                        base_salary = job.get('baseSalary', {})
                        if isinstance(base_salary, dict):
                            value = base_salary.get('value', {})
                            if isinstance(value, dict):
                                min_val = value.get('minValue', '')
                                max_val = value.get('maxValue', '')
                                currency = value.get('currency', '')
                                if min_val and max_val:
                                    salary = f"{currency} {min_val} - {max_val}".strip()
                        
                        job_data = {
                            'Job Title': title,
                            'Job Description': self._clean_description(job.get('description', 'N/A')),
                            'Job Type': job.get('employmentType', 'N/A'),
                            'Company': company_name,
                            'Company Description': company_description,
                            'Job Link': job.get('url', base_url),
                            'Location': location,
                            'Department': job.get('department', 'N/A'),
                            'Salary Range': salary,
                            'Label': label,
                            'Post Date': job.get('datePosted', 'N/A'),
                            'Scraped Date': datetime.now().strftime('%Y-%m-%d')
                        }
                        
                        jobs.append(job_data)
                
                except json.JSONDecodeError:
                    continue
            
            # Look for embedded SmartRecruiters data
            if not jobs:
                scripts = soup.find_all('script')
                for script in scripts:
                    if script.string and ('postings' in script.string or 'jobs' in script.string):
                        try:
                            # Try to extract JSON data
                            json_match = re.search(r'postings["\s:=]+(\[.*?\])', script.string, re.DOTALL)
                            if not json_match:
                                json_match = re.search(r'jobs["\s:=]+(\[.*?\])', script.string, re.DOTALL)
                            
                            if json_match:
                                postings_data = json.loads(json_match.group(1))
                                for posting in postings_data:
                                    job_data = {
                                        'Job Title': posting.get('name', posting.get('title', 'N/A')),
                                        'Job Description': self._clean_description(posting.get('description', 'N/A')),
                                        'Job Type': posting.get('type', 'N/A'),
                                        'Company': company_name,
                                        'Company Description': company_description,
                                        'Job Link': posting.get('url', posting.get('applyUrl', base_url)),
                                        'Location': posting.get('location', 'N/A'),
                                        'Department': posting.get('department', 'N/A'),
                                        'Salary Range': 'N/A',
                                        'Label': label,
                                        'Post Date': posting.get('releasedDate', 'N/A'),
                                        'Scraped Date': datetime.now().strftime('%Y-%m-%d')
                                    }
                                    jobs.append(job_data)
                                break
                        except:
                            continue
        
        except Exception as e:
            logger.debug(f"Error extracting JSON data: {e}")
        
        return jobs
    
    def _extract_job_data(self, element, base_url: str, company_name: str, 
                         company_description: str, label: str) -> Optional[Dict]:
        """Extract job data from an HTML element"""
        
        # Extract title
        title_element = element.find(['h2', 'h3', 'h4', 'a'], class_=re.compile(r'title|name|position', re.I))
        if not title_element:
            title_element = element.find('a')
        
        if not title_element:
            return None
        
        title = title_element.get_text(strip=True)
        
        # Skip if title is too short or looks like navigation
        if len(title) < 3 or title.lower() in ['jobs', 'careers', 'openings', 'back', 'home', 'view all']:
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
        desc_element = element.find(['div', 'p'], class_=re.compile(r'description|summary|snippet', re.I))
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
    
    def _clean_description(self, description: str) -> str:
        """Clean and truncate job description"""
        if not description or description == 'N/A':
            return 'N/A'
        
        # Remove HTML tags
        description = re.sub(r'<[^>]+>', '', description)
        
        # Remove extra whitespace
        description = re.sub(r'\s+', ' ', description)
        
        # Truncate if too long
        max_length = 500
        if len(description) > max_length:
            description = description[:max_length] + '...'
        
        return description.strip()


if __name__ == "__main__":
    # Test the scraper
    scraper = SmartRecruitarsScraper()
    
    # Example URL (replace with actual SmartRecruiters URL)
    test_url = "https://careers.smartrecruiters.com/ExampleCompany"
    test_company = "Example Company"
    test_description = "A test company"
    
    jobs = scraper.scrape_jobs(test_url, test_company, test_description, "smartrecruiters")
    
    print(f"\nFound {len(jobs)} jobs")
    for job in jobs:
        print(f"- {job['Job Title']} | {job['Location']} | {job['Job Link']}")
