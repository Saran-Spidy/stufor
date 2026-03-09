from flask import Flask, render_template, request, redirect
import sqlite3
from database import init_db

app = Flask(__name__)

init_db()

def calculate_reliability(student_name):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM applications WHERE student_name=? AND status='Completed'", (student_name,))
    completed = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM applications WHERE student_name=? AND status='Cancelled'", (student_name,))
    cancelled = c.fetchone()[0]

    c.execute("SELECT AVG(rating) FROM applications WHERE student_name=? AND status='Completed'", (student_name,))
    avg_rating = c.fetchone()[0]

    if avg_rating is None:
        avg_rating = 0

    score = (completed * 2) + avg_rating - (cancelled * 2)

    conn.close()

    return round(score, 2)

from datetime import datetime

from datetime import datetime

@app.route('/')
def home():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Get active jobs
    c.execute("SELECT * FROM jobs WHERE status='Active'")
    jobs = c.fetchall()

    # Expiry check
    for job in jobs:
        expiry_time = job[5]
        if expiry_time:
            expiry_datetime = datetime.strptime(expiry_time, "%Y-%m-%dT%H:%M")
            if datetime.now() > expiry_datetime:
                c.execute("UPDATE jobs SET status='Closed' WHERE id=?", (job[0],))

    conn.commit()

    # Fetch updated jobs
    c.execute("SELECT * FROM jobs WHERE status='Active'")
    jobs = c.fetchall()

    # Fetch applications
    c.execute("SELECT * FROM applications")
    applications_raw = c.fetchall()

    applications_completed = []
    applications_pending = []

    for app_data in applications_raw:
        student_name = app_data[1]
        job_id = app_data[2]
        status = app_data[3]

        reliability_score = calculate_reliability(student_name)

        # Get student skill
        student_skill = ""

        # Get job title
        c.execute("SELECT title FROM jobs WHERE id=?", (job_id,))
        result = c.fetchone()
        job_title = result[0] if result else ""

        skill_bonus = 0
        if student_skill and job_title and student_skill.lower() in job_title.lower():
            skill_bonus = 5

        final_score = reliability_score + skill_bonus

        new_app = app_data + (final_score,)

        if status == "Completed":
            applications_completed.append(new_app)
        else:
            applications_pending.append(new_app)

    # Sort only completed applications
    applications_completed = sorted(applications_completed, key=lambda x: x[-1], reverse=True)

    # Combine completed first, then pending
    applications = applications_completed + applications_pending

    conn.close()

    return render_template("index.html", jobs=jobs)

@app.route('/register_student', methods=['GET', 'POST'])
def register_student():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        age = request.form['age']
        location = request.form['location']
        college = request.form['college']
        department = request.form['department']
        year = request.form['year']
        experience_level = request.form['experience_level']
        selected_roles = request.form.getlist('roles')

        # Insert student
        c.execute("""
            INSERT INTO users 
            (name, role, age, location, college, department, year, experience_level)
            VALUES (?, 'student', ?, ?, ?, ?, ?, ?)
        """, (name, age, location, college, department, year, experience_level))

        student_id = c.lastrowid

        # Insert selected roles
        for role_id in selected_roles:
            c.execute("INSERT INTO student_roles (student_id, role_id) VALUES (?, ?)",
                      (student_id, role_id))

        conn.commit()
        conn.close()

        return redirect('/')

    # Fetch roles for dropdown
    c.execute("SELECT * FROM roles")
    roles = c.fetchall()
    conn.close()

    print("ROLES FROM DB:", roles)
    return render_template("register_student.html", roles=roles)

@app.route('/register_manager', methods=['GET', 'POST'])
def register_manager():
    if request.method == 'POST':
        name = request.form['name']

        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        c.execute("INSERT INTO users (name, role) VALUES (?, 'manager')", (name,))

        conn.commit()
        conn.close()

        return redirect('/')

    return render_template("register_manager.html")

