"""Pull scraped jobs from Google Sheets and save them as local CSV files."""

import argparse
from pathlib import Path

from .data_controller import DataController

DEFAULT_SPREADSHEET = (
    "https://docs.google.com/spreadsheets/d/"
    "1sYI0IqzXp_W19eAYDCdC46ZjzrWqW5fwHfY0sAzUxKw/"
    "edit?gid=2095282077#gid=2095282077"
)

def main():
    parser = argparse.ArgumentParser(description="Pull jobs from Google Sheets.")
    parser.add_argument("--spreadsheet", default=DEFAULT_SPREADSHEET, help="Google Sheet URL or ID")
    parser.add_argument("--all-worksheet", default="All Jobs", help="All jobs worksheet name")
    parser.add_argument("--daily-worksheet", default="Daily New Jobs", help="Daily new jobs worksheet name")
    parser.add_argument("--all-output", default="data/published_all_jobs.csv", help="Local all jobs output path")
    parser.add_argument("--daily-output", default="data/daily_new_jobs.csv", help="Local daily new jobs output path")
    args = parser.parse_args()

    controller = DataController()
    
    print(f"Opening spreadsheet: {args.spreadsheet}")
    
    pulled = []

    # Fetch both worksheets before replacing either local canonical snapshot.
    print(f"Pulling '{args.all_worksheet}'...")
    try:
        all_df = controller.load_data_from_google_sheet(
            args.spreadsheet, args.all_worksheet, data_kind="jobs"
        )
        print(f"Loaded {len(all_df)} all jobs.")
        
        pulled.append((all_df, Path(args.all_output)))
    except Exception as e:
        print(f"Error pulling all jobs: {e}")
        return 1
        
    # Pull Daily New Jobs
    print(f"Pulling '{args.daily_worksheet}'...")
    try:
        daily_df = controller.load_data_from_google_sheet(
            args.spreadsheet, args.daily_worksheet, data_kind="jobs"
        )
        print(f"Loaded {len(daily_df)} daily new jobs.")
        
        pulled.append((daily_df, Path(args.daily_output)))
    except Exception as e:
        print(f"Error pulling daily new jobs: {e}")
        return 1

    for dataframe, output_path in pulled:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
        dataframe.to_csv(temporary_path, index=False, encoding="utf-8")
        temporary_path.replace(output_path)
        print(f"Saved to {output_path}")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
