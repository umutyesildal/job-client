import os
import sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from student_filter import main as filter_student_jobs
from match_cv import match_cv_with_jobs
from generate_motivation import generate_motivation_letters
from sync_to_sheets import sync_to_sheets


def print_header(text: str):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")


def check_requirements():
    print_header("Checking Requirements")
    
    issues = []
    
    if not os.path.exists('../data/all_jobs.csv'):
        issues.append("❌ data/all_jobs.csv not found. Run main_crawler.py first!")
    else:
        print("✅ data/all_jobs.csv found")
    
    if not os.path.exists('cv_keywords.json'):
        issues.append("❌ cv_keywords.json not found")
    else:
        import json
        with open('cv_keywords.json', 'r') as f:
            cv_data = json.load(f)
            if not cv_data.get('keywords') or len(cv_data['keywords']) < 5:
                issues.append("⚠️  cv_keywords.json has fewer than 5 keywords. Please populate with your skills!")
            else:
                print(f"✅ cv_keywords.json found with {len(cv_data['keywords'])} keywords")
    
    if not os.path.exists('../google_credentials.json'):
        issues.append("⚠️  google_credentials.json not found. Sheets sync will be skipped!")
    else:
        print("✅ google_credentials.json found")
    
    try:
        import gspread
        print("✅ gspread installed")
    except ImportError:
        issues.append("⚠️  gspread not installed. Run: pip install gspread google-auth")
    
    if issues:
        print("\n⚠️  Issues found:")
        for issue in issues:
            print(f"   {issue}")
        
        critical = [i for i in issues if i.startswith("❌")]
        if critical:
            print("\n❌ Cannot proceed with critical issues. Please fix them first.")
            return False
    
    print("\n✅ All critical requirements met!")
    return True


def run_pipeline(skip_sheets: bool = False):
    start_time = datetime.now()
    print_header(f"Student Job Pipeline Started - {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if not check_requirements():
        return
    
    try:
        print_header("Stage 1/3: Filtering Student Jobs & Extracting Keywords")
        filter_student_jobs()
        
        print_header("Stage 2/3: Matching with CV Keywords")
        match_cv_with_jobs()
        
        print_header("Stage 3/3: Generating Motivation Letters")
        generate_motivation_letters()
        
        if not skip_sheets:
            print_header("Stage 4/4: Syncing to Google Sheets")
            try:
                sync_to_sheets()
            except FileNotFoundError as e:
                print(f"⚠️  Skipping Google Sheets sync: {e}")
        else:
            print_header("Stage 4/4: Google Sheets Sync (SKIPPED)")
            print("⚠️  Google Sheets sync skipped by user")
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print_header("Pipeline Complete!")
        print(f"✅ All stages completed successfully!")
        print(f"⏱️  Total time: {duration:.2f} seconds")
        print(f"\n📊 Output file: student_pipeline/filtered_student_jobs_final.csv")
        
        if not skip_sheets:
            print(f"☁️  Data synced to Google Sheets")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Pipeline failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Run the student job pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python student_pipeline/run_pipeline.py              # Run full pipeline
  python student_pipeline/run_pipeline.py --skip-sheets # Skip Google Sheets sync
        """
    )
    
    parser.add_argument(
        '--skip-sheets',
        action='store_true',
        help='Skip Google Sheets sync (useful for testing)'
    )
    
    args = parser.parse_args()
    
    run_pipeline(skip_sheets=args.skip_sheets)
