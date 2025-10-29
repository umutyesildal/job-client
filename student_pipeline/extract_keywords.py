import os
import pandas as pd
import google.generativeai as genai
from dotenv import load_dotenv
import time
from typing import List

load_dotenv()
genai.configure(api_key=os.getenv('GEMINI'))
model = genai.GenerativeModel('gemini-2.0-flash-exp')

KEYWORD_EXTRACTION_PROMPT = """You are a technical recruiter analyzing job descriptions for a Computer Science/Software Engineering student.

Extract ONLY relevant technical keywords and meaningful skills from this job description. Focus on:
- Programming languages (Python, JavaScript, Java, C++, etc.)
- Frameworks and libraries (React, Django, TensorFlow, etc.)
- Tools and platforms (Git, Docker, AWS, Kubernetes, etc.)
- Technologies (REST API, GraphQL, microservices, etc.)
- Technical domains (Machine Learning, DevOps, Data Engineering, etc.)
- Relevant soft skills (ONLY: problem-solving, analytical thinking, communication with stakeholders - NOT generic teamwork/multitasking)

EXCLUDE generic terms like: teamwork, multitasking, time management, flexibility, adaptability, organization

Return ONLY a comma-separated list of keywords. Be concise and specific.

Job Title: {job_title}

Job Description:
{job_description}

Keywords:"""


def extract_keywords_with_gemini(job_title: str, job_description: str, retry_count: int = 3) -> str:
    if not job_description or pd.isna(job_description) or job_description.strip() == '':
        return ''
    
    if len(job_description) > 8000:
        job_description = job_description[:8000] + "..."
    
    prompt = KEYWORD_EXTRACTION_PROMPT.format(
        job_title=job_title,
        job_description=job_description
    )
    
    for attempt in range(retry_count):
        try:
            response = model.generate_content(prompt)
            keywords = response.text.strip().replace('\n', ', ').replace('  ', ' ')
            return keywords
        except Exception as e:
            print(f"  ⚠️  Attempt {attempt + 1} failed: {e}")
            if attempt < retry_count - 1:
                time.sleep(2 ** attempt)
    
    return ''


def process_jobs(input_csv: str = 'filtered_student_jobs.csv', output_csv: str = 'filtered_student_jobs_with_keywords.csv'):
    print(f"\n🔑 Extracting keywords from {input_csv}...")
    
    df = pd.read_csv(input_csv)
    print(f"📊 Found {len(df)} jobs to process")
    
    if 'Keywords' not in df.columns:
        df['Keywords'] = ''
    
    processed = 0
    skipped = 0
    
    for idx, row in df.iterrows():
        if pd.notna(row.get('Keywords', '')) and row['Keywords'] != '':
            skipped += 1
            continue
        
        print(f"\n[{idx + 1}/{len(df)}] Processing: {row['Job Title'][:50]}...")
        
        keywords = extract_keywords_with_gemini(
            job_title=row['Job Title'],
            job_description=row.get('Job Description', '')
        )
        
        df.at[idx, 'Keywords'] = keywords
        processed += 1
        
        preview = keywords[:100] + '...' if len(keywords) > 100 else keywords
        print(f"  ✅ Keywords: {preview}")
        
        if processed % 10 == 0:
            print(f"  💤 Processed {processed} jobs, sleeping for 2s...")
            time.sleep(2)
        else:
            time.sleep(0.5)
    
    df.to_csv(output_csv, index=False)
    print(f"\n✅ Done! Processed {processed} jobs, skipped {skipped}")
    print(f"💾 Saved to: {output_csv}")


if __name__ == '__main__':
    process_jobs()
