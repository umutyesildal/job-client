"""
Report generation module for job crawler.

This module handles the creation of detailed reports about job changes,
statistics, and scraping results.
"""

import os
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional


class ReportGenerator:
    """Handles generation of detailed reports for job crawling results."""
    
    @staticmethod
    def generate_job_changes_report(
        old_df: pd.DataFrame,
        new_df: pd.DataFrame,
        added_links: set,
        removed_links: set,
        unchanged_links: set,
        added_jobs: pd.DataFrame,
        removed_jobs: pd.DataFrame,
        no_jobs_companies: List[Dict],
        failed_companies: List[Dict],
        rate_limit_issues: List[Dict],
        request_stats: Dict,
        current_delay: float,
        timing_summary: Optional[Dict] = None,
        timing_trends: Optional[Dict] = None,
        slow_companies: List[Dict] = None,
        should_increase_delay: bool = False,
        delay_recommendation: float = None,
        output_dir: str = "."
    ) -> str:
        """
        Generate a comprehensive job changes report.
        
        Returns:
            str: Path to the generated report file
        """
        # Filter student jobs (only if DataFrames have the required columns)
        student_new_jobs = pd.DataFrame()
        student_removed_jobs = pd.DataFrame()
        
        if not added_jobs.empty and 'Job Title' in added_jobs.columns and 'Location' in added_jobs.columns:
            student_new_jobs = added_jobs[
                (added_jobs['Job Title'].str.lower().str.contains('student|intern|praktikum', na=False)) &
                (added_jobs['Location'].str.lower().str.contains('berlin|germany|deutschland', na=False))
            ]
        
        if not removed_jobs.empty and 'Job Title' in removed_jobs.columns and 'Location' in removed_jobs.columns:
            student_removed_jobs = removed_jobs[
                (removed_jobs['Job Title'].str.lower().str.contains('student|intern|praktikum', na=False)) &
                (removed_jobs['Location'].str.lower().str.contains('berlin|germany|deutschland', na=False))
            ]
        
        # Generate report lines
        report_lines = []
        
        # Header
        ReportGenerator._add_header(report_lines)
        
        # Summary statistics
        ReportGenerator._add_summary_stats(report_lines, old_df, new_df, added_links, removed_links, unchanged_links)
        
        # Student jobs sections
        if len(student_new_jobs) > 0:
            ReportGenerator._add_new_student_jobs(report_lines, student_new_jobs)
        
        if len(student_removed_jobs) > 0:
            ReportGenerator._add_removed_student_jobs(report_lines, student_removed_jobs)
        
        # Companies with no jobs (normal)
        if no_jobs_companies:
            ReportGenerator._add_no_jobs_companies(report_lines, no_jobs_companies)
        
        # Failed companies (problems)
        if failed_companies:
            ReportGenerator._add_failed_companies(report_lines, failed_companies)
        
        # Rate limiting issues
        if rate_limit_issues:
            ReportGenerator._add_rate_limiting_section(
                report_lines, rate_limit_issues, request_stats, current_delay,
                should_increase_delay, delay_recommendation
            )
        
        # Timing statistics
        if timing_summary:
            ReportGenerator._add_timing_statistics(
                report_lines, timing_summary, timing_trends, slow_companies
            )
        
        # Save report to file
        return ReportGenerator._save_report(report_lines, output_dir)
    
    @staticmethod
    def _add_header(report_lines: List[str]) -> None:
        """Add report header."""
        report_lines.append("\n" + "="*80)
        report_lines.append("📊 JOB CHANGES REPORT")
        report_lines.append("="*80)
        report_lines.append(f"📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
    
    @staticmethod
    def _add_summary_stats(
        report_lines: List[str],
        old_df: pd.DataFrame,
        new_df: pd.DataFrame,
        added_links: set,
        removed_links: set,
        unchanged_links: set
    ) -> None:
        """Add summary statistics."""
        report_lines.append(f"📦 Previous: {len(old_df)} jobs")
        report_lines.append(f"📦 Current:  {len(new_df)} jobs")
        report_lines.append(f"📈 Net change: {len(new_df) - len(old_df):+d} jobs")
        report_lines.append("")
        report_lines.append(f"🆕 New jobs:     {len(added_links)}")
        report_lines.append(f"❌ Removed jobs: {len(removed_links)}")
        report_lines.append(f"✓  Unchanged:    {len(unchanged_links)}")
        report_lines.append("="*80)
    
    @staticmethod
    def _add_new_student_jobs(report_lines: List[str], student_new_jobs: pd.DataFrame) -> None:
        """Add new student jobs section."""
        report_lines.append("")
        report_lines.append(f"🎓 NEW STUDENT JOBS ({len(student_new_jobs)}):")
        report_lines.append("-"*80)
        
        for _, job in student_new_jobs.iterrows():
            ReportGenerator._add_job_details(report_lines, job)
        
        report_lines.append("-"*80)
    
    @staticmethod
    def _add_removed_student_jobs(report_lines: List[str], student_removed_jobs: pd.DataFrame) -> None:
        """Add removed student jobs section."""
        report_lines.append("")
        report_lines.append(f"❌ REMOVED STUDENT JOBS ({len(student_removed_jobs)}):")
        report_lines.append("-"*80)
        
        for _, job in student_removed_jobs.iterrows():
            ReportGenerator._add_job_details(report_lines, job)
        
        report_lines.append("-"*80)
    
    @staticmethod
    def _add_job_details(report_lines: List[str], job: pd.Series) -> None:
        """Add job details to report."""
        company = job.get('Company', 'Unknown')
        if pd.isna(company):
            company = 'Unknown'
        
        title = job.get('Job Title', 'Unknown')
        if pd.isna(title):
            title = 'Unknown'
        
        location = job.get('Location', 'Unknown')
        if pd.isna(location):
            location = 'Unknown'
        
        job_link = job.get('Job Link', '')
        if pd.isna(job_link):
            job_link = 'No link available'
        
        report_lines.append(f"  • {title}")
        report_lines.append(f"    @ {company} | {location}")
        report_lines.append(f"    🔗 {job_link}")
        report_lines.append("")
    
    @staticmethod
    def _add_no_jobs_companies(report_lines: List[str], no_jobs_companies: List[Dict]) -> None:
        """Add companies with no jobs section."""
        report_lines.append("")
        report_lines.append(f"ℹ️  COMPANIES WITH NO JOBS - NORMAL ({len(no_jobs_companies)}):")
        report_lines.append("-"*80)
        report_lines.append("(These companies' scrapers work fine, they just don't have job openings)")
        
        # Show first 20, then summarize
        for company in no_jobs_companies[:20]:
            report_lines.append(f"  • {company['Company']} ({company['Time']})")
        
        if len(no_jobs_companies) > 20:
            report_lines.append(f"  ... and {len(no_jobs_companies) - 20} more companies")
        
        report_lines.append("-"*80)
    
    @staticmethod
    def _add_failed_companies(report_lines: List[str], failed_companies: List[Dict]) -> None:
        """Add failed companies section."""
        report_lines.append("")
        report_lines.append(f"❌ COMPANIES WITH ACTUAL PROBLEMS ({len(failed_companies)}):")
        report_lines.append("-"*80)
        report_lines.append("(These need investigation - technical issues, not just no jobs)")
        
        for failure in failed_companies:
            report_lines.append(f"  • {failure['Company']}: {failure['Reason']}")
        
        report_lines.append("-"*80)
    
    @staticmethod
    def _add_rate_limiting_section(
        report_lines: List[str],
        rate_limit_issues: List[Dict],
        request_stats: Dict,
        current_delay: float,
        should_increase_delay: bool,
        delay_recommendation: float
    ) -> None:
        """Add rate limiting section."""
        report_lines.append("")
        report_lines.append(f"⚡ REQUEST ISSUES & RATE LIMITING:")
        report_lines.append("-"*80)
        report_lines.append(f"📊 Request Stats (Current delay: {current_delay}s):")
        report_lines.append(f"  • Total requests: {request_stats['total_requests']}")
        report_lines.append(f"  • Successful: {request_stats['successful']}")
        report_lines.append(f"  • Rate limited: {request_stats['rate_limited']}")
        report_lines.append(f"  • Timeouts: {request_stats['timeouts']}")
        report_lines.append(f"  • Connection errors: {request_stats['connection_errors']}")
        
        if should_increase_delay and delay_recommendation:
            report_lines.append("")
            report_lines.append(f"⚡ RECOMMENDATION: Increase delay from {current_delay}s to {delay_recommendation}s")
        
        report_lines.append("")
        report_lines.append("🔍 Recent Issues:")
        for issue in rate_limit_issues[-10:]:  # Show last 10 issues
            status_info = f" (Status: {issue['status_code']})" if issue['status_code'] else ""
            report_lines.append(f"  • {issue['timestamp']} - {issue['company']}: {issue['issue_type']}{status_info}")
        
        report_lines.append("-"*80)
    
    @staticmethod
    def _add_timing_statistics(
        report_lines: List[str],
        timing_summary: Dict,
        timing_trends: Optional[Dict],
        slow_companies: List[Dict]
    ) -> None:
        """Add timing statistics section."""
        report_lines.append("")
        report_lines.append("⏱️  TIMING STATISTICS:")
        report_lines.append("-"*80)
        report_lines.append(f"📊 Summary:")
        report_lines.append(f"  • Total scraping time: {timing_summary['total_time']:.1f}s")
        report_lines.append(f"  • Average per company: {timing_summary['avg_time']:.1f}s")
        report_lines.append(f"  • Fastest company: {timing_summary['min_time']:.1f}s")
        report_lines.append(f"  • Slowest company: {timing_summary['max_time']:.1f}s")
        report_lines.append(f"  • Average jobs per company: {timing_summary['avg_jobs']:.0f}")
        
        if timing_trends:
            trend_emoji = "📈" if timing_trends['trend'] == 'slower' else "📉" if timing_trends['trend'] == 'faster' else "➡️"
            report_lines.append("")
            report_lines.append(f"📊 Performance Trend vs Last Run:")
            report_lines.append(f"  {trend_emoji} {timing_trends['trend'].upper()} ({timing_trends['change_percent']:+.1f}%)")
            report_lines.append(f"  • Previous avg: {timing_trends['previous_avg']:.1f}s")
            report_lines.append(f"  • Current avg: {timing_trends['current_avg']:.1f}s")
        
        if slow_companies:
            report_lines.append("")
            report_lines.append("🐌 Slow Companies (>20s):")
            for stat in slow_companies:
                rate = f" ({stat['jobs_per_second']:.1f} jobs/sec)" if stat['job_count'] > 0 else ""
                report_lines.append(f"  • {stat['company']}: {stat['elapsed_time']:.1f}s for {stat['job_count']} jobs{rate}")
        
        report_lines.append("-"*80)
    
    @staticmethod
    def _save_report(report_lines: List[str], output_dir: str) -> str:
        """Save report to file and return filename."""
        report_text = "\n".join(report_lines)
        report_filename = f"job_changes_{datetime.now().strftime('%Y-%m-%d')}.txt"
        report_path = os.path.join(output_dir, report_filename)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_text)
        
        return report_filename
    
    @staticmethod
    def get_report_lines(
        old_df: pd.DataFrame,
        new_df: pd.DataFrame,
        added_links: set,
        removed_links: set,
        unchanged_links: set,
        added_jobs: pd.DataFrame,
        removed_jobs: pd.DataFrame,
        no_jobs_companies: List[Dict],
        failed_companies: List[Dict],
        rate_limit_issues: List[Dict],
        request_stats: Dict,
        current_delay: float,
        timing_summary: Optional[Dict] = None,
        timing_trends: Optional[Dict] = None,
        slow_companies: List[Dict] = None,
        should_increase_delay: bool = False,
        delay_recommendation: float = None
    ) -> List[str]:
        """
        Get report lines without saving to file.
        Useful for displaying in console.
        """
        # Filter student jobs (only if DataFrames have the required columns)
        student_new_jobs = pd.DataFrame()
        student_removed_jobs = pd.DataFrame()
        
        if not added_jobs.empty and 'Job Title' in added_jobs.columns and 'Location' in added_jobs.columns:
            student_new_jobs = added_jobs[
                (added_jobs['Job Title'].str.lower().str.contains('student|intern|praktikum', na=False)) &
                (added_jobs['Location'].str.lower().str.contains('berlin|germany|deutschland', na=False))
            ]
        
        if not removed_jobs.empty and 'Job Title' in removed_jobs.columns and 'Location' in removed_jobs.columns:
            student_removed_jobs = removed_jobs[
                (removed_jobs['Job Title'].str.lower().str.contains('student|intern|praktikum', na=False)) &
                (removed_jobs['Location'].str.lower().str.contains('berlin|germany|deutschland', na=False))
            ]
        
        # Generate report lines
        report_lines = []
        
        # Header
        ReportGenerator._add_header(report_lines)
        
        # Summary statistics
        ReportGenerator._add_summary_stats(report_lines, old_df, new_df, added_links, removed_links, unchanged_links)
        
        # Student jobs sections
        if len(student_new_jobs) > 0:
            ReportGenerator._add_new_student_jobs(report_lines, student_new_jobs)
        
        if len(student_removed_jobs) > 0:
            ReportGenerator._add_removed_student_jobs(report_lines, student_removed_jobs)
        
        # Companies with no jobs (normal)
        if no_jobs_companies:
            ReportGenerator._add_no_jobs_companies(report_lines, no_jobs_companies)
        
        # Failed companies (problems)
        if failed_companies:
            ReportGenerator._add_failed_companies(report_lines, failed_companies)
        
        # Rate limiting issues
        if rate_limit_issues:
            ReportGenerator._add_rate_limiting_section(
                report_lines, rate_limit_issues, request_stats, current_delay,
                should_increase_delay, delay_recommendation
            )
        
        # Timing statistics
        if timing_summary:
            ReportGenerator._add_timing_statistics(
                report_lines, timing_summary, timing_trends, slow_companies
            )
        
        return report_lines