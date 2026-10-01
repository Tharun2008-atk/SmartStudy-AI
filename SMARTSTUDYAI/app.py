from flask import Flask, render_template, request, redirect, url_for, session, send_file
import sqlite3
import os
from functools import wraps

from dotenv import load_dotenv
from groq import Groq
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash

import PyPDF2

from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
from flask import send_file
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

# =========================================================
# FLASK APP
# =========================================================

app = Flask(__name__)

# Use an environment variable in production.
app.secret_key = os.getenv("SECRET_KEY", "smartstudyai123")


# =========================================================
# UPLOAD FOLDER
# =========================================================

UPLOAD_FOLDER = "uploads"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# =========================================================
# GROQ AI SETUP
# =========================================================

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY missing in .env file")

client = Groq(api_key=GROQ_API_KEY)


# =========================================================
# AI FUNCTION
# =========================================================

def ask_ai(prompt):
    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.7,
        max_tokens=2000
    )

    return response.choices[0].message.content


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


# =========================================================
# CREATE DATABASE TABLES
# =========================================================

def create_table():

    conn = get_db_connection()

    # -----------------------------------------------------
    # Users
    # -----------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fullname TEXT NOT NULL,
            email TEXT UNIQUE,
            username TEXT UNIQUE,
            password TEXT NOT NULL
        )
    """)

    # -----------------------------------------------------
    # Attendance
    # -----------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            total_classes INTEGER NOT NULL,
            attended_classes INTEGER NOT NULL
        )
    """)

    # -----------------------------------------------------
    # Chat History
    # -----------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # -----------------------------------------------------
    # Notes History
    # -----------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS notes_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            topic TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # -----------------------------------------------------
    # Quiz History
    # -----------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS quiz_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            topic TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # -----------------------------------------------------
    # PDF History
    # -----------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS pdf_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            filename TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


create_table()


# =========================================================
# LOGIN REQUIRED DECORATOR
# =========================================================

def login_required(f):

    @wraps(f)
    def decorated_function(*args, **kwargs):

        if "username" not in session:
            return redirect(url_for("login"))

        return f(*args, **kwargs)

    return decorated_function


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():
    return render_template("index.html")


