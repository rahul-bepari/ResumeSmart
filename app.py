from flask import Flask, render_template, request, redirect, url_for, session
from engine import extract_text, extract_skills, calculate_match_score, calculate_resume_score
import pymysql
import os
import google.generativeai as genai


app = Flask(__name__)
app.secret_key = "resumesmart_secret_key"
# Configure Gemini AI
genai.configure(api_key="AIzaSyBkBv2ZmdZlt8DJ9_bREMUh_oXNU0tNsk0")
gemini_model = genai.GenerativeModel('gemini-1.5-flash')


# Database connection


def get_db():
    host = os.environ.get("DB_HOST", "localhost")
    user = os.environ.get("DB_USER", "root")
    password = os.environ.get("DB_PASSWORD", "")
    database = os.environ.get("DB_NAME", "resumesmart")
    port = int(os.environ.get("DB_PORT", 3306))
    
    if host == "localhost":
        return pymysql.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            port=port
        )
    else:
        return pymysql.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            port=port,
            ssl_verify_cert=False,
            ssl_verify_identity=False
        )

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form["full_name"]
        email = request.form["email"]
        password = request.form["password"]
        
        db = get_db()
        cursor = db.cursor()
        try:
            cursor.execute("INSERT INTO users (full_name, email, password) VALUES (%s, %s, %s)",
                         (full_name, email, password))
            db.commit()
            return redirect(url_for("login"))
        except:
            return render_template("register.html", error="Email already exists!")
        finally:
            db.close()
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE email=%s AND password=%s", (email, password))
        user = cursor.fetchone()
        db.close()
        
        if user:
            session["user_id"] = user[0]
            session["user_name"] = user[1]
            return redirect(url_for("dashboard"))
        else:
            return render_template("login.html", error="Invalid email or password!")
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html", name=session["user_name"])

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))
@app.route("/upload", methods=["GET", "POST"])
def upload():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        file = request.files["resume"]
        job_role = request.form["job_role"]
        if file.filename == "":
            return render_template("upload.html", error="Please select a file!")
        filepath = os.path.join("uploads", file.filename)
        file.save(filepath)
        # Extract text
        text = extract_text(filepath)
        # Get skills
        skills_found = extract_skills(text)
        # Calculate scores
        match_score, matched, missing = calculate_match_score(text, job_role)
        resume_score, feedback = calculate_resume_score(text, skills_found)
        # Save to database
        db = get_db()
        cursor = db.cursor()
        cursor.execute("INSERT INTO resumes (user_id, filename, extracted_text) VALUES (%s, %s, %s)",
                      (session["user_id"], file.filename, text))
        db.commit()
        resume_id = cursor.lastrowid
        cursor.execute("""INSERT INTO scan_results 
                         (user_id, resume_id, job_role, match_score, matched_skills, missing_skills, resume_score, feedback)
                         VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                      (session["user_id"], resume_id, job_role,
                       match_score,
                       ", ".join(matched),
                       ", ".join(missing),
                       resume_score,
                       ", ".join(feedback)))
        db.commit()
        db.close()
        return render_template("results.html",
                             job_role=job_role,
                             match_score=match_score,
                             matched_skills=matched,
                             missing_skills=missing,
                             resume_score=resume_score,
                             feedback=feedback)
    return render_template("upload.html")

@app.route("/analyze")
def analyze():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return redirect(url_for("upload"))

@app.route("/skillgap")
def skillgap():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return redirect(url_for("upload"))

@app.route("/resumescore")
def resumescore():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return redirect(url_for("upload"))
@app.route("/history")
def history():
    if "user_id" not in session:
        return redirect(url_for("login"))
    db = get_db()
    cursor = db.cursor(pymysql.cursors.DictCursor)
    cursor.execute("""
        SELECT sr.*, r.filename 
        FROM scan_results sr 
        JOIN resumes r ON sr.resume_id = r.id 
        WHERE sr.user_id = %s 
        ORDER BY sr.scanned_at DESC
    """, (session["user_id"],))
    results = cursor.fetchall()
    db.close()
    return render_template("history.html", results=results)

@app.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect(url_for("login"))
    db = get_db()
    cursor = db.cursor(pymysql.cursors.DictCursor)
    
    # Get user info
    cursor.execute("SELECT * FROM users WHERE id = %s", (session["user_id"],))
    user = cursor.fetchone()
    
    # Get total scans
    cursor.execute("SELECT COUNT(*) as total FROM scan_results WHERE user_id = %s", (session["user_id"],))
    total_scans = cursor.fetchone()["total"]
    
    # Get average match score
    cursor.execute("SELECT AVG(match_score) as avg_match FROM scan_results WHERE user_id = %s", (session["user_id"],))
    avg_result = cursor.fetchone()
    avg_match = round(avg_result["avg_match"], 2) if avg_result["avg_match"] else 0
    
    # Get best match score
    cursor.execute("SELECT MAX(match_score) as best FROM scan_results WHERE user_id = %s", (session["user_id"],))
    best_result = cursor.fetchone()
    best_score = round(best_result["best"], 2) if best_result["best"] else 0
    
    # Get average resume score
    cursor.execute("SELECT AVG(resume_score) as avg_resume FROM scan_results WHERE user_id = %s", (session["user_id"],))
    avg_resume_result = cursor.fetchone()
    avg_resume = round(avg_resume_result["avg_resume"], 2) if avg_resume_result["avg_resume"] else 0

    # Get recent scans
    cursor.execute("""
        SELECT sr.*, r.filename 
        FROM scan_results sr 
        JOIN resumes r ON sr.resume_id = r.id 
        WHERE sr.user_id = %s 
        ORDER BY sr.scanned_at DESC LIMIT 3
    """, (session["user_id"],))
    recent_scans = cursor.fetchall()
    db.close()
    
    return render_template("profile.html",
                         user=user,
                         total_scans=total_scans,
                         avg_match=avg_match,
                         best_score=best_score,
                         avg_resume=avg_resume,
                         recent_scans=recent_scans)

@app.route("/chat", methods=["POST"])
def chat():
    if "user_id" not in session:
        return {"error": "Not logged in"}, 401
    
    user_message = request.json.get("message", "")
    
    system_prompt = """You are ResumeSmart Career Assistant, a helpful AI career advisor. 
    You help job seekers with:
    - Resume writing tips
    - Skill improvement advice
    - Career guidance
    - Job search strategies
    - Interview preparation
    Keep responses short, friendly and practical. Maximum 3-4 sentences."""
    
    full_prompt = f"{system_prompt}\n\nUser: {user_message}\nAssistant:"
    
    response = gemini_model.generate_content(full_prompt)
    return {"reply": response.text}

if __name__ == "__main__":
    app.run(debug=True)