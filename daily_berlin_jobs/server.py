"""Legacy local web app for Daily Berlin Jobs."""

from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
import threading
import unicodedata
from datetime import datetime
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# Increase CSV field size limit to support long job descriptions
csv.field_size_limit(min(2**31 - 1, sys.maxsize))


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
STATIC_DIR = Path(__file__).resolve().parent / "static"
SRC_DIR = REPO_ROOT / "job_scraper" / "src"
SETTINGS_PATH = DATA_DIR / "daily_berlin_jobs_settings.json"
RUN_LOG_PATH = DATA_DIR / "daily_berlin_jobs_last_run.json"

DEFAULT_SETTINGS = {
    "includeLinkedIn": True,
    "profileFitOnly": False,
    "location": "Berlin, Germany",
    "limitPerQuery": 25,
    "postedWithinSeconds": 86400,
    "delay": 1.0,
    "skipUpload": False,
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
    # Google Sheets is the UI source of truth. These files are refreshed only by
    # pull_from_sheets.py after a successful upload/sync cycle.
    "all": DATA_DIR / "published_all_jobs.csv",
    "daily": DATA_DIR / "daily_new_jobs.csv",
    "linkedin": DATA_DIR / "linkedin_daily_jobs.csv",
}

ROLE_FILTERS = [
    ("fullstack", re.compile(r"\b(full[- ]?stack|fullstack)\b", re.IGNORECASE)),
    ("backend", re.compile(r"\b(backend|back[- ]?end|api|python|java|golang|go|node\.?(js)?|php|ruby|scala)\b", re.IGNORECASE)),
    ("frontend", re.compile(r"\b(frontend|front[- ]?end|react|next\.?js|javascript|typescript|web ui|ui engineer)\b", re.IGNORECASE)),
    ("data_ai", re.compile(r"\b(data engineer|data scientist|machine learning|\bml\b|ai engineer|analytics engineer|data platform|computer vision|nlp|data\b)\b", re.IGNORECASE)),
    ("devops_platform", re.compile(r"\b(devops|sre|site reliability|platform|cloud|infrastructure|systems?)\b", re.IGNORECASE)),
    ("security", re.compile(r"\b(security|application security|appsec|iam|soc)\b", re.IGNORECASE)),
    ("mobile", re.compile(r"\b(android|ios|mobile|react native|flutter)\b", re.IGNORECASE)),
    ("qa", re.compile(r"\b(qa|quality assurance|test automation|sdet|engineer in test)\b", re.IGNORECASE)),
]

LEVEL_FILTERS = [
    ("intern", re.compile(r"\b(intern|internship|working student|werkstudent|praktik|praktikum|thesis student)\b", re.IGNORECASE)),
    ("junior", re.compile(r"\b(junior|entry[- ]?level|graduate|trainee|associate)\b", re.IGNORECASE)),
    ("staff_plus", re.compile(r"\b(staff|principal|distinguished|fellow)\b", re.IGNORECASE)),
    ("lead", re.compile(r"\b(team lead|tech lead|lead)\b", re.IGNORECASE)),
    ("manager_plus", re.compile(r"\b(manager|head|director|vp|chief)\b", re.IGNORECASE)),
    ("senior", re.compile(r"\b(senior|sr\.?)\b", re.IGNORECASE)),
]


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
    path = SOURCES.get(source, SOURCES["all"])
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: value for key, value in row.items()} for row in csv.DictReader(handle)]


def visible_jobs(source: str) -> list[dict]:
    rows = load_jobs(source)
    if source in {"all", "daily"}:
        rows = [row for row in rows if is_berlin_job(row)]
    return dedupe_rows(rows, source)


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


def title_department_blob(row: dict) -> str:
    return " ".join(
        row_value(row, key)
        for key in ["Job Title", "Department"]
    ).casefold()


def is_berlin_job(row: dict) -> bool:
    location = row_value(row, "Location").casefold()
    return "berlin" in location