# =========================================================
# REGISTER
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        fullname = request.form.get("fullname", "").strip()
        email = request.form.get("email", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not fullname or not email or not username or not password:
            return render_template(
                "register.html",
                error="All fields are required."
            )

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()

        try:

            conn.execute(
                """
                INSERT INTO users
                (fullname, email, username, password)
                VALUES (?, ?, ?, ?)
                """,
                (
                    fullname,
                    email,
                    username,
                    hashed_password
                )
            )

            conn.commit()

        except sqlite3.IntegrityError:

            conn.rollback()

            return render_template(
                "register.html",
                error="Email or username already exists."
            )

        finally:

            conn.close()

        return redirect(url_for("login"))

    return render_template("register.html")


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        conn = get_db_connection()

        user = conn.execute(
            """
            SELECT *
            FROM users
            WHERE username = ?
            """,
            (username,)
        ).fetchone()

        conn.close()

        if user and check_password_hash(
            user["password"],
            password
        ):

            session.clear()
            session["username"] = username

            return redirect(url_for("dashboard"))

        return render_template(
            "login.html",
            error="Invalid username or password."
        )

    return render_template("login.html")


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
@login_required
def dashboard():

    username = session["username"]

    conn = get_db_connection()

    # -----------------------------------------------------
    # User
    # -----------------------------------------------------

    user = conn.execute(
        """
        SELECT id, fullname, email, username
        FROM users
        WHERE username = ?
        """,
        (username,)
    ).fetchone()

    if not user:

        conn.close()
        session.clear()

        return redirect(url_for("login"))

    # -----------------------------------------------------
    # Chat Count
    # -----------------------------------------------------

    chats = conn.execute(
        """
        SELECT COUNT(*)
        FROM chat_history
        WHERE username = ?
        """,
        (username,)
    ).fetchone()[0]

    # -----------------------------------------------------
    # Notes Count
    # -----------------------------------------------------

    notes = conn.execute(
        """
        SELECT COUNT(*)
        FROM notes_history
        WHERE username = ?
        """,
        (username,)
    ).fetchone()[0]

    # -----------------------------------------------------
    # Quiz Count
    # -----------------------------------------------------

    quizzes = conn.execute(
        """
        SELECT COUNT(*)
        FROM quiz_history
        WHERE username = ?
        """,
        (username,)
    ).fetchone()[0]

    # -----------------------------------------------------
    # PDF Count
    # -----------------------------------------------------

    pdfs = conn.execute(
        """
        SELECT COUNT(*)
        FROM pdf_history
        WHERE username = ?
        """,
        (username,)
    ).fetchone()[0]

    # -----------------------------------------------------
    # Latest Attendance
    # -----------------------------------------------------

    attendance_data = conn.execute(
        """
        SELECT total_classes, attended_classes
        FROM attendance
        WHERE username = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (username,)
    ).fetchone()

    if (
        attendance_data
        and attendance_data["total_classes"] > 0
    ):

        attendance = round(
            (
                attendance_data["attended_classes"]
                / attendance_data["total_classes"]
            ) * 100,
            2
        )

    else:

        attendance = 0

    # -----------------------------------------------------
    # Recent Chats
    # -----------------------------------------------------

    recent_chats = conn.execute(
        """
        SELECT question, created_at
        FROM chat_history
        WHERE username = ?
        ORDER BY id DESC
        LIMIT 5
        """,
        (username,)
    ).fetchall()

    # -----------------------------------------------------
    # Recent Notes
    # -----------------------------------------------------

    recent_notes = conn.execute(
        """
        SELECT topic, created_at
        FROM notes_history
        WHERE username = ?
        ORDER BY id DESC
        LIMIT 5
        """,
        (username,)
    ).fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        user=user,
        chats=chats,
        notes=notes,
        quizzes=quizzes,
        pdfs=pdfs,
        attendance=attendance,
        recent_chats=recent_chats,
        recent_notes=recent_notes
    )


# =========================================================
# AI CHATBOT
# =========================================================

@app.route("/chatbot", methods=["GET", "POST"])
@login_required
def chatbot():

    answer = ""

    if request.method == "POST":

        question = request.form.get(
            "question",
            ""
        ).strip()

        if not question:

            answer = "Please enter a question."

        else:

            try:

                answer = ask_ai(question)

                conn = get_db_connection()

                conn.execute(
                    """
                    INSERT INTO chat_history
                    (username, question, answer)
                    VALUES (?, ?, ?)
                    """,
                    (
                        session["username"],
                        question,
                        answer
                    )
                )

                conn.commit()
                conn.close()

            except Exception as e:

                print("Chatbot Error:", e)

                answer = "AI service error. Please try again."

    return render_template(
        "chatbot.html",
        answer=answer
    )


# =========================================================
# CHAT HISTORY
# =========================================================

@app.route("/history")
@login_required
def history():

    conn = get_db_connection()

    chats = conn.execute(
        """
        SELECT question, answer, created_at
        FROM chat_history
        WHERE username = ?
        ORDER BY id DESC
        """,
        (session["username"],)
    ).fetchall()

    conn.close()

    return render_template(
        "history.html",
        chats=chats
    )
# =========================================================
# AI QUIZ GENERATOR
# =========================================================

@app.route("/quiz", methods=["GET", "POST"])
@login_required
def quiz():

    quiz = ""
    topic = ""

    if request.method == "POST":

        topic = request.form.get(
            "topic",
            ""
        ).strip()

        if not topic:

            quiz = "Please enter a topic."

        else:

            prompt = f"""
You are SmartStudy AI, an educational assistant
for diploma students.

Create an exam-friendly multiple-choice quiz
about the following topic:

TOPIC:
{topic}

IMPORTANT RULES:

1. Create exactly 10 questions.
2. Every question must have exactly 4 options.
3. Options must be A, B, C and D.
4. Give exactly one correct answer.
5. Questions must be suitable for diploma students.
6. Use simple and clear English.
7. Include basic, intermediate and conceptual questions.
8. Do not use Markdown.
9. Do not use #, ##, ###, **, or backticks.
10. Stay strictly related to the requested topic.

Use EXACTLY this format:

Q1. Question text

A) Option text
B) Option text
C) Option text
D) Option text

