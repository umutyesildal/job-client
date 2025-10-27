# Job Crawler

Scrapes job listings from 19+ ATS platforms.

## Status

### ✅ Working (6 platforms)
- **Ashby** - API-based
- **Greenhouse** - API-based  
- **Workable** - API-based
- **Recruitee** - API-based
- **BambooHR** - API-based
- **Consider/Cherry VC** - API with pagination

### ❌ Not Working (13 platforms)
- Lever, Workday, Personio, SmartRecruiters, Teamtailor, HiBob, Join, Gem, Getro, Rippling, Softgarden, Generic ATS

## Structure

```
job_scraper/
├── scrapers/
│   ├── done/          # 6 working scrapers
│   ├── undone/        # 13 not implemented
│   └── template_scraper.py
└── src/
    └── main_crawler.py
```

## Usage

```bash
cd job_scraper/src
python3 main_crawler.py              # Run all companies
python3 main_crawler.py -l 10        # Limit to 10 companies
```

Output: `../../data/all_jobs.csv`

## Adding New Scraper

1. Copy `scrapers/template_scraper.py` to `scrapers/undone/`
2. Implement `scrape_jobs()` method
3. Test with `-l 1`
4. Move to `scrapers/done/` when working

## Job Fields

Required fields all scrapers must return:
- Company Name
- Job Title
- Location
- Job Link
- Posted Date
- Remote (Yes/No/Hybrid)
- Label (ATS platform)
- ATS (platform name)

Optional: Job Description, Employment Type, Department, Company Description




