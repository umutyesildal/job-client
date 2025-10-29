import os
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
from typing import List, Dict

load_dotenv()

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]


def get_sheets_client(credentials_file: str = 'google_credentials.json'):
    if not os.path.exists(credentials_file):
        print(f"❌ Credentials file not found: {credentials_file}")
        print("\nTo set up Google Sheets API:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a new project or select existing")
        print("3. Enable Google Sheets API and Google Drive API")
        print("4. Create a Service Account")
        print("5. Download the credentials JSON")
        print(f"6. Save as: {credentials_file}")
        raise FileNotFoundError(f"Credentials file not found: {credentials_file}")
    
    credentials = Credentials.from_service_account_file(credentials_file, scopes=SCOPES)
    return gspread.authorize(credentials)


def get_or_create_sheet(client, sheet_name: str = 'Student Jobs Pipeline'):
    try:
        spreadsheet = client.open(sheet_name)
        print(f"✅ Opened existing sheet: {sheet_name}")
    except gspread.SpreadsheetNotFound:
        spreadsheet = client.create(sheet_name)
        print(f"✅ Created new sheet: {sheet_name}")
    
    worksheet = spreadsheet.sheet1
    worksheet.update_title('Jobs')
    
    return spreadsheet, worksheet


def sync_to_sheets(
    input_csv: str = 'filtered_student_jobs_final.csv',
    sheet_name: str = 'Student Jobs Pipeline',
    credentials_file: str = 'google_credentials.json'
):
    print(f"\n☁️  Syncing {input_csv} to Google Sheets...")
    
    df = pd.read_csv(input_csv)
    print(f"📊 Loaded {len(df)} jobs from CSV")
    
    client = get_sheets_client(credentials_file)
    spreadsheet, worksheet = get_or_create_sheet(client, sheet_name)
    
    try:
        existing_data = worksheet.get_all_records()
        existing_df = pd.DataFrame(existing_data)
        
        if len(existing_df) > 0 and 'Job Link' in existing_df.columns:
            existing_links = set(existing_df['Job Link'].tolist())
            print(f"📄 Found {len(existing_links)} existing jobs in sheet")
        else:
            existing_links = set()
            print(f"📄 Sheet is empty or missing Job Link column")
    except Exception as e:
        print(f"⚠️  Could not read existing data: {e}")
        existing_links = set()
    
    if existing_links:
        new_jobs = df[~df['Job Link'].isin(existing_links)]
        print(f"🆕 Found {len(new_jobs)} new jobs to add")
    else:
        new_jobs = df
        print(f"🆕 Adding all {len(new_jobs)} jobs (sheet was empty)")
    
    if len(new_jobs) == 0:
        print("✅ No new jobs to add. Sheet is up to date!")
        return
    
    columns = [
        'Job Title', 'Job Description', 'Employment Type', 'Company', 
        'Company Description', 'Job Link', 'Location', 'Label', 
        'Posted Date', 'Keywords', 'CV_ID', 'Match_Percentage', 
        'Match_Count', 'Matched_Keywords', 'Motivation_Letter'
    ]
    
    if 'Company Point' not in new_jobs.columns:
        new_jobs['Company Point'] = ''
    
    available_columns = [col for col in columns if col in new_jobs.columns]
    if 'Company Point' not in available_columns:
        available_columns.insert(5, 'Company Point')
    
    new_jobs = new_jobs[available_columns]
    
    if len(existing_links) == 0:
        worksheet.clear()
        worksheet.update([available_columns] + new_jobs.values.tolist())
        print(f"✅ Added headers and {len(new_jobs)} jobs")
    else:
        worksheet.append_rows(new_jobs.values.tolist())
        print(f"✅ Appended {len(new_jobs)} new jobs")
    
    print(f"\n🔗 Spreadsheet URL: {spreadsheet.url}")
    print(f"📊 Total jobs in sheet: {len(existing_links) + len(new_jobs)}")


if __name__ == '__main__':
    sync_to_sheets()
