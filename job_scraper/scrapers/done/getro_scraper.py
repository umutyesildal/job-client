"""
Getro ATS Scraper
Scrapes job listings from Getro API (shared job boards like Earlybird VC)
"""

import requests
import logging
import time
import math
from typing import List, Dict
from datetime import datetime
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class GetroScraper:
    """
    Scraper for Getro ATS platform (API-based)
    
    Getro powers shared job boards for VCs and organizations.
    URL format: https://api.getro.com/api/v2/collections/{collection_id}/search/jobs
    """
    
    def __init__(self, delay: float = 1.0):
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'accept': 'application/json',
            'accept-encoding': 'gzip, deflate, br, zstd',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'application/json',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'
        })
    
    def _extract_collection_id(self, url: str) -> str:
        """
        Extract collection ID from Getro API URL
        
        Args:
            url: API URL like https://api.getro.com/api/v2/collections/617/search/jobs
            
        Returns:
            Collection ID as string
        """
        try:
            # Parse URL path: /api/v2/collections/{id}/search/jobs
            parts = urlparse(url).path.split('/')
            if 'collections' in parts:
                idx = parts.index('collections')
                if idx + 1 < len(parts):
                    return parts[idx + 1]
            
            logger.error(f"Could not extract collection ID from URL: {url}")
            return None
        except Exception as e:
            logger.error(f"Error extracting collection ID: {e}")
            return None
    
    def scrape_jobs(self, url: str, company_name: str, company_description: str = '', label: str = '') -> List[Dict]:
        """
        Scrape jobs from Getro API
        
        Args:
            url: Getro API URL (e.g., https://api.getro.com/api/v2/collections/617/search/jobs)
            company_name: Name of the organization/VC
            company_description: Description
            label: Company label
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        
        collection_id = self._extract_collection_id(url)
        if not collection_id:
            logger.error(f"Invalid Getro URL: {url}")
            return jobs
        
        # Build API endpoint
        api_url = f"https://api.getro.com/api/v2/collections/{collection_id}/search/jobs"
        
        # Set origin and referer based on the collection (may vary per board)
        # Using generic values that work for most Getro boards
        self.session.headers.update({
            'origin': f'https://jobs.{company_name.lower().replace(" ", "")}.com',
            'referer': f'https://jobs.{company_name.lower().replace(" ", "")}.com/jobs'
        })
        
        page = 0  
        hits_per_page = 20  
        total_jobs = None
        
        while True:
            payload = {
                "hitsPerPage": hits_per_page,
                "page": page,
                "filters": {
                    "page": page
                },
                "query": ""
            }
            
            try:
                response = self.session.post(api_url, json=payload, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                job_list = data.get('results', {}).get('jobs', [])
                
                if not job_list:
                    break
                
                # Get total count on first page
                if page == 1:
                    total_jobs = data.get('results', {}).get('count', 0)
                    total_pages = math.ceil(total_jobs / hits_per_page)
                    logger.info(f"Found {total_jobs} total jobs, fetching {total_pages} pages")
                
                for job_data in job_list:
                    job = self._parse_job(job_data, company_name, company_description, label)
                    if job:
                        jobs.append(job)
                
                logger.info(f"📄 Page {page}: {len(job_list)} jobs (total: {len(jobs)})")
                
                # Check if we've fetched all jobs
                if total_jobs and len(jobs) >= total_jobs:
                    break
                
                page += 1
                time.sleep(self.delay)
                
            except Exception as e:
                logger.error(f"Error fetching page {page}: {e}")
                break
        
        return jobs
    
    def _parse_job(self, job_data: Dict, company_name: str, company_description: str, label: str) -> Dict:
        """
        Parse a single job from Getro API response
        
        Args:
            job_data: Raw job data from API
            company_name: Board/VC name
            company_description: Description
            label: Label
            
        Returns:
            Standardized job dictionary
        """
        try:
            # Extract organization info
            org = job_data.get('organization', {})
            actual_company = org.get('name', company_name)
            
            # Extract location
            locations = job_data.get('locations', [])
            location_str = ', '.join(locations) if locations else ''
            
            # Convert Unix timestamp to date
            created_at = job_data.get('created_at')
            posted_date = ''
            if created_at:
                try:
                    posted_date = datetime.fromtimestamp(created_at).strftime('%Y-%m-%d')
                except:
                    pass
            
            # Map work_mode to Remote field
            work_mode = job_data.get('work_mode', '').lower()
            remote = 'No'
            if work_mode == 'remote':
                remote = 'Yes'
            elif work_mode == 'hybrid':
                remote = 'Hybrid'
            
            job = {
                'Company Name': actual_company,
                'Job Title': job_data.get('title', ''),
                'Location': location_str,
                'Job Link': job_data.get('url', ''),
                'Job Description': '',  # Not provided in API response
                'Employment Type': '',  # Not provided in API response
                'Department': '',  # Not provided in API response
                'Posted Date': posted_date,
                'Company Description': company_description,
                'Remote': remote,
                'Label': label,
                'ATS': 'Getro'
            }
            
            return job
            
        except Exception as e:
            logger.debug(f"Error parsing job: {e}")
            return None
