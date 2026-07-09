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
cd job_scraper/src

# Test single company
python3 main.py -l 1

# Fast development cycle
python3 main.py -l 3 -d 0.1

# Google Sheets input/output
python3 main.py -t sheets "GOOGLE_SHEET_URL_OR_ID" \
  --input-worksheet companies \
  --output-sheet "GOOGLE_SHEET_URL_OR_ID" \
  --output-worksheet all_jobs

# Current v2 source sheet
python3 main.py -t sheets "https://docs.google.com/spreadsheets/d/1sYI0IqzXp_W19eAYDCdC46ZjzrWqW5fwHfY0sAzUxKw/edit?gid=2095282077#gid=2095282077" \
  --input-worksheet OneSingle

# Build Related Jobs and Daily New Jobs outputs
python3 post_process_jobs.py

# Add new scraper
cp scrapers/template_scraper.py scrapers/undone/new_scraper.py
# Edit implementation, add to SCRAPER_MAP in src/client.py
```

