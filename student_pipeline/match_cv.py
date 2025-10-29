import pandas as pd
import json
from typing import List, Dict, Set


def load_cv_keywords(cv_file: str = 'cv_keywords.json') -> Dict[str, any]:
    try:
        with open(cv_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"⚠️  CV file not found: {cv_file}")
        print("Creating template file...")
        
        template = {
            "cv_id": "umut_cv_2025",
            "keywords": ["Python", "JavaScript", "TypeScript", "React", "Node.js", "SQL", "Git", "Docker", "AWS", "Machine Learning"]
        }
        
        with open(cv_file, 'w', encoding='utf-8') as f:
            json.dump(template, f, indent=2)
        
        print(f"✅ Created template: {cv_file}")
        print("Please update it with your actual skills!")
        return template


def normalize_keyword(keyword: str) -> str:
    return keyword.lower().strip()


def extract_keywords_from_string(keywords_str: str) -> Set[str]:
    if pd.isna(keywords_str) or keywords_str == '':
        return set()
    keywords = [normalize_keyword(k) for k in keywords_str.split(',')]
    return set(k for k in keywords if k)


def calculate_match(job_keywords: Set[str], cv_keywords: Set[str]) -> Dict:
    if not job_keywords:
        return {
            'matched_keywords': [],
            'match_count': 0,
            'job_keyword_count': 0,
            'match_percentage': 0.0
        }
    
    matched = job_keywords.intersection(cv_keywords)
    
    return {
        'matched_keywords': sorted(list(matched)),
        'match_count': len(matched),
        'job_keyword_count': len(job_keywords),
        'match_percentage': round((len(matched) / len(job_keywords)) * 100, 1) if job_keywords else 0.0
    }


def match_cv_with_jobs(
    input_csv: str = 'filtered_student_jobs.csv',
    output_csv: str = 'filtered_student_jobs_matched.csv',
    cv_file: str = 'cv_keywords.json'
):
    print(f"\n🎯 Matching CV with jobs from {input_csv}...")
    
    cv_data = load_cv_keywords(cv_file)
    cv_keywords = set(normalize_keyword(k) for k in cv_data['keywords'])
    cv_id = cv_data['cv_id']
    
    print(f"📄 Loaded CV: {cv_id}")
    print(f"🔑 CV Keywords ({len(cv_keywords)}): {', '.join(sorted(list(cv_keywords))[:10])}...")
    
    df = pd.read_csv(input_csv)
    print(f"📊 Found {len(df)} jobs to match")
    
    if 'CV_ID' not in df.columns:
        df['CV_ID'] = ''
    if 'Match_Percentage' not in df.columns:
        df['Match_Percentage'] = 0.0
    if 'Match_Count' not in df.columns:
        df['Match_Count'] = 0
    if 'Matched_Keywords' not in df.columns:
        df['Matched_Keywords'] = ''
    
    for idx, row in df.iterrows():
        job_keywords_str = row.get('Matched Keywords', '')
        if pd.isna(job_keywords_str) or job_keywords_str == '':
            job_keywords_str = row.get('Keywords', '')
        
        if isinstance(job_keywords_str, str):
            if job_keywords_str.startswith('[') and job_keywords_str.endswith(']'):
                import ast
                job_keywords_list = ast.literal_eval(job_keywords_str)
                job_keywords = set(normalize_keyword(k) for k in job_keywords_list)
            else:
                job_keywords = extract_keywords_from_string(job_keywords_str)
        else:
            job_keywords = set()
        
        match_result = calculate_match(job_keywords, cv_keywords)
        
        df.at[idx, 'CV_ID'] = cv_id
        df.at[idx, 'Match_Percentage'] = match_result['match_percentage']
        df.at[idx, 'Match_Count'] = match_result['match_count']
        df.at[idx, 'Matched_Keywords'] = ', '.join(match_result['matched_keywords'])
        
        if (idx + 1) % 20 == 0:
            print(f"  Processed {idx + 1}/{len(df)} jobs...")
    
    df = df.sort_values('Match_Percentage', ascending=False)
    df.to_csv(output_csv, index=False)
    
    print(f"\n✅ Done!")
    print(f"💾 Saved to: {output_csv}")
    print(f"\n📊 Match Statistics:")
    print(f"  • High match (>50%): {len(df[df['Match_Percentage'] > 50])} jobs")
    print(f"  • Medium match (30-50%): {len(df[(df['Match_Percentage'] >= 30) & (df['Match_Percentage'] <= 50)])} jobs")
    print(f"  • Low match (<30%): {len(df[df['Match_Percentage'] < 30])} jobs")
    print(f"  • Average match: {df['Match_Percentage'].mean():.1f}%")
    print(f"\n🏆 Top 5 Matches:")
    for idx, row in df.head(5).iterrows():
        print(f"  {row['Match_Percentage']:.1f}% - {row['Job Title'][:50]} @ {row['Company']}")


if __name__ == '__main__':
    match_cv_with_jobs()
