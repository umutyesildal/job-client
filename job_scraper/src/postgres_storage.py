"""Portable PostgreSQL storage used by Supabase and local Docker."""

from __future__ import annotations

import hashlib
import os
import re
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

import pandas as pd
from dotenv import load_dotenv


TRACKING_QUERY_PREFIXES = ("utm_",)
TRACKING_QUERY_KEYS = {"fbclid", "gclid", "ref", "source", "trackingid"}


def _normalize_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    normalized = unicodedata.normalize("NFKD", str(value).casefold())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", normalized).strip()


def canonicalize_url(value: object) -> str:
    """Remove fragments/tracking noise while preserving the actual job URL."""
    raw = "" if value is None or pd.isna(value) else str(value).strip()
    if not raw:
        return ""
    try:
        parts = urlsplit(raw)
        query = [
            (key, item)
            for key, item in parse_qsl(parts.query, keep_blank_values=True)
            if key.casefold() not in TRACKING_QUERY_KEYS
            and not key.casefold().startswith(TRACKING_QUERY_PREFIXES)
        ]
        path = parts.path.rstrip("/") or "/"
        return urlunsplit((parts.scheme.casefold(), parts.netloc.casefold(), path, urlencode(query), ""))
    except ValueError:
        return raw


def _digest(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


def job_keys(row: dict) -> tuple[str, Optional[str], str]:
    company = _normalize_text(row.get("Company Name") or row.get("Company"))
    title = _normalize_text(row.get("Job Title"))
    location = _normalize_text(row.get("Location"))
    if not company or not title or not location:
        raise ValueError("A published job needs company, title, and location")
    canonical_url = canonicalize_url(row.get("Job Link"))
    identity_key = _digest(company, title, location)
    url_key = _digest(canonical_url) if canonical_url else None
    return identity_key, url_key, canonical_url


def _split_list(value: object) -> list[str]:
    if value is None or pd.isna(value):
        return []
    return [item.strip() for item in re.split(r"[,;|]", str(value)) if item.strip()]


def _posted_date(value: object) -> Optional[date]:
    if value is None or pd.isna(value) or not str(value).strip():
        return None
    raw = str(value).strip()
    relative = re.fullmatch(r"(\d+)\s+(hour|hours|day|days)\s+ago", raw, re.IGNORECASE)
    if relative:
        amount = int(relative.group(1))
        today = datetime.now(ZoneInfo("Europe/Berlin")).date()
        return today - timedelta(days=amount if "day" in relative.group(2).casefold() else 0)
    parsed = pd.to_datetime(raw, errors="coerce")
    return None if pd.isna(parsed) else parsed.date()


@dataclass
class UpsertStats:
    discovered: int = 0
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    deleted: int = 0


class PostgresJobStorage:
    def __init__(self, database_url: Optional[str] = None, retention_days: int = 30):
        configured_url = database_url or os.getenv("DATABASE_URL", "")
        if not configured_url:
            load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)
            configured_url = os.getenv("DATABASE_URL", "")
        self.database_url = configured_url
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is required for PostgreSQL storage")
        self.retention_days = retention_days

    def connect(self):
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError("PostgreSQL support requires psycopg") from exc
        return psycopg.connect(self.database_url)

    def migrate(self, migrations_dir: Optional[Path] = None) -> list[str]:
        migrations_dir = migrations_dir or Path(__file__).resolve().parents[2] / "db" / "migrations"
        applied = []
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations "
                "(version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
            )
            cursor.execute("SELECT version FROM schema_migrations")
            existing = {row[0] for row in cursor.fetchall()}
            for migration in sorted(migrations_dir.glob("*.sql")):
                if migration.name in existing:
                    continue
                cursor.execute(migration.read_text(encoding="utf-8"))
                cursor.execute("INSERT INTO schema_migrations(version) VALUES (%s)", (migration.name,))
                applied.append(migration.name)
        return applied

    def load_companies(self) -> pd.DataFrame:
        query = """
            SELECT c.name AS "Name", c.website AS "Website", s.career_page AS "Career Page",
                   c.description AS "Description", s.ats_label AS "Label", 'active' AS "Active"
            FROM companies c
            JOIN career_sources s ON s.company_id = c.id
            WHERE c.active AND s.active
            ORDER BY c.name, s.id
        """
        with self.connect() as connection:
            return pd.read_sql_query(query, connection)

    def upsert_companies(self, dataframe: pd.DataFrame) -> int:
        rows = dataframe.fillna("").to_dict(orient="records")
        with self.connect() as connection, connection.cursor() as cursor:
            for row in rows:
                cursor.execute(
                    """
                    INSERT INTO companies(name, website, description, active)
                    VALUES (%s, NULLIF(%s, ''), NULLIF(%s, ''), true)
                    ON CONFLICT (name) DO UPDATE SET website = EXCLUDED.website,
                        description = EXCLUDED.description, active = true, updated_at = now()
                    RETURNING id
                    """,
                    (row.get("Name", ""), row.get("Website", ""), row.get("Description", "")),
                )
                company_id = cursor.fetchone()[0]
                cursor.execute(
                    """
                    INSERT INTO career_sources(company_id, career_page, ats_label, active)
                    VALUES (%s, %s, %s, true)
                    ON CONFLICT (company_id, career_page) DO UPDATE SET
                        ats_label = EXCLUDED.ats_label, active = true, updated_at = now()
                    """,
                    (company_id, row.get("Career Page", ""), row.get("Label", "")),
                )
        return len(rows)

    def upsert_jobs(self, dataframe: pd.DataFrame) -> UpsertStats:
        rows = dataframe.fillna("").to_dict(orient="records")
        stats = UpsertStats(discovered=len(rows))
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.retention_days)
        run_id = uuid.uuid4()

        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute("INSERT INTO crawl_runs(id, discovered_count) VALUES (%s, %s)", (run_id, len(rows)))
            try:
                for row in rows:
                    identity_key, url_key, canonical_url = job_keys(row)
                    cursor.execute(
                        """
                        SELECT f.identity_key, f.first_seen_at
                        FROM job_fingerprints f
                        LEFT JOIN job_url_aliases a ON a.identity_key = f.identity_key
                        WHERE f.identity_key = %s OR a.url_key = %s
                        ORDER BY (a.url_key = %s) DESC LIMIT 1
                        """,
                        (identity_key, url_key, url_key),
                    )
                    existing_fingerprint = cursor.fetchone()
                    stable_key = existing_fingerprint[0] if existing_fingerprint else identity_key
                    first_seen = existing_fingerprint[1] if existing_fingerprint else datetime.now(timezone.utc)
                    cursor.execute(
                        """
                        INSERT INTO job_fingerprints(identity_key, first_seen_at, last_seen_at)
                        VALUES (%s, %s, now())
                        ON CONFLICT (identity_key) DO UPDATE SET
                            last_seen_at = now()
                        """,
                        (stable_key, first_seen),
                    )
                    if url_key:
                        cursor.execute(
                            """
                            INSERT INTO job_url_aliases(url_key, identity_key, last_seen_at)
                            VALUES (%s, %s, now())
                            ON CONFLICT (url_key) DO UPDATE SET last_seen_at = now()
                            """,
                            (url_key, stable_key),
                        )

                    posted_at = _posted_date(row.get("Posted Date"))
                    retention_anchor = datetime.combine(posted_at, datetime.min.time(), timezone.utc) if posted_at else first_seen
                    if retention_anchor < cutoff:
                        stats.skipped += 1
                        continue

                    cursor.execute("SELECT 1 FROM jobs WHERE identity_key = %s", (stable_key,))
                    existed = cursor.fetchone() is not None
                    cursor.execute(
                        """
                        INSERT INTO jobs(
                            identity_key, url_key, company_name, title, location, canonical_url,
                            description, employment_type, department, role, level, work_mode,
                            tech_stack, keywords, classification_version, posted_at,
                            company_description, remote, ats_label, source, first_seen_at, last_seen_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, NULLIF(%s, ''), NULLIF(%s, ''), NULLIF(%s, ''),
                            NULLIF(%s, ''), %s, NULLIF(%s, ''), NULLIF(%s, ''), %s, %s, %s, %s,
                            NULLIF(%s, ''), NULLIF(%s, ''), NULLIF(%s, ''), NULLIF(%s, ''), %s, now()
                        )
                        ON CONFLICT (identity_key) DO UPDATE SET
                            url_key = COALESCE(EXCLUDED.url_key, jobs.url_key),
                            company_name = EXCLUDED.company_name,
                            title = EXCLUDED.title,
                            location = EXCLUDED.location,
                            canonical_url = COALESCE(EXCLUDED.canonical_url, jobs.canonical_url),
                            description = COALESCE(EXCLUDED.description, jobs.description),
                            employment_type = COALESCE(EXCLUDED.employment_type, jobs.employment_type),
                            department = COALESCE(EXCLUDED.department, jobs.department),
                            role = EXCLUDED.role, level = EXCLUDED.level, work_mode = EXCLUDED.work_mode,
                            tech_stack = EXCLUDED.tech_stack, keywords = EXCLUDED.keywords,
                            classification_version = EXCLUDED.classification_version,
                            posted_at = COALESCE(EXCLUDED.posted_at, jobs.posted_at),
                            company_description = COALESCE(EXCLUDED.company_description, jobs.company_description),
                            remote = COALESCE(EXCLUDED.remote, jobs.remote), ats_label = COALESCE(EXCLUDED.ats_label, jobs.ats_label),
                            source = COALESCE(EXCLUDED.source, jobs.source), last_seen_at = now(), updated_at = now()
                        """,
                        (
                            stable_key, url_key, row.get("Company Name") or row.get("Company"),
                            row.get("Job Title"), row.get("Location"), canonical_url,
                            row.get("Job Description"), row.get("Employment Type"), row.get("Department"),
                            row.get("Role"), row.get("Level"), row.get("Work Mode"),
                            _split_list(row.get("Tech Stack")), _split_list(row.get("Keywords")),
                            row.get("Classification Version"), posted_at, row.get("Company Description"),
                            row.get("Remote"), row.get("Label") or row.get("ATS"), row.get("ATS") or row.get("Label"),
                            first_seen,
                        ),
                    )
                    stats.updated += int(existed)
                    stats.inserted += int(not existed)

                cursor.execute(
                    "DELETE FROM jobs WHERE COALESCE(posted_at, (first_seen_at AT TIME ZONE 'Europe/Berlin')::date) "
                    "< (now() AT TIME ZONE 'Europe/Berlin')::date - %s RETURNING id",
                    (self.retention_days,),
                )
                stats.deleted = len(cursor.fetchall())
                cursor.execute(
                    """
                    UPDATE crawl_runs SET finished_at = now(), status = 'succeeded', inserted_count = %s,
                        updated_count = %s, skipped_count = %s, deleted_count = %s WHERE id = %s
                    """,
                    (stats.inserted, stats.updated, stats.skipped, stats.deleted, run_id),
                )
            except Exception as exc:
                connection.rollback()
                with self.connect() as error_connection, error_connection.cursor() as error_cursor:
                    error_cursor.execute(
                        "INSERT INTO crawl_runs(id, finished_at, status, discovered_count, error) "
                        "VALUES (%s, now(), 'failed', %s, %s)",
                        (run_id, len(rows), str(exc)[:2000]),
                    )
                raise
        return stats
