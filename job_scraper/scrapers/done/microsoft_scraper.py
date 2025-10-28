"""
Microsoft Careers Scraper
Scrapes job listings from Microsoft's Careers Search API
"""

import requests
import logging
import time
from typing import List, Dict
from urllib.parse import urlparse, parse_qs
import re

logger = logging.getLogger(__name__)


class MicrosoftScraper:
    """
    Scraper for Microsoft Careers (https://careers.microsoft.com)
    
    Microsoft uses a REST API endpoint for job search.
    URL format: https://gcsservices.careers.microsoft.com/search/api/v1/search
    
    API supports:
    - Location-based search via 'lc' parameter
    - Pagination via 'pg' and 'pgSz' parameters
    - Sorting via 'o' parameter
    - Returns totalJobs count for verification
    """
    
    BASE_API_URL = "https://gcsservices.careers.microsoft.com/search/api/v1/search"
    
    def __init__(self, delay: float = 1.0):
        self.delay = delay
        self.session = requests.Session()
    
    def _extract_location_from_url(self, url: str) -> str:
        """
        Extract location from Microsoft careers URL
        
        Args:
            url: Microsoft careers URL
            
        Returns:
            Location string (e.g., 'Germany')
        """
        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            
            # Check for location in query params
            if 'lc' in params:
                return params['lc'][0]
            if 'location' in params:
                return params['location'][0]
            
            # Try to extract from URL path
            path = parsed.path.lower()
            if 'germany' in path:
                return 'Germany'
            elif 'berlin' in path:
                return 'Germany'
            elif 'uk' in path or 'london' in path:
                return 'United Kingdom'
            
            # Default to empty (all locations)
            logger.info("No location filter found, searching all Microsoft jobs")
            return ''
            
        except Exception as e:
            logger.debug(f"Error parsing URL: {e}")
            return ''
    
    def scrape_jobs(self, url: str, company_name: str, company_description: str = '', label: str = '') -> List[Dict]:
        """
        Scrape jobs from Microsoft Careers Search API
        
        Args:
            url: Microsoft careers URL
            company_name: Name of the company
            company_description: Description
            label: Company label
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        
        # Extract location
        location_filter = self._extract_location_from_url(url)
        if location_filter:
            logger.info(f"Filtering Microsoft jobs by location: {location_filter}")
        else:
            logger.info("Searching all Microsoft jobs (no location filter)")
        
        # Set headers
        headers = {
            'accept': 'application/json',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
            'referer': 'https://careers.microsoft.com/'
        }
        
        # Pagination parameters
        page = 1
        page_size = 20  # Results per page
        total_jobs = None
        
        while True:
            # Build request parameters
            params = {
                'lc': location_filter,
                'l': 'en_us',
                'pg': page,
                'pgSz': page_size,
                'o': 'Recent'  # Sort by recent
            }
            
            try:
                response = self.session.get(self.BASE_API_URL, headers=headers, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                
                # Navigate to the jobs array
                operation_result = data.get('operationResult', {})
                result = operation_result.get('result', {})
                
                # Get total count on first request
                if total_jobs is None:
                    total_jobs = result.get('totalJobs', 0)
                    logger.info(f"Found {total_jobs} total jobs")
                
                # Extract jobs from response
                job_list = result.get('jobs', [])
                
                if not job_list:
                    break
                
                # Parse each job
                for job_data in job_list:
                    job = self._parse_job(job_data, company_name, company_description, label)
                    if job:
                        jobs.append(job)
                
                logger.info(f"📄 Page {page}: {len(job_list)} jobs (total: {len(jobs)})")
                
                # Check if we've got all jobs
                if len(jobs) >= total_jobs:
                    break
                
                # Move to next page
                page += 1
                time.sleep(self.delay)
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching page {page}: {e}")
                break
            except Exception as e:
                logger.error(f"Error parsing response for page {page}: {e}")
                break
        
        return jobs
    
    def _parse_job(self, job_data: dict, company_name: str, company_description: str, label: str) -> Dict:
        """
        Parse a single job from Microsoft API response
        
        Args:
            job_data: Job data from API
            company_name: Company name
            company_description: Description
            label: Label
            
        Returns:
            Standardized job dictionary
        """
        try:
            # Extract basic info
            job_id = job_data.get('jobId', '')
            title = job_data.get('title', '')
            
            # Build job URL
            job_url = f"https://careers.microsoft.com/us/en/job/{job_id}" if job_id else ''
            
            # Location
            location = job_data.get('primaryLocation', '') or job_data.get('locations', '')
            
            # Description (HTML format)
            description = job_data.get('description', '')
            
            # Clean HTML from description
            description = self._clean_html(description)
            
            # Department from profession and discipline
            profession = job_data.get('profession', '')
            discipline = job_data.get('discipline', '')
            
            department_parts = []
            if profession:
                department_parts.append(profession)
            if discipline:
                department_parts.append(discipline)
            department = ' / '.join(department_parts) if department_parts else ''
            
            # Employment type
            employment_type = job_data.get('employmentType', '')
            if not employment_type or employment_type == 'Full-Time':
                employment_type = 'FullTime'
            elif 'Part' in employment_type:
                employment_type = 'PartTime'
            
            # Posted date
            posted_date = job_data.get('postingDate', '')
            # Clean up the date format if needed
            if posted_date:
                # Remove timezone info and reformat if necessary
                posted_date = posted_date.split('T')[0] if 'T' in posted_date else posted_date
            
            # Remote status from workSiteFlexibility
            work_flexibility = job_data.get('workSiteFlexibility', '')
            remote = 'No'
            
            if work_flexibility:
                work_flex_lower = work_flexibility.lower()
                if 'remote' in work_flex_lower or '100%' in work_flex_lower:
                    remote = 'Yes'
                elif 'hybrid' in work_flex_lower or 'day' in work_flex_lower:
                    remote = 'Hybrid'
            
            # Also check location and title
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
                'Job Description': description,
                'Employment Type': employment_type,
                'Department': department,
                'Posted Date': posted_date,
                'Company Description': company_description,
                'Remote': remote,
                'Label': label,
                'ATS': 'Microsoft Careers'
            }
            
            return job
            
        except Exception as e:
            logger.debug(f"Error parsing job: {e}")
            return None
    
    def _clean_html(self, text: str) -> str:
        """Remove HTML tags from text"""
        if not text:
            return ''
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Decode HTML entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
