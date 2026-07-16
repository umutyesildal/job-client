"""
Database Integration Options for Job Crawler
Provides utilities for exporting to different database systems
"""

import pandas as pd
import logging
import json
import re
from typing import Optional
import os
from pathlib import Path
from urllib.parse import quote, urlparse
from urllib.request import urlopen
from .crawler_logger import CrawlerLogger
from .company_catalog import AtsCatalog, normalize_name, normalize_url

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataController:
    """Handle exporting jobs to different database systems"""

    JOB_COLUMN_ORDER = [
        'Company',
        'Company Name',
        'Job Title',
        'Location',
        'Job Link',
        'Job Description',
        'Employment Type',
        'Department',
        'Role',
        'Level',
        'Work Mode',
        'Tech Stack',
        'Keywords',
        'Classification Version',
        'Posted Date',
        'Company Description',
        'Remote',
        'Label',
        'ATS'
    ]
    
    def __init__(self, csv_path: str = 'output/all_jobs.csv'):
        self.csv_path = csv_path
        self.df = None
    
    def load_csv(self):
        """Load jobs from CSV"""
        if not os.path.exists(self.csv_path):
            logger.error(f"CSV file not found: {self.csv_path}")
            return False
        
        self.df = pd.read_csv(self.csv_path, encoding='utf-8')
        self.df = self.normalize_jobs_dataframe(self.df)
        logger.info(f"Loaded {len(self.df)} jobs from {self.csv_path}")
        return True
    
    
    def load_data_from_csv(self, csv_path: str) -> pd.DataFrame:
        """Load company data from CSV file"""
        df = pd.read_csv(csv_path, low_memory=False, dtype=str)
        
        # Normalize column names to handle different schemas
        df = self.normalize_dataframe(df)
        
        return df

    def load_data_from_yaml(self, yaml_path: str) -> pd.DataFrame:
        """Load and validate the contributor-friendly company catalog."""
        try:
            import yaml
        except ImportError as exc:
            raise RuntimeError("YAML catalog support requires PyYAML") from exc

        payload = yaml.safe_load(Path(yaml_path).read_text(encoding='utf-8')) or {}
        records = payload.get('companies')
        if not isinstance(records, list):
            raise ValueError("YAML catalog must contain a companies list")

        ats_path = Path(__file__).resolve().parents[2] / 'catalog' / 'ats.yaml'
        ats_catalog = AtsCatalog.load(ats_path)

        rows = []
        seen_sources = set()
        for index, record in enumerate(records, start=1):
            if not isinstance(record, dict):
                raise ValueError(f"Company entry {index} must be an object")
            name = normalize_name(record.get('name', ''))
            career_page = normalize_url(record.get('career_page', ''))
            website = normalize_url(record.get('website', '')) if record.get('website') else ''
            raw_label = str(record.get('ats', '')).strip()
            label = ats_catalog.resolve(raw_label)
            if not name or not career_page or not raw_label:
                raise ValueError(f"Company entry {index} needs name, career_page, and ats")
            if not label:
                raise ValueError(f"Company entry {index} uses unsupported ATS label: {raw_label}")
            source_key = (name.casefold(), career_page.rstrip('/').casefold())
            if source_key in seen_sources:
                raise ValueError(f"Duplicate company source at entry {index}: {name}")
            seen_sources.add(source_key)
            rows.append({
                'Name': name,
                'Website': website,
                'Career Page': career_page,
                'Description': str(record.get('description', '')).strip(),
                'Label': label,
                'Active': 'active' if record.get('active', True) else 'inactive',
            })

        columns = ['Name', 'Website', 'Career Page', 'Description', 'Label', 'Active']
        return self.normalize_dataframe(pd.DataFrame(rows, columns=columns, dtype=str))

    def load_data_from_google_sheet(
        self,
        sheet_ref: str,
        worksheet_name: Optional[str] = None,
        data_kind: str = 'companies'
    ) -> pd.DataFrame:
        """Load company input or job output data from Google Sheets."""
        if not self._has_google_service_account_credentials():
            api_key = self._get_google_api_key()
            if api_key:
                return self._load_data_from_google_sheets_api(
                    sheet_ref, worksheet_name, api_key, data_kind
                )

        worksheet = self._open_google_worksheet(sheet_ref, worksheet_name)
        values = worksheet.get_all_values()

        return self._values_to_dataframe(values, data_kind)

    def _load_data_from_google_sheets_api(
        self,
        sheet_ref: str,
        worksheet_name: Optional[str],
        api_key: str,
        data_kind: str = 'companies'
    ) -> pd.DataFrame:
        """Load Google Sheet values using API-key access for readable sheets."""
        spreadsheet_id, gid = self._parse_sheet_ref(sheet_ref)
        target_worksheet = worksheet_name or self._get_first_sheet_title(spreadsheet_id, gid, api_key)
        range_name = quote(target_worksheet, safe='')
        url = (
            f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/"
            f"{range_name}?key={api_key}"
        )

        with urlopen(url, timeout=30) as response:
            payload = json.loads(response.read().decode('utf-8'))

        return self._values_to_dataframe(payload.get('values', []), data_kind)

    def _values_to_dataframe(self, values, data_kind: str = 'companies') -> pd.DataFrame:
        """Convert raw worksheet values to normalized company or job rows."""
        if not values:
            empty = pd.DataFrame()
            return self.normalize_jobs_dataframe(empty) if data_kind == 'jobs' else self.normalize_dataframe(empty)

        header = [column.strip() for column in values[0]]
        valid_indexes = [index for index, column in enumerate(header) if column]
        header = [header[index] for index in valid_indexes]
        rows = [
            [row[index] if index < len(row) else '' for index in valid_indexes]
            for row in values[1:]
        ]
        df = pd.DataFrame(rows, columns=header, dtype=str)
        df = df.replace('', pd.NA)

        if data_kind == 'jobs':
            return self.normalize_jobs_dataframe(df)
        if data_kind != 'companies':
            raise ValueError(f"Unsupported Google Sheets data kind: {data_kind}")
        return self.normalize_dataframe(df)

    def _get_first_sheet_title(self, spreadsheet_id: str, gid: Optional[str], api_key: str) -> str:
        metadata_url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}?key={api_key}"
        with urlopen(metadata_url, timeout=30) as response:
            payload = json.loads(response.read().decode('utf-8'))

        sheets = payload.get('sheets', [])
        if not sheets:
            raise RuntimeError("Google Sheet has no worksheets")

        if gid:
            for sheet in sheets:
                properties = sheet.get('properties', {})
                if str(properties.get('sheetId')) == str(gid):
                    return properties.get('title')

        return sheets[0].get('properties', {}).get('title')

    def _parse_sheet_ref(self, sheet_ref: str):
        if sheet_ref.startswith(('http://', 'https://')):
            parsed = urlparse(sheet_ref)
            parts = [part for part in parsed.path.split('/') if part]
            try:
                spreadsheet_id = parts[parts.index('d') + 1]
            except (ValueError, IndexError) as e:
                raise ValueError("Could not parse spreadsheet ID from Google Sheet URL") from e

            gid = None
            if 'gid=' in parsed.fragment:
                gid = parsed.fragment.split('gid=', 1)[1].split('&', 1)[0]
            elif 'gid=' in parsed.query:
                gid = parsed.query.split('gid=', 1)[1].split('&', 1)[0]

            return spreadsheet_id, gid

        return sheet_ref, None
    
    def normalize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize dataframe column names to handle different schemas
        Supports both old schema (Name, Website, Career Page) and new schema (Website, Career Page, Active)
        """
        # Create a copy to avoid modifying original
        df = df.copy()
        
        # If 'Website' exists but 'Name' doesn't, use Website as Name
        if 'Website' in df.columns and 'Name' not in df.columns:
            # Extract domain name from website URL for display
            df['Name'] = self.extract_domain_name(df['Website'])
        
        # Ensure required columns exist
        required_columns = ['Name', 'Career Page', 'Label']
        for col in required_columns:
            if col not in df.columns:
                CrawlerLogger.missing_column_warning(col)
                df[col] = 'N/A'
        
        # Add Description if missing
        if 'Description' not in df.columns:
            df['Description'] = 'N/A'
        
        # Filter by Active status if column exists
        if 'Active' in df.columns:
            # Filter only active entries
            active_count = len(df)
            df = df[df['Active'].str.lower() == 'active'].copy()
            CrawlerLogger.info_message(f"Filtered to {len(df)} active companies (out of {active_count} total)")
        
        return df

    def normalize_jobs_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize scraped job rows so reports, CSV, and Sheets use the same company field."""
        df = df.copy()

        if 'Company' not in df.columns and 'Company Name' in df.columns:
            df['Company'] = df['Company Name']
        elif 'Company Name' not in df.columns and 'Company' in df.columns:
            df['Company Name'] = df['Company']
        elif 'Company' in df.columns and 'Company Name' in df.columns:
            df['Company'] = df['Company'].fillna(df['Company Name'])
            df['Company Name'] = df['Company Name'].fillna(df['Company'])

        ordered_columns = [col for col in self.JOB_COLUMN_ORDER if col in df.columns]
        remaining_columns = [col for col in df.columns if col not in ordered_columns]
        return df[ordered_columns + remaining_columns]

    def export_jobs_to_google_sheet(self, sheet_ref: str, worksheet_name: Optional[str] = None) -> bool:
        """Export the currently configured jobs CSV to a Google Sheet."""
        if self.df is None and not self.load_csv():
            return False

        return self.export_dataframe_to_google_sheet(self.df, sheet_ref, worksheet_name)

    def export_dataframe_to_google_sheet(
        self,
        df: pd.DataFrame,
        sheet_ref: str,
        worksheet_name: Optional[str] = None
    ) -> bool:
        """Replace a Google worksheet with dataframe contents."""
        try:
            worksheet = self._open_google_worksheet(sheet_ref, worksheet_name)
            output_df = self.normalize_jobs_dataframe(df).fillna('')
            values = [output_df.columns.tolist()] + [
                [self._sanitize_sheet_value(value) for value in row]
                for row in output_df.astype(str).values.tolist()
            ]

            worksheet.clear()
            if values:
                worksheet.resize(rows=max(len(values), 2), cols=max(len(values[0]), 1))
                self._update_worksheet_in_chunks(worksheet, values)
                self._format_worksheet_for_compact_rows(worksheet, len(values), len(values[0]))

            logger.info(f"✅ Successfully exported {len(output_df)} rows to Google Sheets")
            return True
        except Exception as e:
            logger.error(f"Error exporting to Google Sheets: {e}")
            return False

    def _open_google_worksheet(self, sheet_ref: str, worksheet_name: Optional[str] = None):
        """Open a worksheet using service-account credentials from the environment."""
        try:
            import gspread
        except ImportError as e:
            raise RuntimeError("Google Sheets support requires gspread") from e

        self._load_dotenv_fallback()
        client = self._get_gspread_client(gspread)

        if sheet_ref.startswith(('http://', 'https://')):
            spreadsheet = client.open_by_url(sheet_ref)
        else:
            spreadsheet = client.open_by_key(sheet_ref)

        if worksheet_name:
            try:
                return spreadsheet.worksheet(worksheet_name)
            except gspread.WorksheetNotFound:
                return spreadsheet.add_worksheet(title=worksheet_name, rows=1000, cols=30)

        return spreadsheet.sheet1

    def _get_gspread_client(self, gspread):
        credentials_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
        credentials_file = (
            os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE') or
            os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        )

        if credentials_json:
            return gspread.service_account_from_dict(json.loads(credentials_json))

        if credentials_file:
            credentials_file = self._resolve_credentials_file(credentials_file)
            return gspread.service_account(filename=credentials_file)

        try:
            import google.auth
            credentials, _ = google.auth.default(scopes=['https://www.googleapis.com/auth/spreadsheets'])
            return gspread.authorize(credentials)
        except Exception:
            return gspread.service_account()

    def _update_worksheet_in_chunks(self, worksheet, values, chunk_size: int = 500) -> None:
        for start_index in range(0, len(values), chunk_size):
            chunk = values[start_index:start_index + chunk_size]
            start_row = start_index + 1
            end_row = start_row + len(chunk) - 1
            end_col = self._column_letter(len(chunk[0]))
            range_name = f"A{start_row}:{end_col}{end_row}"
            worksheet.update(chunk, range_name=range_name, value_input_option='RAW')

    def _sanitize_sheet_value(self, value: str) -> str:
        max_cell_chars = 49000
        value = re.sub(r"\s+", " ", value.replace("\r", " ").replace("\n", " ")).strip()
        if len(value) <= max_cell_chars:
            return value

        return value[:max_cell_chars] + " [truncated for Google Sheets cell limit]"

    def _format_worksheet_for_compact_rows(self, worksheet, row_count: int, column_count: int) -> None:
        sheet_id = worksheet.id
        requests = [
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 0,
                        "endRowIndex": row_count,
                        "startColumnIndex": 0,
                        "endColumnIndex": column_count,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "wrapStrategy": "CLIP",
                            "verticalAlignment": "TOP",
                        }
                    },
                    "fields": "userEnteredFormat.wrapStrategy,userEnteredFormat.verticalAlignment",
                }
            },
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "ROWS",
                        "startIndex": 0,
                        "endIndex": row_count,
                    },
                    "properties": {"pixelSize": 24},
                    "fields": "pixelSize",
                }
            },
        ]
        worksheet.spreadsheet.batch_update({"requests": requests})

    def _column_letter(self, column_number: int) -> str:
        letters = []
        while column_number:
            column_number, remainder = divmod(column_number - 1, 26)
            letters.append(chr(65 + remainder))
        return ''.join(reversed(letters))

    def _resolve_credentials_file(self, credentials_file: str) -> str:
        path = Path(credentials_file).expanduser()
        if path.is_absolute():
            return str(path)

        env_dir = self._find_env_file().parent
        env_relative = env_dir / path
        if env_relative.exists():
            return str(env_relative)

        return str(path)

    def _has_google_service_account_credentials(self) -> bool:
        self._load_dotenv_fallback()
        return bool(
            os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON') or
            os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE') or
            os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        )

    def _get_google_api_key(self) -> Optional[str]:
        self._load_dotenv_fallback()

        for key_name in ('GOOGLE_API_KEY', 'GOOGLE_SHEETS_API_KEY', 'SHEETS_API_KEY'):
            value = os.getenv(key_name)
            if value:
                return value.strip()

        env_path = self._find_env_file()
        if not env_path.exists():
            return None

        raw = env_path.read_text(errors='ignore').strip()
        if not raw:
            return None

        for line in raw.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue

            for separator in ('=', ':'):
                if separator in stripped:
                    name, value = stripped.split(separator, 1)
                    if self._looks_like_google_api_key_name(name):
                        return value.strip().strip('"\'')

            parts = stripped.split()
            if len(parts) == 2 and self._looks_like_google_api_key_name(parts[0]):
                return parts[1].strip().strip('"\'')

        if len(raw.split()) == 1:
            return raw.strip().strip('"\'')

        return None

    def _looks_like_google_api_key_name(self, name: str) -> bool:
        normalized = ''.join(ch for ch in name.lower() if ch.isalnum())
        return 'google' in normalized and 'api' in normalized

    def _load_dotenv_fallback(self) -> None:
        env_path = self._find_env_file()
        if not env_path.exists():
            return

        for line in env_path.read_text(errors='ignore').splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith('#') or '=' not in stripped:
                continue

            name, value = stripped.split('=', 1)
            name = name.strip()
            value = value.strip().strip('"\'')

            if name and name not in os.environ:
                os.environ[name] = value

    def _find_env_file(self) -> Path:
        for directory in [Path.cwd(), *Path.cwd().parents]:
            env_path = directory / '.env'
            if env_path.exists():
                return env_path

        return Path('.env')

    @staticmethod
    def extract_domain_name(url: str) -> str:
        """Extract clean domain name from URL for display"""
        if pd.isna(url) or not url:
            return 'Unknown'
        
        try:
            # Remove protocol
            domain = url.replace('https://', '').replace('http://', '')
            # Remove www.
            domain = domain.replace('www.', '')
            # Take first part before /
            domain = domain.split('/')[0]
            # Capitalize first letter
            domain = domain.split('.')[0].capitalize()
            return domain
        except:
            return url
    
    def export_to_sqlite(self, db_path: str = 'jobs.db', table_name: str = 'jobs'):
        """
        Export jobs to SQLite database
        
        Usage:
            pip install sqlite3  # (usually comes with Python)
            exporter.export_to_sqlite('jobs.db')
        """
        try:
            import sqlite3
            
            if self.df is None and not self.load_csv():
                return False
            
            conn = sqlite3.connect(db_path)
            
            # Create table and insert data
            self.df.to_sql(table_name, conn, if_exists='replace', index=False)
            
            # Create index on Job Link for faster lookups
            conn.execute(f"CREATE INDEX IF NOT EXISTS idx_job_link ON {table_name} ([Job Link])")
            conn.execute(f"CREATE INDEX IF NOT EXISTS idx_company ON {table_name} (Company)")
            conn.execute(f"CREATE INDEX IF NOT EXISTS idx_scraped_date ON {table_name} ([Scraped Date])")
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Successfully exported {len(self.df)} jobs to SQLite: {db_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting to SQLite: {e}")
            return False
    
    def get_stats(self):
        """Get statistics about the jobs database"""
        if self.df is None:
            if not self.load_csv():
                return
        
        logger.info("\n" + "="*60)
        logger.info("📊 JOB DATABASE STATISTICS")
        logger.info("="*60)
        logger.info(f"Total jobs: {len(self.df)}")
        logger.info(f"Unique companies: {self.df['Company'].nunique()}")
        logger.info(f"Unique locations: {self.df['Location'].nunique()}")
        
        logger.info("\n📦 Jobs by ATS Platform:")
        platform_counts = self.df['Label'].value_counts()
        for platform, count in platform_counts.head(10).items():
            logger.info(f"   {platform}: {count}")
        
        logger.info("\n🏢 Top Companies by Job Count:")
        company_counts = self.df['Company'].value_counts()
        for company, count in company_counts.head(10).items():
            logger.info(f"   {company}: {count}")
        
        logger.info("="*60 + "\n")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Export jobs to different database systems')
    parser.add_argument('--csv', default='output/all_jobs.csv', help='Path to jobs CSV file')
    parser.add_argument('--stats', action='store_true', help='Show database statistics')
    parser.add_argument('--sqlite', metavar='DB_PATH', help='Export to SQLite database')
    parser.add_argument('--postgresql', metavar='CONNECTION_STRING', 
                       help='Export to PostgreSQL (e.g., postgresql://user:pass@localhost/db)')
    parser.add_argument('--mongodb', metavar='CONNECTION_STRING',
                       help='Export to MongoDB (e.g., mongodb://localhost:27017/)')
    parser.add_argument('--airtable', nargs=2, metavar=('API_KEY', 'BASE_ID'),
                       help='Export to Airtable (requires API key and base ID)')
    
    args = parser.parse_args()
    
    exporter = DataController(args.csv)
    
    if args.stats:
        exporter.get_stats()
    
    if args.sqlite:
        exporter.export_to_sqlite(args.sqlite)
    
    if args.postgresql:
        exporter.export_to_postgresql(args.postgresql)
    
    if args.mongodb:
        exporter.export_to_mongodb(args.mongodb)
    
    if args.airtable:
        api_key, base_id = args.airtable
        exporter.export_to_airtable(api_key, base_id)


if __name__ == '__main__':
    main()
