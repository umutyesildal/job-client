"""
Lingoda (PinpointHQ) Scraper
Scrapes job listings from Lingoda's PinpointHQ API
"""

import requests
import logging
import re
from typing import List, Dict
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class LingodaScraper:
    """
    Scraper for Lingoda Careers (https://lingoda.pinpointhq.com)
    
    Lingoda uses PinpointHQ platform with a simple JSON API.
    URL format: https://lingoda.pinpointhq.com/postings.json
    
    API returns all jobs in a single request (no pagination).
    """
    
    API_URL = "https://lingoda.pinpointhq.com/postings.json"
    
    def __init__(self, delay: float = 0.2):
        self.delay = delay
        self.session = requests.Session()
    
    def scrape_jobs(self, url: str, company_name: str, company_description: str = '', label: str = '') -> List[Dict]:
        """
        Scrape jobs from Lingoda PinpointHQ API
        
        Args:
            url: Lingoda careers URL
            company_name: Name of the company
            company_description: Description
            label: Company label
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        
        headers = {
            'accept': 'application/json',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        try:
            response = self.session.get(self.API_URL, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            postings = data.get('data', [])
            
            logger.info(f"Found {len(postings)} jobs from Lingoda")
            
            for job_data in postings:
                job = self._parse_job(job_data, company_name, company_description, label)
                if job:
                    jobs.append(job)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Lingoda jobs: {e}")
        except Exception as e:
            logger.error(f"Error parsing Lingoda response: {e}")
        
        return jobs
    
    def _parse_job(self, job_data: dict, company_name: str, company_description: str, label: str) -> Dict:
        """
        Parse a single job from Lingoda PinpointHQ API response
        
        Args:
            job_data: Job data from API
            company_name: Company name
            company_description: Description
            label: Label
            
        Returns:
            Standardized job dictionary
        """
        try:
            title = job_data.get('title', '')
            job_url = job_data.get('url', '')
            
            # Location
            location_data = job_data.get('location', {})
            location_parts = []
            if location_data:
                city = location_data.get('city', '')
                province = location_data.get('province', '')
                country = location_data.get('country', '')
                name = location_data.get('name', '')
                
                if name:
                    location_parts.append(name)
                elif city or province or country:
                    if city:
                        location_parts.append(city)
                    if province and province != city:
                        location_parts.append(province)
                    if country:
                        location_parts.append(country)
            
            location = ', '.join(location_parts) if location_parts else ''
            
            # Department
            department = ''
            job_info = job_data.get('job', {})
            if job_info:
                dept_info = job_info.get('department', {})
                if dept_info:
                    department = dept_info.get('name', '')
                
                # Fallback to division
                if not department:
                    div_info = job_info.get('division', {})
                    if div_info:
                        department = div_info.get('name', '')
            
            # Employment type
            employment_type_raw = job_data.get('employment_type', '')
            employment_type = 'FullTime'
            
            if employment_type_raw:
                emp_lower = employment_type_raw.lower()
                if 'part' in emp_lower or 'teilzeit' in emp_lower:
                    employment_type = 'PartTime'
                elif 'freelance' in emp_lower or 'contractor' in emp_lower:
                    employment_type = 'Contractor'
                elif 'intern' in emp_lower or 'praktikum' in emp_lower:
                    employment_type = 'Internship'
            
            # Remote status
            workplace_type = job_data.get('workplace_type', '').lower()
            remote = 'No'
            
            if 'remote' in workplace_type:
                remote = 'Yes'
            elif 'hybrid' in workplace_type:
                remote = 'Hybrid'
            
            # Also check location
            if location and ('remote' in location.lower()):
                remote = 'Yes'
            
            # Description (clean HTML)
            description = job_data.get('description', '')
            if description:
                description = self._clean_html(description)
            
            # Posted date (not provided in API)
            posted_date = ''
            
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
                'ATS': 'Lingoda (PinpointHQ)'
            }
            
            return job
            
        except Exception as e:
            logger.debug(f"Error parsing job: {e}")
            return None
    
    def _clean_html(self, html_content: str) -> str:
        """Remove HTML tags and clean up text"""
        if not html_content:
            return ''
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            text = soup.get_text(separator=' ', strip=True)
            text = re.sub(r'\s+', ' ', text)
            return text.strip()
        except:
            return html_content