Correct Answer: A

Q2. Question text

A) Option text
B) Option text
C) Option text
D) Option text

Correct Answer: B

Continue until Q10.

TOPIC:
{topic}
"""

            try:

                quiz = ask_ai(prompt)

                session["latest_quiz"] = quiz
                session["latest_quiz_topic"] = topic

                conn = get_db_connection()

                conn.execute(
                    """
                    INSERT INTO quiz_history
                    (username, topic)
                    VALUES (?, ?)
                    """,
                    (
                        session["username"],
                        topic
                    )
                )

                conn.commit()
                conn.close()

            except Exception as e:

                print("Quiz Error:", e)

                quiz = "Unable to generate quiz right now."

    return render_template(
        "quiz.html",
        quiz=quiz,
        topic=topic
    )

# =========================================================
# AI PDF SUMMARIZER
# =========================================================

@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():

    summary = ""

    if request.method == "POST":

        pdf = request.files.get("pdf")

        # -------------------------------------------------
        # CHECK FILE
        # -------------------------------------------------

        if not pdf or pdf.filename == "":
            return render_template(
                "upload.html",
                summary="Please select a PDF file."
            )

        filename = secure_filename(pdf.filename)

        # -------------------------------------------------
        # CHECK EXTENSION
        # -------------------------------------------------

        if not filename.lower().endswith(".pdf"):

            return render_template(
                "upload.html",
                summary="Only PDF files are allowed."
            )

        # -------------------------------------------------
        # SAVE PDF
        # -------------------------------------------------

        filepath = os.path.join(
            app.config["UPLOAD_FOLDER"],
            filename
        )

        try:

            pdf.save(filepath)

            # -------------------------------------------------
            # EXTRACT TEXT FROM PDF
            # -------------------------------------------------

            text = ""

            with open(filepath, "rb") as file:

                reader = PyPDF2.PdfReader(file)

                for page in reader.pages:

                    content = page.extract_text()

                    if content:

                        text += content + "\n"


            # -------------------------------------------------
            # CHECK EXTRACTED TEXT
            # -------------------------------------------------

            if not text.strip():

                summary = (
                    "Could not extract text from this PDF. "
                    "The PDF may contain scanned images instead of text."
                )

            else:

                # -------------------------------------------------
                # LIMIT VERY LARGE PDF TEXT
                # -------------------------------------------------

                max_chars = 30000

                pdf_text = text[:max_chars]


                # -------------------------------------------------
                # AI PROMPT
                # -------------------------------------------------

                prompt = f"""
You are SmartStudy AI, an educational assistant
for diploma students.

Analyze the following PDF content and create a
clear, simple and exam-friendly summary.

IMPORTANT RULES:

1. Use simple English.
2. Focus only on information present in the PDF.
3. Do not invent information.
4. Do not use Markdown symbols such as #, ##, ###, **,
   or triple backticks.
5. Use simple headings.
6. Use bullet points where useful.
7. Keep the summary compact but informative.
8. Highlight important definitions and concepts.
9. Make the summary useful for exam preparation.
10. Do not discuss information unrelated to the PDF.

Use exactly this structure:

📚 MAIN TOPIC
Give the main topic of the PDF.

📌 IMPORTANT DEFINITIONS
List the important definitions from the PDF.

🧠 IMPORTANT CONCEPTS
Explain the major concepts in simple language.

🔹 KEY POINTS
Give the most important points for studying.

