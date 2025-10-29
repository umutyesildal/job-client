# Student Job Pipeline 🎓

Automated pipeline for finding, filtering, and applying to working student positions in Berlin.

## Pipeline Overview

```
main_crawler.py → all_jobs.csv (11,407 jobs)
         ↓
filter_student_jobs.py → filtered_student_jobs.csv (176 jobs)
         ↓
extract_keywords.py (Gemini) → filtered_student_jobs_with_keywords.csv
         ↓
match_cv.py → filtered_student_jobs_matched.csv
         ↓
generate_motivation.py → filtered_student_jobs_final.csv
         ↓
sync_to_sheets.py → Google Sheets
```

## Features

- **Smart Filtering**: Finds working student positions in Berlin/Germany
- **AI Keyword Extraction**: Uses Gemini API to extract technical skills from job descriptions
- **CV Matching**: Calculates match percentage between your skills and job requirements
- **Motivation Letters**: Generates personalized motivation letters using templates
- **Google Sheets Sync**: Syncs results to Google Sheets with duplicate prevention

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Gemini API

1. Get your Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a `.env` file in the project root:

```bash
GEMINI=your_api_key_here
```

### 3. Configure Your CV Keywords

Edit `student_pipeline/cv_keywords.json`:

```json
{
  "cv_id": "your_name_2025",
  "keywords": [
    "Python",
    "JavaScript",
    "React",
    "Node.js",
    "SQL",
    "Git",
    "Docker",
    "AWS",
    "Machine Learning",
    "Data Analysis",
    "Add your skills here..."
  ]
}
```

### 4. Set Up Google Sheets (Optional)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable **Google Sheets API** and **Google Drive API**
4. Create a **Service Account**
5. Download the credentials JSON
6. Save as `google_credentials.json` in project root

## Usage

### Run Complete Pipeline

```bash
python student_pipeline/run_pipeline.py
```

This runs all 5 stages:
1. Filter student jobs
2. Extract keywords with Gemini
3. Match with your CV
4. Generate motivation letters
5. Sync to Google Sheets

### Run Without Google Sheets Sync

```bash
python student_pipeline/run_pipeline.py --skip-sheets
```

### Run Individual Stages

```bash
# Stage 1: Filter student jobs
python student_pipeline/filter_student_jobs.py

# Stage 2: Extract keywords
python student_pipeline/extract_keywords.py

# Stage 3: Match with CV
python student_pipeline/match_cv.py

# Stage 4: Generate motivation letters
python student_pipeline/generate_motivation.py

# Stage 5: Sync to Google Sheets
python student_pipeline/sync_to_sheets.py
```

## Pipeline Components

### 1. Filter Student Jobs (`filter_student_jobs.py`)

Filters jobs based on:
- **Title**: Must contain "working student", "werkstudent", "student", "intern", "internship", or "praktikum"
- **Location**: Must be in Berlin, Germany, Deutschland, GE, or DE

**Output**: `filtered_student_jobs.csv` (176 jobs from 11,407 total)

### 2. Extract Keywords (`extract_keywords.py`)

Uses Gemini API to extract technical keywords from job descriptions.

**Features**:
- Excludes generic terms (teamwork, multitasking, etc.)
- Focuses on technical skills, tools, and frameworks
- Rate limited to avoid API throttling
- Retry logic with exponential backoff

**Output**: `filtered_student_jobs_with_keywords.csv`

### 3. Match CV (`match_cv.py`)

Calculates match percentage between your CV keywords and job keywords.

**Metrics**:
- **Match Percentage**: % of job keywords you have
- **Match Count**: Number of matched keywords
- **Matched Keywords**: List of common skills

**Categories**:
- High Match: >50%
- Medium Match: 30-50%
- Low Match: <30%

**Output**: `filtered_student_jobs_matched.csv` (sorted by match %)

### 4. Generate Motivation Letters (`generate_motivation.py`)

Generates personalized motivation letters using a template.

**Template Variables**:
- `{company}`: Company name
- `{job_title}`: Job title
- `{matched_skills_text}`: Context-aware text about matched skills
- `{experience_section}`: Your experiences (customizable)

**Output**: `filtered_student_jobs_final.csv`

### 5. Sync to Google Sheets (`sync_to_sheets.py`)

Syncs final results to Google Sheets.

**Features**:
- Duplicate prevention (checks Job Link)
- Adds Company Point column (manually fillable)
- Preserves existing data
- Provides spreadsheet URL

**Output**: Google Sheets spreadsheet

## Output Format

Final CSV includes:

| Column | Description |
|--------|-------------|
| Job Title | Position title |
| Job Description | Full job description |
| Employment Type | Full-time, Part-time, etc. |
| Company | Company name |
| Company Description | About the company |
| Company Point | Manual rating (1-10) |
| Job Link | Application URL |
| Location | Job location |
| Label | Job category/label |
| Posted Date | When job was posted |
| Keywords | Extracted technical keywords |
| CV_ID | Your CV identifier |
| Match_Percentage | % match with your CV |
| Match_Count | Number of matched keywords |
| Matched_Keywords | List of common skills |
| Motivation_Letter | Generated motivation letter |

## Customization

### Modify Filter Criteria

Edit `filter_student_jobs.py`:

```python
# Add more job types
student_terms = ['working student', 'werkstudent', 'intern', 'your_term']

# Add more locations
location_terms = ['berlin', 'munich', 'your_city']
```

### Customize Keyword Extraction

Edit the prompt in `extract_keywords.py`:

```python
KEYWORD_EXTRACTION_PROMPT = """
Your custom prompt here...
"""
```

### Modify Motivation Letter Template

Edit `generate_motivation.py`:

```python
MOTIVATION_LETTER_TEMPLATE = """
Your custom template here...
"""
```

## Filtering Results

From the last run:
- **Total Jobs**: 11,407
- **Student Jobs Found**: 176 (1.5%)
- **Match Rate**: Varies (typically 20-60%)

## API Costs

### Gemini API
- **Model**: gemini-2.0-flash-exp
- **Cost**: Free tier available (60 requests/minute)
- **Usage**: ~176 requests per pipeline run
- **Rate Limiting**: 0.5s per job + 2s every 10 jobs

## Troubleshooting

### "google.generativeai not found"

```bash
pip install google-generativeai
```

### "GEMINI API key not found"

Add to `.env`:
```
GEMINI=your_api_key_here
```

### "google_credentials.json not found"

Run pipeline with `--skip-sheets` flag or set up Google Sheets API (see Setup section).

### Empty Keywords Column

Make sure:
1. Gemini API key is set in `.env`
2. `google-generativeai` is installed
3. Run `extract_keywords.py` after filtering

### Low Match Percentage

Update `cv_keywords.json` with more relevant skills from your CV.

## Tips

1. **Run incrementally**: Test each stage individually first
2. **Check API limits**: Gemini free tier has rate limits
3. **Review templates**: Customize motivation letter for better results
4. **Update CV keywords**: Keep your skills list current
5. **Manual review**: Always review generated letters before sending

## Next Steps

1. ✅ Run complete pipeline
2. ✅ Review filtered jobs in Google Sheets
3. ✅ Sort by Match_Percentage
4. ✅ Customize motivation letters
5. ✅ Add Company Point ratings
6. ✅ Apply to high-match jobs!

## Support

For issues or questions:
1. Check this README
2. Review error messages
3. Check API quotas
4. Verify file paths and permissions
