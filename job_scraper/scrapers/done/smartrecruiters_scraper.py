"""
SmartRecruiters ATS Scraper
Scrapes job listings from SmartRecruiters HTML API
"""

import requests
from bs4 import BeautifulSoup
import logging
import time
from typing import List, Dict
from urllib.parse import urlparse
import re

logger = logging.getLogger(__name__)


class SmartRecruitarsScraper:
    """
    Scraper for SmartRecruiters ATS platform (HTML-based)
    
    SmartRecruiters uses HTML endpoints that return grouped job listings by location.
    URL format: https://careers.smartrecruiters.com/{company}/{section}/api/groups?page={n}
    """
    
    def __init__(self, delay: float = 0.2):
        self.delay = delay
        self.session = requests.Session()
    
    def _extract_company_and_section(self, url: str) -> tuple:
        """
        Extract company and section from SmartRecruiters URL
        
        Args:
            url: URL like https://careers.smartrecruiters.com/Flink3/joinus/api/groups
                 or https://careers.smartrecruiters.com/DeliveryHero
            
        Returns:
            Tuple of (company, section) e.g., ('Flink3', 'joinus') or ('DeliveryHero', None)
        """
        try:
            parsed = urlparse(url)
            # Remove /api/groups if present
            path = parsed.path.strip('/').replace('/api/groups', '')
            parts = path.split('/')
            
            if len(parts) >= 2:
                company = parts[0]
                section = parts[1]
                return company, section
            elif len(parts) == 1 and parts[0]:
                # Just company, no section (e.g., /DeliveryHero)
                company = parts[0]
                return company, None
            
            logger.error(f"Could not extract company/section from URL: {url}")
            return None, None
        except Exception as e:
            logger.error(f"Error extracting company info: {e}")
            return None, None
    
    def scrape_jobs(self, url: str, company_name: str, company_description: str = '', label: str = '') -> List[Dict]:
        """
        Scrape jobs from SmartRecruiters HTML API
        
        Args:
            url: SmartRecruiters API URL (e.g., https://careers.smartrecruiters.com/Flink3/joinus/api/groups)
            company_name: Name of the company
            company_description: Description
            label: Company label
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        
        company, section = self._extract_company_and_section(url)
        if company is None:
            logger.error(f"Invalid SmartRecruiters URL: {url}")
            return jobs
        
        # Set headers
        headers = {
            'accept': '*/*',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
            'referer': f'https://careers.smartrecruiters.com/{company}'
        }
        
        # Pagination loop
        page = 1
        total_jobs = 0
        
        while True:
            # Build API URL
            if section:
                api_url = f"https://careers.smartrecruiters.com/{company}/{section}/api/groups"
            else:
                api_url = f"https://careers.smartrecruiters.com/{company}/api/groups"
            params = {'page': page}
            
            try:
                response = self.session.get(api_url, headers=headers, params=params, timeout=30)
                response.raise_for_status()
                
                # Parse HTML response
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find all job sections
                sections = soup.find_all('section', class_='openings-section')
                
                if not sections:
                    break
                
                page_jobs = 0
                for job_section in sections:
                    # Extract location/group from header
                    location_header = job_section.find('h3', class_='opening-title')
                    location = location_header.get_text(strip=True) if location_header else ''
                    
                    # Find all jobs in this location group
                    job_items = job_section.find_all('li', class_='opening-job')
                    
                    for job_item in job_items:
                        job = self._parse_job(job_item, location, company_name, company_description, label)
                        if job:
                            jobs.append(job)
                            page_jobs += 1
                
                total_jobs += page_jobs
                logger.info(f"📄 Page {page}: {page_jobs} jobs (total: {total_jobs})")
                
                # If no jobs found on this page, we're done
                if page_jobs == 0:
                    break
                
                page += 1
                time.sleep(self.delay)
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching page {page}: {e}")
                break
            except Exception as e:
                logger.error(f"Error parsing response for page {page}: {e}")
                break
        
        return jobs
    
    def _parse_job(self, job_item, location: str, company_name: str, company_description: str, label: str) -> Dict:
        """
        Parse a single job from SmartRecruiters HTML
        
        Args:
            job_item: BeautifulSoup job item element
            location: Location/group name
            company_name: Company name
            company_description: Description
            label: Label
            
        Returns:
            Standardized job dictionary
        """
        try:
            # Find the job link
            job_link = job_item.find('a')
            if not job_link:
                return None
            
            job_url = job_link.get('href', '')
            
            # Extract job title
            title_elem = job_link.find('h4', class_='details-title')
            title = title_elem.get_text(strip=True) if title_elem else ''
            
            # Extract department from job description
            desc_elem = job_link.find('p', class_='details-desc')
            department = ''
            if desc_elem:
                dept_span = desc_elem.find('span', class_='margin--right--s')
                if dept_span:
                    department = dept_span.get_text(strip=True)
            
            # Determine remote status from location or title
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
                'Employment Type': '',  # Not provided in list view
                'Department': department,
                'Posted Date': '',  # Not provided in list view
                'Company Description': company_description,
                'Remote': remote,
                'Label': label,
                'ATS': 'SmartRecruiters'
            }
            
            return job
            
        except Exception as e:
            logger.debug(f"Error parsing job: {e}")
            return None
