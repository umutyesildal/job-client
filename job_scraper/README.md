# Job Scraper Engine

Core scraping engine with 23 ATS platform implementations.

## Architecture

```
job_scraper/
├── scrapers/done/         # 23 working implementations
├── scrapers/undone/       # 6 incomplete implementations
├── scrapers/template_scraper.py
└── src/main.py            # Orchestration engine
```

## Implementation Status

**✅ Production Ready (23)**:  
Amazon, Ashby, BambooHR, Capgemini, Consider, Gem, Getro, Greenhouse, HiBob, Join, Lever, Lingoda, Microsoft, PayPal, Personio, Recruitee, Rippling, SmartRecruiters, Stripe, Trade Republic, Wipro, Workable

**❌ Incomplete (6)**:  
Meta, Softgarden, Teamtailor, Tesla, Workday, Generic ATS

## Standard Interface

All scrapers implement the same interface:

```python
def scrape_jobs(self, url: str, company_name: str, 
                company_description: str = '', label: str = '') -> List[Dict]:
    """Return list of standardized job dictionaries"""
```

Output format:
```python
{
    'Company Name': str,
    'Job Title': str,
    'Location': str,
    'Job Link': str,
    'Job Description': str,
    'Employment Type': str,
    'Department': str,
    'Posted Date': str,      # YYYY-MM-DD
    'Company Description': str,
    'Remote': str,          # Yes/No/Hybrid
    'Label': str,           # ATS platform identifier
    'ATS': str             # Platform name
}
```

## Development

```bash
# From the repository root, crawl companies stored in PostgreSQL
.venv/bin/python job_scraper/src/main.py -t postgres -l 1

# Or use a reviewed local YAML catalog
.venv/bin/python job_scraper/src/main.py catalog/companies.yaml -t yaml -l 3 -d 0.1

# Classify, filter, deduplicate, and publish the rolling 30-day collection
.venv/bin/python job_scraper/src/post_process_jobs.py \
  --storage-backend postgres --retention-days 30

# Add new scraper
cp scrapers/template_scraper.py scrapers/undone/new_scraper.py
# Edit implementation, add to SCRAPER_MAP in src/client.py
```

The raw `all_jobs.csv` is a replaceable single-run snapshot. PostgreSQL owns
canonical history; full public job rows expire after 30 days.