⚙️ IMPORTANT PROCESSES
Explain important processes or steps if present.

⭐ EXAM POINTS
Give the points most useful for exam revision.

📝 QUICK REVISION
Give a short revision summary.

🎯 CONCLUSION
Give a short conclusion.

PDF CONTENT:

{pdf_text}
"""


                # -------------------------------------------------
                # ASK AI
                # -------------------------------------------------

                summary = ask_ai(prompt)


                # -------------------------------------------------
                # SAVE HISTORY
                # -------------------------------------------------

                conn = get_db_connection()

                conn.execute(
                    """
                    INSERT INTO pdf_history
                    (username, filename)
                    VALUES (?, ?)
                    """,
                    (
                        session["username"],
                        filename
                    )
                )

                conn.commit()
                conn.close()


        except Exception as e:

            print("PDF Error:", e)

            summary = (
                "PDF processing failed. "
                "Please try another PDF."
            )


    # -------------------------------------------------
    # SHOW PAGE
    # -------------------------------------------------

    return render_template(
        "upload.html",
        summary=summary
    )
# =========================================================
# QUIZ GENERATOR
# =========================================================




# =========================================================
# NOTES GENERATOR
# =========================================================

@app.route("/notes", methods=["GET", "POST"])
@login_required
def notes():

    notes = ""
    topic = ""

    if request.method == "POST":

        topic = request.form.get(
            "topic",
            ""
        ).strip()

        if not topic:

            notes = "Please enter a topic."

        else:

            prompt = f"""
You are SmartStudy AI, an educational assistant
for diploma students.

Create high-quality, exam-friendly study notes about:

TOPIC: {topic}

IMPORTANT RULES:

1. Use simple English.
2. Make the notes clear and easy to study.
3. Do not use Markdown symbols such as #, ##, ###, **, *, or ```.
4. Do not use tables.
5. Use emojis only where they improve readability.
6. Keep the structure clean.
7. Give enough explanation for diploma-level students.
8. Avoid unnecessary introduction.
9. Do not write about any topic other than the requested topic.

Use exactly this structure:

📚 TOPIC
Write the topic name.

📌 DEFINITION
Give a clear definition.

🧠 EXPLANATION
Explain the topic in simple language.

🔹 MAIN CONCEPTS
Give the important concepts as separate bullet points.

⚙️ HOW IT WORKS
Explain the working or process step-by-step if applicable.

💡 EXAMPLES
Give at least 2 easy examples.

✅ ADVANTAGES
Give important advantages.

❌ DISADVANTAGES
Give important disadvantages.

⭐ IMPORTANT POINTS
Give the most important exam points.

📝 EXAM SUMMARY
Give a short revision summary.

🎯 CONCLUSION
Give a short conclusion.

Make the output visually clean and well organized.

