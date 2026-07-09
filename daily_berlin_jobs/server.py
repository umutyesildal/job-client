"""Local web app for Daily Berlin Software Jobs."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import threading
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


class RunState:
    def __init__(self):
        self.running = False
        self.process_main = None
        self.process_linkedin = None
        self.process_post = None
        self.stdout_log = []
        self.return_code = None
        self.lock = threading.Lock()

RUN_STATE = RunState()

def async_run_update():
    started_at = datetime.now().isoformat(timespec="seconds")
    with RUN_STATE.lock:
        RUN_STATE.running = True
        RUN_STATE.stdout_log = ["Starting daily update..."]
        RUN_STATE.return_code = None
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
        RUN_STATE.stdout_log.append("Starting ATS Crawler and LinkedIn Scraper concurrently...")

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
            return

        if p_linkedin.returncode != 0 and p_linkedin.returncode != -9:
            with RUN_STATE.lock:
                RUN_STATE.stdout_log.append(f"LinkedIn Scraper failed with exit code {p_linkedin.returncode}")
                RUN_STATE.running = False
                RUN_STATE.return_code = p_linkedin.returncode
            return

        # If it was manual kill, abort post processing
        if p_main.returncode == -9 or p_linkedin.returncode == -9:
            with RUN_STATE.lock:
                RUN_STATE.running = False
                RUN_STATE.return_code = -9
                RUN_STATE.stdout_log.append("Execution cancelled by user.")
            return

        # Step 3: Run post_process_jobs.py to merge all_jobs.csv and the pre-scraped linkedin file
        post_cmd = build_update_command(settings)
        post_cmd.extend(["--linkedin-pre-scraped", str(DATA_DIR / "linkedin_daily_jobs.csv")])
        
        with RUN_STATE.lock:
            RUN_STATE.stdout_log.append("Starting Post Processing and Sheets Upload...")

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
            RUN_STATE.stdout_log.append(f"Update finished with code {p_post.returncode}")

    except Exception as e:
        with RUN_STATE.lock:
            RUN_STATE.stdout_log.append(f"System Error during update: {e}")
            RUN_STATE.running = False
            RUN_STATE.return_code = 1


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
        if parsed.path == "/api/run/status":
            with RUN_STATE.lock:
                self.send_json({
                    "running": RUN_STATE.running,
                    "returnCode": RUN_STATE.return_code,
                    "logs": "\n".join(RUN_STATE.stdout_log)
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
