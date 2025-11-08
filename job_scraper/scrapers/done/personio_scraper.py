"""
Personio ATS Scraper
Scrapes job listings from Personio public API
"""

import requests
import logging
import time
from typing import List, Dict
from urllib.parse import urlparse
import html

logger = logging.getLogger(__name__)


class PersonioScraper:
    """
    Scraper for Personio ATS platform (API-based)
    
    Personio uses a simple JSON API that returns all jobs in a single request.
    URL format: https://{company}.jobs.personio.com/search.json
    """
    
    def __init__(self, delay: float = 0.2):
        self.delay = delay
        self.session = requests.Session()
    
    def _extract_company_id(self, url: str) -> str:
        """
        Extract company identifier from Personio URL
        
        Args:
            url: URL like https://archlet.jobs.personio.com/search.json 
                 or https://archlet.jobs.personio.com (career page)
            
        Returns:
            Company identifier as string (e.g., 'archlet')
        """
        try:
            parsed = urlparse(url)
            # Extract subdomain from hostname like 'archlet.jobs.personio.com' or 'company.jobs.personio.de'
            parts = parsed.hostname.split('.')
            if len(parts) >= 3 and ('jobs.personio.com' in parsed.hostname or 'jobs.personio.de' in parsed.hostname):
                return parts[0]
            
            logger.error(f"Could not extract company ID from URL: {url}")
            return None
        except Exception as e:
            logger.error(f"Error extracting company ID: {e}")
            return None
    
    def _build_api_url(self, url: str, company_id: str) -> str:
        """
        Build API URL from career page URL or use existing API URL
        
        Args:
            url: Original URL (career page or API endpoint)
            company_id: Extracted company identifier
            
        Returns:
            API endpoint URL
        """
        # If URL already contains search.json, use it as is
        if 'search.json' in url:
            return url
        
        # Otherwise, build the API URL
        parsed = urlparse(url)
        # Preserve the domain (.com or .de)
        if '.personio.de' in parsed.hostname:
            return f"https://{company_id}.jobs.personio.de/search.json"
        else:
            return f"https://{company_id}.jobs.personio.com/search.json"
    
    def scrape_jobs(self, url: str, company_name: str, company_description: str = '', label: str = '') -> List[Dict]:
        """
        Scrape jobs from Personio API
        
        Args:
            url: Personio URL (career page or API endpoint)
                 e.g., https://archlet.jobs.personio.com/search.json
                 or https://archlet.jobs.personio.com
            company_name: Name of the company
            company_description: Description
            label: Company label
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        
        company_id = self._extract_company_id(url)
        if not company_id:
            logger.error(f"Invalid Personio URL: {url}")
            return jobs
        
        # Build the API URL
        api_url = self._build_api_url(url, company_id)
        
        # Set headers
        headers = {
            'accept': 'application/json, text/plain, */*',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'
        }
        
        try:
            response = self.session.get(api_url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Personio returns an array directly
            if not isinstance(data, list):
                logger.error(f"Unexpected response format for {company_id}")
                return jobs
            
            logger.info(f"Found {len(data)} jobs for {company_name}")
            
            for job_data in data:
                job = self._parse_job(job_data, company_id, company_name, company_description, label)
                if job:
                    jobs.append(job)
            
            time.sleep(self.delay)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching jobs for {company_id}: {e}")
        except Exception as e:
            logger.error(f"Error parsing response for {company_id}: {e}")
        
        return jobs
    
    def _parse_job(self, job_data: Dict, company_id: str, company_name: str, company_description: str, label: str) -> Dict:
        """
        Parse a single job from Personio API response
        
        Args:
            job_data: Raw job data from API
            company_id: Company identifier
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
            
            # Build job URL: https://{company}.jobs.personio.com/job/{id}
            job_url = f"https://{company_id}.jobs.personio.com/job/{job_id}" if job_id else ''
            
            # Extract location from offices array or office field
            offices = job_data.get('offices', [])
            office = job_data.get('office', '')
            
            if offices:
                location_str = ', '.join(offices)
            else:
                location_str = office
            
            # Extract employment type and schedule
            employment_type = job_data.get('employment_type', '')
            schedule = job_data.get('schedule', '')
            
            # Combine employment type and schedule for fuller picture
            if schedule and schedule not in employment_type:
                employment_type = f"{employment_type} ({schedule})" if employment_type else schedule
            
            # Extract department
            department = job_data.get('department', '')
            
            # Determine remote status
            # Personio doesn't explicitly provide remote status, check office/description
            remote = 'No'
            if location_str:
                location_lower = location_str.lower()
                if 'remote' in location_lower:
                    remote = 'Yes'
                elif 'hybrid' in location_lower:
                    remote = 'Hybrid'
            
            # Extract description (HTML format)
            description_html = job_data.get('description', '')
            description = html.unescape(description_html) if description_html else ''
            
            # Personio doesn't provide posted date in the API response
            posted_date = ''
            
            job = {
                'Company Name': company_name,
                'Job Title': title,
                'Location': location_str,
                'Job Link': job_url,
                'Job Description': description,
                'Employment Type': employment_type,
                'Department': department,
                'Posted Date': posted_date,
                'Company Description': company_description,
                'Remote': remote,
                'Label': label,
                'ATS': 'Personio'
            }
            
            return job
            
        except Exception as e:
            logger.debug(f"Error parsing job: {e}")
            return None
