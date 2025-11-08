"""
Ashby ATS Scraper - API-based
Scrapes job listings from Ashby API
"""

import requests
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class AshbyScraper:
    def __init__(self, delay: float = 0.2):
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def scrape_jobs(self, url: str, company_name: str, company_description: str = '', label: str = '') -> List[Dict]:
        """
        Scrape jobs from Ashby API
        
        Args:
            url: Ashby career page URL (e.g., https://jobs.ashbyhq.com/9fin)
            company_name: Name of the company
            company_description: Description of the company
            label: Company label/category
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        
        try:
            # Extract company slug from URL (e.g., "9fin" from https://jobs.ashbyhq.com/9fin)
            company_slug = url.rstrip('/').split('/')[-1]
            
            # Construct API URL
            api_url = f"https://api.ashbyhq.com/posting-api/job-board/{company_slug}?includeCompensation=true"
            
            response = self.session.get(api_url, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            for job_data in data.get('jobs', []):
                try:
                    job = {
                        'Company Name': company_name,
                        'Job Title': job_data.get('title', ''),
                        'Location': job_data.get('location', ''),
                        'Job Link': job_data.get('jobUrl', ''),
                        'Job Description': job_data.get('descriptionPlain', ''),
                        'Employment Type': job_data.get('employmentType', ''),
                        'Department': job_data.get('department', ''),
                        'Posted Date': job_data.get('publishedAt', '').split('T')[0] if job_data.get('publishedAt') else '',
                        'Company Description': company_description,
                        'Remote': 'Yes' if job_data.get('isRemote') else 'No',
                        'Label': label,
                        'ATS': 'Ashby'
                    }
                    jobs.append(job)
                except Exception as e:
                    continue
            
        except Exception as e:
            pass
        
        return jobs

