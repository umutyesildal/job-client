"""
Lever ATS Scraper
Scrapes job listings from Lever.co public API
"""

import requests
import logging
import time
from typing import List, Dict
from datetime import datetime
from urllib.parse import urlparse, parse_qs
import re

logger = logging.getLogger(__name__)


class LeverScraper:
    """
    Scraper for Lever ATS platform (API-based)
    
    Lever uses a public REST API with pagination support.
    URL format: https://api.lever.co/v0/postings/{company} or https://api.eu.lever.co/v0/postings/{company}
    """
    
    def __init__(self, delay: float = 0.2):
        self.delay = delay
        self.session = requests.Session()
    
    def _extract_company_and_region(self, url: str) -> tuple:
        """
        Extract company ID and API region from Lever URL
        
        Args:
            url: URL like https://api.eu.lever.co/v0/postings/kaiko?skip=0&limit=25&mode=json
            
        Returns:
            Tuple of (company_id, base_url) e.g., ('kaiko', 'https://api.eu.lever.co')
        """
        try:
            parsed = urlparse(url)
            
            # Determine base URL (api.lever.co or api.eu.lever.co)
            if 'api.eu.lever.co' in parsed.netloc:
                base_url = 'https://api.eu.lever.co'
            else:
                base_url = 'https://api.lever.co'
            
            # Extract company from path: /v0/postings/{company}
            match = re.search(r'/v0/postings/([^/?]+)', parsed.path)
            if match:
                company_id = match.group(1)
                return company_id, base_url
            
            logger.error(f"Could not extract company ID from URL: {url}")
            return None, None
        except Exception as e:
            logger.error(f"Error extracting company info: {e}")
            return None, None
    
    def scrape_jobs(self, url: str, company_name: str, company_description: str = '', label: str = '') -> List[Dict]:
        """
        Scrape jobs from Lever API
        
        Args:
            url: Lever API URL (e.g., https://api.eu.lever.co/v0/postings/kaiko?skip=0&limit=25&mode=json)
            company_name: Name of the company
            company_description: Description
            label: Company label
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        
        company_id, base_url = self._extract_company_and_region(url)
        if not company_id or not base_url:
            logger.error(f"Invalid Lever URL: {url}")
            return jobs
        
        # Set headers
        headers = {
            'accept': 'application/json',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'
        }
        
        # Pagination loop
        skip = 0
        limit = 100  # Fetch 100 at a time for efficiency
        page = 1
        
        while True:
            api_url = f"{base_url}/v0/postings/{company_id}"
            params = {
                'skip': skip,
                'limit': limit,
                'mode': 'json'
            }
            
            try:
                response = self.session.get(api_url, headers=headers, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                # Lever returns an array directly
                if not isinstance(data, list):
                    logger.error(f"Unexpected response format for {company_id}")
                    break
                
                if not data:
                    break
                
                if page == 1:
                    logger.info(f"Fetching jobs for {company_name} (pagination in progress)")
                
                for job_data in data:
                    job = self._parse_job(job_data, company_id, base_url, company_name, company_description, label)
                    if job:
                        jobs.append(job)
                
                logger.info(f"📄 Page {page}: {len(data)} jobs (total: {len(jobs)})")
                
                # If we got fewer jobs than limit, we've reached the end
                if len(data) < limit:
                    break
                
                skip += limit
                page += 1
                time.sleep(self.delay)
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching page {page}: {e}")
                break
            except Exception as e:
                logger.error(f"Error parsing response for page {page}: {e}")
                break
        
        return jobs
    
    def _parse_job(self, job_data: Dict, company_id: str, base_url: str, company_name: str, company_description: str, label: str) -> Dict:
        """
        Parse a single job from Lever API response
        
        Args:
            job_data: Raw job data from API
            company_id: Company identifier
            base_url: API base URL
            company_name: Company name
            company_description: Description
            label: Label
            
        Returns:
            Standardized job dictionary
        """
        try:
            # Extract basic info
            job_id = job_data.get('id', '')
            title = job_data.get('text', '')  # Lever uses 'text' for title
            
            # Job URL from hostedUrl field
            job_url = job_data.get('hostedUrl', '')
            
            # Extract categories
            categories = job_data.get('categories', {})
            location = categories.get('location', '')
            department = categories.get('department', '')
            team = categories.get('team', '')
            commitment = categories.get('commitment', '')  # Employment type
            
            # Use team if available, otherwise department
            dept_value = team if team else department
            
            # Extract location from allLocations or primary location
            all_locations = categories.get('allLocations', [])
            if all_locations:
                location_str = ', '.join(all_locations[:3])  # First 3 locations
            else:
                location_str = location
            
            # Determine remote status from workplaceType
            workplace_type = job_data.get('workplaceType', '').lower()
            remote = 'No'
            if workplace_type == 'remote':
                remote = 'Yes'
            elif workplace_type == 'hybrid':
                remote = 'Hybrid'
            
            # Extract description (use plain text version)
            description = job_data.get('descriptionPlain', '')
            if not description:
                description = job_data.get('openingPlain', '')
            
            # Extract posted date from createdAt (Unix timestamp in milliseconds)
            created_at = job_data.get('createdAt')
            posted_date = ''
            if created_at:
                try:
                    # Convert milliseconds to seconds
                    dt = datetime.fromtimestamp(created_at / 1000)
                    posted_date = dt.strftime('%Y-%m-%d')
                except:
                    pass
            
            job = {
                'Company Name': company_name,
                'Job Title': title,
                'Location': location_str,
                'Job Link': job_url,
                'Job Description': description,
                'Employment Type': commitment,
                'Department': dept_value,
                'Posted Date': posted_date,
                'Company Description': company_description,
                'Remote': remote,
                'Label': label,
                'ATS': 'Lever'
            }
            
            return job
            
        except Exception as e:
            logger.debug(f"Error parsing job: {e}")
            return None
