"""
Rippling ATS Scraper
Scrapes job listings from Rippling ATS public API
"""

import requests
import logging
import time
from typing import List, Dict
from urllib.parse import urlparse
import re

logger = logging.getLogger(__name__)


class RipplingScraper:
    """
    Scraper for Rippling ATS platform (API-based)
    
    Rippling uses a paginated REST API with zero-based page indexing.
    URL format: https://ats.rippling.com/api/v2/board/{boardId}/jobs
    """
    
    def __init__(self, delay: float = 1.0):
        self.delay = delay
        self.session = requests.Session()
    
    def _extract_board_id(self, url: str) -> str:
        """
        Extract board ID from Rippling URL
        
        Args:
            url: URL like https://ats.rippling.com/api/v2/board/rudderstack-careers/jobs
            
        Returns:
            Board ID as string (e.g., 'rudderstack-careers')
        """
        try:
            # Extract from path: /api/v2/board/{boardId}/jobs
            match = re.search(r'/board/([^/]+)(?:/jobs)?', url)
            if match:
                return match.group(1)
            
            logger.error(f"Could not extract board ID from URL: {url}")
            return None
        except Exception as e:
            logger.error(f"Error extracting board ID: {e}")
            return None
    
    def scrape_jobs(self, url: str, company_name: str, company_description: str = '', label: str = '') -> List[Dict]:
        """
        Scrape jobs from Rippling API
        
        Args:
            url: Rippling API URL (e.g., https://ats.rippling.com/api/v2/board/rudderstack-careers/jobs)
            company_name: Name of the company
            company_description: Description
            label: Company label
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        
        board_id = self._extract_board_id(url)
        if not board_id:
            logger.error(f"Invalid Rippling URL: {url}")
            return jobs
        
        # Set headers
        headers = {
            'accept': 'application/json',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'
        }
        
        # Pagination loop (zero-based)
        page = 0
        page_size = 20
        
        while True:
            api_url = f"https://ats.rippling.com/api/v2/board/{board_id}/jobs"
            params = {
                'page': page,
                'pageSize': page_size
            }
            
            try:
                response = self.session.get(api_url, headers=headers, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                items = data.get('items', [])
                total_items = data.get('totalItems', 0)
                total_pages = data.get('totalPages', 0)
                
                if page == 0:
                    logger.info(f"Found {total_items} total jobs, fetching {total_pages} pages")
                
                if not items:
                    break
                
                for job_data in items:
                    job = self._parse_job(job_data, board_id, company_name, company_description, label)
                    if job:
                        jobs.append(job)
                
                logger.info(f"📄 Page {page}: {len(items)} jobs (total: {len(jobs)})")
                
                # Check if we've reached the last page
                if page >= total_pages - 1:
                    break
                
                page += 1
                time.sleep(self.delay)
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching page {page}: {e}")
                break
            except Exception as e:
                logger.error(f"Error parsing response for page {page}: {e}")
                break
        
        return jobs
    
    def _parse_job(self, job_data: Dict, board_id: str, company_name: str, company_description: str, label: str) -> Dict:
        """
        Parse a single job from Rippling API response
        
        Args:
            job_data: Raw job data from API
            board_id: Board identifier
            company_name: Company name
            company_description: Description
            label: Label
            
        Returns:
            Standardized job dictionary
        """
        try:
            # Extract basic info
            job_id = job_data.get('id', '')
            title = job_data.get('name', '')
            job_url = job_data.get('url', '')
            
            # Extract department
            department_obj = job_data.get('department', {})
            department = department_obj.get('name', '') if department_obj else ''
            
            # Extract locations
            locations = job_data.get('locations', [])
            location_parts = []
            workplace_types = set()
            
            for loc in locations:
                loc_name = loc.get('name', '')
                if loc_name:
                    location_parts.append(loc_name)
                
                workplace_type = loc.get('workplaceType', '')
                if workplace_type:
                    workplace_types.add(workplace_type)
            
            location_str = ', '.join(location_parts) if location_parts else ''
            
            # Determine remote status from workplaceType
            remote = 'No'
            if 'REMOTE' in workplace_types:
                remote = 'Yes'
            elif 'HYBRID' in workplace_types:
                remote = 'Hybrid'
            elif 'ON_SITE' not in workplace_types and location_str.lower().startswith('remote'):
                remote = 'Yes'
            
            job = {
                'Company Name': company_name,
                'Job Title': title,
                'Location': location_str,
                'Job Link': job_url,
                'Job Description': '',  # Not provided in list API
                'Employment Type': '',  # Not provided in list API
                'Department': department,
                'Posted Date': '',  # Not provided in list API
                'Company Description': company_description,
                'Remote': remote,
                'Label': label,
                'ATS': 'Rippling'
            }
            
            return job
            
        except Exception as e:
            logger.debug(f"Error parsing job: {e}")
            return None