TOPIC:
{topic}
"""

            try:

                notes = ask_ai(prompt)

                session["latest_notes"] = notes
                session["latest_notes_topic"] = topic

                conn = get_db_connection()

                conn.execute(
                    """
                    INSERT INTO notes_history
                    (username, topic)
                    VALUES (?, ?)
                    """,
                    (
                        session["username"],
                        topic
                    )
                )

                conn.commit()
                conn.close()

            except Exception as e:

                print("Notes Error:", e)

                notes = "Unable to generate notes right now."

    return render_template(
        "notes.html",
        notes=notes,
        topic=topic
    )
#downloadnotes#
@app.route("/download_notes")
@login_required
def download_notes():

    # Get latest notes from session
    notes = session.get("latest_notes", "")
    topic = session.get("latest_notes_topic", "Study Notes")

    # If there are no notes
    if not notes:
        return redirect(url_for("notes"))

    # Create PDF in memory
    pdf_buffer = BytesIO()

    document = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=45,
        bottomMargin=45
    )

    styles = getSampleStyleSheet()

    # Title style
    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Title"],
        fontSize=20,
        leading=24,
        alignment=TA_CENTER,
        spaceAfter=15
    )

    # Topic style
    topic_style = ParagraphStyle(
        "TopicStyle",
        parent=styles["Heading2"],
        fontSize=14,
        leading=18,
        spaceAfter=12
    )

    # Section heading
    heading_style = ParagraphStyle(
        "HeadingStyle",
        parent=styles["Heading2"],
        fontSize=13,
        leading=17,
        spaceBefore=12,
        spaceAfter=7
    )

    # Normal text
    body_style = ParagraphStyle(
        "BodyStyle",
        parent=styles["BodyText"],
        fontSize=10.5,
        leading=16,
        spaceAfter=6
    )

    # Bullet text
    bullet_style = ParagraphStyle(
        "BulletStyle",
        parent=styles["BodyText"],
        fontSize=10.5,
        leading=15,
        leftIndent=15,
        firstLineIndent=-8,
        spaceAfter=4
    )

    story = []

    # PDF title
    story.append(
        Paragraph(
            "SmartStudy AI",
            title_style
        )
    )

    story.append(
        Paragraph(
            "AI Generated Study Notes",
            topic_style
        )
    )

    story.append(
        Paragraph(
            f"<b>Topic:</b> {topic}",
            body_style
        )
    )

    story.append(Spacer(1, 10))

    # Process notes line by line
    for line in notes.split("\n"):

        line = line.strip()

        if not line:
            story.append(Spacer(1, 6))
            continue

        # Remove Markdown if AI accidentally produces it
        clean_line = (
            line
            .replace("###", "")
            .replace("##", "")
            .replace("#", "")
            .replace("**", "")
            .replace("`", "")
        )

        # Section headings
        if clean_line.startswith(
            (
                "📚",
                "📌",
                "🧠",
                "🔹",
                "⚙️",
                "💡",
                "✅",
                "❌",
                "⭐",
                "📝",
                "🎯"
            )
        ):

            story.append(
                Paragraph(
                    clean_line,
                    heading_style
                )
            )

        # Bullet points
        elif clean_line.startswith("•"):

            text = clean_line[1:].strip()

            story.append(
                Paragraph(
                    f"• {text}",
                    bullet_style
                )
            )

        elif clean_line.startswith("-"):

            text = clean_line[1:].strip()

            story.append(
                Paragraph(
                    f"• {text}",
                    bullet_style
                )
            )

        else:

            story.append(
                Paragraph(
                    clean_line,
                    body_style
                )
            )

    # Build PDF
    document.build(story)

    # Move buffer to beginning
    pdf_buffer.seek(0)

    # Safe filename
    safe_topic = "".join(
        c for c in topic
        if c.isalnum() or c in (" ", "_", "-")
    ).strip()

    if not safe_topic:
        safe_topic = "Study_Notes"

    filename = f"SmartStudy_AI_{safe_topic}.pdf"

    return send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename
    )
# =========================================================
# ATTENDANCE
# =========================================================
@app.route("/attendance", methods=["GET", "POST"])
@login_required
def attendance():

    percentage = None
    total = ""
    attended = ""
    error = ""

    if request.method == "POST":

        # Get values from form
        total = request.form.get("total", "").strip()
        attended = request.form.get("attended", "").strip()

        try:

            total_classes = int(total)
            attended_classes = int(attended)

            # Validation
            if total_classes <= 0:

                error = "Total classes must be greater than 0."

            elif attended_classes < 0:

                error = "Attended classes cannot be negative."

            elif attended_classes > total_classes:

                error = (
                    "Attended classes cannot be greater "
                    "than total classes."
                )

            else:

                # Calculate percentage
                percentage = round(
                    (attended_classes / total_classes) * 100,
                    2
                )

                # Save valid attendance to database
                conn = get_db_connection()

                conn.execute(
                    """
                    INSERT INTO attendance
                    (
                        username,
                        total_classes,
                        attended_classes
                    )
                    VALUES (?, ?, ?)
                    """,
                    (
                        session["username"],
                        total_classes,
                        attended_classes
                    )
                )

                conn.commit()
                conn.close()

        except (ValueError, TypeError):

            error = "Please enter valid numbers."

    return render_template(
        "attendance.html",
        percentage=percentage,
        total=total,
        attended=attended,
        error=error
    )
# =========================================================
# AI FLASHCARD GENERATOR
# =========================================================

@app.route("/flashcards", methods=["GET", "POST"])
@login_required
def flashcards():

    flashcards = ""
    topic = ""

    if request.method == "POST":

        topic = request.form.get(
            "topic",
            ""
        ).strip()

        if not topic:

            flashcards = "Please enter a topic."

        else:

            prompt = f"""
