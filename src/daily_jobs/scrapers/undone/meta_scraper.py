"""
Meta Careers (Facebook) Scraper
Scrapes job listings from Meta's careers GraphQL API

STATUS: NOT WORKING
REASON: GraphQL API changed - doc_id and payload format need to be updated
ERROR: 400 Bad Request when calling https://www.metacareers.com/graphql
SOLUTION NEEDED: Inspect browser network traffic to get current doc_id and request format
"""

import requests
import logging
import json
from typing import List, Dict
from urllib.parse import urlparse, parse_qs
import re

logger = logging.getLogger(__name__)


class MetaScraper:
    """
    Scraper for Meta Careers (https://www.metacareers.com)
    
    Meta uses a GraphQL API endpoint for job search.
    URL format: https://www.metacareers.com/graphql (POST)
    
    API supports:
    - Location-based search via 'q' parameter
    - Team/division filtering
    - Remote/leadership filters
    - Returns all jobs and featured jobs
    """
    
    BASE_API_URL = "https://www.metacareers.com/graphql"
    
    def __init__(self, delay: float = 1.0):
        self.delay = delay
        self.session = requests.Session()
    
    def _extract_location_from_url(self, url: str) -> str:
        """
        Extract location search term from Meta careers URL
        
        Args:
            url: Meta careers URL
            
        Returns:
            Location search term
        """
        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            
            # Check for location in query params
            if 'location' in params:
                return params['location'][0]
            if 'q' in params:
                return params['q'][0]
            
            # Try to extract from URL path
            path = parsed.path.lower()
            if 'berlin' in path:
                return 'berlin'
            elif 'germany' in path:
                return 'germany'
            elif 'london' in path:
                return 'london'
            
            # Default to empty (all locations)
            logger.info("No location filter found, searching all Meta jobs")
            return ''
            
        except Exception as e:
            logger.debug(f"Error parsing URL: {e}")
            return ''
    
    def scrape_jobs(self, url: str, company_name: str, company_description: str = '', label: str = '') -> List[Dict]:
        """
        Scrape jobs from Meta Careers GraphQL API
        
        Args:
            url: Meta careers URL
            company_name: Name of the company
            company_description: Description
            label: Company label
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        
        # Extract location search term
        location_query = self._extract_location_from_url(url)
        if location_query:
            logger.info(f"Searching Meta jobs with location: {location_query}")
        else:
            logger.info("Searching all Meta jobs (no location filter)")
        
        # Set headers
        headers = {
            'accept': '*/*',
            'content-type': 'application/json',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
            'referer': 'https://www.metacareers.com/jobs',
            'origin': 'https://www.metacareers.com'
        }
        
        # Build GraphQL payload - simplified
        payload = {
            "operationName": "SearchResultsPageQuery",
            "variables": {
                "search_input": {
                    "q": location_query,
                    "divisions": [],
                    "offices": [],
                    "roles": [],
                    "leadership_levels": [],
                    "is_leadership": False,
                    "is_remote_only": False
                },
                "page": 1
            },
            "doc_id": "8943193319054290"
        }
        
        try:
            response = self.session.post(self.BASE_API_URL, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract jobs from response
            job_search_data = data.get('data', {}).get('job_search_with_featured_jobs', {})
            
            # Get both all jobs and featured jobs
            all_jobs = job_search_data.get('all_jobs', [])
            featured_jobs = job_search_data.get('featured_jobs', [])
            
            # Combine (featured jobs might be duplicates)
            all_job_ids = set()
            combined_jobs = []
            
            for job_data in all_jobs + featured_jobs:
                job_id = job_data.get('id')
                if job_id not in all_job_ids:
                    all_job_ids.add(job_id)
                    combined_jobs.append(job_data)
            
            logger.info(f"Found {len(combined_jobs)} total jobs (all: {len(all_jobs)}, featured: {len(featured_jobs)})")
            
            # Parse each job
            for job_data in combined_jobs:
                job = self._parse_job(job_data, company_name, company_description, label)
                if job:
                    jobs.append(job)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching jobs: {e}")
        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            logger.debug(f"Response content: {response.text[:500] if 'response' in locals() else 'N/A'}")
        
        return jobs
    
    def _parse_job(self, job_data: dict, company_name: str, company_description: str, label: str) -> Dict:
        """
        Parse a single job from Meta API response
        
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
            job_id = job_data.get('id', '')
            title = job_data.get('title', '')
            
            # Build job URL
            job_url = f"https://www.metacareers.com/jobs/{job_id}/" if job_id else ''
            
            # Locations (array of strings)
            locations = job_data.get('locations', [])
            location = ', '.join(locations) if locations else ''
            
            # Teams and sub_teams
            teams = job_data.get('teams', [])
            sub_teams = job_data.get('sub_teams', [])
            
            # Build department from teams
            department_parts = []
            if teams:
                department_parts.extend(teams)
            if sub_teams:
                department_parts.extend(sub_teams)
            department = ' / '.join(department_parts) if department_parts else ''
            
            # Remote status
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
                'Employment Type': 'FullTime',  # Meta typically posts full-time roles
                'Department': department,
                'Posted Date': '',  # Not provided in list view
                'Company Description': company_description,
                'Remote': remote,
                'Label': label,
                'ATS': 'Meta Careers'
            }
            
            return job
            
        except Exception as e:
            logger.debug(f"Error parsing job: {e}")
            return None
