"""
Gem ATS Scraper
Scrapes job listings from Gem GraphQL API (jobs.gem.com)
"""

import requests
import logging
import time
from typing import List, Dict
from datetime import datetime
import html

logger = logging.getLogger(__name__)


class GemScraper:
    """
    Scraper for Gem ATS platform (GraphQL-based)
    
    Gem uses a GraphQL API with batched queries.
    URL format: https://jobs.gem.com/{boardId}
    """
    
    def __init__(self, delay: float = 0.2):
        self.delay = delay
        self.session = requests.Session()
        self.api_url = "https://jobs.gem.com/api/public/graphql/batch"
        
    def _extract_board_id(self, url: str) -> str:
        """
        Extract board ID from Gem URL
        
        Args:
            url: URL like https://jobs.gem.com/astroforge-io
            
        Returns:
            Board ID as string (e.g., 'astroforge-io')
        """
        try:
            # Remove trailing slashes and extract the last path segment
            url = url.rstrip('/')
            parts = url.split('/')
            board_id = parts[-1]
            
            if board_id and board_id != 'jobs.gem.com':
                return board_id
            
            logger.error(f"Could not extract board ID from URL: {url}")
            return None
        except Exception as e:
            logger.error(f"Error extracting board ID: {e}")
            return None
    
    def scrape_jobs(self, url: str, company_name: str, company_description: str = '', label: str = '') -> List[Dict]:
        """
        Scrape jobs from Gem GraphQL API
        
        Args:
            url: Gem board URL (e.g., https://jobs.gem.com/astroforge-io)
            company_name: Name of the company
            company_description: Description
            label: Company label
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        
        board_id = self._extract_board_id(url)
        if not board_id:
            logger.error(f"Invalid Gem URL: {url}")
            return jobs
        
        # Set headers to mimic browser request
        headers = {
            'accept': '*/*',
            'content-type': 'application/json',
            'batch': 'true',
            'origin': 'https://jobs.gem.com',
            'referer': f'https://jobs.gem.com/{board_id}',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
        }
        
        # GraphQL batched query payload
        payload = [
            {
                "operationName": "JobBoardTheme",
                "variables": {
                    "boardId": board_id
                },
                "query": "query JobBoardTheme($boardId: String!) { publicBrandingTheme(externalId: $boardId) { id theme __typename } }"
            },
            {
                "operationName": "JobBoardList",
                "variables": {
                    "boardId": board_id
                },
                "query": """
                    fragment ExternalJobPostFragment on PublicOatsJobPost {
                        id
                        title
                        descriptionHtml
                        extId
                        locations {
                            name
                            city
                            isoCountry
                            isRemote
                            __typename
                        }
                        job {
                            locationType
                            employmentType
                            department {
                                name
                                __typename
                            }
                            __typename
                        }
                        jobPostSectionHtml {
                            introHtml
                            outroHtml
                            __typename
                        }
                        firstPublishedTsSec
                        compensationHtml
                        __typename
                    }
                    query JobBoardList($boardId: String!) {
                        oatsExternalJobPostings(boardId: $boardId) {
                            jobPostings {
                                ...ExternalJobPostFragment
                            }
                            __typename
                        }
                        oatsExternalJobPostingsFilters(boardId: $boardId) {
                            type
                            displayName
                            rawValue
                            value
                            count
                            __typename
                        }
                        jobBoardExternal(vanityUrlPath: $boardId) {
                            id
                            teamDisplayName
                            descriptionHtml
                            pageTitle
                            __typename
                        }
                    }
                """
            }
        ]
        
        try:
            response = self.session.post(self.api_url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # The response is an array with 2 elements:
            # [0] = theme data, [1] = job postings data
            if len(data) < 2:
                logger.error(f"Unexpected response structure for {board_id}")
                return jobs
            
            job_data = data[1].get('data', {})
            job_postings = job_data.get('oatsExternalJobPostings', {}).get('jobPostings', [])
            
            logger.info(f"Found {len(job_postings)} jobs for {company_name}")
            
            for job_posting in job_postings:
                job = self._parse_job(job_posting, board_id, company_name, company_description, label)
                if job:
                    jobs.append(job)
            
            time.sleep(self.delay)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching jobs for {board_id}: {e}")
        except Exception as e:
            logger.error(f"Error parsing response for {board_id}: {e}")
        
        return jobs
    
    def _parse_job(self, job_data: Dict, board_id: str, company_name: str, company_description: str, label: str) -> Dict:
        """
        Parse a single job from Gem GraphQL response
        
        Args:
            job_data: Raw job data from API
            board_id: Board ID for URL construction
            company_name: Company name
            company_description: Description
            label: Label
            
        Returns:
            Standardized job dictionary
        """
        try:
            # Extract basic info
            title = job_data.get('title', '')
            ext_id = job_data.get('extId', '')
            
            # Build job URL: https://jobs.gem.com/{boardId}/{extId}
            job_url = f"https://jobs.gem.com/{board_id}/{ext_id}" if ext_id else ''
            
            # Extract location
            locations = job_data.get('locations', [])
            location_parts = []
            is_remote = False
            
            for loc in locations:
                if loc.get('isRemote'):
                    is_remote = True
                city = loc.get('city', '')
                country = loc.get('isoCountry', '')
                if city and country:
                    location_parts.append(f"{city}, {country}")
                elif city:
                    location_parts.append(city)
                elif country:
                    location_parts.append(country)
            
            location_str = ', '.join(location_parts) if location_parts else ''
            
            # Extract job details
            job_info = job_data.get('job', {})
            location_type = job_info.get('locationType', '').upper()
            employment_type = job_info.get('employmentType', '').replace('_', ' ').title()
            
            department_obj = job_info.get('department', {})
            department = department_obj.get('name', '') if department_obj else ''
            
            # Determine remote status
            remote = 'No'
            if is_remote or location_type == 'REMOTE':
                remote = 'Yes'
            elif location_type == 'HYBRID':
                remote = 'Hybrid'
            
            # Extract description (HTML)
            description_html = job_data.get('descriptionHtml', '')
            # Strip HTML tags for plain text description
            description = html.unescape(description_html) if description_html else ''
            
            # Extract posted date
            first_published = job_data.get('firstPublishedTsSec')
            posted_date = ''
            if first_published:
                try:
                    posted_date = datetime.fromtimestamp(first_published).strftime('%Y-%m-%d')
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
                'ATS': 'Gem'
            }
            
            return job
            
        except Exception as e:
            logger.debug(f"Error parsing job: {e}")
            return None