You are SmartStudy AI, an educational assistant
for diploma students.

Create exactly 15 study flashcards about:

TOPIC:
{topic}

IMPORTANT RULES:

1. Create exactly 15 flashcards.
2. Every flashcard must contain one question and one answer.
3. Keep questions clear and exam-focused.
4. Keep answers short and easy to understand.
5. Use simple English.
6. Focus on important diploma-level concepts.
7. Do not add introductions.
8. Do not add conclusions.
9. Do not use Markdown.
10. Do not use #, ##, ###, **, or backticks.
11. Do not skip any flashcard.
12. Stay strictly related to the requested topic.

Use EXACTLY this format:

Q: Question text
A: Answer text

Q: Question text
A: Answer text

Continue until exactly 15 flashcards are created.

TOPIC:
{topic}
"""

            try:

                flashcards = ask_ai(prompt)

            except Exception as e:

                print("Flashcard Error:", e)

                flashcards = (
                    "Unable to generate flashcards right now."
                )

    return render_template(
        "flashcards.html",
        flashcards=flashcards,
        topic=topic
    )

# =========================================================
# AI RESUME ANALYZER
# =========================================================

@app.route("/resume", methods=["GET", "POST"])
@login_required
def resume():

    result = ""

    if request.method == "POST":

        resume_file = request.files.get("resume")

        # -------------------------------------------------
        # CHECK FILE
        # -------------------------------------------------

        if (
            not resume_file
            or resume_file.filename == ""
        ):

            return render_template(
                "resume.html",
                result="Please select a PDF resume."
            )


        filename = secure_filename(
            resume_file.filename
        )


        # -------------------------------------------------
        # CHECK PDF
        # -------------------------------------------------

        if not filename.lower().endswith(".pdf"):

            return render_template(
                "resume.html",
                result="Please upload a PDF resume."
            )


        filepath = os.path.join(
            app.config["UPLOAD_FOLDER"],
            filename
        )


        try:

            # -------------------------------------------------
            # SAVE FILE
            # -------------------------------------------------

            resume_file.save(filepath)


            # -------------------------------------------------
            # EXTRACT TEXT
            # -------------------------------------------------

            text = ""


            with open(filepath, "rb") as file:

                reader = PyPDF2.PdfReader(file)


                for page in reader.pages:

                    page_text = page.extract_text()


                    if page_text:

                        text += (
                            page_text
                            + "\n"
                        )


            # -------------------------------------------------
            # CHECK TEXT
            # -------------------------------------------------

            if not text.strip():

                result = (
                    "Could not extract text from this resume. "
                    "Please make sure the PDF contains selectable text."
                )


            else:

                # -------------------------------------------------
                # LIMIT TEXT
                # -------------------------------------------------

                resume_text = text[:25000]


                # -------------------------------------------------
                # AI PROMPT
                # -------------------------------------------------

                prompt = f"""
You are SmartStudy AI, a career assistant
for diploma and entry-level software students.

Analyze the resume below carefully.

Give practical and honest feedback.

IMPORTANT RULES:

1. Use simple English.
2. Do not invent information that is not present.
3. Do not make claims about the candidate that cannot
   be supported by the resume.
