"""
Crawler Logger
Clean logging interface for the job crawler with formatted outputs
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class CrawlerLogger:
    """Clean logging interface for job crawler"""
    
    @staticmethod
    def startup_header(total_companies: int, existing_jobs: int):
        """Log crawler startup information"""
        logger.info("\n" + "="*80)
        logger.info("🚀 STARTING JOB CRAWLER")
        logger.info("="*80)
        logger.info(f"📊 Processing {total_companies} companies")
        logger.info(f"📦 Existing jobs: {existing_jobs}")
        logger.info("="*80 + "\n")
    
    @staticmethod
    def company_start(index: int, total: int, company_name: str, label: str):
        """Log company processing start"""
        current_time = datetime.now().strftime('%H:%M:%S')
        logger.info(f"\n[{index + 1}/{total}] 🏢 {company_name} ({label})")
        logger.info(f"  ⏱️  Starting at: {current_time}")
    
    @staticmethod
    def company_success(jobs_count: int, new_jobs_count: int, elapsed_time: float, 
                       company_name: str = "", show_jobs: List[str] = None):
        """Log successful company processing"""
        jobs_per_sec = jobs_count / elapsed_time if elapsed_time > 0 else 0
        completion_time = datetime.now().strftime('%H:%M:%S')
        
        logger.info(f"  ✅ Found {jobs_count} jobs ({new_jobs_count} new) in {elapsed_time:.1f}s ({jobs_per_sec:.1f} jobs/sec)")
        logger.info(f"  ⏱️  Completed at: {completion_time} | Duration: {elapsed_time:.1f}s")
        
        # Show sample new jobs
        if show_jobs:
            for job in show_jobs[:3]:
                logger.info(f"     • {job}")
            if len(show_jobs) > 3:
                logger.info(f"     ... and {len(show_jobs) - 3} more")
    
    @staticmethod
    def company_no_jobs(elapsed_time: float):
        """Log company with no jobs (normal case)"""
        completion_time = datetime.now().strftime('%H:%M:%S')
        logger.info(f"  ℹ️  No jobs available in {elapsed_time:.1f}s (not an error)")
        logger.info(f"  ⏱️  Completed at: {completion_time} | Duration: {elapsed_time:.1f}s")
    
    @staticmethod
    def company_error(error_msg: str, elapsed_time: float):
        """Log company processing error"""
        completion_time = datetime.now().strftime('%H:%M:%S')
        logger.error(f"  ❌ Error: {str(error_msg)[:80]} (after {elapsed_time:.1f}s)")
        logger.info(f"  ⏱️  Failed at: {completion_time} | Duration: {elapsed_time:.1f}s")
    
    @staticmethod
    def progress_update(successful: int, failed: int, total_jobs: int, new_jobs: int):
        """Log progress update"""
        logger.info(f"  📊 Progress: ✓{successful} ❌{failed} | Total: {total_jobs} jobs ({new_jobs} new)")
    
    @staticmethod
    def warning_no_career_page(company_name: str):
        """Log warning for missing career page"""
        logger.warning(f"  ⚠️  No career page - skipping")
    
    @staticmethod
    def warning_no_ats_platform():
        """Log warning for missing ATS platform"""
        logger.warning(f"  ⚠️  No ATS platform - skipping")
    
    @staticmethod
    def warning_no_scraper(label: str):
        """Log warning for missing scraper"""
        logger.warning(f"  ⚠️  No scraper for {label} - skipping")
    
    @staticmethod
    def warning_slow_company(company_name: str, elapsed_time: float, jobs_count: int = 0):
        """Log slow company warning"""
        if elapsed_time > 60:
            if jobs_count > 0:
                logger.warning(f"  🐌 SLOW COMPANY: {company_name} took {elapsed_time:.1f}s - Adding to problems list")
            else:
                logger.warning(f"  🐌 SLOW COMPANY: {company_name} took {elapsed_time:.1f}s with no jobs - Possible scraping issue")
        elif elapsed_time > 30:
            logger.warning(f"  ⏱️  SLOW WARNING: {company_name} took {elapsed_time:.1f}s")
    
    @staticmethod
    def warning_rate_limiting(recommended_delay: float, current_delay: float):
        """Log rate limiting warning"""
        logger.warning(f"  ⚡ HIGH ERROR RATE! Consider increasing delay from {current_delay}s to {recommended_delay}s")
    
    @staticmethod
    def completion_summary(successful: int, failed: int, total_jobs: int, new_jobs: int, 
                          no_jobs_count: int, output_dir: str):
        """Log completion summary"""
        logger.info("\n" + "="*80)
        logger.info("🎉 COMPLETED!")
        logger.info("="*80)
        logger.info(f"✓ Successful: {successful} | ❌ Failed: {failed}")
        logger.info(f"📦 Total jobs: {total_jobs} | 🆕 New: {new_jobs}")
        logger.info(f"ℹ️  Companies with no jobs: {no_jobs_count} (normal)")
        logger.info(f"💾 Saved to: {output_dir}/all_jobs.csv")
    
    @staticmethod
    def timing_summary(timing_summary: Dict, timing_trends: Dict = None):
        """Log timing summary"""
        if not timing_summary:
            return
            
        logger.info(f"⏱️  Total time: {timing_summary['total_time']:.1f}s | Avg per company: {timing_summary['avg_time']:.1f}s")
        logger.info(f"⚡ Fastest: {timing_summary['min_time']:.1f}s | Slowest: {timing_summary['max_time']:.1f}s")
        
        if timing_trends:
            trend_emoji = "📈" if timing_trends['trend'] == 'slower' else "📉" if timing_trends['trend'] == 'faster' else "➡️"
            logger.info(f"{trend_emoji} Performance trend: {timing_trends['trend']} ({timing_trends['change_percent']:+.1f}% vs last run)")
        
        logger.info("="*80)
    
    @staticmethod
    def no_jobs_companies_section(companies: List[Dict]):
        """Log section for companies with no jobs (normal case)"""
        if not companies:
            return
            
        logger.info("\n" + "="*80)
        logger.info("ℹ️  COMPANIES WITH NO JOBS (NORMAL):")
        logger.info("="*80)
        logger.info(f"📊 {len(companies)} companies currently have no job openings")
        logger.info("(This is normal business operation, not an error)")
        
        # Show first 10, then count the rest
        for company in companies[:10]:
            logger.info(f"  • {company['Company']} ({company['Time']})")
        
        if len(companies) > 10:
            logger.info(f"  ... and {len(companies) - 10} more companies")
        
        logger.info("="*80)
    
    @staticmethod
    def failed_companies_section(companies: List[Dict]):
        """Log section for failed companies (actual problems)"""
        if not companies:
            return
            
        logger.info("\n" + "="*80)
        logger.info("❌ COMPANIES WITH ACTUAL PROBLEMS:")
        logger.info("="*80)
        logger.info("(These need investigation - technical issues, not just no jobs)")
        for failure in companies:
            logger.info(f"  • {failure['Company']}: {failure['Reason']}")
        logger.info("="*80)
    
    @staticmethod
    def timing_statistics_section(timing_summary: Dict, timing_trends: Dict = None, 
                                slow_companies: List[Dict] = None):
        """Log detailed timing statistics section"""
        if not timing_summary:
            return
            
        logger.info("\n" + "="*80)
        logger.info("⏱️  TIMING STATISTICS:")
        logger.info("="*80)
        logger.info(f"📊 Summary:")
        logger.info(f"  • Total scraping time: {timing_summary['total_time']:.1f}s")
        logger.info(f"  • Average per company: {timing_summary['avg_time']:.1f}s")
        logger.info(f"  • Fastest company: {timing_summary['min_time']:.1f}s")
        logger.info(f"  • Slowest company: {timing_summary['max_time']:.1f}s")
        logger.info(f"  • Average jobs per company: {timing_summary['avg_jobs']:.0f}")
        
        if timing_trends:
            trend_emoji = "📈" if timing_trends['trend'] == 'slower' else "📉" if timing_trends['trend'] == 'faster' else "➡️"
            logger.info(f"\n📊 Performance Trend vs Last Run:")
            logger.info(f"  {trend_emoji} {timing_trends['trend'].upper()} ({timing_trends['change_percent']:+.1f}%)")
            logger.info(f"  • Previous avg: {timing_trends['previous_avg']:.1f}s")
            logger.info(f"  • Current avg: {timing_trends['current_avg']:.1f}s")
        
        if slow_companies:
            logger.info(f"\n🐌 Slow Companies (>20s):")
            for stat in slow_companies:
                rate = f" ({stat['jobs_per_second']:.1f} jobs/sec)" if stat['job_count'] > 0 else ""
                logger.info(f"  • {stat['company']}: {stat['elapsed_time']:.1f}s for {stat['job_count']} jobs{rate}")
        
        logger.info("="*80)
    
    @staticmethod
    def rate_limiting_section(request_stats: Dict, rate_limit_issues: List[Dict], 
                            current_delay: float, recommended_delay: float = None):
        """Log rate limiting section"""
        if not rate_limit_issues:
            return
            
        logger.info("\n" + "="*80)
        logger.info("⚡ REQUEST ISSUES & RATE LIMITING:")
        logger.info("="*80)
        logger.info(f"📊 Request Stats:")
        logger.info(f"  • Total requests: {request_stats['total_requests']}")
        logger.info(f"  • Successful: {request_stats['successful']}")
        logger.info(f"  • Rate limited: {request_stats['rate_limited']}")
        logger.info(f"  • Timeouts: {request_stats['timeouts']}")
        logger.info(f"  • Connection errors: {request_stats['connection_errors']}")
        
        if recommended_delay:
            logger.info(f"⚡ RECOMMENDATION: Increase delay from {current_delay}s to {recommended_delay}s")

        logger.info("="*80)


    @staticmethod
    def rate_limited_request(company_name: str, status_code: int, current_delay: float):
        """Log rate limited request"""
        logger.warning(f"  ⚡ RATE LIMITED: {company_name} (Status: {status_code}) - Consider increasing delay from {current_delay}s")
    
    @staticmethod
    def timeout_request(company_name: str, details: str):
        """Log timeout request"""
        logger.warning(f"  ⏰ TIMEOUT: {company_name} - {details}")
    
    @staticmethod
    def connection_error_request(company_name: str, details: str):
        """Log connection error request"""
        logger.warning(f"  🔌 CONNECTION ERROR: {company_name} - {details}")
    
    @staticmethod
    def info_message(message: str):
        """Log generic info message"""
        logger.info(message)
    
    @staticmethod
    def warning_message(message):
        """Generic warning message"""
        logger.warning(message)
        
    @staticmethod
    def error_message(message):
        """Generic error message"""
        logger.error(message)
    
    @staticmethod
    def slow_company_warning(company_name, elapsed_time, job_count):
        """Warning for slow companies"""
        logger.warning(f"  ⏱️  SLOW COMPANY: {company_name} took {elapsed_time:.1f}s for {job_count} jobs")
    
    @staticmethod
    def very_slow_company_warning(company_name, elapsed_time):
        """Warning for very slow companies"""
        logger.warning(f"  🐌 VERY SLOW: {company_name} took {elapsed_time:.1f}s - Consider review")
    
    @staticmethod
    def missing_column_warning(column):
        """Warning for missing column"""
        logger.warning(f"Missing required column: {column}")
    
    @staticmethod
    def debug_existing_jobs(count):
        """Debug message for loaded existing jobs"""
        logger.debug(f"Loaded {count} existing jobs from database")
    
    @staticmethod
    def debug_load_error(error):
        """Debug message for load error"""
        logger.debug(f"Could not load existing jobs: {error}")
    
    @staticmethod
    def no_career_page_warning(name):
        """Warning for missing career page"""
        logger.warning(f"No career page URL for {name}, skipping...")
    
    @staticmethod
    def no_label_warning(name):
        """Warning for missing label"""
        logger.warning(f"No label specified for {name}, skipping...")
    
    @staticmethod
    def scraper_not_found_error(label):
        """Error for scraper not found"""
        logger.error(f"Could not find scraper for label: {label}")
    
    @staticmethod
    def jobs_found(count, company_name):
        """Info message for jobs found"""
        logger.info(f"Found {count} jobs for {company_name}")
    
    @staticmethod
    def scraping_error(company_name, error):
        """Error message for scraping failure"""
        logger.error(f"Error scraping {company_name}: {error}")
    
    @staticmethod
    def no_previous_data():
        """Info message for no previous data"""
        logger.info("\n📝 No previous data to compare (first run)")
    
    @staticmethod
    def empty_previous_file():
        """Info message for empty previous file"""
        logger.info("\n📝 Previous file was empty, no comparison needed")
    
    @staticmethod
    def backup_success(count):
        """Info message for successful backup"""
        logger.info(f"\n💾 Backed up previous data: {count} jobs → all_jobs_backup.csv")
    
    @staticmethod
    def backup_error(error):
        """Error message for backup failure"""
        logger.error(f"❌ Error during backup: {error}")
    
    @staticmethod
    def report_saved(filename):
        """Info message for saved report"""
        logger.info(f"\n💾 Report saved to: {filename}\n")
    
    @staticmethod
    def comparison_report_error(error):
        """Error message for comparison report failure"""
        logger.error(f"❌ Error generating comparison report: {error}")
    
    @staticmethod
    def debug_jobs_added(new_count, total_count):
        """Debug message for jobs added to database"""
        logger.debug(f"Added {new_count} new jobs to database (total: {total_count})")
    
    @staticmethod
    def jobs_update_error(error):
        """Error message for jobs update failure"""
        logger.error(f"Error updating jobs file: {error}")
    
    @staticmethod
    def debug_new_database(count):
        """Debug message for new database creation"""
        logger.debug(f"Created new jobs database with {count} jobs")
    
    @staticmethod
    def interrupted_warning():
        """Warning message for interrupted execution"""
        logger.warning("\n⚠️  Interrupted - partial results saved")
    
    @staticmethod
    def general_error(error):
        """General error message"""
        logger.error(f"❌ Error: {error}")
    
    @staticmethod
    def display_report_lines(report_lines):
        """Display all report lines"""
        for line in report_lines:
            logger.info(line)
    
    @staticmethod
    def debug_message(message: str):
        """Log generic debug message"""
        logger.debug(message)
