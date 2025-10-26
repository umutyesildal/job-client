import requests
import time
import logging
import json
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)


# Default payload template. This can be adjusted per-board by passing query params
# in the career page URL (see scrape_jobs behavior below).
DEFAULT_PAYLOAD = {
    'meta': {'size': 100},
    'board': {'id': 'cherry-ventures', 'isParent': True},
    'query': {'promoteFeatured': True}
}


class ConsiderScraper:
    """Consider/Cherry-style API scraper.

    Usage: main crawler calls ConsiderScraper().scrape_jobs(career_page_url, ...)
    The career_page_url should be the API endpoint (e.g.
    https://talent.cherry.vc/api-boards/search-jobs) optionally with query params
    to customize the payload. Supported query params (optional):
      - board: override board.id (string)
      - size: override meta.size (int)
      - promoteFeatured: override query.promoteFeatured (true/false)

    This keeps the interface identical to other scrapers while allowing the CSV
    entry to fully describe which Consider board to query.
    """

    def __init__(self, delay: float = 1.0):
        self.delay = delay
        self.tracking_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'consider_tracking.json')
        self.session = requests.Session()

    def load_tracking_data(self) -> Optional[Dict]:
        if os.path.exists(self.tracking_file):
            with open(self.tracking_file, 'r') as f:
                return json.load(f)
        return None

    def save_tracking_data(self, latest_job_url: str, latest_job_title: str, total_jobs: int):
        os.makedirs(os.path.dirname(self.tracking_file), exist_ok=True)
        data = {
            'last_run': datetime.now().isoformat(),
            'latest_job_url': latest_job_url,
            'latest_job_title': latest_job_title,
            'total_jobs_last_run': total_jobs
        }
        with open(self.tracking_file, 'w') as f:
            json.dump(data, f, indent=2)

    def _build_payload_from_url(self, career_page_url: str) -> Tuple[str, Dict]:
        """Build api_url and payload from the career_page_url.

        If career_page_url contains query params (board, size, promoteFeatured)
        they are applied to the DEFAULT_PAYLOAD.
        """
        api_url = career_page_url
        payload = json.loads(json.dumps(DEFAULT_PAYLOAD))  # deep-ish copy

        try:
            parsed = urlparse(career_page_url)
            qs = parse_qs(parsed.query)

            # board override
            if 'board' in qs and qs['board']:
                payload['board']['id'] = qs['board'][0]

            # size override
            if 'size' in qs and qs['size']:
                try:
                    payload['meta']['size'] = int(qs['size'][0])
                except ValueError:
                    logger.debug('Invalid size param, using default')

            # promoteFeatured override
            if 'promotefeatured' in qs or 'promoteFeatured' in qs:
                key = 'promotefeatured' if 'promotefeatured' in qs else 'promoteFeatured'
                val = qs.get(key, [qs.get('promoteFeatured', ['true'])[0]])[0].lower()
                payload['query']['promoteFeatured'] = val in ('1', 'true', 'yes')

        except Exception:
            # be conservative: fall back to DEFAULT_PAYLOAD
            logger.debug('Could not parse career_page_url for dynamic payload, using defaults')

        return api_url, payload

    def scrape_jobs(self, url: str, company_name: str, company_description: str = '', label: str = '') -> List[Dict]:
        api_url, payload = self._build_payload_from_url(url)

        all_jobs: List[Dict] = []
        sequence = None
        tracking = self.load_tracking_data()
        is_first_run = tracking is None
        page = 1
        max_retries = 3

        while True:
            # attach sequence token if present
            if sequence:
                payload['meta']['sequence'] = sequence

            # perform request with retries
            for attempt in range(max_retries):
                try:
                    resp = self.session.post(api_url, json=payload, timeout=30)
                    resp.raise_for_status()
                    data = resp.json()
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error(f'Failed after {max_retries} attempts: {e}')
                        if all_jobs:
                            # save partial progress
                            self.save_tracking_data(all_jobs[0].get('Job Link', ''), all_jobs[0].get('Job Title', ''), len(all_jobs))
                        return all_jobs
                    time.sleep(1)

            jobs = data.get('jobs', [])
            if not jobs:
                break

            for job in jobs:
                job_url = job.get('url') or job.get('applyUrl')

                # if incremental run and we reached last seen job, stop early
                if not is_first_run and tracking and job_url == tracking.get('latest_job_url'):
                    logger.info(f'🔄 Reached last known job, stopping (page {page})')
                    if all_jobs:
                        self.save_tracking_data(all_jobs[0].get('Job Link', ''), all_jobs[0].get('Job Title', ''), len(all_jobs))
                    return all_jobs

                job_dict = {
                    'Company Name': job.get('companyName', '') or company_name,
                    'Job Title': job.get('title', ''),
                    'Location': ', '.join(job.get('locations', [])) if job.get('locations') else '',
                    'Job Link': job_url,
                    'Job Description': '',
                    'Employment Type': '',
                    'Department': ', '.join([jf.get('label', '') for jf in job.get('jobFunctions', [])]) if job.get('jobFunctions') else '',
                    'Posted Date': job.get('timeStamp', '').split('T')[0] if job.get('timeStamp') else '',
                    'Company Description': company_description,
                    'Remote': 'Yes' if job.get('remote') else ('Hybrid' if job.get('hybrid') else 'No'),
                    'Label': label,
                    'ATS': 'Consider'
                }
                all_jobs.append(job_dict)

            logger.info(f'📄 Page {page}: {len(jobs)} jobs (total: {len(all_jobs)})')

            sequence = data.get('meta', {}).get('sequence')
            if not sequence:
                break

            page += 1
            time.sleep(self.delay)

        if all_jobs:
            self.save_tracking_data(all_jobs[0].get('Job Link', ''), all_jobs[0].get('Job Title', ''), len(all_jobs))

        return all_jobs
