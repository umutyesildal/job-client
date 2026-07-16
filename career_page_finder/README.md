# Career Page Finder

Find company career pages from a CSV containing `Name` and `Website` columns.
The command checks sitemaps first, then automatically falls back to links on
the company homepage. Existing values in an optional `Career Page` column are
left unchanged.

## Usage

Run from the repository root and provide an output file so the source CSV stays
untouched:

```bash
.venv/bin/python career_page_finder/career_page_finder.py companies.csv \
  --output career-pages.csv \
  --delay 2
```

The homepage-only script remains available for diagnostics:

```bash
.venv/bin/python career_page_finder/homepage_career_finder.py companies.csv \
  --output career-pages.csv
```

The finder writes progress to the output CSV after every company and logs to
the terminal. It does not create log or data files in the repository.
