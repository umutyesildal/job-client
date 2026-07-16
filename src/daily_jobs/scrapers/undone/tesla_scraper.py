"""
Tesla Scraper
Scrapes job listings from Tesla's careers API

STATUS: NOT WORKING
REASON: Rate limited (429 Too Many Requests) - Tesla API has strict rate limiting
ERROR: 429 errors even with retry and exponential backoff
SOLUTION NEEDED: Add longer delays between requests or rotate IPs/user agents
NOTE: The scraper logic works, just needs better rate limit handling
"""

import requests
import logging
import time
from typing import List, Dict
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)


class TeslaScraper:
    """
    Scraper for Tesla Careers (https://www.tesla.com/careers)
    
    Tesla uses a unique JSON API that returns all jobs with lookup tables.
    URL format: https://www.tesla.com/cua-api/apps/careers/state
    
    API returns all jobs in a single response with location/department mappings.
    """
    
    API_URL = "https://www.tesla.com/cua-api/apps/careers/state"
    BASE_JOB_URL = "https://www.tesla.com/careers/search/job"
    
    def __init__(self, delay: float = 1.0):
        self.delay = delay
        self.session = requests.Session()
    
    def _extract_location_from_url(self, url: str) -> str:
        """
        Extract location filter from Tesla careers URL
        
        Args:
            url: Tesla careers URL
            
        Returns:
            Location string to filter by
        """
        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            
            # Check for location in query params
            if 'location' in params:
                return params['location'][0].lower()
            
            # Check URL path for location hints
            url_lower = url.lower()
            if 'germany' in url_lower or 'berlin' in url_lower:
                return 'germany'
            if 'brandenburg' in url_lower:
                return 'brandenburg'
            
            # Default to Germany
            logger.info("No location filter found, defaulting to Germany")
            return 'germany'
            
        except Exception as e:
            logger.debug(f"Error parsing URL: {e}")
            return 'germany'
    
    def scrape_jobs(self, url: str, company_name: str, company_description: str = '', label: str = '') -> List[Dict]:
        """
        Scrape jobs from Tesla API
        
        Args:
            url: Tesla careers URL
            company_name: Name of the company
            company_description: Description
            label: Company label
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        
        # Extract location filter
        location_filter = self._extract_location_from_url(url)
        logger.info(f"Filtering Tesla jobs by: {location_filter}")
        
        headers = {
            'accept': 'application/json',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                response = self.session.get(self.API_URL, headers=headers, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                
                # Extract lookup tables
                locations = data.get('lookup', {}).get('locations', {})
                departments = data.get('lookup', {}).get('departments', {})
                types = data.get('lookup', {}).get('types', {})
                
                # Get all jobs
                all_jobs = data.get('jobs', [])
                
                logger.info(f"Total Tesla jobs: {len(all_jobs)}")
                
                # Filter jobs by location
                for job_data in all_jobs:
                    # Get location name
                    loc_id = str(job_data.get('l', ''))
                    location_name = locations.get(loc_id, '').lower()
                    
                    # Check if location matches filter
                    if location_filter in location_name:
                        job = self._parse_job(job_data, company_name, company_description, label, 
                                             locations, departments, types)
                        if job:
                            jobs.append(job)
                
                logger.info(f"Found {len(jobs)} jobs matching '{location_filter}'")
                break  # Success, exit retry loop
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    if attempt < max_retries - 1:
                        logger.warning(f"Rate limited (429), retrying in {retry_delay}s... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
                    else:
                        logger.error(f"Rate limited after {max_retries} attempts")
                else:
                    logger.error(f"Error fetching Tesla jobs: {e}")
                break
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching Tesla jobs: {e}")
                break
            except Exception as e:
                logger.error(f"Error parsing Tesla response: {e}")
                break
        
        return jobs
    
    def _parse_job(self, job_data: dict, company_name: str, company_description: str, label: str,
                   locations: dict, departments: dict, types: dict) -> Dict:
        """
        Parse a single job from Tesla API response
        
        Args:
            job_data: Job data from API
            company_name: Company name
            company_description: Description
            label: Label
            locations: Location lookup table
            departments: Department lookup table
            types: Employment type lookup table
            
        Returns:
            Standardized job dictionary
        """
        try:
            job_id = job_data.get('id', '')
            title = job_data.get('t', '')
            
            # Build job URL
            job_url = f"{self.BASE_JOB_URL}/{job_id}"
            
            # Location
            loc_id = str(job_data.get('l', ''))
            location = locations.get(loc_id, '')
            
            # Department
            dept_id = str(job_data.get('dp', ''))
            department = departments.get(dept_id, '')
            
            # Employment type
            type_id = str(job_data.get('y', ''))
            type_name = types.get(type_id, '').lower()
            
            employment_type = 'FullTime'
            if 'part' in type_name:
                employment_type = 'PartTime'
            elif 'intern' in type_name:
                employment_type = 'Internship'
            elif 'contract' in type_name:
                employment_type = 'Contractor'
            
            # Remote detection
            remote = 'No'
            location_lower = location.lower()
            title_lower = title.lower()
            
            if 'remote' in location_lower or 'remote' in title_lower:
                remote = 'Yes'
            elif 'hybrid' in location_lower or 'hybrid' in title_lower:
                remote = 'Hybrid'
            
            job = {
                'Company Name': company_name,
                'Job Title': title,
                'Location': location,
                'Job Link': job_url,
                'Job Description': '',  # Not provided in list view
                'Employment Type': employment_type,
                'Department': department,
                'Posted Date': '',  # Not provided in API
                'Company Description': company_description,
                'Remote': remote,
                'Label': label,
                'ATS': 'Tesla'
            }
            
            return job
            
        except Exception as e:
            logger.debug(f"Error parsing job: {e}")
            return None
