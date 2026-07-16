"""Normalization, auditing, and moderation helpers for company sources."""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import yaml


SUGGESTION_STATUSES = {
    "submitted",
    "needs_info",
    "verified",
    "approved",
    "rejected",
    "disabled",
}
TRACKING_KEYS = {"fbclid", "gclid", "ref", "source"}


def normalize_token(value: object) -> str:
    raw = unicodedata.normalize("NFKD", str(value or "").casefold())
    raw = "".join(char for char in raw if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "", raw)


def normalize_name(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def normalize_url(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    parts = urlsplit(raw)
    if parts.scheme.casefold() not in {"http", "https"} or not parts.hostname:
        raise ValueError("URL must use http or https and include a hostname")
    if parts.username or parts.password:
        raise ValueError("URL must not contain embedded credentials")
    host = parts.hostname.casefold()
    if parts.port:
        host = f"{host}:{parts.port}"
    query = [
        (key, item)
        for key, item in parse_qsl(parts.query, keep_blank_values=True)
        if key.casefold() not in TRACKING_KEYS
        and not key.casefold().startswith("utm_")
    ]
    path = re.sub(r"/+", "/", parts.path).rstrip("/") or "/"
    return urlunsplit((parts.scheme.casefold(), host, path, urlencode(query), ""))


def normalized_domain(value: object) -> str:
    url = normalize_url(value)
    host = urlsplit(url).hostname or ""
    return host[4:] if host.startswith("www.") else host


def parse_timestamp(value: object) -> Optional[datetime]:
    raw = str(value or "").strip()
    if not raw:
        return None
    parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class AtsCatalog:
    def __init__(self, canonical: dict[str, set[str]]):
        self.canonical = canonical
        self.aliases: dict[str, str] = {}
        for identifier, aliases in canonical.items():
            for alias in {identifier, *aliases}:
                token = normalize_token(alias)
                previous = self.aliases.get(token)
                if previous and previous != identifier:
                    raise ValueError(f"ATS alias {alias!r} maps to both {previous} and {identifier}")
                self.aliases[token] = identifier

    @classmethod
    def load(cls, path: Path) -> "AtsCatalog":
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        entries = payload.get("ats")
        if not isinstance(entries, list):
            raise ValueError("ATS catalog must contain an ats list")
        canonical: dict[str, set[str]] = {}
        for entry in entries:
            if isinstance(entry, str):
                identifier, aliases = entry, set()
            elif isinstance(entry, dict):
                identifier = str(entry.get("id", "")).strip()
                aliases = {str(value).strip() for value in entry.get("aliases", [])}
            else:
                raise ValueError("ATS entries must be strings or objects")
            if not identifier or normalize_token(identifier) != identifier:
                raise ValueError(f"Invalid canonical ATS identifier: {identifier!r}")
            canonical[identifier] = aliases
        return cls(canonical)

    def resolve(self, value: object) -> Optional[str]:
        return self.aliases.get(normalize_token(value))

    def identifiers(self) -> set[str]:
        return set(self.canonical)


@dataclass
class AuditFinding:
    code: str
    severity: str
    message: str


@dataclass
class AuditedCompany:
    index: int
    name: str
    website: str
    career_page: str
    website_domain: str
    career_domain: str
    ats: str
    active: bool
    status: str
    findings: list[AuditFinding] = field(default_factory=list)

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["findings"] = [asdict(finding) for finding in self.findings]
        return payload


@dataclass
class CatalogAuditReport:
    companies: list[AuditedCompany]

    @property
    def summary(self) -> dict[str, int]:
        values: dict[str, int] = {"total": len(self.companies)}
        for company in self.companies:
            values[company.status] = values.get(company.status, 0) + 1
        values["errors"] = sum(
            finding.severity == "error"
            for company in self.companies
            for finding in company.findings
        )
        values["warnings"] = sum(
            finding.severity == "warning"
            for company in self.companies
            for finding in company.findings
        )
        return values

    def to_dict(self) -> dict:
        return {
            "summary": self.summary,
            "companies": [company.to_dict() for company in self.companies],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)


def _is_active(row: dict) -> bool:
    value = row.get("active", row.get("Active", True))
    if isinstance(value, bool):
        return value
    return str(value).strip().casefold() not in {"false", "0", "no", "inactive", "disabled"}


def _row_value(row: dict, *keys: str) -> object:
    for key in keys:
        if key in row:
            return row[key]
    return ""


def audit_companies(
    rows: Iterable[dict],
    ats_catalog: AtsCatalog,
    *,
    now: Optional[datetime] = None,
    stale_days: int = 90,
    url_checker=None,
) -> CatalogAuditReport:
    now = now or datetime.now(timezone.utc)
    audited: list[AuditedCompany] = []
    website_domains: dict[str, list[int]] = {}
    career_urls: dict[str, list[int]] = {}

    for index, row in enumerate(rows, start=1):
        findings: list[AuditFinding] = []
        name = normalize_name(_row_value(row, "name", "Name"))
        active = _is_active(row)
        if not name:
            findings.append(AuditFinding("missing_name", "error", "Company name is required"))

        website = career_page = website_domain = career_domain = ""
        for field_name, keys in (
            ("website", ("website", "Website")),
            ("career_page", ("career_page", "Career Page")),
        ):
            raw = _row_value(row, *keys)
            try:
                normalized = normalize_url(raw)
                if not normalized:
                    raise ValueError("URL is required")
            except ValueError as exc:
                findings.append(AuditFinding(f"invalid_{field_name}", "error", str(exc)))
                normalized = ""
            if field_name == "website":
                website = normalized
                website_domain = normalized_domain(normalized) if normalized else ""
            else:
                career_page = normalized
                career_domain = normalized_domain(normalized) if normalized else ""

        raw_ats = _row_value(row, "ats", "Label")
        ats = ats_catalog.resolve(raw_ats) or ""
        if not ats:
            findings.append(
                AuditFinding(
                    "unsupported_ats",
                    "error",
                    f"ATS label {str(raw_ats).strip()!r} does not resolve to a supported scraper",
                )
            )

        verified_at = None
        try:
            verified_at = parse_timestamp(_row_value(row, "verified_at", "Verified At"))
        except ValueError:
            findings.append(
                AuditFinding("invalid_verified_at", "warning", "verified_at is not an ISO timestamp")
            )
        if active and verified_at is None:
            findings.append(
                AuditFinding("unverified", "warning", "Source has no verification timestamp")
            )
        elif active and verified_at and verified_at < now - timedelta(days=stale_days):
            findings.append(
                AuditFinding(
                    "stale",
                    "warning",
                    f"Source has not been verified in more than {stale_days} days",
                )
            )

        if active and url_checker and career_page:
            ok, detail = url_checker(career_page)
            if not ok:
                findings.append(AuditFinding("failing", "error", detail))

        if not active:
            status = "disabled"
        elif any(finding.code == "unsupported_ats" for finding in findings):
            status = "unsupported"
        elif any(finding.severity == "error" for finding in findings):
            status = "failing"
        elif any(finding.code == "stale" for finding in findings):
            status = "stale"
        elif any(finding.code == "unverified" for finding in findings):
            status = "unverified"
        else:
            status = "supported"

        audited.append(
            AuditedCompany(
                index=index,
                name=name,
                website=website,
                career_page=career_page,
                website_domain=website_domain,
                career_domain=career_domain,
                ats=ats,
                active=active,
                status=status,
                findings=findings,
            )
        )
        if website_domain:
            website_domains.setdefault(website_domain, []).append(index - 1)
        if career_page:
            career_urls.setdefault(career_page, []).append(index - 1)

    for code, groups, label in (
        ("duplicate_company_domain", website_domains, "company domain"),
        ("duplicate_career_url", career_urls, "careers URL"),
    ):
        for value, indexes in groups.items():
            if len(indexes) < 2:
                continue
            names = ", ".join(audited[index].name or f"row {index + 1}" for index in indexes)
            for index in indexes:
                audited[index].findings.append(
                    AuditFinding(code, "error", f"Duplicate {label} {value!r}: {names}")
                )
                if audited[index].active:
                    audited[index].status = "failing"

    return CatalogAuditReport(audited)


ISSUE_FIELD_LABELS = {
    "Company name": "name",
    "Company website": "website",
    "Careers page": "career_page",
    "ATS platform": "ats",
    "Berlin role evidence": "berlin_evidence",
    "Notes": "notes",
}


def parse_issue_form(body: str) -> dict[str, str]:
    result: dict[str, str] = {}
    sections = re.split(r"(?m)^###\s+", body or "")
    for section in sections[1:]:
        title, _, value = section.partition("\n")
        key = ISSUE_FIELD_LABELS.get(title.strip())
        if not key:
            continue
        cleaned = value.strip()
        if cleaned == "_No response_":
            cleaned = ""
        result[key] = cleaned
    return result


@dataclass
class SuggestionVerification:
    status: str
    normalized: dict[str, str]
    findings: list[AuditFinding]
    needs_scraper: bool = False

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "normalized": self.normalized,
            "findings": [asdict(finding) for finding in self.findings],
            "needs_scraper": self.needs_scraper,
        }


def verify_suggestion(
    suggestion: dict,
    existing_rows: Iterable[dict],
    ats_catalog: AtsCatalog,
    *,
    url_checker=None,
    scraper_smoke=None,
) -> SuggestionVerification:
    findings: list[AuditFinding] = []
    normalized = {"name": normalize_name(suggestion.get("name"))}
    if not normalized["name"]:
        findings.append(AuditFinding("missing_name", "error", "Company name is required"))

    for field_name in ("website", "career_page", "berlin_evidence"):
        try:
            normalized[field_name] = normalize_url(suggestion.get(field_name))
            if not normalized[field_name]:
                raise ValueError("URL is required")
        except ValueError as exc:
            normalized[field_name] = ""
            findings.append(AuditFinding(f"invalid_{field_name}", "error", str(exc)))

    ats = ats_catalog.resolve(suggestion.get("ats"))
    needs_scraper = ats is None
    normalized["ats"] = ats or ""
    if needs_scraper:
        findings.append(
            AuditFinding(
                "unsupported_ats",
                "error",
                f"ATS {suggestion.get('ats', '')!r} is unsupported and needs scraper work",
            )
        )

    existing_report = audit_companies(existing_rows, ats_catalog)
    website_domain = normalized_domain(normalized["website"]) if normalized["website"] else ""
    career_page = normalized["career_page"]
    for company in existing_report.companies:
        if website_domain and company.website_domain == website_domain:
            findings.append(
                AuditFinding(
                    "duplicate_company_domain",
                    "error",
                    f"Company domain already belongs to {company.name}",
                )
            )
        if career_page and company.career_page == career_page:
            findings.append(
                AuditFinding(
                    "duplicate_career_url",
                    "error",
                    f"Careers URL already belongs to {company.name}",
                )
            )

    if url_checker:
        for field_name in ("website", "career_page", "berlin_evidence"):
            value = normalized.get(field_name)
            if not value:
                continue
            ok, detail = url_checker(value)
            if not ok:
                findings.append(AuditFinding(f"unreachable_{field_name}", "error", detail))

    url_failed = any(finding.code.startswith("unreachable_") for finding in findings)
    if scraper_smoke and not url_failed and normalized["ats"] and normalized["career_page"]:
        ok, detail = scraper_smoke(
            normalized["name"], normalized["career_page"], normalized["ats"]
        )
        if not ok:
            findings.append(AuditFinding("scraper_smoke_failed", "error", detail))

    status = "needs_info" if any(finding.severity == "error" for finding in findings) else "verified"
    return SuggestionVerification(status, normalized, findings, needs_scraper)
