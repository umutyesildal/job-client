#!/usr/bin/env python3
"""Analyze current Berlin jobs and suggest consumer-facing filter groups."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from daily_berlin_jobs.server import visible_jobs  # noqa: E402


TITLE_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9+#.-]{2,}")
NOISE_TOKEN_PATTERNS = [
    re.compile(r"^[mfwd]/[mfwd]/[mfwd]$", re.IGNORECASE),
    re.compile(r"^[mfwd]-?[mfwd]-?[mfwd]$", re.IGNORECASE),
]
TITLE_STOPWORDS = {
    "all",
    "berlin",
    "developer",
    "developers",
    "engineer",
    "engineers",
    "genders",
    "intern",
    "junior",
    "lead",
    "manager",
    "new",
    "principal",
    "role",
    "roles",
    "senior",
    "software",
    "staff",
    "student",
    "today",
    "working",
}


@dataclass(frozen=True)
class CategoryRule:
    key: str
    label: str
    pattern: re.Pattern[str]


LEVEL_RULES = [
    CategoryRule("intern", "Intern / Working Student", re.compile(r"\b(intern|internship|working student|werkstudent|praktik|praktikum|thesis student)\b", re.IGNORECASE)),
    CategoryRule("junior", "Junior / Entry", re.compile(r"\b(junior|entry[- ]?level|graduate|trainee|associate)\b", re.IGNORECASE)),
    CategoryRule("staff_plus", "Staff / Principal", re.compile(r"\b(staff|principal|distinguished|fellow)\b", re.IGNORECASE)),
    CategoryRule("lead", "Lead", re.compile(r"\b(team lead|tech lead|lead)\b", re.IGNORECASE)),
    CategoryRule("manager_plus", "Manager / Head / Director", re.compile(r"\b(manager|head|director|vp|chief)\b", re.IGNORECASE)),
    CategoryRule("senior", "Senior", re.compile(r"\b(senior|sr\.?)\b", re.IGNORECASE)),
    CategoryRule("mid", "Mid", re.compile(r"\b(mid|intermediate)\b", re.IGNORECASE)),
]

ROLE_RULES = [
    CategoryRule("fullstack", "Fullstack", re.compile(r"\b(full[- ]?stack|fullstack)\b", re.IGNORECASE)),
    CategoryRule("backend", "Backend", re.compile(r"\b(backend|back[- ]?end|api|python|java|golang|go|node\.?(js)?|php|ruby|scala)\b", re.IGNORECASE)),
    CategoryRule("frontend", "Frontend", re.compile(r"\b(frontend|front[- ]?end|react|next\.?js|javascript|typescript|web ui|ui engineer)\b", re.IGNORECASE)),
    CategoryRule("data_ai", "Data / AI / ML", re.compile(r"\b(data engineer|data scientist|machine learning|\bml\b|ai engineer|analytics engineer|data platform|computer vision|nlp|data\b)\b", re.IGNORECASE)),
    CategoryRule("devops_platform", "Platform / DevOps / SRE", re.compile(r"\b(devops|sre|site reliability|platform|cloud|infrastructure|systems?)\b", re.IGNORECASE)),
    CategoryRule("security", "Security", re.compile(r"\b(security|application security|appsec|iam|soc)\b", re.IGNORECASE)),
    CategoryRule("mobile", "Mobile", re.compile(r"\b(android|ios|mobile|react native|flutter)\b", re.IGNORECASE)),
    CategoryRule("qa", "QA / Test", re.compile(r"\b(qa|quality assurance|test automation|sdet|engineer in test)\b", re.IGNORECASE)),
    CategoryRule("product", "Product", re.compile(r"\b(product manager|product owner|technical product manager)\b", re.IGNORECASE)),
    CategoryRule("operations", "Operations", re.compile(r"\b(operations|sales ops|revops|business operations|ml ops|ai operations)\b", re.IGNORECASE)),
]

TECH_GATE = re.compile(
    r"\b(engineer|developer|devops|sre|data scientist|machine learning|software|frontend|backend|fullstack|full stack|platform|cloud|security|qa|ios|android|mobile|product manager|technical product manager)\b",
    re.IGNORECASE,
)


def classify(text: str, rules: list[CategoryRule], default_key: str) -> str:
    for rule in rules:
        if rule.pattern.search(text):
            return rule.key
    return default_key


def title_terms(title: str) -> list[str]:
    tokens: list[str] = []
    for raw in TITLE_TOKEN_RE.findall(title.lower()):
        token = raw.strip(".-")
        if len(token) < 3 or token in TITLE_STOPWORDS:
            continue
        if any(pattern.match(token) for pattern in NOISE_TOKEN_PATTERNS):
            continue
        tokens.append(token)
    return tokens


def pct(count: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(count * 100 / total, 1)


def summarize(source: str, top_n: int) -> dict:
    jobs = visible_jobs(source)
    level_counts: Counter[str] = Counter()
    role_counts: Counter[str] = Counter()
    tech_role_counts: Counter[str] = Counter()
    token_counts: Counter[str] = Counter()
    bigram_counts: Counter[str] = Counter()

    for job in jobs:
        title = job.get("Job Title", "")
        department = job.get("Department", "")
        text = f"{title} {department}".strip()

        level_key = classify(text, LEVEL_RULES, "unspecified")
        role_key = classify(text, ROLE_RULES, "other")

        level_counts[level_key] += 1
        role_counts[role_key] += 1
        if TECH_GATE.search(text):
            tech_role_counts[role_key] += 1

        terms = title_terms(title)
        token_counts.update(terms)
        bigram_counts.update(" ".join(pair) for pair in zip(terms, terms[1:]))

    suggested_level_filters = [
        {
            "key": key,
            "label": next(rule.label for rule in LEVEL_RULES if rule.key == key),
            "count": level_counts[key],
            "sharePct": pct(level_counts[key], len(jobs)),
        }
        for key in ["intern", "junior", "senior", "staff_plus", "lead", "manager_plus"]
        if level_counts[key] > 0
    ]

    suggested_role_filters = [
        {
            "key": key,
            "label": next(rule.label for rule in ROLE_RULES if rule.key == key),
            "count": tech_role_counts[key],
            "sharePct": pct(tech_role_counts[key], len(jobs)),
        }
        for key in ["backend", "frontend", "fullstack", "data_ai", "devops_platform", "security", "mobile", "qa", "product"]
        if tech_role_counts[key] >= 8
    ]

    return {
        "source": source,
        "totalJobs": len(jobs),
        "levelCounts": level_counts,
        "roleCounts": role_counts,
        "techRoleCounts": tech_role_counts,
        "topTitleTokens": token_counts.most_common(top_n),
        "topTitleBigrams": bigram_counts.most_common(top_n),
        "suggestedLevelFilters": suggested_level_filters,
        "suggestedRoleFilters": suggested_role_filters,
        "notes": [
            "Operations is noisy in the raw market because many titles are business or sales operations, not engineering operations.",
            "Mid-level titles are rarely explicit, so a dedicated Mid filter is likely low value.",
            "Platform / DevOps / SRE is strong enough to deserve its own consumer-facing filter.",
        ],
    }


def print_report(report: dict) -> None:
    total = report["totalJobs"]
    print(f"Source: {report['source']}")
    print(f"Visible Berlin jobs analyzed: {total}")
    print()

    print("Level breakdown")
    for key in ["intern", "junior", "senior", "staff_plus", "lead", "manager_plus", "mid", "unspecified"]:
        count = report["levelCounts"].get(key, 0)
        if count:
            print(f"  - {key}: {count} ({pct(count, total)}%)")
    print()

    print("Role breakdown (all visible jobs)")
    for key, count in report["roleCounts"].most_common():
        print(f"  - {key}: {count} ({pct(count, total)}%)")
    print()

    print("Role breakdown (tech-safe subset)")
    for key, count in report["techRoleCounts"].most_common():
        print(f"  - {key}: {count} ({pct(count, total)}%)")
    print()

    print("Top title keywords")
    for token, count in report["topTitleTokens"]:
        print(f"  - {token}: {count}")
    print()

    print("Top title bigrams")
    for phrase, count in report["topTitleBigrams"]:
        print(f"  - {phrase}: {count}")
    print()

    print("Suggested level filters")
    for item in report["suggestedLevelFilters"]:
        print(f"  - {item['label']} ({item['count']})")
    print()

    print("Suggested role filters")
    for item in report["suggestedRoleFilters"]:
        print(f"  - {item['label']} ({item['count']})")
    print()

    print("Notes")
    for note in report["notes"]:
        print(f"  - {note}")


def to_jsonable(report: dict) -> dict:
    return {
        **report,
        "levelCounts": dict(report["levelCounts"]),
        "roleCounts": dict(report["roleCounts"]),
        "techRoleCounts": dict(report["techRoleCounts"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze current Berlin job titles and suggest filter groups.")
    parser.add_argument("--source", default="all", choices=["all", "daily"], help="Job source to analyze.")
    parser.add_argument("--top", type=int, default=15, help="How many top tokens / bigrams to print.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a text report.")
    args = parser.parse_args()

    report = summarize(args.source, args.top)
    if args.json:
        print(json.dumps(to_jsonable(report), indent=2, ensure_ascii=False))
    else:
        print_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
