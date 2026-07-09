# LinkedIn Guest Jobs Documentation

This project features a fully functional, login-free LinkedIn guest jobs client located at [linkedin_guest_jobs.py](file:///Users/umutyesildal/Desktop/job-client/job_scraper/scrapers/done/linkedin_guest_jobs.py). It queries LinkedIn's public job search endpoints, bypasses authwalls, extracts job cards, and enriches them by retrieving details directly from public view URLs.

---

## How It Works

1. **Guest API Query**:
   The client issues a GET request to:
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
   For each job, the client visits the public detail page (`https://de.linkedin.com/jobs/view/...`) to extract:
   - **Job Description** (from `show-more-less-html__markup`)
   - **Employment Type** (parsed from the criteria list using multi-lingual support: `Employment type` / `Beschäftigungsverhältnis`)
   - **Department/Function** (parsed from `Job function` / `Tätigkeitsbereich`)
   - **Remote Status Double-Check** (verifies if remote or hybrid is explicitly listed inside the description body)

---

## Parameter Specification

When instantiating the client:
- `delay` (float): The delay between successive requests in seconds. Default is `1.0`. A delay of `0.5` to `1.0` is recommended to prevent rate limits.

When calling the LinkedIn jobs method:
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
To score the collected LinkedIn jobs against the early-career software profile and see the fit scores:
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

---

## Daily Google Sheets Feed

The normal post-processing step can also append recent LinkedIn jobs before it
builds `Related Jobs` and `Daily New Jobs`.

```bash
python3 post_process_jobs.py --include-linkedin-daily
```

By default this runs Berlin searches for software, backend, frontend,
full-stack, Python, React, and TypeScript roles posted in the last 24 hours.
It deduplicates overlapping keyword results, keeps only profile-fit roles using
the same `Related Jobs` filter, and saves the LinkedIn-only pull to
`data/linkedin_daily_jobs.csv`.

Useful options:
- `--linkedin-keywords`: Override the default keyword set, e.g. `--linkedin-keywords "software engineer" "backend engineer"`
- `--linkedin-location`: Override the LinkedIn location (default: `"Berlin, Germany"`)
- `--linkedin-limit-per-query`: Maximum jobs per keyword (default: `25`)
- `--linkedin-posted-within-seconds`: Posted-time filter; default `86400` means last 24 hours
- `--linkedin-raw-daily`: Append raw LinkedIn results instead of profile-fit rows only
