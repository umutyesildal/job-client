import pandas as pd
from typing import Dict


MOTIVATION_LETTER_TEMPLATE = """Dear Hiring Manager at {company},

I am writing to express my strong interest in the {job_title} position. As a Computer Science student currently based in Berlin, I am excited about the opportunity to contribute to {company}'s innovative work.

I have carefully reviewed the job requirements and believe my skills align well with what you're looking for. {matched_skills_text}

{experience_section}

I am particularly drawn to this position because it offers the opportunity to work with cutting-edge technologies while contributing to real-world projects. As a working student, I am eager to apply my academic knowledge in a practical setting and grow alongside your team.

I would welcome the opportunity to discuss how my skills and enthusiasm can contribute to {company}'s success. Thank you for considering my application.

Best regards,
Umut Yesildal
"""


def generate_matched_skills_text(matched_keywords: str, match_percentage: float) -> str:
    if not matched_keywords or pd.isna(matched_keywords) or matched_keywords.strip() == '':
        return "My diverse technical background and eagerness to learn make me a strong candidate for this role."
    
    keywords = [k.strip() for k in matched_keywords.split(',')]
    
    if len(keywords) == 0:
        return "My diverse technical background and eagerness to learn make me a strong candidate for this role."
    elif len(keywords) <= 3:
        skills_list = ', '.join(keywords)
        return f"My experience with {skills_list} directly relates to the key requirements of this position."
    elif len(keywords) <= 6:
        first_skills = ', '.join(keywords[:3])
        remaining = len(keywords) - 3
        return f"My technical expertise includes {first_skills}, among {remaining} other relevant skills that match this role."
    else:
        first_skills = ', '.join(keywords[:4])
        remaining = len(keywords) - 4
        return f"I bring strong technical skills including {first_skills}, plus {remaining} additional competencies that align well with your requirements."


def generate_experience_section(company: str, job_title: str) -> str:
    return """Through my academic projects and previous experiences, I have developed strong problem-solving skills and the ability to work effectively in fast-paced environments. I am comfortable with agile methodologies and collaborative development practices."""


def generate_motivation_letter(
    company: str,
    job_title: str,
    matched_keywords: str = '',
    match_percentage: float = 0.0,
    custom_experience: str = None
) -> str:
    matched_skills_text = generate_matched_skills_text(matched_keywords, match_percentage)
    experience_section = custom_experience or generate_experience_section(company, job_title)
    
    letter = MOTIVATION_LETTER_TEMPLATE.format(
        company=company,
        job_title=job_title,
        matched_skills_text=matched_skills_text,
        experience_section=experience_section
    )
    
    return letter.strip()


def generate_motivation_letters(
    input_csv: str = 'filtered_student_jobs_matched.csv',
    output_csv: str = 'filtered_student_jobs_final.csv'
):
    print(f"\n✉️  Generating motivation letters from {input_csv}...")
    
    df = pd.read_csv(input_csv)
    print(f"📊 Found {len(df)} jobs to process")
    
    if 'Motivation_Letter' not in df.columns:
        df['Motivation_Letter'] = ''
    
    generated = 0
    skipped = 0
    
    for idx, row in df.iterrows():
        if pd.notna(row.get('Motivation_Letter', '')) and row['Motivation_Letter'].strip() != '':
            skipped += 1
            continue
        
        letter = generate_motivation_letter(
            company=row.get('Company', 'the company'),
            job_title=row.get('Job Title', 'this position'),
            matched_keywords=row.get('Matched_Keywords', ''),
            match_percentage=row.get('Match_Percentage', 0.0)
        )
        
        df.at[idx, 'Motivation_Letter'] = letter
        generated += 1
        
        if generated % 20 == 0:
            print(f"  Generated {generated} letters...")
    
    df.to_csv(output_csv, index=False)
    print(f"\n✅ Done! Generated {generated} letters, skipped {skipped}")
    print(f"💾 Saved to: {output_csv}")


if __name__ == '__main__':
    generate_motivation_letters()