@app.route('/applications')
def applications_page():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("SELECT * FROM applications WHERE status='Applied'")
    applications_raw = c.fetchall()

    detailed_applications = []

    for app in applications_raw:
        app_id = app[0]
        student_name = app[1]

        # Count completed jobs
        c.execute(
            "SELECT COUNT(*) FROM applications WHERE student_name=? AND status='Completed'",
            (student_name,)
        )
        completed_count = c.fetchone()[0]

        # Average rating
        c.execute(
            "SELECT AVG(rating) FROM applications WHERE student_name=? AND status='Completed'",
            (student_name,)
        )
        avg_rating = c.fetchone()[0]
        if avg_rating is None:
            avg_rating = 0

        reliability_score = calculate_reliability(student_name)
        recommendation_score = reliability_score + (avg_rating * 2) + completed_count

        # Get student id
        c.execute("SELECT id FROM users WHERE name=?", (student_name,))
        user = c.fetchone()

        roles_text = "None"

        if user:
            student_id = user[0]

            c.execute("""
                SELECT roles.role_name
                FROM roles
                JOIN student_roles
                ON roles.id = student_roles.role_id
                WHERE student_roles.student_id=?
            """, (student_id,))

            roles = c.fetchall()

            if roles:
               roles_text = ", ".join([r[0] for r in roles])

        detailed_applications.append({
            "app_id": app_id,
            "student_name": student_name,
            "skill": roles_text,
            "completed_count": completed_count,
            "avg_rating": round(avg_rating, 2),
            "reliability_score": reliability_score,
            "recommendation_score": recommendation_score
        })

    detailed_applications = sorted(
        detailed_applications,
        key=lambda x: x["recommendation_score"],
        reverse=True
    )

    conn.close()

    return render_template("applications.html", applications=detailed_applications)
@app.route('/selected')
def selected_page():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("SELECT * FROM applications WHERE status='Selected'")
    selected = c.fetchall()

    conn.close()

    return render_template("selected.html", selected=selected)

@app.route('/completed')
def completed_page():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("SELECT * FROM applications WHERE status='Completed'")
    completed = c.fetchall()

    conn.close()

    return render_template("completed.html", completed=completed)

@app.route('/ranking')
def ranking_page():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("SELECT DISTINCT student_name FROM applications WHERE status='Completed'")
    students = c.fetchall()

    ranking = []

    for student in students:
        name = student[0]
        score = calculate_reliability(name)
        ranking.append((name, score))

    ranking = sorted(ranking, key=lambda x: x[1], reverse=True)

    conn.close()

    return render_template("ranking.html", ranking=ranking)

# Post Job
@app.route('/post_job', methods=['GET', 'POST'])
def post_job():
    if request.method == 'POST':
        manager_name = request.form['manager_name']

        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        # Check if manager registered
        c.execute("SELECT * FROM users WHERE name=? AND role='manager'", (manager_name,))
        manager = c.fetchone()

        if not manager:
            conn.close()
            return "Manager not registered!"

        title = request.form['title']
        description = request.form['description']
        pay = request.form['pay']
        required_count = request.form['required_count']
        expiry_time = request.form['expiry_time']

        c.execute("""
            INSERT INTO jobs (title, description, pay, required_count, expiry_time)
            VALUES (?, ?, ?, ?, ?)
        """, (title, description, pay, required_count, expiry_time))

        conn.commit()
        conn.close()

        return redirect('/')

    return render_template("post_job.html")

