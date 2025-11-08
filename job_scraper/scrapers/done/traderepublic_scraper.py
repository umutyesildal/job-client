"""
Trade Republic Scraper
Scrapes job listings from Trade Republic's careers API
"""

import requests
import logging
import re
from typing import List, Dict
from bs4 import BeautifulSoup
from datetime import datetime

logger = logging.getLogger(__name__)


class TradeRepublicScraper:
    """
    Scraper for Trade Republic Careers (https://traderepublic.com/careers)
    
    Trade Republic uses a simple JSON API that returns all jobs in one request.
    URL format: https://api.traderepublic.com/api/v1/career/jobs?content=true
    
    API returns all jobs in a single response (no pagination).
    """
    
    API_URL = "https://api.traderepublic.com/api/v1/career/jobs"
    
    def __init__(self, delay: float = 0.2):
        self.delay = delay
        self.session = requests.Session()
    
    def scrape_jobs(self, url: str, company_name: str, company_description: str = '', label: str = '') -> List[Dict]:
        """
        Scrape jobs from Trade Republic API
        
        Args:
            url: Trade Republic careers URL
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
        
        params = {
            'content': 'true'  # Get full content
        }
        
        try:
            response = self.session.get(self.API_URL, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            job_list = data.get('jobs', [])
            
            logger.info(f"Found {len(job_list)} jobs from Trade Republic")
            
            for job_data in job_list:
                job = self._parse_job(job_data, company_name, company_description, label)
                if job:
                    jobs.append(job)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Trade Republic jobs: {e}")
        except Exception as e:
            logger.error(f"Error parsing Trade Republic response: {e}")
        
        return jobs
    
    def _parse_job(self, job_data: dict, company_name: str, company_description: str, label: str) -> Dict:
        """
        Parse a single job from Trade Republic API response
        
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
            job_url = job_data.get('absolute_url', '')
            
            # Location - combine location and offices
            location_parts = []
            
            # Check location object
            location_obj = job_data.get('location', {})
            if location_obj and isinstance(location_obj, dict):
                loc_name = location_obj.get('name', '')
                if loc_name and loc_name != 'Headquarter':
                    location_parts.append(loc_name)
            
            # Check offices array
            offices = job_data.get('offices', [])
            if offices:
                for office in offices:
                    office_name = office.get('name', '')
                    office_location = office.get('location', '')
                    
                    if office_name and office_name not in location_parts:
                        location_parts.append(office_name)
                    elif office_location and office_location not in location_parts:
                        location_parts.append(office_location)
            
            location = ', '.join(location_parts) if location_parts else ''
            
            # Department
            department = ''
            departments = job_data.get('departments', [])
            if departments:
                dept_names = [d.get('name', '') for d in departments if d.get('name')]
                department = ', '.join(dept_names)
            
            # Posted date
            posted_date = ''
            first_published = job_data.get('first_published', '')
            if first_published:
                try:
                    # Parse ISO timestamp
                    dt = datetime.fromisoformat(first_published.replace('Z', '+00:00'))
                    posted_date = dt.strftime('%Y-%m-%d')
                except:
                    posted_date = ''
            
            # Employment type (default to FullTime)
            employment_type = 'FullTime'
            title_lower = title.lower()
            
            if 'intern' in title_lower or 'praktikum' in title_lower:
                employment_type = 'Internship'
            elif 'working student' in title_lower or 'werkstudent' in title_lower:
                employment_type = 'PartTime'
            
            # Remote detection
            remote = 'No'
            location_lower = location.lower()
            
            if 'remote' in location_lower or 'remote' in title_lower:
                remote = 'Yes'
            elif 'hybrid' in location_lower or 'hybrid' in title_lower:
                remote = 'Hybrid'
            
            # Description (clean HTML content)
            content = job_data.get('content', '')
            description = ''
            if content:
                description = self._clean_html(content)
            
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
                'ATS': 'Trade Republic'
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
