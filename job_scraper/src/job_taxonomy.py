"""Canonical classification rules for Daily Berlin Jobs engineering roles.

The publishing pipeline owns classification. Consumers such as the Next.js app
read the normalized columns written to Google Sheets instead of reimplementing
these rules.
"""

from __future__ import annotations

import re
from collections.abc import Mapping


CLASSIFICATION_VERSION = "engineering-v2"

ENGINEERING_EXCLUDE_PATTERN = re.compile(
    r"\b(?:sales engineer|solutions? engineer|customer success|support engineer|field engineer|"
    r"mechanical engineer|electrical engineer|electronics engineer|civil engineer|process engineer|"
    r"manufacturing engineer|industrial engineer|production engineer|environmental engineer|"
    r"energy engineer|service engineer|commissioning engineer|maintenance engineer|"
    r"account executive|recruiter|talent acquisition|marketing|"
    r"partnerships?|finance|product manager|product owner)\b",
    re.IGNORECASE,
)

ROLE_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("Fullstack", re.compile(r"\b(?:full[- ]?stack|fullstack)\b", re.IGNORECASE)),
    (
        "Backend",
        re.compile(
            r"\b(?:(?:backend|back[- ]?end).{0,24}(?:engineer|developer|tech lead)|"
            r"(?:engineer|developer|tech lead).{0,24}(?:backend|back[- ]?end)|api engineer|python (?:developer|engineer)|"
            r"java (?:developer|engineer)|golang|go (?:developer|engineer)|"
            r"node\.?js (?:developer|engineer)|php (?:developer|engineer)|"
            r"ruby (?:developer|engineer)|scala (?:developer|engineer))\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Frontend",
        re.compile(
            r"\b(?:(?:frontend|front[- ]?end).{0,24}(?:engineer|developer|tech lead)|"
            r"(?:engineer|developer|tech lead).{0,24}(?:frontend|front[- ]?end)|head of frontend|"
            r"ui engineer|web (?:developer|engineer)|"
            r"react (?:developer|engineer)|javascript (?:developer|engineer)|"
            r"typescript (?:developer|engineer))\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Data / AI / ML",
        re.compile(
            r"\b(?:data engineer|data scientist|analytics engineer|machine learning|ml engineer|"
            r"ai engineer|data platform engineer|computer vision engineer|nlp engineer)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Platform / DevOps / SRE",
        re.compile(
            r"\b(?:devops|sre|site reliability|platform engineer|cloud engineer|"
            r"infrastructure engineer|systems engineer)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Security",
        re.compile(
            r"\b(?:security engineer|application security|appsec engineer|iam engineer|"
            r"security architect|security developer)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Mobile",
        re.compile(
            r"\b(?:android (?:developer|engineer)|ios (?:developer|engineer)|mobile (?:developer|engineer)|"
            r"react native (?:developer|engineer)|flutter (?:developer|engineer))\b",
            re.IGNORECASE,
        ),
    ),
    (
        "QA / Test",
        re.compile(
            r"\b(?:qa engineer|quality engineer|quality assurance engineer|test automation|sdet|engineer in test)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Embedded / Firmware / Robotics",
        re.compile(
            r"\b(?:embedded(?: software)? engineer|firmware (?:engineer|developer)|"
            r"robotics(?: software)? engineer|autonomous systems engineer|controls software engineer)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Engineering Leadership",
        re.compile(
            r"(?:\b(?:engineering manager|head of engineering|director of engineering|"
            r"vp engineering|chief technology officer|engineering lead)\b|^(?:group )?cto(?:\s|$))",
            re.IGNORECASE,
        ),
    ),
    (
        "Software Engineering",
        re.compile(
            r"\b(?:software engineer|software developer|product engineer|development engineer|"
            r"deployment engineer|deployments engineer|software architect|solutions architect)\b",
            re.IGNORECASE,
        ),
    ),
]

LEVEL_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("Intern / Working Student", re.compile(r"\b(?:intern|internship|working student|werkstudent|praktik|praktikum|thesis student)\b", re.IGNORECASE)),
    ("Junior / Entry", re.compile(r"\b(?:junior|entry[- ]?level|graduate|trainee|associate)\b", re.IGNORECASE)),
    ("Staff / Principal", re.compile(r"\b(?:staff|principal|distinguished|fellow)\b", re.IGNORECASE)),
    ("Lead", re.compile(r"\b(?:team lead|tech lead|lead)\b", re.IGNORECASE)),
    ("Manager / Head / Director", re.compile(r"(?:\b(?:engineering manager|head of engineering|director of engineering|vp engineering|chief technology officer)\b|^(?:group )?cto(?:\s|$))", re.IGNORECASE)),
    ("Senior", re.compile(r"\b(?:senior|sr\.?)\b", re.IGNORECASE)),
]

TECH_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("JavaScript", re.compile(r"\bjavascript\b|\bjs\b", re.IGNORECASE)),
    ("TypeScript", re.compile(r"\btypescript\b|\bts\b", re.IGNORECASE)),
    ("React", re.compile(r"\breact(?:\.js)?\b", re.IGNORECASE)),
    ("Next.js", re.compile(r"\bnext\.?js\b", re.IGNORECASE)),
    ("Node.js", re.compile(r"\bnode\.?js\b", re.IGNORECASE)),
    ("Python", re.compile(r"\bpython\b", re.IGNORECASE)),
    ("Java", re.compile(r"\bjava\b", re.IGNORECASE)),
    ("Go", re.compile(r"\bgolang\b|\bgo (?:developer|engineer)\b", re.IGNORECASE)),
    ("C#", re.compile(r"\bc#\b|\b\.net\b", re.IGNORECASE)),
    ("C++", re.compile(r"\bc\+\+", re.IGNORECASE)),
    ("Ruby", re.compile(r"\bruby\b", re.IGNORECASE)),
    ("PHP", re.compile(r"\bphp\b", re.IGNORECASE)),
    ("Kotlin", re.compile(r"\bkotlin\b", re.IGNORECASE)),
    ("Swift", re.compile(r"\bswift\b", re.IGNORECASE)),
    ("AWS", re.compile(r"\baws\b|amazon web services", re.IGNORECASE)),
    ("Azure", re.compile(r"\bazure\b", re.IGNORECASE)),
    ("GCP", re.compile(r"\bgcp\b|google cloud", re.IGNORECASE)),
    ("Kubernetes", re.compile(r"\bkubernetes\b|\bk8s\b", re.IGNORECASE)),
    ("Docker", re.compile(r"\bdocker\b", re.IGNORECASE)),
    ("Terraform", re.compile(r"\bterraform\b", re.IGNORECASE)),
    ("SQL", re.compile(r"\bsql\b|postgres|mysql", re.IGNORECASE)),
]


def _text(row: Mapping[str, object], *keys: str) -> str:
    return " ".join(str(row.get(key, "") or "").strip() for key in keys).strip()


def classify_role(row: Mapping[str, object]) -> str:
    title = _text(row, "Job Title")
    if ENGINEERING_EXCLUDE_PATTERN.search(title):
        return ""
    for label, pattern in ROLE_RULES:
        if pattern.search(title):
            return label
    return ""


def classify_level(row: Mapping[str, object]) -> str:
    title = _text(row, "Job Title")
    for label, pattern in LEVEL_RULES:
        if pattern.search(title):
            return label
    return "Not specified"


def classify_work_mode(row: Mapping[str, object]) -> str:
    remote = _text(row, "Remote").casefold()
    location = _text(row, "Location").casefold()
    if "hybrid" in remote or "hybrid" in location:
        return "Hybrid"
    if remote == "yes" or "remote" in remote or "remote" in location:
        return "Remote"
    return "On-site"


def classify_technologies(row: Mapping[str, object]) -> list[str]:
    searchable = _text(row, "Job Title", "Department", "Job Description")
    return [label for label, pattern in TECH_RULES if pattern.search(searchable)]


def classify_job(row: Mapping[str, object]) -> dict[str, str]:
    """Return the normalized fields persisted with every published job."""
    role = classify_role(row)
    level = classify_level(row)
    work_mode = classify_work_mode(row)
    technologies = classify_technologies(row)
    department = _text(row, "Department")
    keywords = list(dict.fromkeys([item for item in [role, department, *technologies] if item]))
    return {
        "Role": role,
        "Level": level,
        "Work Mode": work_mode,
        "Tech Stack": ", ".join(technologies),
        "Keywords": ", ".join(keywords),
        "Classification Version": CLASSIFICATION_VERSION,
    }


def is_engineering_job(row: Mapping[str, object]) -> bool:
    return bool(classify_role(row))