def preview_text(value: str, max_length: int = 220) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= max_length:
        return text
    return f"{text[:max_length - 1].rstrip()}..."


def normalize_identity_value(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or "").casefold())
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", normalized).strip()


def row_identity(row: dict) -> tuple[str, str, str] | None:
    company = normalize_identity_value(row_value(row, "Company Name", "Company"))
    title = normalize_identity_value(row_value(row, "Job Title"))
    location = normalize_identity_value(row_value(row, "Location"))
    if not company or not title:
        return None
    return (company, title, location)


def row_sort_priority(row: dict, source: str) -> tuple:
    if source == "related":
        return (
            safe_int(row.get("Fit Score"), 0, 0, 999),
            sortable_posted_date(row_value(row, "Posted Date")),
            row_value(row, "Job Link"),
        )
    return (
        sortable_posted_date(row_value(row, "Posted Date")),
        safe_int(row.get("Fit Score"), 0, 0, 999),
        row_value(row, "Job Link"),
    )


def dedupe_rows(rows: list[dict], source: str) -> list[dict]:
    deduped: dict[tuple[str, str, str] | str, dict] = {}
    for row in rows:
        identity = row_identity(row)
        key = identity or row_value(row, "Job Link") or str(id(row))
        current = deduped.get(key)
        if current is None or row_sort_priority(row, source) > row_sort_priority(current, source):
            deduped[key] = row
    return list(deduped.values())


