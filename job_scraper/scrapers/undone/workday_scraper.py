"""
Workday ATS Scraper (myworkdayjobs.com)
Scrapes job listings from Workday career pages.
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


class WorkdayScraper:
    """Scraper for Workday ATS platform (myworkdayjobs.com)"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9'
        })
    
    def scrape_jobs(self, url: str, company_name: str, company_description: str, label: str) -> List[Dict]:
        """
        Scrape jobs from a Workday career page
        
        Args:
            url: URL of the career page (typically company.myworkdayjobs.com)
            company_name: Name of the company
            company_description: Description of the company
            label: Label/ATS platform identifier
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        
        try:
            logger.info(f"Scraping Workday jobs from: {url}")
            
            # Workday URLs are typically:
            # - https://company.myworkdayjobs.com/company-site
            # - https://company.myworkdayjobs.com/en-US/company-site
            
            # Try API endpoint first (Workday has a GraphQL API)
            api_jobs = self._try_api_scrape(url, company_name, company_description, label)
            if api_jobs:
                return api_jobs
            
            # Fallback to HTML scraping
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try to find embedded JSON data
            json_jobs = self._extract_json_data(soup, url, company_name, company_description, label)
            if json_jobs:
                return json_jobs
            
            # Method 1: Look for Workday-specific job list items
            job_elements = soup.find_all('li', class_=re.compile(r'job|position|css-', re.I))
            
            if not job_elements:
                # Method 2: Look for data-automation attributes (Workday uses these)
                job_elements = soup.find_all(attrs={'data-automation-id': re.compile(r'job|posting', re.I)})
            
            if not job_elements:
                # Method 3: Look for links containing job postings
                job_elements = soup.find_all('a', href=re.compile(r'/job/', re.I))
            
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
            logger.error(f"Error fetching Workday page {url}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error scraping Workday jobs: {e}")
            return []
    
    def _try_api_scrape(self, url: str, company_name: str, company_description: str, label: str) -> List[Dict]:
        """Try to scrape using Workday API/GraphQL endpoint"""
        try:
            # Extract company identifier from URL
            if '.myworkdayjobs.com' not in url:
                return []
            
            # Parse the URL to get company and site
            parts = url.split('.myworkdayjobs.com')
            company_id = parts[0].split('://')[-1]
            site_path = parts[1].strip('/') if len(parts) > 1 else ''
            
            # Remove language code if present (e.g., /en-US/)
            site_parts = [p for p in site_path.split('/') if p and not re.match(r'^[a-z]{2}-[A-Z]{2}$', p)]
            site_id = site_parts[0] if site_parts else ''
            
            # Try Workday's search API endpoint
            api_url = f"https://{company_id}.myworkdayjobs.com/wday/cxs/{company_id}/{site_id}/jobs"
            
            # Workday uses a POST request with search parameters
            payload = {
                "appliedFacets": {},
                "limit": 20,
                "offset": 0,
                "searchText": ""
            }
            
            response = self.session.post(api_url, json=payload, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                jobs = []
                
                # Workday returns jobs in jobPostings array
                job_postings = data.get('jobPostings', [])
                
                for job in job_postings:
                    # Extract title
                    title = job.get('title', 'N/A')
                    
                    # Extract location
                    location = 'N/A'
                    locations = job.get('locationsText', '')
                    if locations:
                        location = locations
                    
                    # Extract job link
                    job_id = job.get('bulletFields', [])
                    external_path = job.get('externalPath', '')
                    job_link = f"https://{company_id}.myworkdayjobs.com{external_path}" if external_path else url
                    
                    # Extract posted date
                    posted_on = job.get('postedOn', 'N/A')
                    
                    # Extract job type
                    time_type = job.get('timeType', 'N/A')
                    
                    job_data = {
                        'Job Title': title,
                        'Job Description': 'N/A',  # Not available in list view
                        'Job Type': time_type,
                        'Company': company_name,
                        'Company Description': company_description,
                        'Job Link': job_link,
                        'Location': location,
                        'Department': 'N/A',
                        'Salary Range': 'N/A',
                        'Label': label,
                        'Post Date': posted_on,
                        'Scraped Date': datetime.now().strftime('%Y-%m-%d')
                    }
                    jobs.append(job_data)
                
                if jobs:
                    logger.info(f"Successfully scraped {len(jobs)} jobs from Workday API")
                    return jobs
        
        except Exception as e:
            logger.debug(f"Workday API scraping not available: {e}")
        
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
                        
                        job_data = {
                            'Job Title': title,
                            'Job Description': self._clean_description(job.get('description', 'N/A')),
                            'Job Type': job.get('employmentType', 'N/A'),
                            'Company': company_name,
                            'Company Description': company_description,
                            'Job Link': job.get('url', base_url),
                            'Location': location,
                            'Department': 'N/A',
                            'Salary Range': 'N/A',
                            'Label': label,
                            'Post Date': job.get('datePosted', 'N/A'),
                            'Scraped Date': datetime.now().strftime('%Y-%m-%d')
                        }
                        
                        jobs.append(job_data)
                
                except json.JSONDecodeError:
                    continue
            
            # Look for embedded Workday data
            if not jobs:
                scripts = soup.find_all('script')
                for script in scripts:
                    if script.string and ('jobPostings' in script.string or 'jobs' in script.string):
                        try:
                            # Try to extract JSON data
                            json_match = re.search(r'jobPostings["\s:=]+(\[.*?\])', script.string, re.DOTALL)
                            if json_match:
                                jobs_data = json.loads(json_match.group(1))
                                for job in jobs_data:
                                    job_data = {
                                        'Job Title': job.get('title', job.get('name', 'N/A')),
                                        'Job Description': self._clean_description(job.get('description', 'N/A')),
                                        'Job Type': job.get('timeType', job.get('type', 'N/A')),
                                        'Company': company_name,
                                        'Company Description': company_description,
                                        'Job Link': job.get('url', job.get('externalPath', base_url)),
                                        'Location': job.get('locationsText', job.get('location', 'N/A')),
                                        'Department': 'N/A',
                                        'Salary Range': 'N/A',
                                        'Label': label,
                                        'Post Date': job.get('postedOn', 'N/A'),
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
        title_element = element.find(['h2', 'h3', 'h4', 'a'], attrs={'data-automation-id': 'jobTitle'})
        if not title_element:
            title_element = element.find(['h2', 'h3', 'h4', 'a'], class_=re.compile(r'title|name', re.I))
        if not title_element:
            title_element = element.find('a')
        
        if not title_element:
            return None
        
        title = title_element.get_text(strip=True)
        
        # Skip if title is too short or looks like navigation
        if len(title) < 3 or title.lower() in ['jobs', 'careers', 'openings', 'back', 'home', 'search']:
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
        location_element = element.find(attrs={'data-automation-id': 'location'})
        if not location_element:
            location_element = element.find(['span', 'div', 'p'], class_=re.compile(r'location|city', re.I))
        if location_element:
            location = location_element.get_text(strip=True)
        
        # Extract posted date
        post_date = 'N/A'
        date_element = element.find(attrs={'data-automation-id': 'postedOn'})
        if not date_element:
            date_element = element.find(['span', 'div', 'time'], class_=re.compile(r'posted|date', re.I))
        if date_element:
            post_date = date_element.get_text(strip=True)
        
        # Extract job type
        job_type = 'N/A'
        type_element = element.find(attrs={'data-automation-id': 'timeType'})
        if not type_element:
            type_element = element.find(['span', 'div'], class_=re.compile(r'type|employment', re.I))
        if type_element:
            job_type = type_element.get_text(strip=True)
        
        job_data = {
            'Job Title': title,
            'Job Description': 'N/A',  # Workday doesn't show descriptions in list view
            'Job Type': job_type,
            'Company': company_name,
            'Company Description': company_description,
            'Job Link': job_link,
            'Location': location,
            'Department': 'N/A',
            'Salary Range': 'N/A',
            'Label': label,
            'Post Date': post_date,
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
    scraper = WorkdayScraper()
    
    # Example URL (replace with actual Workday URL)
    test_url = "https://example.myworkdayjobs.com/example-careers"
    test_company = "Example Company"
    test_description = "A test company"
    
    jobs = scraper.scrape_jobs(test_url, test_company, test_description, "myworkdayjobs")
    
    print(f"\nFound {len(jobs)} jobs")
    for job in jobs:
        print(f"- {job['Job Title']} | {job['Location']} | {job['Job Link']}")
