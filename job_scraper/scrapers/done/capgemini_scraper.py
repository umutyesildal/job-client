"""
Capgemini Jobs Scraper
Scrapes job listings from Capgemini's WordPress Jobs API
"""

import requests
import logging
import time
from typing import List, Dict
from urllib.parse import urlparse, parse_qs
import re

logger = logging.getLogger(__name__)


class CapgeminiScraper:
    """
    Scraper for Capgemini Jobs (https://www.capgemini.com)
    
    Capgemini uses a WordPress JSON API endpoint for job search.
    URL format: https://www.capgemini.com/wp-json/macs/v1/jobs?country={code}&size={n}
    
    API supports:
    - Country-based filtering
    - Pagination via size parameter
    - Returns total count for verification
    """
    
    BASE_API_URL = "https://www.capgemini.com/wp-json/macs/v1/jobs"
    
    def __init__(self, delay: float = 1.0):
        self.delay = delay
        self.session = requests.Session()
    
    def _extract_country_from_url(self, url: str) -> str:
        """
        Extract country code from Capgemini jobs URL
        
        Args:
            url: Capgemini jobs URL
            
        Returns:
            Country code (e.g., 'DE', 'US')
        """
        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            
            if 'country' in params:
                return params['country'][0]
            
            # Try to extract from URL path or default to DE (Germany)
            if '/de/' in url.lower() or 'germany' in url.lower():
                return 'DE'
            
            logger.info("No country code found, defaulting to DE (Germany)")
            return 'DE'
            
        except Exception as e:
            logger.debug(f"Error parsing URL: {e}")
            return 'DE'
    
    def scrape_jobs(self, url: str, company_name: str, company_description: str = '', label: str = '') -> List[Dict]:
        """
        Scrape jobs from Capgemini Jobs API
        
        Args:
            url: Capgemini jobs URL
            company_name: Name of the company
            company_description: Description
            label: Company label
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        
        # Extract country code
        country = self._extract_country_from_url(url)
        logger.info(f"Scraping Capgemini jobs for country: {country}")
        
        # Build API URL
        api_url = f"{self.BASE_API_URL}?country={country}"
        
        # Set headers
        headers = {
            'accept': 'application/json',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'referer': 'https://www.capgemini.com/'
        }
        
        # Request parameters
        params = {
            'size': 500  # Try to get all jobs at once
        }
        
        try:
            response = self.session.get(api_url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            jobs_data = data.get('jobs', [])
            total_jobs = data.get('total', 0)
            
            logger.info(f"Found {len(jobs_data)} jobs (total: {total_jobs})")
            
            # Parse each job
            for job_data in jobs_data:
                job = self._parse_job(job_data, company_name, company_description, label)
                if job:
                    jobs.append(job)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Capgemini jobs: {e}")
        except Exception as e:
            logger.error(f"Error parsing Capgemini response: {e}")
        
        return jobs
    
    def _parse_job(self, job_data: dict, company_name: str, company_description: str, label: str) -> Dict:
        """
        Parse a single job from Capgemini API response
        
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
            
            # Job URL
            job_url = job_data.get('apply_job_url', '')
            
            # Location
            location = job_data.get('location', '')
            
            # Description (HTML format)
            description = job_data.get('description', '')
            
            # Clean HTML from description
            description = self._clean_html(description)
            
            # Contract type / Employment type
            contract_type = job_data.get('contract_type', '')
            employment_type = 'FullTime'
            if 'befristet' in contract_type.lower() or 'temporary' in contract_type.lower():
                employment_type = 'Temporary'
            elif 'praktikum' in contract_type.lower() or 'intern' in contract_type.lower():
                employment_type = 'Internship'
            elif 'teilzeit' in contract_type.lower() or 'part' in contract_type.lower():
                employment_type = 'PartTime'
            
            # Department
            department = job_data.get('professional_communities', '') or job_data.get('department', '')
            
            # Experience level
            experience = job_data.get('experience_level', '')
            if experience:
                department = f"{department} - {experience}" if department else experience
            
            # Posted/Updated date
            updated_at = job_data.get('updated_at', '')
            posted_date = ''
            if updated_at:
                try:
                    # Convert unix timestamp to readable format
                    from datetime import datetime
                    posted_date = datetime.fromtimestamp(int(updated_at)).strftime('%Y-%m-%d')
                except:
                    posted_date = str(updated_at)
            
            # Remote status
            remote = 'No'
            location_lower = location.lower()
            title_lower = title.lower()
            desc_lower = description.lower() if description else ''
            
            if 'remote' in location_lower or 'remote' in title_lower or 'remote' in desc_lower:
                remote = 'Yes'
            elif 'hybrid' in location_lower or 'hybrid' in title_lower or 'hybrid' in desc_lower:
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
                'ATS': 'Capgemini'
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
