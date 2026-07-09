"""Local web app for Daily Berlin Software Jobs."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from datetime import datetime
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
STATIC_DIR = Path(__file__).resolve().parent / "static"
SRC_DIR = REPO_ROOT / "job_scraper" / "src"
SETTINGS_PATH = DATA_DIR / "daily_berlin_jobs_settings.json"
RUN_LOG_PATH = DATA_DIR / "daily_berlin_jobs_last_run.json"

DEFAULT_SETTINGS = {
    "includeLinkedIn": True,
    "profileFitOnly": True,
    "location": "Berlin, Germany",
    "limitPerQuery": 25,
    "postedWithinSeconds": 86400,
    "delay": 1.0,
    "skipUpload": True,
    "keywords": [
        "software engineer",
        "software developer",
        "backend engineer",
        "backend developer",
        "frontend engineer",
        "frontend developer",
        "fullstack engineer",
        "full stack engineer",
        "fullstack developer",
        "python developer",
        "react developer",
        "typescript developer",
    ],
}

SOURCES = {
    "related": DATA_DIR / "related_jobs.csv",
    "daily": DATA_DIR / "daily_new_jobs.csv",
    "linkedin": DATA_DIR / "linkedin_daily_jobs.csv",
}

ROLE_KEYWORDS = {
    "backend": ("backend", "back-end", "api", "python", "django", "fastapi", "node"),
    "frontend": ("frontend", "front-end", "react", "typescript", "javascript", "next"),
    "fullstack": ("fullstack", "full-stack", "full stack"),
    "data": ("data engineer", "machine learning", "ml engineer", "ai engineer"),
    "junior": ("junior", "intern", "working student", "graduate", "entry"),
}


def read_json(path: Path, fallback):
    if not path.exists():
        return fallback
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return fallback


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def load_settings() -> dict:
    stored = read_json(SETTINGS_PATH, {})
    settings = DEFAULT_SETTINGS | stored
    settings["keywords"] = normalize_keywords(settings.get("keywords"))
    settings["limitPerQuery"] = safe_int(settings.get("limitPerQuery"), DEFAULT_SETTINGS["limitPerQuery"], 1, 200)
    settings["postedWithinSeconds"] = safe_int(
        settings.get("postedWithinSeconds"),
        DEFAULT_SETTINGS["postedWithinSeconds"],
        0,
        604800,
    )
    settings["delay"] = safe_float(settings.get("delay"), DEFAULT_SETTINGS["delay"], 0, 10)
    return settings


def normalize_keywords(value) -> list[str]:
    if isinstance(value, str):
        parts = value.replace("\r", "\n").split("\n")
    elif isinstance(value, list):
        parts = value
    else:
        parts = DEFAULT_SETTINGS["keywords"]

    keywords = []
    seen = set()
    for item in parts:
        keyword = str(item).strip()
        key = keyword.casefold()
        if keyword and key not in seen:
            keywords.append(keyword)
            seen.add(key)

    return keywords or DEFAULT_SETTINGS["keywords"]


def safe_int(value, fallback: int, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return fallback
    return min(max(number, minimum), maximum)


def safe_float(value, fallback: float, minimum: float, maximum: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    return min(max(number, minimum), maximum)


def load_jobs(source: str) -> list[dict]:
    path = SOURCES.get(source, SOURCES["related"])
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: value for key, value in row.items()} for row in csv.DictReader(handle)]


def row_value(row: dict, *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value:
            return str(value)
    return ""


def text_blob(row: dict) -> str:
    return " ".join(
        row_value(row, key)
        for key in [
            "Company Name",
            "Company",
            "Job Title",
            "Location",
            "Department",
            "Job Description",
            "Fit Reasons",
            "Remote",
        ]
    ).casefold()


def compact_job(row: dict) -> dict:
    return {
        "company": row_value(row, "Company Name", "Company"),
        "title": row_value(row, "Job Title"),
        "location": row_value(row, "Location"),
        "link": row_value(row, "Job Link"),
        "description": row_value(row, "Job Description"),
        "employmentType": row_value(row, "Employment Type"),
        "department": row_value(row, "Department"),
        "postedDate": row_value(row, "Posted Date"),
        "remote": row_value(row, "Remote") or "No",
        "label": row_value(row, "Label"),
        "ats": row_value(row, "ATS"),
        "fitScore": safe_int(row.get("Fit Score"), 0, 0, 999),
        "fitCategory": row_value(row, "Fit Category"),
        "fitReasons": row_value(row, "Fit Reasons"),
    }


def filter_jobs(rows: list[dict], params: dict) -> list[dict]:
    query = first_param(params, "q").casefold()
    role = first_param(params, "role")
    remote = first_param(params, "remote")
    min_score = safe_int(first_param(params, "minScore"), 0, 0, 999)

    filtered = []
    for row in rows:
        blob = text_blob(row)
        job = compact_job(row)

        if query and query not in blob:
            continue
        if role and role != "all" and not any(keyword in blob for keyword in ROLE_KEYWORDS.get(role, ())):
            continue
        if remote and remote != "all" and job["remote"].casefold() != remote.casefold():
            continue
        if min_score and job["fitScore"] < min_score:
            continue

        filtered.append(job)

    filtered.sort(key=lambda item: (item["fitScore"], item["company"], item["title"]), reverse=True)
    return filtered


def first_param(params: dict, key: str) -> str:
    values = params.get(key, [""])
    return values[0] if values else ""


def source_summary() -> dict:
    summary = {}
    for source, path in SOURCES.items():
        rows = load_jobs(source)
        summary[source] = {
            "count": len(rows),
            "path": str(path.relative_to(REPO_ROOT)),
            "updatedAt": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds") if path.exists() else None,
        }
    return summary


def build_update_command(settings: dict) -> list[str]:
    python = str(REPO_ROOT / ".venv" / "bin" / "python")
    if not Path(python).exists():
        python = sys.executable

    command = [python, str(SRC_DIR / "post_process_jobs.py"), "--no-update-baseline"]
    if settings.get("skipUpload", True):
        command.append("--skip-upload")
    if settings.get("includeLinkedIn", True):
        command.append("--include-linkedin-daily")
        command.extend(["--linkedin-location", str(settings["location"])])
        command.extend(["--linkedin-limit-per-query", str(settings["limitPerQuery"])])
        command.extend(["--linkedin-delay", str(settings["delay"])])
        command.extend(["--linkedin-posted-within-seconds", str(settings["postedWithinSeconds"])])
        if not settings.get("profileFitOnly", True):
            command.append("--linkedin-raw-daily")
        if settings.get("keywords"):
            command.append("--linkedin-keywords")
            command.extend(settings["keywords"])

    return command


def run_update() -> dict:
    settings = load_settings()
    command = build_update_command(settings)
    started_at = datetime.now().isoformat(timespec="seconds")

    try:
        completed = subprocess.run(
            command,
            cwd=str(REPO_ROOT),
            text=True,
            capture_output=True,
            timeout=600,
            check=False,
        )
        result = {
            "startedAt": started_at,
            "finishedAt": datetime.now().isoformat(timespec="seconds"),
            "returnCode": completed.returncode,
            "command": command,
            "stdout": completed.stdout[-12000:],
            "stderr": completed.stderr[-12000:],
        }
    except subprocess.TimeoutExpired as exc:
        result = {
            "startedAt": started_at,
            "finishedAt": datetime.now().isoformat(timespec="seconds"),
            "returnCode": 124,
            "command": command,
            "stdout": (exc.stdout or "")[-12000:] if isinstance(exc.stdout, str) else "",
            "stderr": "Daily update timed out after 600 seconds.",
        }

    write_json(RUN_LOG_PATH, result)
    return result


class DailyBerlinJobsHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/jobs":
            params = parse_qs(parsed.query)
            source = first_param(params, "source") or "related"
            jobs = filter_jobs(load_jobs(source), params)
            self.send_json({"source": source, "count": len(jobs), "jobs": jobs[:500]})
            return
        if parsed.path == "/api/summary":
            self.send_json({
                "sources": source_summary(),
                "settings": load_settings(),
                "lastRun": read_json(RUN_LOG_PATH, None),
            })
            return
        if parsed.path == "/api/settings":
            self.send_json(load_settings())
            return
        if parsed.path == "/api/run/latest":
            self.send_json(read_json(RUN_LOG_PATH, None) or {})
            return
        if parsed.path == "/":
            self.path = "/index.html"

        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/settings":
            payload = self.read_json_body()
            settings = load_settings() | {
                "includeLinkedIn": bool(payload.get("includeLinkedIn", True)),
                "profileFitOnly": bool(payload.get("profileFitOnly", True)),
                "location": str(payload.get("location") or DEFAULT_SETTINGS["location"]).strip(),
                "limitPerQuery": safe_int(payload.get("limitPerQuery"), DEFAULT_SETTINGS["limitPerQuery"], 1, 200),
                "postedWithinSeconds": safe_int(
                    payload.get("postedWithinSeconds"),
                    DEFAULT_SETTINGS["postedWithinSeconds"],
                    0,
                    604800,
                ),
                "delay": safe_float(payload.get("delay"), DEFAULT_SETTINGS["delay"], 0, 10),
                "skipUpload": bool(payload.get("skipUpload", True)),
                "keywords": normalize_keywords(payload.get("keywords")),
            }
            write_json(SETTINGS_PATH, settings)
            self.send_json(settings)
            return
        if parsed.path == "/api/run":
            self.send_json(run_update())
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def read_json_body(self) -> dict:
        length = safe_int(self.headers.get("Content-Length"), 0, 0, 5_000_000)
        if not length:
            return {}
        raw_body = self.rfile.read(length).decode("utf-8")
        try:
            return json.loads(raw_body)
        except json.JSONDecodeError:
            return {}

    def send_json(self, payload, status=HTTPStatus.OK):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Daily Berlin Software Jobs web app")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), DailyBerlinJobsHandler)
    print(f"Daily Berlin Software Jobs running at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Daily Berlin Software Jobs")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
