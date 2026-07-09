"""Pull scraped jobs from Google Sheets and save them as local CSV files."""

import argparse
import sys
from pathlib import Path

JOB_SCRAPER_ROOT = Path(__file__).resolve().parents[1]
if str(JOB_SCRAPER_ROOT) not in sys.path:
    sys.path.insert(0, str(JOB_SCRAPER_ROOT))

from data_controller import DataController

DEFAULT_SPREADSHEET = (
    "https://docs.google.com/spreadsheets/d/"
    "1sYI0IqzXp_W19eAYDCdC46ZjzrWqW5fwHfY0sAzUxKw/"
    "edit?gid=2095282077#gid=2095282077"
)

def main():
    parser = argparse.ArgumentParser(description="Pull jobs from Google Sheets.")
    parser.add_argument("--spreadsheet", default=DEFAULT_SPREADSHEET, help="Google Sheet URL or ID")
    parser.add_argument("--related-worksheet", default="Related Jobs", help="Related jobs worksheet name")
    parser.add_argument("--daily-worksheet", default="Daily New Jobs", help="Daily new jobs worksheet name")
    parser.add_argument("--related-output", default="data/related_jobs.csv", help="Local related jobs output path")
    parser.add_argument("--daily-output", default="data/daily_new_jobs.csv", help="Local daily new jobs output path")
    args = parser.parse_args()

    controller = DataController()
    
    print(f"Opening spreadsheet: {args.spreadsheet}")
    
    # Pull Related Jobs
    print(f"Pulling '{args.related_worksheet}'...")
    try:
        related_df = controller.load_data_from_google_sheet(args.spreadsheet, args.related_worksheet)
        print(f"Loaded {len(related_df)} related jobs.")
        
        # Save to local CSV
        output_path = Path(args.related_output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Drop columns containing all empty/NaN values if necessary
        related_df.to_csv(output_path, index=False, encoding="utf-8")
        print(f"Saved to {args.related_output}")
    except Exception as e:
        print(f"Error pulling related jobs: {e}")
        
    # Pull Daily New Jobs
    print(f"Pulling '{args.daily_worksheet}'...")
    try:
        daily_df = controller.load_data_from_google_sheet(args.spreadsheet, args.daily_worksheet)
        print(f"Loaded {len(daily_df)} daily new jobs.")
        
        # Save to local CSV
        output_path = Path(args.daily_output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        daily_df.to_csv(output_path, index=False, encoding="utf-8")
        print(f"Saved to {args.daily_output}")
    except Exception as e:
        print(f"Error pulling daily new jobs: {e}")

if __name__ == "__main__":
    main()
