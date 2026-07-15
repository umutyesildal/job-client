#!/usr/bin/env python3
"""Destructive integration smoke test for a disposable local PostgreSQL DB."""

import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "job_scraper" / "src"))

from postgres_storage import PostgresJobStorage  # noqa: E402


def main() -> int:
    database_url = os.environ.get("DATABASE_URL", "")
    host = urlsplit(database_url).hostname
    if host not in {"localhost", "127.0.0.1"}:
        raise RuntimeError("Smoke test is destructive and only accepts a local disposable database")

    storage = PostgresJobStorage(retention_days=30)
    storage.migrate()
    with storage.connect() as connection, connection.cursor() as cursor:
        cursor.execute(
            "TRUNCATE jobs, job_url_aliases, job_fingerprints, crawl_runs RESTART IDENTITY CASCADE"
        )

    today = datetime.now(ZoneInfo("Europe/Berlin")).date().isoformat()
    common = {
        "Company Name": "München Labs",
        "Job Title": "Junior Software Engineer (m/f/d)",
        "Location": "Berlin, Germany",
        "Role": "Software Engineering",
        "Classification Version": "engineering-v2",
        "Posted Date": today,
    }
    rows = pd.DataFrame([
        {**common, "Job Link": "https://example.com/jobs/old?utm_source=test"},
        {
            **common,
            "Company Name": "Munchen Labs",
            "Job Title": "Junior Software Engineer - m/f/d",
            "Location": "Berlin Germany",
            "Job Link": "https://example.com/jobs/new#apply",
        },
        {
            "Company Name": "Old Co",
            "Job Title": "Backend Engineer",
            "Location": "Berlin",
            "Job Link": "https://example.com/jobs/expired",
            "Role": "Backend",
            "Classification Version": "engineering-v2",
            "Posted Date": "2020-01-01",
        },
    ])
    stats = storage.upsert_jobs(rows)
    assert (stats.inserted, stats.updated, stats.skipped) == (1, 1, 1), stats

    alias_stats = storage.upsert_jobs(pd.DataFrame([{
        **common,
        "Job Title": "Software Engineer II",
        "Job Link": "https://example.com/jobs/old",
    }]))
    assert (alias_stats.inserted, alias_stats.updated) == (0, 1), alias_stats

    with storage.connect() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM jobs")
        assert cursor.fetchone()[0] == 1
        cursor.execute("SELECT title FROM jobs")
        assert cursor.fetchone()[0] == "Software Engineer II"
        cursor.execute("SELECT count(*) FROM job_fingerprints")
        assert cursor.fetchone()[0] == 2
        cursor.execute("SELECT count(*) FROM job_url_aliases")
        assert cursor.fetchone()[0] == 3
        cursor.execute(
            "UPDATE jobs SET posted_at = NULL, first_seen_at = now() - interval '31 days'"
        )

    retention_stats = storage.upsert_jobs(pd.DataFrame())
    assert retention_stats.deleted == 1, retention_stats
    with storage.connect() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM jobs")
        assert cursor.fetchone()[0] == 0
        cursor.execute("SELECT count(*) FROM job_fingerprints")
        assert cursor.fetchone()[0] == 2
        cursor.execute("SET ROLE daily_jobs_web")
        cursor.execute("SELECT job_count FROM data_status")
        assert cursor.fetchone()[0] == 0
        cursor.execute("RESET ROLE")

    print("PostgreSQL smoke: migration, semantic dedup, URL mutation, expiry skip, and 30-day deletion passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
