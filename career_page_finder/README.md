# Career Page Finder

Find career pages by analyzing website sitemaps and homepage links.

## Scripts

- `career_page_finder.py` - Sitemap scraper (recommended first)
- `homepage_career_finder.py` - Homepage link scraper (fallback method)
- `clear_career_pages.py` - Clear all career pages from database

## Usage

```bash
# Run sitemap scraper
python3 career_page_finder.py ../Database.csv

# Run homepage scraper for missing entries
python3 homepage_career_finder.py ../Database.csv

# Clear all career pages
python3 clear_career_pages.py ../Database.csv
```

## Features

- ✅ Detects career-specific sitemaps
- ✅ Scrapes homepage footer links
- ✅ Priority-based URL matching
- ✅ Filters out job listings
- ✅ Comprehensive error handling
