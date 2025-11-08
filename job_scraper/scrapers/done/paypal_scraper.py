"""
PayPal Careers (Eightfold) Scraper
Scrapes job listings from PayPal's Eightfold AI-powered careers API
"""

import requests
import logging
import time
from typing import List, Dict
from urllib.parse import urlparse, parse_qs
from datetime import datetime

logger = logging.getLogger(__name__)


class PayPalScraper:
    """
    Scraper for PayPal Careers (https://paypal.eightfold.ai)
    
    PayPal uses Eightfold AI platform with a REST API endpoint for job search.
    URL format: https://paypal.eightfold.ai/api/pcsx/search
    
    API supports:
    - Location-based search
    - Distance filtering (radius in km)
    - Pagination via 'start' parameter
    - Sorting by timestamp (most recent first)
    - Various work location options (onsite, hybrid, remote)
    """
    
    BASE_API_URL = "https://paypal.eightfold.ai/api/pcsx/search"
    BASE_JOB_URL = "https://paypal.eightfold.ai/careers/job"
    
    def __init__(self, delay: float = 0.2):
        self.delay = delay
        self.session = requests.Session()
    
    def _extract_location_from_url(self, url: str) -> str:
        """
        Extract location from PayPal careers URL
        
        Args:
            url: PayPal careers URL
            
        Returns:
            Location string
        """
        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            
            # Check for location in query params
            if 'location' in params:
                location = params['location'][0]
                # Simplify location to just country if too specific
                if 'germany' in location.lower():
                    return 'Germany'
                return location
            
            # Check URL for location hints
            url_lower = url.lower()
            if 'germany' in url_lower or 'berlin' in url_lower:
                return 'Germany'
            
            # Default to empty (all locations)
            logger.info("No location filter found, searching all PayPal jobs")
            return ''
            
        except Exception as e:
            logger.debug(f"Error parsing URL: {e}")
            return ''
    
    def scrape_jobs(self, url: str, company_name: str, company_description: str = '', label: str = '') -> List[Dict]:
        """
        Scrape jobs from PayPal Eightfold API
        
        Args:
            url: PayPal careers URL
            company_name: Name of the company
            company_description: Description
            label: Company label
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        
        # Extract location
        location_filter = self._extract_location_from_url(url)
        if location_filter:
            logger.info(f"Filtering PayPal jobs by location: {location_filter}")
        else:
            logger.info("Searching all PayPal jobs (no location filter)")
        
        # Set headers
        headers = {
            'accept': 'application/json',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
            'referer': 'https://paypal.eightfold.ai/careers'
        }
        
        # Pagination parameters
        start = 0
        page_size = 20  # Typical page size
        
        while True:
            # Build request parameters
            params = {
                'domain': 'paypal.com',
                'query': '',
                'location': location_filter,
                'start': start,
                'sort_by': 'timestamp',  # Most recent first
            }
            
            # Add distance filter if we have a location
            if location_filter:
                params['filter_distance'] = 80  # 80km radius
            
            try:
                response = self.session.get(self.BASE_API_URL, headers=headers, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                
                # Extract jobs from response
                positions = data.get('data', {}).get('positions', [])
                
                if not positions:
                    logger.debug(f"No positions at start={start}")
                    break
                
                logger.info(f"📄 Start {start}: {len(positions)} jobs (total: {len(jobs)})")
                
                # Parse each job
                for job_data in positions:
                    job = self._parse_job(job_data, company_name, company_description, label)
                    if job:
                        jobs.append(job)
                    else:
                        logger.debug(f"Failed to parse job: {job_data.get('name', 'Unknown')}")
                
                logger.debug(f"Parsed {len(jobs)} jobs so far")
                
                # Check if we got fewer jobs than expected (last page)
                if len(positions) < page_size:
                    break
                
                # Move to next page
                start += page_size
                time.sleep(self.delay)
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching jobs at start={start}: {e}")
                break
            except Exception as e:
                logger.error(f"Error parsing response at start={start}: {e}")
                break
        
        return jobs
    
    def _parse_job(self, job_data: dict, company_name: str, company_description: str, label: str) -> Dict:
        """
        Parse a single job from PayPal Eightfold API response
        
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
            display_job_id = job_data.get('displayJobId', '')
            title = job_data.get('name', '')
            
            # Build job URL using positionUrl
            position_url = job_data.get('positionUrl', '')
            if position_url:
                # positionUrl is like "/careers/job/274908757128"
                if position_url.startswith('/careers/job/'):
                    job_id_str = position_url.replace('/careers/job/', '')
                    job_url = f"{self.BASE_JOB_URL}?domain=paypal.com&pid=careersjob{job_id_str}"
                elif position_url.startswith('careersjob'):
                    job_url = f"{self.BASE_JOB_URL}?domain=paypal.com&pid={position_url}"
                else:
                    job_url = f"{self.BASE_JOB_URL}?domain=paypal.com&pid=careersjob{job_id}"
            else:
                job_url = f"{self.BASE_JOB_URL}?domain=paypal.com&pid=careersjob{job_id}"
            
            # Location (can be list or string)
            locations_data = job_data.get('locations', [])
            if isinstance(locations_data, list):
                location = ', '.join(locations_data) if locations_data else ''
            else:
                location = locations_data
            
            if not location:
                # Try standardizedLocations
                std_locations = job_data.get('standardizedLocations', [])
                if isinstance(std_locations, list):
                    location = ', '.join(std_locations) if std_locations else ''
                else:
                    location = std_locations
            
            # Department
            department = job_data.get('department', '')
            
            # Work location option (onsite, hybrid, remotelocal)
            work_location = job_data.get('workLocationOption', '')
            remote = 'No'
            
            if work_location:
                work_loc_lower = work_location.lower()
                if 'remote' in work_loc_lower:
                    remote = 'Yes'
                elif 'hybrid' in work_loc_lower:
                    remote = 'Hybrid'
            
            # Also check location and title
            location_lower = location.lower() if location else ''
            title_lower = title.lower()
            
            if 'remote' in location_lower or 'remote' in title_lower:
                remote = 'Yes'
            elif 'hybrid' in location_lower or 'hybrid' in title_lower:
                remote = 'Hybrid'
            
            # Posted date from timestamp
            posted_ts = job_data.get('postedTs', '')
            posted_date = ''
            if posted_ts:
                try:
                    # Convert unix timestamp to date
                    posted_date = datetime.fromtimestamp(int(posted_ts)).strftime('%Y-%m-%d')
                except:
                    posted_date = ''
            
            # Employment type
            employment_type = 'FullTime'  # Default, can be refined if data available
            
            job = {
                'Company Name': company_name,
                'Job Title': title,
                'Location': location,
                'Job Link': job_url,
                'Job Description': '',  # Not provided in list view
                'Employment Type': employment_type,
                'Department': department,
                'Posted Date': posted_date,
                'Company Description': company_description,
                'Remote': remote,
                'Label': label,
                'ATS': 'PayPal (Eightfold)'
            }
            
            return job
            
        except Exception as e:
            logger.error(f"Error parsing job: {e}")
            logger.debug(f"Job data: {job_data}")
            return None
