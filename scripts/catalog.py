#!/usr/bin/env python3
"""Read-only catalog audits and maintainer-controlled suggestion moderation."""

from __future__ import annotations

import argparse
import ipaddress
import json
import signal
import socket
import tempfile
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import pandas as pd
import requests
import yaml

from daily_jobs.company_catalog import (
    AtsCatalog,
    audit_companies,
    parse_issue_form,
    verify_suggestion,
)
from daily_jobs.postgres_storage import PostgresJobStorage


REPO_ROOT = Path(__file__).resolve().parents[1]
ATS_PATH = REPO_ROOT / "catalog" / "ats.yaml"
DEFAULT_CATALOG_PATH = REPO_ROOT / "catalog" / "companies.yaml"


def load_yaml_rows(path: Path) -> list[dict]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    rows = payload.get("companies")
    if not isinstance(rows, list):
        raise ValueError(f"{path} must contain a companies list")
    return rows


def load_rows(source: str, input_type: str) -> list[dict]:
    if input_type == "postgres":
        return PostgresJobStorage().load_companies().fillna("").to_dict(orient="records")
    path = Path(source)
    if input_type == "yaml":
        return load_yaml_rows(path)
    return pd.read_csv(path, low_memory=False, dtype=str).fillna("").to_dict(orient="records")


def check_url(url: str) -> tuple[bool, str]:
    try:
        current = url
        for _ in range(6):
            hostname = urlsplit(current).hostname
            if not hostname:
                return False, "URL has no hostname"
            addresses = {
                ipaddress.ip_address(item[4][0])
                for item in socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)
            }
            if not addresses or any(not address.is_global for address in addresses):
                return False, f"{current} resolves to a private or non-public address"
            response = requests.get(
                current,
                timeout=15,
                allow_redirects=False,
                headers={"User-Agent": "daily-berlin-jobs-catalog-audit/1.0"},
                stream=True,
            )
            if response.is_redirect or response.is_permanent_redirect:
                target = response.headers.get("location", "")
                response.close()
                if not target:
                    return False, f"{current} returned a redirect without a location"
                current = urljoin(current, target)
                continue
            ok = response.status_code < 400
            detail = f"{current} returned HTTP {response.status_code}"
            response.close()
            return ok, detail
        return False, f"{url} exceeded the redirect limit"
    except requests.RequestException as exc:
        return False, f"{url} could not be reached: {exc.__class__.__name__}"
    except (socket.gaierror, ValueError):
        return False, f"{url} hostname could not be resolved"


def smoke_scraper(company: str, career_page: str, ats: str) -> tuple[bool, str]:
    from daily_jobs.client import JobCrawlerController

    with tempfile.TemporaryDirectory() as output_dir:
        controller = JobCrawlerController(delay=0, output_dir=output_dir, max_workers=1)
        scraper = controller.get_scraper(ats)
        if scraper is None:
            return False, f"No scraper resolves for canonical ATS {ats!r}"
        alarm_signal = getattr(signal, "SIGALRM", None)
        previous_handler = signal.getsignal(alarm_signal) if alarm_signal else None

        def timeout_handler(_signum, _frame):
            raise TimeoutError("Scraper smoke test exceeded 60 seconds")

        try:
            if alarm_signal:
                signal.signal(alarm_signal, timeout_handler)
                signal.alarm(60)
            jobs = scraper.scrape_jobs(
                url=career_page,
                company_name=company,
                company_description="",
                label=ats,
            )
        except Exception as exc:
            return False, f"Scraper raised {exc.__class__.__name__}: {str(exc)[:200]}"
        finally:
            if alarm_signal:
                signal.alarm(0)
                signal.signal(alarm_signal, previous_handler)
        if jobs is None or not isinstance(jobs, list):
            return False, "Scraper did not return a job list"
        return True, f"Scraper completed and returned {len(jobs)} jobs"


def read_issue_event(path: Path) -> tuple[dict, dict]:
    event = json.loads(path.read_text(encoding="utf-8"))
    issue = event.get("issue") or {}
    if not issue.get("number") or not issue.get("html_url"):
        raise ValueError("GitHub event does not contain an issue")
    suggestion = parse_issue_form(issue.get("body", ""))
    suggestion["notes"] = suggestion.get("notes", "")
    return issue, suggestion


def verification_from_event(args) -> tuple[dict, dict, object]:
    issue, suggestion = read_issue_event(Path(args.event))
    existing_rows = load_yaml_rows(Path(args.catalog))
    verification = verify_suggestion(
        suggestion,
        existing_rows,
        AtsCatalog.load(ATS_PATH),
        url_checker=check_url if args.check_urls else None,
        scraper_smoke=smoke_scraper if args.smoke_test else None,
    )
    return issue, suggestion, verification


