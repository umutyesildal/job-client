# Job Crawler

Scrapes job listings from 25+ ATS platforms.

## Status

### ✅ Done (22 scrapers)
Amazon, Ashby, BambooHR, Capgemini, Consider, Gem, Getro, Greenhouse, HiBob, Join, Lever, Lingoda, Microsoft, PayPal, Personio, Recruitee, Rippling, SmartRecruiters, Stripe, Trade Republic, Wipro, Workable

### ❌ Undone (5 scrapers)
Meta (GraphQL API changed), Softgarden, Teamtailor, Tesla (rate limited), Workday

## Structure

```
job_scraper/
├── scrapers/
│   ├── done/          # 22 working scrapers
│   ├── undone/        # 5 not implemented
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




