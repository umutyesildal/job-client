# Daily Berlin Jobs architecture

## Product boundary

Daily Berlin Jobs currently publishes Berlin engineering roles only. The brand
name is intentionally broader than the initial taxonomy, but scope expansion is
deferred. LinkedIn queries remain engineering-focused.

## Data flow

1. The crawler collects ATS jobs using the companies configured in `OneSingle`.
2. The daily LinkedIn collector adds recent engineering-query results.
3. `post_process_jobs.py` sends every incoming row through
   `job_taxonomy.py`.
4. Non-Berlin and non-engineering rows are excluded from the public collection.
5. Matching rows are deduplicated and written to `All Jobs`.
6. Jobs posted today or yesterday in `Europe/Berlin` are written to
   `Daily New Jobs`.
7. Next.js reads both worksheets on the server and renders their normalized
   fields.

The crawler runs in GitHub Actions. Vercel reads Sheets and dispatches the
workflow; it never runs the crawler itself.

## Published job contract

In addition to the source job columns, every public row contains:

| Column | Meaning |
| --- | --- |
| `Role` | Engineering area used by the public filter |
| `Level` | Normalized seniority or `Not specified` |
| `Work Mode` | `Remote`, `Hybrid`, or `On-site` |
| `Tech Stack` | Comma-separated technologies derived from job text |
| `Keywords` | Search terms derived from role, department, and technologies |
| `Classification Version` | Rule version; currently `engineering-v1` |

The Python pipeline is the only classification authority. The Next.js app may
parse these values but must not recreate taxonomy regexes.

## Scope changes

A future expansion must create a new classification version, add tests for the
new include/exclude boundary, update query inputs deliberately, and validate a
manual workflow run before the public filters are changed.

## Legacy boundary

`daily_berlin_jobs/` is the previous local stdlib UI. It remains only until
public and admin parity are confirmed in the deployed Next.js app. No new
product behavior should be added to it.
