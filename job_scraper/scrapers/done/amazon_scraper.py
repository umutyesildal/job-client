"""
Amazon Jobs Scraper
Scrapes job listings from Amazon's public jobs search API
"""

import requests
import logging
import time
from typing import List, Dict
from urllib.parse import urlparse, parse_qs
import re

logger = logging.getLogger(__name__)


class AmazonScraper:
    """
    Scraper for Amazon Jobs (https://www.amazon.jobs)
    
    Amazon uses a public JSON API endpoint for job search.
    URL format: https://www.amazon.jobs/en/search.json
    
    API supports:
    - Pagination via offset and result_limit
    - Geographic filters (country, city, region)
    - Keyword search
    - Various job filters (category, schedule, etc.)
    """
    
    BASE_API_URL = "https://www.amazon.jobs/en/search.json"
    
    def __init__(self, delay: float = 1.0):
        self.delay = delay
        self.session = requests.Session()
    
    def _extract_filters_from_url(self, url: str) -> dict:
        """
        Extract search filters from Amazon jobs URL
        
        Args:
            url: Amazon jobs URL (e.g., https://www.amazon.jobs/en/search?...)
            
        Returns:
            Dictionary of filters (simplified to get ALL jobs)
        """
        filters = {}
        
        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            
            # Only extract location filters to get ALL jobs in that location
            # Ignore schedule_type_id and other restrictive filters
            
            if 'country' in params:
                filters['country'] = params['country'][0]
                logger.info(f"Filtering by country: {filters['country']}")
            
            if 'loc_query' in params:
                filters['loc_query'] = params['loc_query'][0]
                logger.info(f"Filtering by location: {filters['loc_query']}")
            
            if 'city' in params:
                filters['city'] = params['city'][0]
                logger.info(f"Filtering by city: {filters['city']}")
            
            if 'region' in params:
                filters['region'] = params['region'][0]
                logger.info(f"Filtering by region: {filters['region']}")
            
            # If no location filters found, it's a general search for all jobs
            if not filters:
                logger.info("No location filters found, searching all Amazon jobs globally")
            
        except Exception as e:
            logger.debug(f"Error parsing URL filters: {e}")
        
        return filters
    
    def scrape_jobs(self, url: str, company_name: str, company_description: str = '', label: str = '') -> List[Dict]:
        """
        Scrape jobs from Amazon Jobs API
        
        Args:
            url: Amazon jobs URL (career page or search URL)
            company_name: Name of the company (should be "Amazon")
            company_description: Description
            label: Company label
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        
        # Extract any filters from the URL
        filters = self._extract_filters_from_url(url)
        
        # Set headers
        headers = {
            'accept': 'application/json',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
            'referer': 'https://www.amazon.jobs/en/'
        }
        
        # Pagination parameters
        offset = 0
        result_limit = 100  # Maximum recommended for faster scraping
        total_jobs = None
        
        while True:
            # Build request parameters
            params = {
                'offset': offset,
                'result_limit': result_limit,
                'sort': 'relevant',
            }
            
            # Add any extracted filters
            params.update(filters)
            
            try:
                response = self.session.get(self.BASE_API_URL, headers=headers, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                
                # Get total count on first request
                if total_jobs is None:
                    total_jobs = data.get('hits', 0)
                    logger.info(f"Found {total_jobs} total jobs")
                
                # Extract jobs from response
                job_list = data.get('jobs', [])
                
                if not job_list:
                    break
                
                # Parse each job
                for job_data in job_list:
                    job = self._parse_job(job_data, company_name, company_description, label)
                    if job:
                        jobs.append(job)
                
                logger.info(f"📄 Offset {offset}: {len(job_list)} jobs (total: {len(jobs)})")
                
                # Check if we've got all jobs
                if len(jobs) >= total_jobs or len(job_list) < result_limit:
                    break
                
                # Move to next page
                offset += result_limit
                time.sleep(self.delay)
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching jobs at offset {offset}: {e}")
                break
            except Exception as e:
                logger.error(f"Error parsing response at offset {offset}: {e}")
                break
        
        return jobs
    
    def _parse_job(self, job_data: dict, company_name: str, company_description: str, label: str) -> Dict:
        """
        Parse a single job from Amazon API response
        
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
            title = job_data.get('title', '')
            job_id = job_data.get('id', '')
            
            # Build job URL
            job_path = job_data.get('job_path', '')
            if job_path:
                job_url = f"https://www.amazon.jobs{job_path}"
            else:
                job_url = job_data.get('url_next_step', '')
            
            # Location info
            city = job_data.get('city', '')
            state = job_data.get('state', '')
            country = job_data.get('country_code', '')
            
            # Build location string
            location_parts = [p for p in [city, state, country] if p]
            location = ', '.join(location_parts) if location_parts else job_data.get('location', '')
            
            # Job description
            description_short = job_data.get('description_short', '')
            description_full = job_data.get('description', '')
            basic_qualifications = job_data.get('basic_qualifications', '')
            preferred_qualifications = job_data.get('preferred_qualifications', '')
            
            # Combine descriptions
            description_parts = []
            if description_short:
                description_parts.append(description_short)
            if description_full:
                description_parts.append(description_full)
            if basic_qualifications:
                description_parts.append(f"Basic Qualifications: {basic_qualifications}")
            if preferred_qualifications:
                description_parts.append(f"Preferred Qualifications: {preferred_qualifications}")
            
            description = '\n\n'.join(description_parts)
            
            # Clean HTML from description
            description = self._clean_html(description)
            
            # Department/Category
            department = job_data.get('business_category', '') or job_data.get('job_category', '')
            
            # Employment type from schedule
            schedule = job_data.get('schedule_type_id', '')
            employment_type = 'FullTime' if 'full' in schedule.lower() else ''
            
            # Posted date
            posted_date = job_data.get('posted_date', '')
            
            # Remote status
            remote = 'No'
            if 'virtual' in location.lower() or 'remote' in location.lower():
                remote = 'Yes'
            elif 'hybrid' in location.lower():
                remote = 'Hybrid'
            
            # Check if manager or intern
            is_manager = job_data.get('is_manager', 0)
            is_intern = job_data.get('is_intern', 0)
            
            if is_manager:
                department = f"{department} - Manager" if department else "Manager"
            if is_intern:
                department = f"{department} - Intern" if department else "Intern"
            
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
                'ATS': 'Amazon Jobs'
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
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
