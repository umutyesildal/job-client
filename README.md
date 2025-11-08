# Job Crawler

Intelligent job scraping system that monitors 535+ companies across 23 ATS platforms, with automated filtering and change detection.

## 🔄 Pipeline Overview

```
📊 Input (535 companies)           🔍 Processing                    📈 Output & Analysis
┌─────────────────────┐            ┌──────────────────────┐         ┌─────────────────────┐
│ job_search.csv      │──────────→ │ Main Crawler Engine  │────────→│ all_jobs.csv        │
│ - Name, Career Page │            │ - 23 ATS Scrapers    │         │ - 46,000+ jobs      │
│ - Description       │            │ - Rate Limit Detect  │         │                     │
│ - Label (ATS type)  │            │ - Error Categorize   │         └─────────────────────┘
│ - Active status     │            │ - Individual Timing  │                     │
└─────────────────────┘            └──────────────────────┘                     │
                                                │                               │
┌─────────────────────┐            ┌──────────────────────┐                     │
│ timing_history.json │←───────────│ Performance Monitor  │                     │
│ - Response times    │            │ - Jobs/second        │                     │
│ - Success/failure   │            │ - Trend analysis     │                     │
│ - Rate limit logs   │            │ - Problem detection  │                     │
└─────────────────────┘            └──────────────────────┘                     │
                                                                                  │
                                   ┌──────────────────────┐                     │
                                   │ Change Detection     │←────────────────────┘
                                   │ - Compare with backup│
                                   │ - Identify new/removed│
                                   │ - Generate reports   │
                                   └──────────────────────┘
                                                │
                                                ▼
                                   ┌──────────────────────┐         ┌─────────────────────┐
                                   │ Student Pipeline     │────────→│ Filtered Results    │
                                   │ - Berlin/Germany     │         │ - Student jobs only │
                                   │ - Technical keywords │         │ - Google Sheets     │
                                   │ - CV matching        │         │ - Daily reports     │
                                   └──────────────────────┘         └─────────────────────┘
```

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run complete pipeline (535 companies)
cd job_scraper/src
python3 main_crawler.py

# Development mode (fast testing)
python3 main_crawler.py -l 10 -d 0.1

# Student pipeline (after main crawler)
cd ../../student_pipeline  
python3 run_pipeline.py
```

## 📊 System Status

**🟢 Active Companies**: 535 companies across 23 ATS platforms  
**📈 Daily Job Volume**: ~46,000 jobs processed  
**⚡ Performance**: 9-60 jobs/second per company  
**🎯 Student Jobs**: ~25 new Berlin tech positions daily

### Working ATS Platforms (23)
- **API-Based**: Amazon, Ashby, BambooHR, Consider, Gem, Getro, Greenhouse, HiBob, Join, Lever, Lingoda, Microsoft, PayPal, Personio, Recruitee, SmartRecruiters, Workable
- **Web-Based**: Capgemini, Rippling, Stripe, Trade Republic, Wipro

### Rate Limiting & Monitoring
- **Smart Detection**: Handles 429/403/503 responses automatically
- **Performance Tracking**: Individual company timing + trends
- **Error Categorization**: Distinguishes "no jobs found" vs technical issues
- **Adaptive Delays**: 0.1s (testing) to 2.0s (production)

## 📁 Data Flow

### Input Sources
- `data/job_search.csv` - 535 company records with ATS configurations
- `data/all_jobs_backup.csv` - Previous run for change detection

### Processing Outputs  
- `data/all_jobs.csv` - Current complete job database
- `data/timing_history.json` - Performance metrics and trends
- `data/job_changes_YYYY-MM-DD.txt` - Daily comparison reports

### Student Pipeline Outputs
- `student_pipeline/filtered_student_jobs_final.csv` - Berlin tech jobs
- Google Sheets sync for real-time access
- CV keyword matching and motivation letters

## ⚙️ Configuration Options

```bash
# Basic usage
python3 main_crawler.py                    # All companies, 2s delay

# Performance tuning  
python3 main_crawler.py -d 0.1 -l 5       # Fast testing
python3 main_crawler.py -d 2.0             # Safe production

# Input sources
python3 main_crawler.py companies.csv      # Custom CSV
python3 main_crawler.py -t sheets "url"    # Google Sheets

# Custom output
python3 main_crawler.py -o /custom/path    # Custom directory
```

## 🔍 Monitoring & Analytics

The system provides comprehensive monitoring:

- **Real-time Performance**: Jobs/second, response times, success rates
- **Trend Analysis**: Historical performance patterns  
- **Problem Detection**: Rate limits, timeouts, parsing failures
- **Change Tracking**: New vs removed jobs with detailed reports
- **Student Focus**: Berlin tech positions with keyword matching

## 📋 Example Outputs

**Daily Change Report**:
```
📊 JOB CHANGES REPORT - 2025-11-08
📦 Previous: 45,500 jobs → Current: 46,486 jobs
📈 Net change: +986 jobs
🎓 New student jobs: 25 (Berlin tech positions)
```

**Performance Metrics**:
```
⚡ Amazon: 538 jobs in 9.0s (59.7 jobs/sec)
⚡ Microsoft: 284 jobs in 4.2s (67.6 jobs/sec) 
🔄 Cherry VC: 1,280 jobs in 12.3s (104.1 jobs/sec)
```