def compact_job(row: dict) -> dict:
    return {
        "company": row_value(row, "Company Name", "Company"),
        "title": row_value(row, "Job Title"),
        "location": row_value(row, "Location"),
        "link": row_value(row, "Job Link"),
        "description": preview_text(row_value(row, "Job Description")),
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


def classify_role(row: dict) -> str:
    text = title_department_blob(row)
    for key, pattern in ROLE_FILTERS:
        if pattern.search(text):
            return key
    return "other"


def classify_level(row: dict) -> str:
    text = title_department_blob(row)
    for key, pattern in LEVEL_FILTERS:
        if pattern.search(text):
            return key
    return "unspecified"


def classify_remote_mode(value: str) -> str:
    text = normalize_identity_value(value)
    if not text or text in {"no", "on site", "onsite"}:
        return "on_site"
    if "hybrid" in text:
        return "hybrid"
    if text in {"yes", "remote"} or "remote" in text:
        return "remote"
    return "other"


def sortable_posted_date(value: str) -> tuple[int, str]:
    text = str(value or "").strip()
    if not text:
        return (0, "")
    try:
        parsed = datetime.fromisoformat(text)
        return (1, parsed.isoformat())
    except ValueError:
        return (0, text)


def filter_jobs(rows: list[dict], params: dict, source: str) -> list[dict]:
    query = first_param(params, "q").casefold()
    role = first_param(params, "role")
    level = first_param(params, "level")
    remote = first_param(params, "remote")

    filtered = []
    for row in rows:
        blob = text_blob(row)
        job = compact_job(row)

        if query and query not in blob:
            continue
        if role and role != "all" and classify_role(row) != role:
            continue
        if level and level != "all" and classify_level(row) != level:
            continue
        remote_mode = classify_remote_mode(job["remote"])
        if remote == "remote_or_hybrid" and remote_mode not in {"remote", "hybrid"}:
            continue
        if remote and remote not in {"all", "remote_or_hybrid"} and remote_mode != remote:
            continue

        filtered.append(job)

    filtered.sort(
        key=lambda item: (
            sortable_posted_date(item["postedDate"]),
            item["company"].casefold(),
            item["title"].casefold(),
        ),
        reverse=True,
    )
    return filtered


def first_param(params: dict, key: str) -> str:
    values = params.get(key, [""])
    return values[0] if values else ""


def source_summary() -> dict:
    summary = {}
    for source, path in SOURCES.items():
        rows = visible_jobs(source) if source != "linkedin" else load_jobs(source)
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


class RunState:
    def __init__(self):
        self.running = False
        self.process_main = None
        self.process_linkedin = None
        self.process_post = None
        self.stdout_log = []
        self.return_code = None
        self.step = "idle"
        self.step_label = "Ready"
        self.progress = 0
        self.lock = threading.Lock()

RUN_STATE = RunState()


def set_run_progress(step: str, label: str, progress: int, log: str | None = None) -> None:
    with RUN_STATE.lock:
        RUN_STATE.step = step
        RUN_STATE.step_label = label
        RUN_STATE.progress = max(0, min(progress, 100))
        if log:
            RUN_STATE.stdout_log.append(log)

def async_run_update():
    started_at = datetime.now().isoformat(timespec="seconds")
    with RUN_STATE.lock:
        RUN_STATE.running = True
        RUN_STATE.stdout_log = ["Starting daily update..."]
        RUN_STATE.return_code = None
        RUN_STATE.step = "crawling"
        RUN_STATE.step_label = "Collecting jobs"
        RUN_STATE.progress = 5
        RUN_STATE.process_main = None
        RUN_STATE.process_linkedin = None
        RUN_STATE.process_post = None

    settings = load_settings()
    python = str(REPO_ROOT / ".venv" / "bin" / "python")
    if not Path(python).exists():
        python = sys.executable

    # Step 1: Prepare command for main.py crawler (crawls ATS platforms from OneSingle sheet)
    main_cmd = [
        python,
        str(SRC_DIR / "main.py"),
        "https://docs.google.com/spreadsheets/d/1sYI0IqzXp_W19eAYDCdC46ZjzrWqW5fwHfY0sAzUxKw/",
        "-t", "sheets",
        "--input-worksheet", "OneSingle"
    ]

    # Step 2: Prepare command for linkedin_daily.py (scrapes recent LinkedIn queries)
    linkedin_cmd = [
        python,
        str(SRC_DIR / "linkedin_daily.py"),
        "--location", str(settings.get("location") or "Berlin, Germany"),
        "--limit-per-query", str(settings.get("limitPerQuery") or 25),
        "--delay", str(settings.get("delay") or 1.0),
        "--posted-within-seconds", str(settings.get("postedWithinSeconds") or 86400),
        "--output", str(DATA_DIR / "linkedin_daily_jobs.csv"),
    ]
    if settings.get("keywords"):
        linkedin_cmd.append("--keywords")
        linkedin_cmd.extend(settings["keywords"])

    with RUN_STATE.lock:
        RUN_STATE.stdout_log.append("Step 1/4 · Collecting ATS and LinkedIn jobs...")

    try:
        # Start both processes concurrently (in parallel!)
        p_main = subprocess.Popen(
            main_cmd,
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Redirect stderr to stdout so we capture it in one stream
            text=True,
            bufsize=1
        )
        p_linkedin = subprocess.Popen(
            linkedin_cmd,
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        with RUN_STATE.lock:
            RUN_STATE.process_main = p_main
            RUN_STATE.process_linkedin = p_linkedin

        # Threads to capture streams in real-time
        def log_reader(stream, prefix):
            for line in iter(stream.readline, ""):
                if not line:
                    break
                line_str = line.strip()
                if line_str:
                    with RUN_STATE.lock:
                        RUN_STATE.stdout_log.append(f"{prefix} {line_str}")
            stream.close()

        t_main = threading.Thread(target=log_reader, args=(p_main.stdout, "[ATS]"))
        t_linkedin = threading.Thread(target=log_reader, args=(p_linkedin.stdout, "[LinkedIn]"))

        t_main.daemon = True
        t_linkedin.daemon = True
        t_main.start()
        t_linkedin.start()

        # Wait for both processes to complete concurrently
        p_main.wait()
        p_linkedin.wait()

        # Join the reader threads
        t_main.join(timeout=2.0)
        t_linkedin.join(timeout=2.0)

        # Check return codes
        if p_main.returncode != 0 and p_main.returncode != -9:  # -9 is manual kill
            with RUN_STATE.lock:
                RUN_STATE.stdout_log.append(f"ATS Crawler failed with exit code {p_main.returncode}")
                RUN_STATE.running = False
                RUN_STATE.return_code = p_main.returncode
                RUN_STATE.step = "failed"
                RUN_STATE.step_label = "ATS crawl failed"
            return

        if p_linkedin.returncode != 0 and p_linkedin.returncode != -9:
            with RUN_STATE.lock:
                RUN_STATE.stdout_log.append(f"LinkedIn Scraper failed with exit code {p_linkedin.returncode}")
                RUN_STATE.running = False
                RUN_STATE.return_code = p_linkedin.returncode
                RUN_STATE.step = "failed"
                RUN_STATE.step_label = "LinkedIn crawl failed"
            return

        # If it was manual kill, abort post processing
        if p_main.returncode == -9 or p_linkedin.returncode == -9:
            with RUN_STATE.lock:
                RUN_STATE.running = False
                RUN_STATE.return_code = -9
                RUN_STATE.stdout_log.append("Execution cancelled by user.")
                RUN_STATE.step = "cancelled"
                RUN_STATE.step_label = "Cancelled"
            return

        # Step 3: Run post_process_jobs.py to merge all_jobs.csv and the pre-scraped linkedin file
        post_cmd = build_update_command(settings)
        post_cmd.extend(["--linkedin-pre-scraped", str(DATA_DIR / "linkedin_daily_jobs.csv")])
        
        set_run_progress("uploading", "Processing and writing Google Sheets", 60,
                         "Step 2/4 · Processing results and writing Google Sheets...")

        p_post = subprocess.Popen(
            post_cmd,
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        with RUN_STATE.lock:
            RUN_STATE.process_post = p_post

        t_post = threading.Thread(target=log_reader, args=(p_post.stdout, "[Post]"))
        t_post.daemon = True
        t_post.start()

        p_post.wait()
        t_post.join(timeout=2.0)

        if p_post.returncode != 0:
            with RUN_STATE.lock:
                RUN_STATE.running = False
                RUN_STATE.return_code = p_post.returncode
                RUN_STATE.step = "failed"
                RUN_STATE.step_label = "Google Sheets upload failed"
                RUN_STATE.stdout_log.append(f"Update failed with code {p_post.returncode}")
            return

        set_run_progress("syncing", "Syncing canonical data from Google Sheets", 88,
                         "Step 3/4 · Syncing canonical data back from Google Sheets...")
        sync_result = run_sync_sheets()
        for output in (sync_result.get("stdout"), sync_result.get("stderr")):
            if output:
                with RUN_STATE.lock:
                    RUN_STATE.stdout_log.extend(
                        f"[Sync] {line}" for line in str(output).splitlines() if line.strip()
                    )
        if sync_result["returnCode"] != 0:
            with RUN_STATE.lock:
                RUN_STATE.running = False
                RUN_STATE.return_code = sync_result["returnCode"]
                RUN_STATE.step = "failed"
                RUN_STATE.step_label = "Google Sheets sync failed"
                RUN_STATE.stdout_log.append("Sync failed; the UI kept the previous canonical snapshot.")
            return

        set_run_progress("refreshing", "Refreshing job list", 97,
                         "Step 4/4 · Refreshing the UI data snapshot...")

        # Save run log JSON
        result = {
            "startedAt": started_at,
            "finishedAt": datetime.now().isoformat(timespec="seconds"),
            "returnCode": p_post.returncode,
            "command": post_cmd,
            "stdout": "\n".join(RUN_STATE.stdout_log)[-12000:],
            "stderr": "",
        }
        write_json(RUN_LOG_PATH, result)

        with RUN_STATE.lock:
            RUN_STATE.running = False
            RUN_STATE.return_code = p_post.returncode
            RUN_STATE.step = "complete"
            RUN_STATE.step_label = "Update complete"
            RUN_STATE.progress = 100
            RUN_STATE.stdout_log.append("Update complete. The latest Sheets data is ready.")

    except Exception as e:
        with RUN_STATE.lock:
            RUN_STATE.stdout_log.append(f"System Error during update: {e}")
            RUN_STATE.running = False
            RUN_STATE.return_code = 1
            RUN_STATE.step = "failed"
            RUN_STATE.step_label = "Update failed"


def run_sync_sheets() -> dict:
    python = str(REPO_ROOT / ".venv" / "bin" / "python")
    if not Path(python).exists():
        python = sys.executable

    command = [python, str(SRC_DIR / "pull_from_sheets.py")]
    started_at = datetime.now().isoformat(timespec="seconds")

    try:
        completed = subprocess.run(
            command,
            cwd=str(REPO_ROOT),
            text=True,
            capture_output=True,
            timeout=120,
            check=False,
        )
        result = {
            "startedAt": started_at,
            "finishedAt": datetime.now().isoformat(timespec="seconds"),
            "returnCode": completed.returncode,
            "command": command,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    except subprocess.TimeoutExpired as exc:
        result = {
            "startedAt": started_at,
            "finishedAt": datetime.now().isoformat(timespec="seconds"),
            "returnCode": 124,
            "command": command,
            "stdout": (exc.stdout or ""),
            "stderr": "Google Sheets sync timed out.",
        }
    except Exception as e:
        result = {
            "startedAt": started_at,
            "finishedAt": datetime.now().isoformat(timespec="seconds"),
            "returnCode": 1,
            "command": command,
            "stdout": "",
            "stderr": str(e),
        }
    return result


class DailyBerlinJobsHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def end_headers(self):
        # The app is local and changes frequently; stale HTML/JS pairs can refer
        # to DOM controls that no longer exist.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/jobs":
            params = parse_qs(parsed.query)
            source = first_param(params, "source") or "all"
            jobs = filter_jobs(visible_jobs(source), params, source)
            self.send_json({"source": source, "count": len(jobs), "jobs": jobs})
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
        if parsed.path == "/api/run/status":
            with RUN_STATE.lock:
                self.send_json({
                    "running": RUN_STATE.running,
                    "returnCode": RUN_STATE.return_code,
                    "logs": "\n".join(RUN_STATE.stdout_log),
                    "step": RUN_STATE.step,
                    "stepLabel": RUN_STATE.step_label,
                    "progress": RUN_STATE.progress,
                })
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
            with RUN_STATE.lock:
                if RUN_STATE.running:
                    self.send_json({"status": "already_running"})
                    return
            thread = threading.Thread(target=async_run_update)
            thread.daemon = True
            thread.start()
            self.send_json({"status": "started"})
            return
        if parsed.path == "/api/run/stop":
            with RUN_STATE.lock:
                if RUN_STATE.running:
                    killed = False
                    for proc in (RUN_STATE.process_main, RUN_STATE.process_linkedin, RUN_STATE.process_post):
                        if proc and proc.poll() is None:
                            try:
                                proc.kill()
                                killed = True
                            except Exception:
                                pass
                    if killed:
                        RUN_STATE.stdout_log.append("Update manual cancellation requested by user. Killing subprocesses...")
                    RUN_STATE.running = False
                    RUN_STATE.return_code = -9
                    RUN_STATE.step = "cancelled"
                    RUN_STATE.step_label = "Cancelled"
                    self.send_json({"status": "stopped"})
                    return
                self.send_json({"status": "not_running"})
                return
        if parsed.path == "/api/sync-sheets":
            self.send_json(run_sync_sheets())
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

    parser = argparse.ArgumentParser(description="Legacy Daily Berlin Jobs web app")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), DailyBerlinJobsHandler)
    print(f"Daily Berlin Jobs legacy app running at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Daily Berlin Jobs legacy app")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
