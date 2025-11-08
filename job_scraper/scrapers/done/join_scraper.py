"""
Join ATS Scraper
Scrapes job listings from Join.com public API
"""

import requests
import logging
import time
from typing import List, Dict
from datetime import datetime
from urllib.parse import urlparse
import re

logger = logging.getLogger(__name__)


class JoinScraper:
    """
    Scraper for Join ATS platform (API-based)
    
    Join uses a public REST API with pagination support.
    URL format: https://join.com/api/public/companies/{companyId}/jobs
    """
    
    def __init__(self, delay: float = 0.2):
        self.delay = delay
        self.session = requests.Session()
    
    def _extract_company_id(self, url: str) -> str:
        """
        Extract company ID from Join API URL
        
        Args:
            url: URL like https://join.com/api/public/companies/310/jobs
            
        Returns:
            Company ID as string (e.g., '310')
        """
        try:
            # Extract from path: /api/public/companies/{id}/jobs
            match = re.search(r'/companies/(\d+)', url)
            if match:
                return match.group(1)
            
            logger.error(f"Could not extract company ID from URL: {url}")
            return None
        except Exception as e:
            logger.error(f"Error extracting company ID: {e}")
            return None
    
    def scrape_jobs(self, url: str, company_name: str, company_description: str = '', label: str = '') -> List[Dict]:
        """
        Scrape jobs from Join API
        
        Args:
            url: Join API URL (e.g., https://join.com/api/public/companies/310/jobs)
            company_name: Name of the company
            company_description: Description
            label: Company label
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        
        company_id = self._extract_company_id(url)
        if not company_id:
            logger.error(f"Invalid Join URL: {url}")
            return jobs
        
        # Set headers to mimic browser request
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate',  # Remove br to avoid compression issues
            'accept-language': 'en-US,en;q=0.9,tr;q=0.8',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
            'referer': f'https://join.com/companies/{company_id}'
        }
        
        # Pagination loop
        page = 1
        page_size = 25
        total_jobs = 0
        
        while True:
            api_url = f"https://join.com/api/public/companies/{company_id}/jobs"
            params = {
                'locale': 'en-us',
                'page': page,
                'pageSize': page_size
            }
            
            try:
                response = self.session.get(api_url, headers=headers, params=params, timeout=30)
                response.raise_for_status()
                
                # Debug response
                logger.debug(f"Response status: {response.status_code}")
                logger.debug(f"Response headers: {dict(response.headers)}")
                logger.debug(f"Response content type: {response.headers.get('content-type')}")
                
                # Handle JSON parsing with better error handling
                try:
                    data = response.json()
                except ValueError as e:
                    logger.error(f"JSON parsing error: {e}")
                    logger.error(f"Response text[:500]: {response.text[:500]}")
                    break
                
                items = data.get('items', [])
                pagination = data.get('pagination', {})
                
                if page == 1:
                    total_jobs = pagination.get('rowCount', 0)
                    total_pages = pagination.get('pageCount', 1)
                    logger.info(f"Found {total_jobs} total jobs, fetching {total_pages} pages")
                
                if not items:
                    break
                
                for job_data in items:
                    job = self._parse_job(job_data, company_id, company_name, company_description, label)
                    if job:
                        jobs.append(job)
                
                logger.info(f"📄 Page {page}: {len(items)} jobs (total: {len(jobs)})")
                
                # Check if we've reached the last page
                if page >= pagination.get('pageCount', 1):
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
    
    def _parse_job(self, job_data: Dict, company_id: str, company_name: str, company_description: str, label: str) -> Dict:
        """
        Parse a single job from Join API response
        
        Args:
            job_data: Raw job data from API
            company_id: Company ID for URL construction
            company_name: Company name
            company_description: Description
            label: Label
            
        Returns:
            Standardized job dictionary
        """
        try:
            # Extract basic info
            job_id = job_data.get('id', '')
            id_param = job_data.get('idParam', '')
            title = job_data.get('title', '')
            
            # Build job URL: https://join.com/companies/{companyId}/jobs/{idParam}
            job_url = f"https://join.com/companies/{company_id}/jobs/{id_param}" if id_param else ''
            
            # Extract location
            city_obj = job_data.get('city', {})
            country_obj = job_data.get('country', {})
            
            city_name = city_obj.get('cityName', '')
            country_name = country_obj.get('name', '')
            
            location_parts = []
            if city_name:
                location_parts.append(city_name)
            if country_name:
                location_parts.append(country_name)
            location_str = ', '.join(location_parts)
            
            # Extract employment type
            employment_type_obj = job_data.get('employmentType', {})
            employment_type = employment_type_obj.get('name', '')
            
            # Extract department/category
            category_obj = job_data.get('category', {})
            department = category_obj.get('name', '')
            
            # Determine remote status from workplaceType
            workplace_type = job_data.get('workplaceType', '').upper()
            remote = 'No'
            if workplace_type == 'REMOTE':
                remote = 'Yes'
            elif workplace_type == 'HYBRID':
                remote = 'Hybrid'
            
            # Extract posted date
            created_at = job_data.get('createdAt', '')
            posted_date = ''
            if created_at:
                try:
                    # Parse ISO format: 2025-10-23T09:15:49.907Z
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    posted_date = dt.strftime('%Y-%m-%d')
                except:
                    pass
            
            job = {
                'Company Name': company_name,
                'Job Title': title,
                'Location': location_str,
                'Job Link': job_url,
                'Job Description': '',  # Not provided in list API
                'Employment Type': employment_type,
                'Department': department,
                'Posted Date': posted_date,
                'Company Description': company_description,
                'Remote': remote,
                'Label': label,
                'ATS': 'Join'
            }
            
            return job
            
        except Exception as e:
            logger.debug(f"Error parsing job: {e}")
            return None
