import pdfplumber
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ── Skill database ──────────────────────────────────────────
SKILLS_DB = [
    "python","java","javascript","html","css","sql","mysql",
    "php","react","nodejs","flask","django","mongodb","git",
    "github","c","c++","machine learning","deep learning",
    "data analysis","excel","power bi","tableau","figma",
    "photoshop","communication","teamwork","leadership",
    "problem solving","project management","agile","scrum",
    "aws","azure","linux","networking","cybersecurity",
    "kotlin","swift","flutter","docker","kubernetes"
]

# ── Job role required skills ─────────────────────────────────
JOB_ROLES = {
    "Web Developer": [
        "html","css","javascript","react","nodejs","git","mysql","php"
    ],
    "Python Developer": [
        "python","flask","django","sql","git","mysql","mongodb","linux"
    ],
    "Data Analyst": [
        "python","sql","excel","power bi","tableau","data analysis","mysql"
    ],
    "Machine Learning Engineer": [
        "python","machine learning","deep learning","sql","git","data analysis"
    ],
    "Android Developer": [
        "kotlin","java","git","mysql","android","flutter"
    ],
    "UI/UX Designer": [
        "figma","photoshop","html","css","communication"
    ],
    "Software Engineer": [
        "python","java","c++","git","sql","problem solving","agile"
    ],
    "Cybersecurity Analyst": [
        "networking","linux","cybersecurity","python","sql"
    ]
}

# ── Extract text from PDF ────────────────────────────────────
def extract_text(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + " "
    return text.lower()

# ── Extract skills from resume text ─────────────────────────
def extract_skills(text):
    found = []
    for skill in SKILLS_DB:
        if skill.lower() in text:
            found.append(skill)
    return found

# ── Calculate match score using TF-IDF ──────────────────────
def calculate_match_score(resume_text, job_role):
    if job_role not in JOB_ROLES:
        return 0, [], []
    
    required_skills = JOB_ROLES[job_role]
    resume_skills   = extract_skills(resume_text)
    
    matched  = [s for s in required_skills if s in resume_skills]
    missing  = [s for s in required_skills if s not in resume_skills]
    
    # TF-IDF cosine similarity
    job_text    = " ".join(required_skills)
    vectorizer  = TfidfVectorizer()
    tfidf       = vectorizer.fit_transform([resume_text, job_text])
    score       = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]
    percentage  = round(score * 100, 2)
    
    return percentage, matched, missing

# ── Resume quality score ─────────────────────────────────────
def calculate_resume_score(text, skills_found):
    score    = 0
    feedback = []

    if len(text) > 300:
        score += 20
    else:
        feedback.append("Your resume is too short. Add more details.")

    if len(skills_found) >= 5:
        score += 25
    elif len(skills_found) >= 3:
        score += 15
        feedback.append("Add more technical skills to strengthen your resume.")
    else:
        feedback.append("Very few skills found. List your technical skills clearly.")

    keywords = ["education","experience","project","skill","certificate"]
    found_kw = [k for k in keywords if k in text]
    score   += len(found_kw) * 10
    if len(found_kw) < 3:
        feedback.append("Make sure your resume has Education, Experience and Skills sections.")

    if "@" in text:
        score += 10
    else:
        feedback.append("Add your email address to your resume.")

    if not feedback:
        feedback.append("Great resume! Well structured and detailed.")

    return min(score, 100), feedback