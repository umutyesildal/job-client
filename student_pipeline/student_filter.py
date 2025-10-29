"""
Student Job Filter Pipeline
Filters jobs from all_jobs.csv for working student positions suitable for Berlin/Germany
"""

import pandas as pd
import logging
import os
import re
from typing import List, Dict, Set
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[
        logging.FileHandler('student_pipeline.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class StudentJobFilter:
    """Filters jobs for working student positions with technical keywords"""
    
    # Technical keywords (hard skills only)
    TECH_KEYWORDS = {
        # Programming Languages
        'python', 'java', 'javascript', 'typescript', 'ruby', 'c++', 'go', 'kotlin', 'swift',
        
        # Frontend
        'react', 'vue.js', 'next.js', 'html', 'css', 'tailwind', 'vite', 'apollo',
        
        # Backend
        'node.js', 'nestjs', 'ruby on rails', 'api', 'rest api', 'graphql', 'websockets',
        
        # Mobile
        'flutter', 'react native', 'android', 'ios',
        
        # Databases
        'sql', 'postgresql', 'mongodb', 'mysql', 'nosql', 'bigquery', 'supabase',
        
        # Cloud & DevOps
        'aws', 'gcp', 'azure', 'docker', 'kubernetes', 'terraform', 'github actions',
        'ci/cd', 'jenkins', 'vercel', 'cloudflare',
        
        # Data & Analytics
        'data analysis', 'data engineering', 'etl', 'airflow', 'dataform', 'looker',
        'tableau', 'power bi', 'bigquery', 'data warehouse', 'bi',
        
        # AI/ML
        'machine learning', 'deep learning', 'nlp', 'bert', 'transformers', 'llm',
        'pytorch', 'tensorflow', 'langchain', 'llamaindex', 'rag',
        
        # Tools & Frameworks
        'git', 'github', 'jira', 'confluence', 'atlassian', 'google workspace',
        'playwright', 'codecov', 'datadog', 'soda core',
        
        # IT/System Admin
        'vpn', 'mdm', 'mobile device management', 'backup', 'google meets',
        'user management', 'hardware', 'infrastructure', 'iac',
        
        # Other Technical
        'automation', 'devops', 'microservices', 'containers', 'serverless',
        'tdd', 'code review', 'deployment', 'monitoring'
    }
    
    # Student job identifiers
    STUDENT_KEYWORDS = {
        'working student', 'werkstudent', 'student researcher',
        'internship', 'praktikum', 'intern'
    }
    
    EXCLUDED_KEYWORDS = {
        'recruiting', 'recruiter', 'recruitment', 'hr', 'human resources',
        'talent acquisition', 'people operations', 'personnel'
    }
    
    LOCATION_KEYWORDS = {
        'berlin', 'germany', 'deutschland', 'de', 'ge', 'remote'
    }
    
    def __init__(self, input_csv: str = '../data/all_jobs.csv', output_csv: str = './filtered_student_jobs.csv'):
        self.input_csv = input_csv
        self.output_csv = output_csv
    
    def _is_student_job(self, job_title: str, employment_type: str) -> bool:
        title_lower = str(job_title).lower() if pd.notna(job_title) else ''
        emp_type_lower = str(employment_type).lower() if pd.notna(employment_type) else ''
        
        for keyword in self.EXCLUDED_KEYWORDS:
            if keyword in title_lower:
                return False
        
        for keyword in self.STUDENT_KEYWORDS:
            if keyword in title_lower:
                return True
        
        if 'parttime' in emp_type_lower or 'part-time' in emp_type_lower:
            if any(word in title_lower for word in ['student', 'werkstudent', 'intern']):
                return True
        
        return False
    
    def _is_valid_location(self, location: str, remote: str) -> bool:
        """Check if location is Berlin/Germany or remote with Germany"""
        location_str = str(location).lower() if pd.notna(location) else ''
        
        if not location_str:
            return False
        
        # Check for location keywords
        for keyword in self.LOCATION_KEYWORDS:
            if keyword in location_str:
                # If remote, must also mention Germany
                if 'remote' in location_str:
                    return any(loc in location_str for loc in ['germany', 'deutschland', 'berlin', 'de'])
                return True
        
        return False
    
    def _extract_tech_keywords(self, job_description: str) -> List[str]:
        """Extract matching technical keywords from job description"""
        desc_str = str(job_description).lower() if pd.notna(job_description) else ''
        
        if not desc_str:
            return []
        
        matched_keywords = []
        
        for keyword in self.TECH_KEYWORDS:
            # Use word boundaries for better matching
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, desc_str):
                matched_keywords.append(keyword)
        
        return matched_keywords
    
    def _calculate_relevance_score(self, matched_keywords: List[str]) -> float:
        """Calculate relevance score based on matched keywords"""
        if not matched_keywords:
            return 0.0
        
        # Weight keywords by category
        category_weights = {
            # High priority - core programming & frameworks
            ('python', 'javascript', 'typescript', 'react', 'vue.js', 'flutter', 'node.js'): 3.0,
            
            # Medium-high priority - data & cloud
            ('data analysis', 'data engineering', 'aws', 'gcp', 'azure', 'sql', 'machine learning'): 2.5,
            
            # Medium priority - tools & DevOps
            ('docker', 'kubernetes', 'git', 'ci/cd', 'terraform', 'automation'): 2.0,
            
            # Lower priority - general tools
            ('jira', 'confluence', 'google workspace'): 1.5,
        }
        
        score = 0.0
        for keyword in matched_keywords:
            weight = 1.0  # Default weight
            for keywords_group, group_weight in category_weights.items():
                if keyword in keywords_group:
                    weight = group_weight
                    break
            score += weight
        
        # Bonus for having multiple keywords
        if len(matched_keywords) >= 5:
            score *= 1.2
        elif len(matched_keywords) >= 3:
            score *= 1.1
        
        return round(score, 2)
    
    def filter_jobs(self) -> pd.DataFrame:
        """Main filtering function"""
        logger.info("\n" + "="*80)
        logger.info("🎓 STUDENT JOB FILTER PIPELINE")
        logger.info("="*80 + "\n")
        
        # Read input CSV
        logger.info(f"📥 Loading jobs from: {self.input_csv}")
        try:
            df = pd.read_csv(self.input_csv)
            logger.info(f"✓ Loaded {len(df)} total jobs\n")
        except FileNotFoundError:
            logger.error(f"❌ File not found: {self.input_csv}")
            return pd.DataFrame()
        
        # Filter step 1: Student jobs
        logger.info("Step 1: Filtering for working student positions...")
        df['is_student_job'] = df.apply(
            lambda row: self._is_student_job(
                row.get('Job Title', ''),
                row.get('Employment Type', '')
            ), axis=1
        )
        student_jobs = df[df['is_student_job']].copy()
        logger.info(f"✓ Found {len(student_jobs)} student jobs\n")
        
        if len(student_jobs) == 0:
            logger.warning("⚠️  No student jobs found!")
            return pd.DataFrame()
        
        # Filter step 2: Location
        logger.info("Step 2: Filtering for Berlin/Germany locations...")
        student_jobs['valid_location'] = student_jobs.apply(
            lambda row: self._is_valid_location(
                row.get('Location', ''),
                row.get('Remote', '')
            ), axis=1
        )
        filtered_jobs = student_jobs[student_jobs['valid_location']].copy()
        logger.info(f"✓ Found {len(filtered_jobs)} jobs in Berlin/Germany\n")
        
        if len(filtered_jobs) == 0:
            logger.warning("⚠️  No jobs found in Berlin/Germany!")
            return pd.DataFrame()
        
        # Filter step 3: Technical keywords
        logger.info("Step 3: Extracting technical keywords and calculating relevance...")
        filtered_jobs['matched_keywords'] = filtered_jobs['Job Description'].apply(
            self._extract_tech_keywords
        )
        filtered_jobs['keyword_count'] = filtered_jobs['matched_keywords'].apply(len)
        filtered_jobs['relevance_score'] = filtered_jobs['matched_keywords'].apply(
            self._calculate_relevance_score
        )
        
        # Sort by relevance score
        filtered_jobs = filtered_jobs.sort_values('relevance_score', ascending=False)
        
        logger.info(f"✓ Scored {len(filtered_jobs)} jobs by relevance\n")
        
        # Prepare output DataFrame
        output_df = pd.DataFrame({
            'Job Title': filtered_jobs['Job Title'],
            'Job Description': filtered_jobs['Job Description'],
            'Job Type': filtered_jobs['Employment Type'],
            'Company': filtered_jobs['Company Name'],
            'Company Description': filtered_jobs.get('Company Description', ''),
            'Job Link': filtered_jobs['Job Link'],
            'Location': filtered_jobs['Location'],
            'Label': filtered_jobs['Label'],
            'Post Date': filtered_jobs.get('Posted Date', ''),
            'Keywords': '',  # Empty for LLM processing later
            'Keyword Count': filtered_jobs['keyword_count'],
            'Relevance Score': filtered_jobs['relevance_score'],
            'Matched Keywords': filtered_jobs['matched_keywords'].apply(lambda x: ', '.join(x))
        })
        
        # Save to CSV
        logger.info(f"💾 Saving filtered jobs to: {self.output_csv}")
        output_df.to_csv(self.output_csv, index=False, encoding='utf-8')
        logger.info(f"✓ Saved {len(output_df)} jobs\n")
        
        # Print summary
        logger.info("="*80)
        logger.info("📊 SUMMARY")
        logger.info("="*80)
        logger.info(f"Total jobs processed:     {len(df)}")
        logger.info(f"Student jobs:             {len(student_jobs)}")
        logger.info(f"Berlin/Germany:           {len(filtered_jobs)}")
        logger.info(f"Final filtered:           {len(output_df)}")
        logger.info(f"Average relevance score:  {output_df['Relevance Score'].mean():.2f}")
        logger.info("="*80 + "\n")
        
        # Print top 10 jobs
        if len(output_df) > 0:
            logger.info("🏆 TOP 10 MOST RELEVANT JOBS:")
            logger.info("-"*80)
            for idx, row in output_df.head(10).iterrows():
                logger.info(f"\n{row['Relevance Score']:.1f} pts | {row['Company']}")
                logger.info(f"  📋 {row['Job Title']}")
                logger.info(f"  📍 {row['Location']}")
                logger.info(f"  🔧 {row['Keyword Count']} keywords matched")
            logger.info("\n" + "="*80)
        
        return output_df


def main():
    """Main entry point"""
    # Get script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Set paths relative to script location
    input_csv = os.path.join(script_dir, '..', 'data', 'all_jobs.csv')
    output_csv = os.path.join(script_dir, 'filtered_student_jobs.csv')
    
    # Run filter
    filter_pipeline = StudentJobFilter(input_csv, output_csv)
    filtered_df = filter_pipeline.filter_jobs()
    
    if len(filtered_df) > 0:
        logger.info("✅ Pipeline completed successfully!")
    else:
        logger.warning("⚠️  No jobs matched the filters")


if __name__ == "__main__":
    main()
