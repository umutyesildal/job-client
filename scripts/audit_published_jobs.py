#!/usr/bin/env python3
"""Audit the classified Daily Berlin Jobs output before or after Sheets sync."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = {
    "Role",
    "Level",
    "Work Mode",
    "Tech Stack",
    "Keywords",
    "Classification Version",
}


def audit(path: Path) -> int:
    jobs = pd.read_csv(path, low_memory=False, dtype=str).fillna("")
    missing = sorted(REQUIRED_COLUMNS.difference(jobs.columns))
    if missing:
        print(f"Missing classification columns: {', '.join(missing)}")
        return 1

    empty_roles = int(jobs["Role"].str.strip().eq("").sum())
    versions = Counter(jobs["Classification Version"])
    print(f"File: {path}")
    print(f"Published engineering jobs: {len(jobs)}")
    print(f"Unclassified published rows: {empty_roles}")
    print(f"Classification versions: {dict(versions)}")

    for column in ["Role", "Level", "Work Mode"]:
        print(f"\n{column}")
        for label, count in Counter(jobs[column]).most_common():
            print(f"  - {label or '(empty)'}: {count}")

    return 1 if empty_roles else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit normalized Daily Berlin Jobs output")
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=Path("data/published_all_jobs.csv"),
        help="Classified CSV pulled from or ready for Google Sheets",
    )
    return audit(parser.parse_args().path)


if __name__ == "__main__":
    raise SystemExit(main())
