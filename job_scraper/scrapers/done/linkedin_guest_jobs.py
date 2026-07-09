"""
LinkedIn Guest Jobs - API-based public job collector
Collects job listings from public LinkedIn guest search pages and enriches them by crawling job descriptions and criteria.
"""

import requests
import time
import logging
from typing import List, Dict
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

logger = logging.getLogger(__name__)


class LinkedInGuestJobsClient:
    """
    Client for the LinkedIn Jobs guest API.
    """

    def __init__(self, delay: float = 1.0):
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        })

    def scrape_jobs(self, url: str, company_name: str, company_description: str = '', label: str = '', limit: int = 50) -> List[Dict]:
        """
        Collect jobs from LinkedIn Guest Search URL.
        Paginates until limits are met or no more listings are returned.
        
        Args:
            url: Guest search page URL
            company_name: Fallback company name
            company_description: Description of the company
            label: Company label/category
            limit: Maximum number of jobs to fetch
            
        Returns:
            List of standardized job dictionaries
        """
        jobs = []
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        
        # Clean query parameters - start will be managed dynamically
        query_params.pop('start', None)
        
        start = 0
        
        logger.info(f"Starting LinkedIn collection for {company_name}...")
        
        while len(jobs) < limit:
            current_params = query_params.copy()
            current_params['start'] = [str(start)]
            
            reconstructed_query = urlencode(current_params, doseq=True)
            page_url = urlunparse(parsed_url._replace(query=reconstructed_query))
            
            logger.info(f"Fetching LinkedIn page at start={start}: {page_url}")
            try:
                response = self.session.get(page_url, timeout=15)
                if response.status_code != 200:
                    logger.warning(f"Failed to fetch page (Status: {response.status_code})")
                    break
                    
                soup = BeautifulSoup(response.text, 'html.parser')
                li_items = soup.find_all('li')
                
                if not li_items:
                    logger.info("No more job cards found on LinkedIn page.")
                    break
                    
                page_jobs_added = 0
                for li in li_items:
                    if len(jobs) >= limit:
                        break
                        
                    job = self._parse_job_card(li, company_name, company_description, label)
                    if job:
                        # Fetch the description and detailed metadata
                        detail_url = job.get('Job Link')
                        if detail_url:
                            time.sleep(self.delay)
                            self._enrich_job_details(detail_url, job)
                            
                        jobs.append(job)
                        page_jobs_added += 1
                        
                if page_jobs_added == 0:
                    logger.info("No valid job postings parsed on this page.")
                    break
                    
                # Increment start parameter by 25 (standard LinkedIn page increment)
                start += 25
                time.sleep(self.delay)
                
            except Exception as e:
                logger.error(f"Error collecting LinkedIn page at start={start}: {e}")
                break
                
        logger.info(f"Completed LinkedIn collection. Found {len(jobs)} jobs.")
        return jobs

    def _parse_job_card(self, li, company_name: str, company_description: str, label: str) -> Dict:
        """Parse job details from the search list card HTML."""
        try:
            # Title
            title_elem = li.find("h3", class_="base-search-card__title")
            if not title_elem:
                title_elem = li.find("span", class_="sr-only")
            title = title_elem.get_text(strip=True) if title_elem else ""
            
            if not title:
                return None
                
            # Company
            company_elem = li.find("h4", class_="base-search-card__subtitle")
            if not company_elem:
                company_elem = li.find("a", class_="hidden-nested-link")
            card_company = company_elem.get_text(strip=True) if company_elem else company_name
            
            # Location
            location_elem = li.find("span", class_="job-search-card__location")
            location = location_elem.get_text(strip=True) if location_elem else ""
            
            # Link
            link_elem = li.find("a", class_="base-card__full-link")
            link = link_elem.get("href") if link_elem else ""
            if link and "?" in link:
                link = link.split("?")[0]
                
            if not link:
                return None
                
            # Date
            date_elem = li.find("time", class_="job-search-card__listdate")
            if not date_elem:
                date_elem = li.find("time", class_="job-search-card__listdate--new")
            posted_date = date_elem.get("datetime") if date_elem else ""
            if not posted_date and date_elem:
                posted_date = date_elem.get_text(strip=True)
                
            # Remote classification from title/location
            remote_val = 'No'
            loc_lower = location.lower()
            title_lower = title.lower()
            if 'remote' in loc_lower or 'remote' in title_lower or 'telecommute' in loc_lower:
                remote_val = 'Yes'
            elif 'hybrid' in loc_lower or 'hybrid' in title_lower:
                remote_val = 'Hybrid'
                
            job = {
                'Company Name': card_company,
                'Job Title': title,
                'Location': location,
                'Job Link': link,
                'Job Description': '',
                'Employment Type': '',
                'Department': '',
                'Posted Date': posted_date,
                'Company Description': company_description,
                'Remote': remote_val,
                'Label': label,
                'ATS': 'LinkedIn'
            }
            return job
        except Exception as e:
            logger.debug(f"Error parsing LinkedIn job card: {e}")
            return None

    def _enrich_job_details(self, url: str, job: Dict):
        """Fetch the public job detail page to enrich description and criteria."""
        try:
            logger.info(f"Enriching job details from: {url}")
            response = self.session.get(url, timeout=15)
            if response.status_code != 200:
                logger.warning(f"Failed to fetch job details for {url} (Status: {response.status_code})")
                return
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Description
            description_elem = soup.find("div", class_="show-more-less-html__markup")
            if not description_elem:
                description_elem = soup.find("div", class_="description__text")
            if not description_elem:
                description_elem = soup.find("section", class_="description")
                
            if description_elem:
                job['Job Description'] = description_elem.get_text(separator=' ', strip=True)
                
            # Update Remote status if it's explicitly mentioned in the description
            desc_lower = job['Job Description'].lower()
            if job['Remote'] == 'No':
                if 'remote' in desc_lower or 'home office' in desc_lower:
                    job['Remote'] = 'Yes'
                elif 'hybrid' in desc_lower:
                    job['Remote'] = 'Hybrid'
                
            # Criteria List (Employment Type, Department/Function)
            criteria_list = soup.find("ul", class_="description__job-criteria-list")
            if criteria_list:
                items = criteria_list.find_all("li")
                for item in items:
                    subheader = item.find("h3")
                    text = item.find("span")
                    if subheader and text:
                        sh_val = subheader.get_text(strip=True).lower()
                        t_val = text.get_text(strip=True)
                        
                        # Employment type matching (handles English / German)
                        if any(term in sh_val for term in ["employment type", "beschäftigungsverhältnis", "type"]):
                            job['Employment Type'] = t_val
                        # Department matching
                        elif any(term in sh_val for term in ["job function", "tätigkeitsbereich", "function"]):
                            job['Department'] = t_val
                            
        except Exception as e:
            logger.debug(f"Error enriching LinkedIn job details: {e}")
