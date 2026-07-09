# LinkedIn Guest Scraper Documentation

This project features a fully functional, login-free LinkedIn Scraper located at [linkedin_scraper.py](file:///Users/umutyesildal/Desktop/job-client/job_scraper/scrapers/done/linkedin_scraper.py). It queries LinkedIn's public job search endpoints, bypasses authwalls, extracts job cards, and enriches them by retrieving details directly from public view URLs.

---

## How It Works

1. **Guest API Query**:
   The scraper issues a GET request to:
   `https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search`
   with parameters like `keywords`, `location`, and `start`.

2. **Automatic Pagination**:
   It increments the `start` parameter by `25` (LinkedIn's standard page size) until the requested `limit` is reached or no more listings are returned by the API.

3. **Job Card Extraction**:
   For each item, it parses the HTML fragment to extract:
   - **Job Title**
   - **Company Name**
   - **Location**
   - **Job Link** (cleaned of tracking query parameters)
   - **Posted Date**
   - **Remote Classification** (classified as `'Yes'`, `'No'`, or `'Hybrid'` based on location/title keywords)

4. **Job Detail Enrichment**:
   For each job, the scraper visits the public detail page (`https://de.linkedin.com/jobs/view/...`) to extract:
   - **Job Description** (from `show-more-less-html__markup`)
   - **Employment Type** (parsed from the criteria list using multi-lingual support: `Employment type` / `Beschäftigungsverhältnis`)
   - **Department/Function** (parsed from `Job function` / `Tätigkeitsbereich`)
   - **Remote Status Double-Check** (verifies if remote or hybrid is explicitly listed inside the description body)

---

## Parameter Specification

When instantiating the scraper:
- `delay` (float): The delay between successive requests in seconds. Default is `1.0`. A delay of `0.5` to `1.0` is recommended to prevent rate limits.

When calling `scrape_jobs(url, company_name, company_description, label, limit)`:
- `url` (str): The search URL containing the initial parameters (`keywords`, `location`, etc.).
- `company_name` (str): Fallback company name if not found on the card.
- `company_description` (str): Fallback company description.
- `label` (str): Category label.
- `limit` (int): Maximum number of jobs to fetch. Default is `50`.

---

## Standalone Query Tool

To run dynamic queries from the terminal, use the newly added [`query_linkedin.py`](file:///Users/umutyesildal/Desktop/job-client/job_scraper/src/query_linkedin.py) script.

### Basic Usage
```bash
python3 query_linkedin.py --keywords "software engineer" --location "Berlin" --limit 50
```

### Advanced Usage (With Scoring)
To score the scraped LinkedIn jobs against the early-career software profile and see the fit scores:
```bash
python3 query_linkedin.py --keywords "react developer" --location "Berlin" --limit 100 --score
```

### Options
- `--keywords`: Search term (e.g. `"software engineer"`, `"data scientist"`)
- `--location`: Search location (e.g. `"Berlin"`, `"Germany"`)
- `--limit`: Maximum number of jobs to retrieve (default: `50`)
- `--delay`: Delay between detail page fetches in seconds (default: `1.0`)
- `--output`: File path to save results (default: `data/linkedin_results.csv`)
- `--score`: Run the early-career profile fit scoring logic on the results and print/save scores.