4. Focus on software/IT internship and entry-level roles.
5. Keep the feedback practical.
6. Do not use Markdown symbols such as #, ##, ###,
   **, or triple backticks.
7. Use clear headings.
8. Use bullet points where useful.
9. Do not give unnecessary motivational content.

Use EXACTLY this structure:

📊 RESUME OVERVIEW
Give a short overall assessment.

🎯 RESUME SCORE
Give a score from 1 to 10 based on:
- clarity
- relevant skills
- projects
- education
- formatting
- internship readiness

Explain briefly why you gave the score.

💪 STRENGTHS
List the strongest parts of the resume.

⚠️ AREAS TO IMPROVE
List the most important weaknesses or improvements.

🛠️ SKILLS
Separate into:

Existing Skills:
List skills already present.

Recommended Skills:
Suggest practical skills that would strengthen
the resume for software internships.

💻 PROJECTS
Analyze the projects.

Mention:
- What is good
- What is missing
- How projects could be presented better

📄 RESUME FORMATTING
Give practical formatting suggestions.

🎓 DIPLOMA STUDENT ADVICE
Give practical advice specifically for a diploma
student applying for software internships.

🚀 NEXT STEPS
Give 5 specific actions the student should take
to improve the resume.

📝 FINAL SUMMARY
Give a short summary of the most important changes.

RESUME:

{resume_text}
"""


                # -------------------------------------------------
                # AI ANALYSIS
                # -------------------------------------------------

                result = ask_ai(prompt)


        except Exception as e:

            print(
                "Resume Error:",
                e
            )

            result = (
                "Unable to analyze the resume right now. "
                "Please try again."
            )


    return render_template(
        "resume.html",
        result=result
    )
# =========================================================
# ANALYTICS
# =========================================================

# =========================================================
# LEARNING ANALYTICS
# =========================================================

@app.route("/analytics")
@login_required
def analytics():

    username = session["username"]

    conn = get_db_connection()


    # -----------------------------------------------------
    # TOTAL CHATS
    # -----------------------------------------------------

    total_chats = conn.execute(
        """
        SELECT COUNT(*)
        FROM chat_history
        WHERE username = ?
        """,
        (username,)
    ).fetchone()[0]


    # -----------------------------------------------------
    # TOTAL NOTES
    # -----------------------------------------------------

    total_notes = conn.execute(
        """
        SELECT COUNT(*)
        FROM notes_history
        WHERE username = ?
        """,
        (username,)
    ).fetchone()[0]


    # -----------------------------------------------------
    # TOTAL QUIZZES
    # -----------------------------------------------------

    total_quizzes = conn.execute(
        """
        SELECT COUNT(*)
        FROM quiz_history
        WHERE username = ?
        """,
        (username,)
    ).fetchone()[0]


    # -----------------------------------------------------
    # TOTAL PDFs
    # -----------------------------------------------------

    total_pdfs = conn.execute(
        """
        SELECT COUNT(*)
        FROM pdf_history
        WHERE username = ?
        """,
        (username,)
    ).fetchone()[0]


    # -----------------------------------------------------
    # TOTAL AI ACTIVITIES
    # -----------------------------------------------------

    total_activity = (
        total_chats
        + total_notes
        + total_quizzes
        + total_pdfs
    )


    # -----------------------------------------------------
    # LATEST ATTENDANCE
    # -----------------------------------------------------

    attendance_data = conn.execute(
        """
        SELECT
            total_classes,
            attended_classes
        FROM attendance
        WHERE username = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (username,)
    ).fetchone()


    if (
        attendance_data
        and attendance_data["total_classes"] > 0
    ):

        attendance_percentage = round(
            (
                attendance_data["attended_classes"]
                /
                attendance_data["total_classes"]
            ) * 100,
            2
        )

    else:

        attendance_percentage = 0


    conn.close()


    # -----------------------------------------------------
    # RENDER ANALYTICS
    # -----------------------------------------------------

    return render_template(

        "analytics.html",

        total_chats=total_chats,

        total_notes=total_notes,

        total_quizzes=total_quizzes,

        total_pdfs=total_pdfs,

        total_activity=total_activity,

        attendance=attendance_percentage,

        latest_notes=session.get(
            "latest_notes"
        )
    )


