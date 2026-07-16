"""
Workable ATS Scraper - API-based
Scrapes job listings from Workable API
"""

import requests
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class WorkableScraper:
    def __init__(self, delay: float = 0.2):
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def scrape_jobs(self, url: str, company_name: str, company_description: str = '', label: str = '') -> List[Dict]:
        """
        Scrape jobs from Workable API
        
        Args:
            url: Workable career page URL (e.g., https://apply.workable.com/soda-data-nv)
                 or direct API URL
            company_name: Name of the company
            company_description: Description of the company
            label: Company label/category
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        
        try:
            # Check if URL is already an API URL
            if '/api/v1/widget/accounts/' in url:
                api_url = url
            else:
                # Extract company slug from URL
                company_slug = url.rstrip('/').split('/')[-1]
                # Construct API URL
                api_url = f"https://apply.workable.com/api/v1/widget/accounts/{company_slug}"
            
            response = self.session.get(api_url, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            for job_data in data.get('jobs', []):
                try:
                    # Get location
                    locations = job_data.get('locations', [])
                    location_parts = []
                    if locations:
                        loc = locations[0]
                        city = loc.get('city', '')
                        country = loc.get('country', '')
                        if city:
                            location_parts.append(city)
                        if country:
                            location_parts.append(country)
                    location = ', '.join(location_parts) if location_parts else job_data.get('city', '')
                    
                    job = {
                        'Company Name': company_name,
                        'Job Title': job_data.get('title', ''),
                        'Location': location,
                        'Job Link': job_data.get('url', ''),
                        'Job Description': '',
                        'Employment Type': job_data.get('employment_type', ''),
                        'Department': job_data.get('department', '') or job_data.get('function', ''),
                        'Posted Date': job_data.get('published_on', ''),
                        'Company Description': company_description,
                        'Remote': 'Yes' if job_data.get('telecommuting') else 'No',
                        'Label': label,
                        'ATS': 'Workable'
                    }
                    jobs.append(job)
                except Exception as e:
                    continue
            
        except Exception as e:
            pass
        
        return jobs
