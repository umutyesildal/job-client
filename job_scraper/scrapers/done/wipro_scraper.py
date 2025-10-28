"""
Wipro Scraper
Scrapes job listings from Wipro's careers API
"""

import requests
import logging
import time
from typing import List, Dict
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)


class WiproScraper:
    """
    Scraper for Wipro Careers (https://careers.wipro.com)
    
    Wipro uses a POST API endpoint that requires JSON payload.
    URL format: https://careers.wipro.com/services/recruiting/v1/jobs
    
    API supports:
    - Country/location filtering via facetFilters
    - Pagination via pageNumber
    - Sorting by date
    - Keyword search
    """
    
    API_URL = "https://careers.wipro.com/services/recruiting/v1/jobs"
    BASE_JOB_URL = "https://careers.wipro.com/careers-home/jobs"
    
    def __init__(self, delay: float = 1.0):
        self.delay = delay
        self.session = requests.Session()
    
    def _extract_location_from_url(self, url: str) -> str:
        """
        Extract location filter from Wipro careers URL
        
        Args:
            url: Wipro careers URL
            
        Returns:
            Country name to filter by
        """
        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            
            # Check for location/country in query params
            if 'country' in params:
                return params['country'][0]
            if 'location' in params:
                return params['location'][0]
            
            # Check URL for location hints
            url_lower = url.lower()
            if 'germany' in url_lower:
                return 'Germany'
            
            # Default to Germany
            logger.info("No location filter found, defaulting to Germany")
            return 'Germany'
            
        except Exception as e:
            logger.debug(f"Error parsing URL: {e}")
            return 'Germany'
    
    def scrape_jobs(self, url: str, company_name: str, company_description: str = '', label: str = '') -> List[Dict]:
        """
        Scrape jobs from Wipro API
        
        Args:
            url: Wipro careers URL
            company_name: Name of the company
            company_description: Description
            label: Company label
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        
        # Extract location filter
        country_filter = self._extract_location_from_url(url)
        logger.info(f"Filtering Wipro jobs by country: {country_filter}")
        
        headers = {
            'accept': 'application/json',
            'content-type': 'application/json',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        page_number = 0
        
        while True:
            # Build request payload
            payload = {
                "locale": "en_US",
                "pageNumber": page_number,
                "sortBy": "date",
                "keywords": "",
                "location": "",
                "facetFilters": {
                    "jobLocationCountry": [country_filter]
                },
                "brand": "",
                "skills": [],
                "categoryId": 0,
                "alertId": "",
                "rcmCandidateId": ""
            }
            
            try:
                response = self.session.post(self.API_URL, headers=headers, json=payload, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                
                # Extract jobs
                job_results = data.get('jobSearchResult', [])
                total_jobs = data.get('totalJobs', 0)
                
                if not job_results:
                    break
                
                # Parse each job
                for job_result in job_results:
                    job_data = job_result.get('response', {})
                    job = self._parse_job(job_data, company_name, company_description, label)
                    if job:
                        jobs.append(job)
                
                logger.info(f"📄 Page {page_number}: {len(job_results)} jobs (total: {len(jobs)}/{total_jobs})")
                
                # Check if we got all jobs
                if len(jobs) >= total_jobs:
                    break
                
                # Move to next page
                page_number += 1
                time.sleep(self.delay)
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching jobs at page {page_number}: {e}")
                break
            except Exception as e:
                logger.error(f"Error parsing response at page {page_number}: {e}")
                break
        
        return jobs
    
    def _parse_job(self, job_data: dict, company_name: str, company_description: str, label: str) -> Dict:
        """
        Parse a single job from Wipro API response
        
        Args:
            job_data: Job data from API
            company_name: Company name
            company_description: Description
            label: Label
            
        Returns:
            Standardized job dictionary
        """
        try:
            # Title
            title = job_data.get('unifiedStandardTitle', '') or job_data.get('unifiedUrlTitle', '')
            
            # Job ID and URL
            job_id = job_data.get('id', '')
            url_title = job_data.get('urlTitle', '')
            
            if url_title:
                job_url = f"{self.BASE_JOB_URL}/{job_id}/{url_title}"
            else:
                job_url = f"{self.BASE_JOB_URL}/{job_id}"
            
            # Location - combine city, state, country
            location_parts = []
            
            # Try main location
            locations = job_data.get('sfstd_jobLocation_obj', [])
            if locations and isinstance(locations, list):
                location_parts.extend([loc for loc in locations if loc])
            
            # Add state if different
            states = job_data.get('jobLocationState', [])
            if states and isinstance(states, list):
                for state in states:
                    if state and state not in location_parts:
                        location_parts.append(state)
            
            # Add country
            countries = job_data.get('jobLocationCountry', [])
            if countries and isinstance(countries, list):
                for country in countries:
                    if country and country not in location_parts:
                        location_parts.append(country)
            
            location = ', '.join(location_parts) if location_parts else ''
            
            # Department
            department = ''
            domains = job_data.get('custRMKMappingPicklist', [])
            if domains and isinstance(domains, list):
                department = ', '.join([d for d in domains if d])
            
            # Employment type (default to FullTime)
            employment_type = 'FullTime'
            title_lower = title.lower()
            
            if 'intern' in title_lower:
                employment_type = 'Internship'
            elif 'contract' in title_lower:
                employment_type = 'Contractor'
            
            # Remote detection
            remote = 'No'
            location_lower = location.lower()
            
            if 'remote' in location_lower or 'remote' in title_lower:
                remote = 'Yes'
            elif 'hybrid' in location_lower or 'hybrid' in title_lower:
                remote = 'Hybrid'
            
            # Posted date
            posted_date = ''
            start_date = job_data.get('unifiedStandardStart', '')
            if start_date:
                # Format is MM/DD/YY, convert to YYYY-MM-DD
                try:
                    from datetime import datetime
                    dt = datetime.strptime(start_date, '%m/%d/%y')
                    posted_date = dt.strftime('%Y-%m-%d')
                except:
                    posted_date = ''
            
            job = {
                'Company Name': company_name,
                'Job Title': title,
                'Location': location,
                'Job Link': job_url,
                'Job Description': '',  # Not provided in list view
                'Employment Type': employment_type,
                'Department': department,
                'Posted Date': posted_date,
                'Company Description': company_description,
                'Remote': remote,
                'Label': label,
                'ATS': 'Wipro'
            }
            
            return job
            
        except Exception as e:
            logger.debug(f"Error parsing job: {e}")
            return None
