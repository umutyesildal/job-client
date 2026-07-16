"""
BambooHR ATS Scraper - API-based
Scrapes job listings from BambooHR API
"""

import requests
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class BambooHRScraper:
    def __init__(self, delay: float = 0.2):
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def scrape_jobs(self, url: str, company_name: str, company_description: str = '', label: str = '') -> List[Dict]:
        """
        Scrape jobs from BambooHR API
        
        Args:
            url: BambooHR career page URL (e.g., https://bluelayer.bamboohr.com/careers/list)
                 or any bamboohr.com URL
            company_name: Name of the company
            company_description: Description of the company
            label: Company label/category
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        
        try:
            # Extract company slug from URL
            # e.g., "bluelayer" from https://bluelayer.bamboohr.com/careers/list
            if '.bamboohr.com' in url:
                company_slug = url.split('//')[1].split('.bamboohr.com')[0]
            else:
                return []
            
            # Construct API URL
            api_url = f"https://{company_slug}.bamboohr.com/careers/list"
            
            response = self.session.get(api_url, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            for job_data in data.get('result', []):
                try:
                    # Get location
                    location_data = job_data.get('location', {})
                    city = location_data.get('city', '') if location_data else ''
                    state = location_data.get('state', '') if location_data else ''
                    
                    location_parts = []
                    if city:
                        location_parts.append(city)
                    if state:
                        location_parts.append(state)
                    location = ', '.join(location_parts)
                    
                    # Remote status
                    is_remote = job_data.get('isRemote')
                    remote = 'Yes' if is_remote else 'No'
                    
                    # Job URL
                    job_id = job_data.get('id', '')
                    job_url = f"https://{company_slug}.bamboohr.com/careers/{job_id}"
                    
                    job = {
                        'Company Name': company_name,
                        'Job Title': job_data.get('jobOpeningName', ''),
                        'Location': location,
                        'Job Link': job_url,
                        'Job Description': '',  # BambooHR API doesn't include full description
                        'Employment Type': job_data.get('employmentStatusLabel', ''),
                        'Department': job_data.get('departmentLabel', ''),
                        'Posted Date': '',  # Not provided in this API response
                        'Company Description': company_description,
                        'Remote': remote,
                        'Label': label,
                        'ATS': 'BambooHR'
                    }
                    jobs.append(job)
                except Exception as e:
                    continue
            
        except Exception as e:
            pass
        
        return jobs
