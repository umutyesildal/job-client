"""
Stripe Scraper
Scrapes job listings from Stripe's jobs search API
"""

import requests
import logging
import time
from typing import List, Dict
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class StripeScraper:
    """
    Scraper for Stripe Careers (https://stripe.com/jobs)
    
    Stripe uses a paginated search API with client-side rendering.
    URL format: https://stripe.com/jobs/search?view_type=list
    
    API supports:
    - Pagination via skip/limit parameters
    - Location filtering (office and remote)
    - Department filtering
    - Tag filtering
    """
    
    BASE_API_URL = "https://stripe.com/jobs/search"
    BASE_JOB_URL = "https://stripe.com/jobs"
    
    def __init__(self, delay: float = 1.0):
        self.delay = delay
        self.session = requests.Session()
    
    def _extract_filters_from_url(self, url: str) -> Dict:
        """
        Extract filters from Stripe careers URL
        
        Args:
            url: Stripe careers URL
            
        Returns:
            Dictionary of filters
        """
        filters = {}
        
        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            
            # Extract location filters
            if 'officelocationids' in params:
                filters['officelocationids'] = params['officelocationids'][0]
            
            if 'remotelocationids' in params:
                filters['remotelocationids'] = params['remotelocationids'][0]
            
            # Extract department filter
            if 'departmentids' in params:
                filters['departmentids'] = params['departmentids'][0]
            
            # Extract tag filter
            if 'tagnames' in params:
                filters['tagnames'] = params['tagnames'][0]
            
        except Exception as e:
            logger.debug(f"Error parsing URL filters: {e}")
        
        return filters
    
    def scrape_jobs(self, url: str, company_name: str, company_description: str = '', label: str = '') -> List[Dict]:
        """
        Scrape jobs from Stripe search API
        
        Args:
            url: Stripe careers URL
            company_name: Name of the company
            company_description: Description
            label: Company label
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        
        # Extract filters from URL
        filters = self._extract_filters_from_url(url)
        if filters:
            logger.info(f"Applying filters: {filters}")
        else:
            logger.info("Searching all Stripe jobs (no filters)")
        
        headers = {
            'accept': 'application/json',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'referer': 'https://stripe.com/jobs'
        }
        
        # Pagination parameters
        skip = 0
        limit = 100
        
        while True:
            # Build request parameters
            params = {
                'skip': skip,
                'limit': limit
            }
            
            # Add filters
            params.update(filters)
            
            try:
                response = self.session.get(self.BASE_API_URL, headers=headers, params=params, timeout=30)
                response.raise_for_status()
                
                # Try JSON first
                try:
                    data = response.json()
                    jobs_list = data.get('jobs', [])
                    
                    if not jobs_list:
                        break
                    
                    # Parse each job from JSON
                    for job_data in jobs_list:
                        job = self._parse_job_json(job_data, company_name, company_description, label)
                        if job:
                            jobs.append(job)
                    
                    logger.info(f"📄 Skip {skip}: {len(jobs_list)} jobs (total: {len(jobs)})")
                    
                    if len(jobs_list) < limit:
                        break
                    
                except ValueError:
                    # Fallback to HTML parsing
                    soup = BeautifulSoup(response.text, 'html.parser')
                    job_rows = soup.find_all('tr', class_='JobsList__item')
                    
                    if not job_rows:
                        job_rows = soup.select('table tbody tr')
                        job_rows = [row for row in job_rows if row.find('a')]
                    
                    if not job_rows:
                        break
                    
                    for row in job_rows:
                        job = self._parse_job_row(row, company_name, company_description, label)
                        if job:
                            jobs.append(job)
                    
                    logger.info(f"📄 Skip {skip}: {len(job_rows)} jobs (total: {len(jobs)})")
                    
                    if len(job_rows) < limit:
                        break
                
                # Move to next page
                skip += limit
                time.sleep(self.delay)
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching jobs at skip={skip}: {e}")
                break
            except Exception as e:
                logger.error(f"Error parsing response at skip={skip}: {e}")
                break
        
        return jobs
    
    def _parse_job_json(self, job_data: dict, company_name: str, company_description: str, label: str) -> Dict:
        """
        Parse a single job from Stripe JSON API response
        
        Args:
            job_data: Job data from JSON API
            company_name: Company name
            company_description: Description
            label: Label
            
        Returns:
            Standardized job dictionary
        """
        try:
            title = job_data.get('title', '') or job_data.get('name', '')
            job_url = job_data.get('absolute_url', '') or job_data.get('url', '')
            
            if not job_url.startswith('http'):
                job_url = f"https://stripe.com{job_url}"
            
            # Location
            location = job_data.get('location', '') or job_data.get('office', '')
            
            # Department/Team
            department = job_data.get('team', '') or job_data.get('department', '')
            
            # Remote detection
            remote = 'No'
            location_lower = location.lower() if location else ''
            title_lower = title.lower()
            
            if 'remote' in location_lower or 'remote' in title_lower:
                remote = 'Yes'
            elif 'hybrid' in location_lower or 'hybrid' in title_lower:
                remote = 'Hybrid'
            
            # Employment type
            employment_type = 'FullTime'
            if 'intern' in title_lower:
                employment_type = 'Internship'
            elif 'contract' in title_lower:
                employment_type = 'Contractor'
            
            job = {
                'Company Name': company_name,
                'Job Title': title,
                'Location': location,
                'Job Link': job_url,
                'Job Description': '',
                'Employment Type': employment_type,
                'Department': department,
                'Posted Date': '',
                'Company Description': company_description,
                'Remote': remote,
                'Label': label,
                'ATS': 'Stripe'
            }
            
            return job
            
        except Exception as e:
            logger.debug(f"Error parsing job JSON: {e}")
            return None
    
    def _parse_job_row(self, row, company_name: str, company_description: str, label: str) -> Dict:
        """
        Parse a single job row from Stripe HTML response
        
        Args:
            row: BeautifulSoup row element
            company_name: Company name
            company_description: Description
            label: Label
            
        Returns:
            Standardized job dictionary
        """
        try:
            # Find job link
            link = row.find('a')
            if not link:
                return None
            
            # Title and URL
            title = link.get_text(strip=True)
            job_path = link.get('href', '')
            
            if job_path.startswith('/'):
                job_url = f"https://stripe.com{job_path}"
            else:
                job_url = f"{self.BASE_JOB_URL}/{job_path}"
            
            # Find all cells
            cells = row.find_all('td')
            
            department = ''
            location = ''
            
            # Parse cells (typically: Role, Team, Location)
            if len(cells) >= 2:
                # Second cell is usually Team/Department
                dept_cell = cells[1]
                department = dept_cell.get_text(strip=True)
            
            if len(cells) >= 3:
                # Third cell is usually Location
                loc_cell = cells[2]
                location = loc_cell.get_text(strip=True)
            
            # Remote detection
            remote = 'No'
            location_lower = location.lower()
            title_lower = title.lower()
            
            if 'remote' in location_lower or 'remote' in title_lower:
                remote = 'Yes'
            elif 'hybrid' in location_lower or 'hybrid' in title_lower:
                remote = 'Hybrid'
            
            # Employment type (default to FullTime)
            employment_type = 'FullTime'
            
            if 'intern' in title_lower:
                employment_type = 'Internship'
            elif 'contract' in title_lower or 'contractor' in title_lower:
                employment_type = 'Contractor'
            
            job = {
                'Company Name': company_name,
                'Job Title': title,
                'Location': location,
                'Job Link': job_url,
                'Job Description': '',  # Not provided in list view
                'Employment Type': employment_type,
                'Department': department,
                'Posted Date': '',  # Not provided in list view
                'Company Description': company_description,
                'Remote': remote,
                'Label': label,
                'ATS': 'Stripe'
            }
            
            return job
            
        except Exception as e:
            logger.debug(f"Error parsing job row: {e}")
            return None
