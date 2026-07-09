"""Daily LinkedIn query feed for Berlin software engineering roles."""

from __future__ import annotations

import logging
import re
import sys
import unicodedata
from pathlib import Path
from typing import Iterable, List
from urllib.parse import urlencode

import pandas as pd

JOB_SCRAPER_ROOT = Path(__file__).resolve().parents[1]
if str(JOB_SCRAPER_ROOT) not in sys.path:
    sys.path.insert(0, str(JOB_SCRAPER_ROOT))

from data_controller import DataController
from scrapers.done.linkedin_guest_jobs import LinkedInGuestJobsClient

logger = logging.getLogger(__name__)

LINKEDIN_GUEST_SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
DEFAULT_LINKEDIN_KEYWORDS = [
    "software engineer",
    "software developer",
    "backend engineer",
    "backend developer",
    "frontend engineer",
    "frontend developer",
    "fullstack engineer",
    "full stack engineer",
    "fullstack developer",
    "python developer",
    "react developer",
    "typescript developer",
]


def build_linkedin_search_url(
    keywords: str,
    location: str,
    posted_within_seconds: int = 86400,
) -> str:
    """Build a LinkedIn guest search URL for one keyword/location query."""
    query_params = {
        "keywords": keywords,
        "location": location,
    }
    if posted_within_seconds and posted_within_seconds > 0:
        query_params["f_TPR"] = f"r{posted_within_seconds}"

    return f"{LINKEDIN_GUEST_SEARCH_URL}?{urlencode(query_params)}"


def _normalize_identity_value(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value).casefold())
    value = "".join(character for character in value if not unicodedata.combining(character))
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def _job_identity(row: dict) -> tuple[str, str, str] | None:
    company = _normalize_identity_value(row.get("Company Name") or row.get("Company", ""))
    title = _normalize_identity_value(row.get("Job Title", ""))
    location = _normalize_identity_value(row.get("Location", ""))
    if not company or not title:
        return None
    return company, title, location


def _dedupe_jobs(rows: Iterable[dict]) -> List[dict]:
    seen_links = set()
    seen_identities = set()
    deduped = []

    for row in rows:
        link = str(row.get("Job Link", "")).strip()
        identity = _job_identity(row)

        if link and link in seen_links:
            continue
        if identity is not None and identity in seen_identities:
            continue

        deduped.append(row)
        if link:
            seen_links.add(link)
        if identity is not None:
            seen_identities.add(identity)

    return deduped


def collect_daily_linkedin_jobs(
    keywords: Iterable[str] | None = None,
    location: str = "Berlin, Germany",
    limit_per_query: int = 25,
    delay: float = 1.0,
    posted_within_seconds: int = 86400,
) -> pd.DataFrame:
    """Collect recent LinkedIn jobs for a set of software engineering searches."""
    keyword_list = [keyword.strip() for keyword in (keywords or DEFAULT_LINKEDIN_KEYWORDS) if keyword.strip()]
    if not keyword_list:
        return DataController().normalize_jobs_dataframe(pd.DataFrame())

    client = LinkedInGuestJobsClient(delay=delay)
    all_jobs = []

    for keyword in keyword_list:
        url = build_linkedin_search_url(keyword, location, posted_within_seconds)
        logger.info("Collecting LinkedIn daily query: %s", keyword)
        jobs = client.scrape_jobs(
            url=url,
            company_name="LinkedIn",
            company_description=f"LinkedIn daily query: {keyword}",
            label="linkedin",
            limit=limit_per_query,
        )
        all_jobs.extend(jobs or [])

    df = pd.DataFrame(_dedupe_jobs(all_jobs))
    return DataController().normalize_jobs_dataframe(df)


def save_linkedin_daily_jobs(df: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8")