@app.route('/apply/<int:job_id>', methods=['POST'])
def apply(job_id):
    student_name = request.form['student_name']

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Check student exists
    c.execute("SELECT id FROM users WHERE name=? AND role='student'", (student_name,))
    user = c.fetchone()

    if not user:
        conn.close()
        return "Student not registered!"

    student_id = user[0]

    # Get job title
    c.execute("SELECT title FROM jobs WHERE id=?", (job_id,))
    job = c.fetchone()

    if not job:
        conn.close()
        return "Job not found!"

    job_title = job[0]

    # Get role id that matches job title
    c.execute("SELECT id FROM roles WHERE role_name=?", (job_title,))
    role = c.fetchone()

    if role:
        role_id = role[0]

        # Check if student has this role
        c.execute("""
            SELECT *
            FROM student_roles
            WHERE student_id=? AND role_id=?
        """, (student_id, role_id))

        role_match = c.fetchone()

        if not role_match:
            conn.close()
            return "You are not eligible for this job role!"

    # Prevent duplicate application
    c.execute("SELECT * FROM applications WHERE student_name=? AND job_id=?", (student_name, job_id))
    existing_application = c.fetchone()

    if existing_application:
        conn.close()
        return "You already applied for this job!"

    # Insert application
    c.execute(
        "INSERT INTO applications (student_name, job_id) VALUES (?, ?)",
        (student_name, job_id)
    )

    conn.commit()
    conn.close()

    return redirect('/')

@app.route('/complete/<int:application_id>', methods=['POST'])
def complete(application_id):
    rating = request.form['rating']

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Update application as completed and store rating
    c.execute("""
        UPDATE applications 
        SET status='Completed', rating=? 
        WHERE id=?
    """, (rating, application_id))

    conn.commit()
    conn.close()

    return redirect('/')

@app.route('/select/<int:application_id>', methods=['POST'])
def select_candidate(application_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Get job_id of this application
    c.execute("SELECT job_id FROM applications WHERE id=?", (application_id,))
    job = c.fetchone()

    if not job:
        conn.close()
        return redirect('/')

    job_id = job[0]

    # Get required_count
    c.execute("SELECT required_count FROM jobs WHERE id=?", (job_id,))
    required_count = c.fetchone()[0]

    # Count already selected
    c.execute("SELECT COUNT(*) FROM applications WHERE job_id=? AND status='Selected'", (job_id,))
    selected_count = c.fetchone()[0]

    # LIMIT LOGIC (Step 3)
    if selected_count >= required_count:
        conn.close()
        return "Selection limit reached!"

    # Update status to Selected
    c.execute("UPDATE applications SET status='Selected' WHERE id=?", (application_id,))
    conn.commit()
    conn.close()

    return redirect('/')

@app.route('/reliability/<student_name>')
def reliability(student_name):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM applications WHERE student_name=? AND status='Completed'", (student_name,))
    completed = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM applications WHERE student_name=? AND status='Cancelled'", (student_name,))
    cancelled = c.fetchone()[0]

    c.execute("SELECT AVG(rating) FROM applications WHERE student_name=? AND status='Completed'", (student_name,))
    avg_rating = c.fetchone()[0]

    if avg_rating is None:
        avg_rating = 0

    score = (completed * 2) + avg_rating - (cancelled * 2)

    # Classification
    if score >= 20:
        level = "Elite Performer"
    elif score >= 10:
        level = "High Reliability"
    elif score >= 5:
        level = "Moderate"
    else:
        level = "Risky"

    conn.close()

    return f"""
    Reliability Score for {student_name}: {round(score,2)} <br>
    Level: {level}
    """
@app.route('/dashboard')
def dashboard():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Total jobs
    c.execute("SELECT COUNT(*) FROM jobs")
    total_jobs = c.fetchone()[0]

    # Total applications
    c.execute("SELECT COUNT(*) FROM applications")
    total_applications = c.fetchone()[0]

    # Completed jobs
    c.execute("SELECT COUNT(*) FROM applications WHERE status='Completed'")
    completed_jobs = c.fetchone()[0]

    # Get unique students
    c.execute("SELECT DISTINCT student_name FROM applications")
    students = c.fetchall()

    student_scores = []

    for student in students:
        name = student[0]
        score = calculate_reliability(name)
        student_scores.append((name, score))

    student_scores = sorted(student_scores, key=lambda x: x[1], reverse=True)

    conn.close()

    return render_template(
        "dashboard.html",
        total_jobs=total_jobs,
        total_applications=total_applications,
        completed_jobs=completed_jobs,
        student_scores=student_scores[:3]  # Top 3
    )

if __name__ == '__main__':
    app.run(debug=True)