# =========================================================
# DOWNLOAD NOTES AS PDF
# =========================================================


# =========================================================
# ADMIN PANEL
# =========================================================

@app.route("/admin")
def admin():

    if not session.get("is_admin"):

        return redirect(
            url_for("admin_login")
        )

    conn = get_db_connection()

    # -----------------------------------------------------
    # Total Users
    # -----------------------------------------------------

    total_users = conn.execute(
        """
        SELECT COUNT(*)
        FROM users
        """
    ).fetchone()[0]

    # -----------------------------------------------------
    # Total Chats
    # -----------------------------------------------------

    total_chats = conn.execute(
        """
        SELECT COUNT(*)
        FROM chat_history
        """
    ).fetchone()[0]

    # -----------------------------------------------------
    # Total Notes
    # -----------------------------------------------------

    total_notes = conn.execute(
        """
        SELECT COUNT(*)
        FROM notes_history
        """
    ).fetchone()[0]

    # -----------------------------------------------------
    # Total Quizzes
    # -----------------------------------------------------

    total_quizzes = conn.execute(
        """
        SELECT COUNT(*)
        FROM quiz_history
        """
    ).fetchone()[0]

    # -----------------------------------------------------
    # Users
    # -----------------------------------------------------

    users = conn.execute(
        """
        SELECT
            fullname,
            email,
            username
        FROM users
        ORDER BY id DESC
        """
    ).fetchall()

    conn.close()

    return render_template(
        "admin.html",

        total_users=total_users,

        total_chats=total_chats,

        total_notes=total_notes,

        total_quizzes=total_quizzes,

        users=users
    )


# =========================================================
# ADMIN LOGIN
# =========================================================

@app.route(
    "/admin-login",
    methods=["GET", "POST"]
)
def admin_login():

    error = ""

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        admin_username = os.getenv(
            "ADMIN_USERNAME"
        )

        admin_password = os.getenv(
            "ADMIN_PASSWORD"
        )

        if (
            admin_username
            and admin_password
            and username == admin_username
            and password == admin_password
        ):

            session["is_admin"] = True

            return redirect(
                url_for("admin")
            )

        error = (
            "Invalid admin username or password."
        )

    return render_template(
        "admin_login.html",
        error=error
    )


# =========================================================
# ADMIN LOGOUT
# =========================================================

@app.route("/admin-logout")
def admin_logout():

    session.pop(
        "is_admin",
        None
    )

    return redirect(
        url_for("admin_login")
    )


# =========================================================
# 404 ERROR
# =========================================================

@app.errorhandler(404)
def page_not_found(error):

    return render_template(
        "error.html",
        error_message=(
            "The page you are looking for "
            "does not exist."
        )
    ), 404


# =========================================================
# 500 ERROR
# =========================================================

@app.errorhandler(500)
def internal_server_error(error):

    return render_template(
        "error.html",
        error_message=(
            "An internal server error occurred. "
            "Please try again."
        )
    ), 500


# =========================================================
# REGISTERED ROUTES DEBUG
# =========================================================

print("\n==============================")
print("REGISTERED ROUTES")
print("==============================")

for rule in app.url_map.iter_rules():

    print(
        f"{rule.rule} -> {rule.endpoint}"
    )

print("==============================\n")
@app.route("/profile")
@login_required
def profile():

    conn = get_db_connection()

    user = conn.execute(
        """
        SELECT id, fullname, email, username
        FROM users
        WHERE username = ?
        """,
        (session["username"],)
    ).fetchone()

    conn.close()

    if not user:
        session.clear()
        return redirect(url_for("login"))

    return render_template(
        "profile.html",
        user=user
    )

# =========================================================
# RUN FLASK
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )
