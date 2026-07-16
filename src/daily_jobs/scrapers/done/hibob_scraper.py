"""
HiBob ATS Scraper
Scrapes job listings from HiBob API (careers.hibob.com)
"""

import requests
import logging
import time
from typing import List, Dict
from datetime import datetime
from urllib.parse import urlparse
import html

logger = logging.getLogger(__name__)


class HiBobScraper:
    """
    Scraper for HiBob ATS platform (API-based)
    
    HiBob uses a simple GET API endpoint that returns all jobs and filters.
    URL format: https://{company}.careers.hibob.com/
    """
    
    def __init__(self, delay: float = 0.2):
        self.delay = delay
        self.session = requests.Session()
    
    def _extract_company_identifier(self, url: str) -> str:
        """
        Extract company identifier from HiBob URL
        
        Args:
            url: URL like https://cloudnc.careers.hibob.com or https://cloudnc.careers.hibob.com/jobs
            
        Returns:
            Company identifier as string (e.g., 'cloudnc')
        """
        try:
            parsed = urlparse(url)
            # Extract subdomain from hostname like 'cloudnc.careers.hibob.com'
            parts = parsed.hostname.split('.')
            if len(parts) >= 3 and 'careers.hibob.com' in parsed.hostname:
                return parts[0]
            
            logger.error(f"Could not extract company identifier from URL: {url}")
            return None
        except Exception as e:
            logger.error(f"Error extracting company identifier: {e}")
            return None
    
    def scrape_jobs(self, url: str, company_name: str, company_description: str = '', label: str = '') -> List[Dict]:
        """
        Scrape jobs from HiBob API
        
        Args:
            url: HiBob careers URL (e.g., https://cloudnc.careers.hibob.com/jobs)
            company_name: Name of the company
            company_description: Description
            label: Company label
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        
        company_id = self._extract_company_identifier(url)
        if not company_id:
            logger.error(f"Invalid HiBob URL: {url}")
            return jobs
        
        # Build API endpoint
        api_url = f"https://{company_id}.careers.hibob.com/api/job-ad"
        
        # Set headers to mimic browser request
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br, zstd',
            'accept-language': 'en,tr-TR;q=0.9,tr;q=0.8,en-US;q=0.7',
            'companyidentifier': company_id,
            'referer': f'https://{company_id}.careers.hibob.com/jobs',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
            'priority': 'u=1, i'
        }
        
        try:
            response = self.session.get(api_url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            job_postings = data.get('jobAdDetails', [])
            
            logger.info(f"Found {len(job_postings)} jobs for {company_name}")
            
            for job_data in job_postings:
                job = self._parse_job(job_data, company_id, company_name, company_description, label)
                if job:
                    jobs.append(job)
            
            time.sleep(self.delay)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching jobs for {company_id}: {e}")
        except Exception as e:
            logger.error(f"Error parsing response for {company_id}: {e}")
        
        return jobs
    
    def _parse_job(self, job_data: Dict, company_id: str, company_name: str, company_description: str, label: str) -> Dict:
        """
        Parse a single job from HiBob API response
        
        Args:
            job_data: Raw job data from API
            company_id: Company identifier for URL construction
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
            
            # Build job URL: https://{company}.careers.hibob.com/jobs/{id}
            job_url = f"https://{company_id}.careers.hibob.com/jobs/{job_id}" if job_id else ''
            
            # Extract location
            site = job_data.get('site', '')
            country = job_data.get('country', '')
            location_parts = []
            if site:
                location_parts.append(site)
            if country and country not in str(site):
                location_parts.append(country)
            location_str = ', '.join(location_parts)
            
            # Extract employment type
            employment_type = job_data.get('employmentType', '')
            
            # Extract department
            department = job_data.get('department', '')
            
            # Determine remote status from workspaceType
            workspace_type = job_data.get('workspaceType', '').lower()
            remote = 'No'
            if 'remote' in workspace_type:
                remote = 'Yes'
            elif 'hybrid' in workspace_type:
                remote = 'Hybrid'
            
            # Extract description (combine all HTML fields)
            description_html = job_data.get('description', '')
            requirements_html = job_data.get('requirements', '')
            responsibilities_html = job_data.get('responsibilities', '')
            
            # Combine and strip HTML for plain text description
            full_description = ' '.join(filter(None, [description_html, requirements_html, responsibilities_html]))
            description = html.unescape(full_description) if full_description else ''
            
            # Extract posted date
            published_at = job_data.get('publishedAt', '')
            posted_date = ''
            if published_at:
                try:
                    # Parse ISO format: 2025-09-16T08:02:10.768417521Z
                    dt = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                    posted_date = dt.strftime('%Y-%m-%d')
                except:
                    pass
            
            job = {
                'Company Name': company_name,
                'Job Title': title,
                'Location': location_str,
                'Job Link': job_url,
                'Job Description': description,
                'Employment Type': employment_type,
                'Department': department,
                'Posted Date': posted_date,
                'Company Description': company_description,
                'Remote': remote,
                'Label': label,
                'ATS': 'HiBob'
            }
            
            return job
            
        except Exception as e:
            logger.debug(f"Error parsing job: {e}")
            return None