def audit_command(args) -> int:
    report = audit_companies(
        load_rows(args.source, args.input_type),
        AtsCatalog.load(ATS_PATH),
        stale_days=args.stale_days,
        url_checker=check_url if args.check_urls else None,
    )
    output = report.to_json()
    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 1 if report.summary.get("errors", 0) else 0


def export_command(args) -> int:
    rows = PostgresJobStorage().load_companies().fillna("").to_dict(orient="records")
    report = audit_companies(rows, AtsCatalog.load(ATS_PATH))
    if report.summary.get("errors", 0):
        print(report.to_json(), file=sys.stderr)
        raise RuntimeError("Database catalog contains audit errors and cannot be exported")
    payload = {
        "companies": [
            {
                "name": company.name,
                "website": company.website,
                "career_page": company.career_page,
                "ats": company.ats,
                "active": company.active,
            }
            for company in report.companies
        ]
    }
    Path(args.output).write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    print(f"Exported {len(report.companies)} non-secret company sources to {args.output}")
    return 0


def verify_issue_command(args) -> int:
    issue, _, verification = verification_from_event(args)
    payload = {
        "issue": issue["number"],
        "source_url": issue["html_url"],
        **verification.to_dict(),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 1 if verification.status != "verified" else 0


def approve_issue_command(args) -> int:
    issue, suggestion, verification = verification_from_event(args)
    if verification.status != "verified":
        print(json.dumps(verification.to_dict(), indent=2), file=sys.stderr)
        raise RuntimeError("Suggestion must pass verification before approval")
    normalized = {**suggestion, **verification.normalized}
    submitted_at = datetime.fromisoformat(issue["created_at"].replace("Z", "+00:00"))
    storage = PostgresJobStorage()
    storage.migrate()
    suggestion_id = storage.approve_company_suggestion(
        normalized,
        source_issue=int(issue["number"]),
        source_url=issue["html_url"],
        actor=args.actor,
        submitted_at=submitted_at,
    )
    print(
        json.dumps(
            {
                "id": suggestion_id,
                "issue": issue["number"],
                "status": "approved",
                "company": normalized["name"],
                "ats": normalized["ats"],
            },
            indent=2,
        )
    )
    return 0


def decision_command(args) -> int:
    issue, suggestion = read_issue_event(Path(args.event))
    verification = verify_suggestion(
        suggestion,
        load_yaml_rows(Path(args.catalog)),
        AtsCatalog.load(ATS_PATH),
    )
    normalized = {**suggestion, **verification.normalized}
    submitted_at = datetime.fromisoformat(issue["created_at"].replace("Z", "+00:00"))
    storage = PostgresJobStorage()
    storage.migrate()
    method = (
        storage.disable_company_suggestion
        if args.status == "disabled"
        else storage.record_company_suggestion
    )
    suggestion_id = method(
        normalized,
        source_issue=int(issue["number"]),
        source_url=issue["html_url"],
        status=args.status,
        actor=args.actor,
        submitted_at=submitted_at,
        findings=[finding.__dict__ for finding in verification.findings],
    )
    print(json.dumps({"id": suggestion_id, "issue": issue["number"], "status": args.status}))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit = subparsers.add_parser("audit", help="Audit a catalog without changing its source")
    audit.add_argument("source", nargs="?", default=str(DEFAULT_CATALOG_PATH))
    audit.add_argument("--input-type", choices=["yaml", "csv", "postgres"], default="yaml")
    audit.add_argument("--check-urls", action="store_true")
    audit.add_argument("--stale-days", type=int, default=90)
    audit.add_argument("--output")
    audit.set_defaults(handler=audit_command)

    exporter = subparsers.add_parser(
        "export-postgres",
        help="Export a reviewed non-secret PostgreSQL catalog fixture",
    )
    exporter.add_argument("--output", default=str(DEFAULT_CATALOG_PATH))
    exporter.set_defaults(handler=export_command)

    for command, handler in (
        ("verify-issue", verify_issue_command),
        ("approve-issue", approve_issue_command),
    ):
        item = subparsers.add_parser(command)
        item.add_argument("--event", required=True)
        item.add_argument("--catalog", default=str(DEFAULT_CATALOG_PATH))
        item.add_argument("--check-urls", action="store_true")
        item.add_argument("--smoke-test", action="store_true")
        if command == "approve-issue":
            item.add_argument("--actor", required=True)
        item.set_defaults(handler=handler)

    decision = subparsers.add_parser("record-decision")
    decision.add_argument("--event", required=True)
    decision.add_argument("--catalog", default=str(DEFAULT_CATALOG_PATH))
    decision.add_argument("--status", choices=["rejected", "disabled"], required=True)
    decision.add_argument("--actor", required=True)
    decision.set_defaults(handler=decision_command)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
