"""
Recruitee ATS Scraper - API-based
Scrapes job listings from Recruitee API
"""

import requests
import logging
from typing import List, Dict
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class RecruiteeScraper:
    def __init__(self, delay: float = 0.2):
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def scrape_jobs(self, url: str, company_name: str, company_description: str = '', label: str = '') -> List[Dict]:
        """
        Scrape jobs from Recruitee API
        
        Args:
            url: Recruitee career page URL (e.g., https://zeotap.recruitee.com)
                 or direct API URL (e.g., https://zeotap.recruitee.com/api/offers)
            company_name: Name of the company
            company_description: Description of the company
            label: Company label/category
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        
        try:
            # Check if URL is already an API URL
            if '/api/offers' in url:
                api_url = url
            else:
                # Extract company slug and construct API URL
                # e.g., "zeotap" from https://zeotap.recruitee.com
                if '.recruitee.com' in url:
                    company_slug = url.split('//')[1].split('.recruitee.com')[0]
                    api_url = f"https://{company_slug}.recruitee.com/api/offers"
                else:
                    return []
            
            response = self.session.get(api_url, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            for job_data in data.get('offers', []):
                try:
                    # Get location from locations array
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
                    
                    # Fallback to individual fields
                    if not location_parts:
                        city = job_data.get('city', '')
                        country = job_data.get('country', '')
                        if city:
                            location_parts.append(city)
                        if country:
                            location_parts.append(country)
                    
                    location = ', '.join(location_parts) if location_parts else job_data.get('location', '')
                    
                    # Clean HTML description
                    description_html = job_data.get('description', '')
                    description_plain = BeautifulSoup(description_html, 'html.parser').get_text(separator=' ', strip=True) if description_html else ''
                    
                    # Determine remote status
                    remote = 'Yes' if job_data.get('remote') or job_data.get('hybrid') else 'No'
                    
                    job = {
                        'Company Name': company_name,
                        'Job Title': job_data.get('title', ''),
                        'Location': location,
                        'Job Link': job_data.get('careers_url', ''),
                        'Job Description': description_plain,
                        'Employment Type': job_data.get('employment_type_code', '').replace('_', ' ').title(),
                        'Department': job_data.get('department', ''),
                        'Posted Date': job_data.get('published_at', '').split(' ')[0] if job_data.get('published_at') else '',
                        'Company Description': company_description,
                        'Remote': remote,
                        'Label': label,
                        'ATS': 'Recruitee'
                    }
                    jobs.append(job)
                except Exception as e:
                    continue
            
        except Exception as e:
            pass
        
        return jobs
