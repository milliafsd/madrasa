import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import sqlite3
import pytz
import plotly.express as px
import plotly.graph_objects as go
import os
import hashlib
import shutil
import zipfile
import io
import secrets
import re

# ==================== 1. سیکیورٹی کنفیگریشن ====================
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 15
SESSION_TIMEOUT_MINUTES = 120

def sanitize_input(text: str, max_length: int = 500) -> str:
    """خطرناک کریکٹرز کو صاف کریں"""
    if not text:
        return ""
    text = str(text).strip()[:max_length]
    dangerous = ["'", '"', ";", "--", "/*", "*/", "xp_", "EXEC", "DROP", "DELETE FROM", "INSERT INTO"]
    for d in dangerous:
        text = text.replace(d, "")
    return text

def validate_phone(phone: str) -> bool:
    if not phone:
        return True
    pattern = r'^[0-9+\-\s()]{7,15}$'
    return bool(re.match(pattern, phone))

def validate_id_card(id_card: str) -> bool:
    if not id_card:
        return True
    pattern = r'^[0-9]{5}-[0-9]{7}-[0-9]$'
    return bool(re.match(pattern, id_card))

# ==================== 2. ڈیٹا بیس سیٹ اپ ====================
DB_NAME = 'jamia_millia_data.db'

def get_db_connection():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn

def hash_password(password: str) -> str:
    salt = "jamia_millia_2024_secure_salt"
    return hashlib.sha256((password + salt).encode()).hexdigest()

def verify_password_strength(password: str) -> tuple[bool, str]:
    if len(password) < 8:
        return False, "پاسورڈ کم از کم 8 حروف کا ہونا چاہیے"
    if not any(c.isdigit() for c in password):
        return False, "پاسورڈ میں کم از کم ایک عدد ہونا چاہیے"
    return True, "مضبوط"

def column_exists(table, column):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in c.fetchall()]
    conn.close()
    return column in columns

def add_column_if_not_exists(table, column, col_type):
    if not column_exists(table, column):
        conn = get_db_connection()
        c = conn.cursor()
        try:
            c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
            conn.commit()
        except:
            pass
        conn.close()

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS teachers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        dept TEXT,
        phone TEXT,
        address TEXT,
        id_card TEXT,
        photo TEXT,
        joining_date DATE,
        is_active INTEGER DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS login_attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        attempt_time DATETIME,
        success INTEGER DEFAULT 0,
        ip_hint TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        father_name TEXT NOT NULL,
        mother_name TEXT,
        dob DATE,
        admission_date DATE,
        exit_date DATE,
        exit_reason TEXT,
        id_card TEXT,
        photo TEXT,
        phone TEXT,
        address TEXT,
        teacher_name TEXT,
        dept TEXT,
        class TEXT,
        section TEXT,
        roll_no TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS hifz_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        r_date DATE NOT NULL,
        student_id INTEGER NOT NULL,
        t_name TEXT NOT NULL,
        surah TEXT,
        a_from TEXT,
        a_to TEXT,
        sq_p TEXT,
        sq_a INTEGER DEFAULT 0,
        sq_m INTEGER DEFAULT 0,
        m_p TEXT,
        m_a INTEGER DEFAULT 0,
        m_m INTEGER DEFAULT 0,
        attendance TEXT NOT NULL,
        principal_note TEXT,
        lines INTEGER DEFAULT 0,
        cleanliness TEXT,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS qaida_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        r_date DATE NOT NULL,
        student_id INTEGER NOT NULL,
        t_name TEXT NOT NULL,
        lesson_no TEXT,
        total_lines INTEGER DEFAULT 0,
        details TEXT,
        attendance TEXT NOT NULL,
        principal_note TEXT,
        cleanliness TEXT,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS general_education (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        r_date DATE NOT NULL,
        student_id INTEGER NOT NULL,
        t_name TEXT NOT NULL,
        dept TEXT,
        book_subject TEXT,
        today_lesson TEXT,
        homework TEXT,
        performance TEXT,
        attendance TEXT,
        cleanliness TEXT,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS t_attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        t_name TEXT NOT NULL,
        a_date DATE NOT NULL,
        arrival TEXT,
        departure TEXT,
        actual_arrival TEXT,
        actual_departure TEXT,
        UNIQUE(t_name, a_date)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS leave_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        t_name TEXT NOT NULL,
        reason TEXT,
        start_date DATE,
        back_date DATE,
        status TEXT DEFAULT 'پینڈنگ',
        request_date DATE,
        l_type TEXT,
        days INTEGER DEFAULT 1,
        notification_seen INTEGER DEFAULT 0
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS exams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        dept TEXT,
        exam_type TEXT,
        from_para INTEGER,
        to_para INTEGER,
        book_name TEXT,
        amount_read TEXT,
        start_date TEXT,
        end_date TEXT,
        total_days INTEGER,
        q1 INTEGER DEFAULT 0,
        q2 INTEGER DEFAULT 0,
        q3 INTEGER DEFAULT 0,
        q4 INTEGER DEFAULT 0,
        q5 INTEGER DEFAULT 0,
        total INTEGER DEFAULT 0,
        grade TEXT,
        status TEXT DEFAULT 'پینڈنگ',
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS passed_paras (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        para_no INTEGER,
        book_name TEXT,
        passed_date DATE,
        exam_type TEXT,
        grade TEXT,
        marks INTEGER DEFAULT 0,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS timetable (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        t_name TEXT NOT NULL,
        day TEXT NOT NULL,
        period TEXT,
        book TEXT,
        room TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        message TEXT,
        target TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        seen INTEGER DEFAULT 0
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT NOT NULL,
        action TEXT NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        details TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS staff_monitoring (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        staff_name TEXT NOT NULL,
        date DATE,
        note_type TEXT,
        description TEXT,
        action_taken TEXT,
        status TEXT DEFAULT 'زیر التواء',
        created_by TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    extra_cols = [
        ('teachers', 'dept', 'TEXT'), ('teachers', 'phone', 'TEXT'),
        ('teachers', 'address', 'TEXT'), ('teachers', 'id_card', 'TEXT'),
        ('teachers', 'photo', 'TEXT'), ('teachers', 'joining_date', 'DATE'),
        ('teachers', 'is_active', 'INTEGER DEFAULT 1'),
        ('students', 'roll_no', 'TEXT'),
        ('hifz_records', 'student_id', 'INTEGER'), ('hifz_records', 'lines', 'INTEGER'),
        ('hifz_records', 'cleanliness', 'TEXT'),
        ('qaida_records', 'student_id', 'INTEGER'), ('qaida_records', 'cleanliness', 'TEXT'),
        ('general_education', 'student_id', 'INTEGER'), ('general_education', 'attendance', 'TEXT'),
        ('general_education', 'cleanliness', 'TEXT'),
        ('exams', 'student_id', 'INTEGER'), ('exams', 'amount_read', 'TEXT'),
        ('exams', 'total_days', 'INTEGER'),
        ('passed_paras', 'student_id', 'INTEGER'), ('passed_paras', 'book_name', 'TEXT'),
        ('passed_paras', 'marks', 'INTEGER'),
    ]
    for table, col, col_type in extra_cols:
        add_column_if_not_exists(table, col, col_type)

    conn.commit()
    
    admin_hash = hash_password("jamia123")
    admin_exists = c.execute("SELECT 1 FROM teachers WHERE name='admin'").fetchone()
    if not admin_exists:
        c.execute("INSERT INTO teachers (name, password, dept, is_active) VALUES (?,?,?,?)",
                  ("admin", admin_hash, "Admin", 1))
    else:
        # اگر پاسورڈ ہیش نہ ہو تو اپ ڈیٹ کریں
        cur = c.execute("SELECT password FROM teachers WHERE name='admin'").fetchone()
        if cur and len(cur[0]) != 64:
            c.execute("UPDATE teachers SET password=? WHERE name='admin'", (admin_hash,))
    conn.commit()
    conn.close()

init_db()

# ==================== 3. سیکیورٹی فنکشنز ====================
def check_login_attempts(username: str) -> tuple[bool, int]:
    conn = get_db_connection()
    cutoff = datetime.now() - timedelta(minutes=LOCKOUT_MINUTES)
    attempts = conn.execute(
        "SELECT COUNT(*) FROM login_attempts WHERE username=? AND attempt_time>? AND success=0",
        (username, cutoff)
    ).fetchone()[0]
    conn.close()
    return attempts >= MAX_LOGIN_ATTEMPTS, attempts

def record_login_attempt(username: str, success: bool):
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO login_attempts (username, attempt_time, success) VALUES (?,?,?)",
        (username, datetime.now(), 1 if success else 0)
    )
    conn.commit()
    conn.close()

def log_audit(user: str, action: str, details: str = ""):
    try:
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO audit_log (user, action, timestamp, details) VALUES (?,?,?,?)",
            (user, action, datetime.now(), details[:1000])
        )
        conn.commit()
        conn.close()
    except:
        pass

def verify_login(username: str, password: str):
    username = sanitize_input(username, 100)
    if not username or not password:
        return None
    
    locked, attempts = check_login_attempts(username)
    if locked:
        return "locked"
    
    conn = get_db_connection()
    hashed = hash_password(password)
    res = conn.execute(
        "SELECT * FROM teachers WHERE name=? AND password=? AND is_active=1",
        (username, hashed)
    ).fetchone()
    
    # پرانے پلین یا ہیش کو سپورٹ کریں
    if not res:
        old_hash = hashlib.sha256(password.encode()).hexdigest()
        res = conn.execute(
            "SELECT * FROM teachers WHERE name=? AND password=? AND is_active=1",
            (username, old_hash)
        ).fetchone()
        if not res:
            res = conn.execute(
                "SELECT * FROM teachers WHERE name=? AND password=? AND is_active=1",
                (username, password)
            ).fetchone()
        if res:
            conn.execute("UPDATE teachers SET password=? WHERE name=?", (hashed, username))
            conn.commit()
    
    conn.close()
    record_login_attempt(username, res is not None)
    return res

def verify_password_db(user: str, plain_password: str) -> bool:
    conn = get_db_connection()
    res = conn.execute("SELECT password FROM teachers WHERE name=?", (user,)).fetchone()
    conn.close()
    if not res:
        return False
    hashed_new = hash_password(plain_password)
    hashed_old = hashlib.sha256(plain_password.encode()).hexdigest()
    return res[0] in [hashed_new, hashed_old, plain_password]

def change_password(user: str, old_pass: str, new_pass: str) -> tuple[bool, str]:
    if not verify_password_db(user, old_pass):
        return False, "پرانا پاسورڈ غلط ہے"
    valid, msg = verify_password_strength(new_pass)
    if not valid:
        return False, msg
    conn = get_db_connection()
    conn.execute("UPDATE teachers SET password=? WHERE name=?", (hash_password(new_pass), user))
    conn.commit()
    conn.close()
    log_audit(user, "Password Changed", "Success")
    return True, "کامیاب"

def admin_reset_password(teacher_name: str, new_pass: str) -> tuple[bool, str]:
    valid, msg = verify_password_strength(new_pass)
    if not valid:
        return False, msg
    conn = get_db_connection()
    conn.execute("UPDATE teachers SET password=? WHERE name=?",
                 (hash_password(new_pass), teacher_name))
    conn.commit()
    conn.close()
    log_audit(st.session_state.username, "Admin Reset Password", f"Teacher: {teacher_name}")
    return True, "کامیاب"

# ==================== 4. ہیلپر فنکشنز ====================
def get_pk_time():
    tz = pytz.timezone('Asia/Karachi')
    return datetime.now(tz).strftime("%I:%M %p")

def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8-sig')

def calculate_grade_with_attendance(attendance, sabaq_nagha, sq_nagha, m_nagha, sq_mistakes, m_mistakes):
    if attendance == "غیر حاضر": return "غیر حاضر"
    if attendance == "رخصت": return "رخصت"
    nagha_count = sum([sabaq_nagha, sq_nagha, m_nagha])
    if nagha_count == 1: return "ناقص (ناغہ)"
    elif nagha_count == 2: return "کمزور (ناغہ)"
    elif nagha_count == 3: return "ناکام (مکمل ناغہ)"
    total = sq_mistakes + m_mistakes
    if total <= 2: return "ممتاز"
    elif total <= 5: return "جید جداً"
    elif total <= 8: return "جید"
    elif total <= 12: return "مقبول"
    else: return "دوبارہ کوشش کریں"

def cleanliness_to_score(clean):
    return {"بہترین": 3, "بہتر": 2, "ناقص": 1}.get(clean, 0)

def generate_html_report(df, title, student_name="", start_date="", end_date="", passed_paras=None):
    html_table = df.to_html(index=False, classes='print-table', border=1, justify='center', escape=False)
    passed_html = ""
    if passed_paras:
        passed_html = f"<div style='margin-top:20px'><b>پاس شدہ پارے:</b> {', '.join(map(str, passed_paras))}</div>"
    return f"""<!DOCTYPE html><html dir="rtl">
<head><meta charset="UTF-8"><title>{title}</title>
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu&display=swap');
    body{{font-family:'Noto Nastaliq Urdu',Arial,sans-serif;margin:20px;direction:rtl;text-align:right;background:#f8f9fa}}
    .card{{background:white;border-radius:12px;padding:20px;box-shadow:0 4px 12px rgba(0,0,0,.08);max-width:900px;margin:auto}}
    h2,h3{{text-align:center;color:#1e5631}}
    table{{width:100%;border-collapse:collapse;margin:20px 0}}
    th,td{{border:1px solid #ddd;padding:10px;text-align:center}}
    th{{background:#1e5631;color:white}}
    tr:nth-child(even){{background:#f5f5f5}}
    @media print{{body{{margin:0}}.no-print{{display:none}}}}
</style></head>
<body><div class="card">
    <h2>🕌 جامعہ ملیہ اسلامیہ فیصل آباد</h2>
    <h3>{title}</h3>
    {f"<p><b>طالب علم:</b> {student_name} &nbsp;&nbsp; <b>تاریخ:</b> {start_date} تا {end_date}</p>" if student_name else ""}
    {html_table}{passed_html}
    <div style="display:flex;justify-content:space-between;margin-top:50px">
        <span>دستخط استاذ: _______________________</span>
        <span>دستخط مہتمم: _______________________</span>
    </div>
</div>
<div class="no-print" style="text-align:center;margin-top:30px">
    <button onclick="window.print()" style="padding:10px 30px;background:#1e5631;color:white;border:none;border-radius:8px;cursor:pointer">🖨️ پرنٹ کریں</button>
</div></body></html>"""

def generate_para_report(student_name, father_name, passed_paras_df):
    if passed_paras_df.empty:
        return "<p>کوئی پاس شدہ پارہ نہیں</p>"
    return generate_html_report(passed_paras_df, "پارہ تعلیمی رپورٹ", student_name=f"{student_name} ولد {father_name}")

def generate_timetable_html(df_timetable):
    if df_timetable.empty:
        return "<p>کوئی ٹائم ٹیبل دستیاب نہیں</p>"
    day_order = {"ہفتہ": 0, "اتوار": 1, "پیر": 2, "منگل": 3, "بدھ": 4, "جمعرات": 5}
    df_timetable = df_timetable.copy()
    df_timetable['day_order'] = df_timetable['دن'].map(day_order)
    df_timetable = df_timetable.sort_values(['day_order', 'وقت'])
    pivot = df_timetable.pivot(index='وقت', columns='دن', values='کتاب').fillna("—")
    return generate_html_report(pivot.reset_index(), "ٹائم ٹیبل")

# ==================== 5. خوبصورت CSS ====================
st.set_page_config(
    page_title="جامعہ ملیہ اسلامیہ | سمارٹ ERP",
    page_icon="🕌",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
/* ===== فونٹ امپورٹ ===== */
@import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu:wght@400;500;600;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Amiri:wght@400;700&display=swap');

/* ===== بنیادی ===== */
:root {
    --green-dark: #0d3b2b;
    --green-mid: #1e5631;
    --green-light: #2d7a47;
    --green-pale: #e8f5e9;
    --gold: #c9a227;
    --gold-light: #f5e6b3;
    --white: #ffffff;
    --gray-100: #f8fafb;
    --gray-200: #eef1f4;
    --gray-400: #9ca3af;
    --text-dark: #1a2535;
    --shadow-soft: 0 4px 20px rgba(0,0,0,0.06);
    --shadow-card: 0 8px 32px rgba(13,59,43,0.10);
    --radius: 16px;
    --radius-sm: 10px;
}

* {
    font-family: 'Noto Nastaliq Urdu', 'Amiri', Georgia, serif !important;
    direction: rtl;
}

html, body, [class*="css"] {
    direction: rtl;
    text-align: right;
}

/* ===== بیک گراؤنڈ ===== */
.stApp {
    background: linear-gradient(145deg, #f0f7f3 0%, #e8f5e9 40%, #f5f0e8 100%);
    min-height: 100vh;
}

/* ===== سائیڈ بار ===== */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d3b2b 0%, #1e5631 60%, #0d3b2b 100%) !important;
    border-left: 3px solid #c9a227;
    box-shadow: -4px 0 20px rgba(0,0,0,0.3);
}

[data-testid="stSidebar"] * {
    color: #e8f5e9 !important;
}

[data-testid="stSidebar"] .stRadio label {
    color: #d4e8d9 !important;
    font-weight: 500;
    font-size: 0.95rem;
    padding: 4px 0;
}

[data-testid="stSidebar"] [role="radiogroup"] {
    gap: 4px;
}

[data-testid="stSidebar"] [data-testid="stRadio"] > div {
    background: rgba(255,255,255,0.05);
    border-radius: 10px;
    padding: 4px 8px;
    transition: all 0.2s;
    border: 1px solid transparent;
}

[data-testid="stSidebar"] [data-testid="stRadio"] > div:hover {
    background: rgba(201,162,39,0.15) !important;
    border-color: rgba(201,162,39,0.3);
}

/* ===== ہیڈر ===== */
.main-header {
    background: linear-gradient(135deg, #0d3b2b 0%, #1e5631 50%, #2d7a47 100%);
    padding: 2rem 2.5rem;
    border-radius: var(--radius);
    margin-bottom: 1.5rem;
    text-align: center;
    position: relative;
    overflow: hidden;
    box-shadow: var(--shadow-card);
}

.main-header::before {
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: radial-gradient(ellipse at center, rgba(201,162,39,0.08) 0%, transparent 60%);
    animation: shimmer 6s ease-in-out infinite;
}

@keyframes shimmer {
    0%, 100% { transform: translate(-10%, -10%); opacity: 0.5; }
    50% { transform: translate(10%, 10%); opacity: 1; }
}

.main-header h1 {
    color: #ffffff !important;
    font-size: 2rem !important;
    font-weight: 700 !important;
    margin: 0 !important;
    text-shadow: 0 2px 8px rgba(0,0,0,0.3);
    letter-spacing: 0.5px;
}

.main-header .subtitle {
    color: #c9a227 !important;
    font-size: 1.1rem;
    margin-top: 0.4rem;
    opacity: 0.9;
}

.header-decoration {
    display: flex;
    justify-content: center;
    gap: 0.5rem;
    margin-top: 0.8rem;
}

.header-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #c9a227;
    animation: pulse 2s ease-in-out infinite;
}
.header-dot:nth-child(2) { animation-delay: 0.3s; }
.header-dot:nth-child(3) { animation-delay: 0.6s; }

@keyframes pulse {
    0%, 100% { transform: scale(1); opacity: 0.7; }
    50% { transform: scale(1.5); opacity: 1; }
}

/* ===== کارڈ ===== */
.report-card {
    background: rgba(255,255,255,0.95);
    border-radius: var(--radius);
    padding: 1.8rem;
    box-shadow: var(--shadow-card);
    margin-bottom: 1.2rem;
    border: 1px solid rgba(30,86,49,0.08);
    backdrop-filter: blur(8px);
    transition: transform 0.2s, box-shadow 0.2s;
}

.report-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 12px 40px rgba(13,59,43,0.15);
}

/* ===== میٹرک کارڈ ===== */
.metric-card {
    background: linear-gradient(135deg, #ffffff 0%, #f0f9f3 100%);
    border-radius: var(--radius);
    padding: 1.5rem;
    text-align: center;
    box-shadow: var(--shadow-card);
    border: 1px solid rgba(30,86,49,0.1);
    position: relative;
    overflow: hidden;
    transition: all 0.3s;
}

.metric-card::after {
    content: '';
    position: absolute;
    bottom: 0;
    right: 0;
    left: 0;
    height: 4px;
    background: linear-gradient(90deg, #1e5631, #c9a227);
    border-radius: 0 0 var(--radius) var(--radius);
}

.metric-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 16px 48px rgba(13,59,43,0.18);
}

.metric-number {
    font-size: 2.8rem;
    font-weight: 700;
    color: #1e5631;
    line-height: 1;
}

.metric-label {
    color: #6b7280;
    font-size: 0.95rem;
    margin-top: 0.5rem;
}

.metric-icon {
    font-size: 2rem;
    margin-bottom: 0.5rem;
    display: block;
}

/* ===== بٹن ===== */
.stButton > button {
    background: linear-gradient(135deg, #1e5631, #2d7a47) !important;
    color: white !important;
    border-radius: 12px !important;
    border: none !important;
    padding: 0.55rem 1.4rem !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    transition: all 0.25s !important;
    box-shadow: 0 3px 10px rgba(30,86,49,0.25) !important;
    letter-spacing: 0.3px;
}

.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(30,86,49,0.4) !important;
    background: linear-gradient(135deg, #0d3b2b, #1e5631) !important;
}

.stButton > button:active {
    transform: translateY(0) !important;
}

/* ===== ٹیبز ===== */
.stTabs [data-baseweb="tab-list"] {
    background: rgba(30,86,49,0.05);
    border-radius: 12px;
    padding: 4px;
    gap: 4px;
}

.stTabs [data-baseweb="tab"] {
    border-radius: 10px !important;
    padding: 0.5rem 1.2rem !important;
    transition: all 0.2s !important;
    background: transparent !important;
    color: #4b5563 !important;
    font-weight: 500 !important;
    border: 1px solid transparent !important;
}

.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #1e5631, #2d7a47) !important;
    color: white !important;
    box-shadow: 0 3px 10px rgba(30,86,49,0.25) !important;
}

/* ===== انپٹ فیلڈز ===== */
.stTextInput > div > div > input,
.stTextArea textarea,
.stSelectbox > div > div,
.stNumberInput > div > div > input {
    border-radius: var(--radius-sm) !important;
    border: 1.5px solid #d1d5db !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
    background: rgba(255,255,255,0.9) !important;
    direction: rtl !important;
}

.stTextInput > div > div > input:focus,
.stTextArea textarea:focus {
    border-color: #1e5631 !important;
    box-shadow: 0 0 0 3px rgba(30,86,49,0.12) !important;
    outline: none !important;
}

/* ===== الرٹس ===== */
.stSuccess {
    background: linear-gradient(135deg, #f0fdf4, #dcfce7) !important;
    border: 1px solid #86efac !important;
    border-radius: var(--radius-sm) !important;
    color: #14532d !important;
}

.stError {
    background: linear-gradient(135deg, #fff1f2, #ffe4e6) !important;
    border: 1px solid #fca5a5 !important;
    border-radius: var(--radius-sm) !important;
}

.stWarning {
    background: linear-gradient(135deg, #fffbeb, #fef3c7) !important;
    border: 1px solid #fcd34d !important;
    border-radius: var(--radius-sm) !important;
}

.stInfo {
    background: linear-gradient(135deg, #eff6ff, #dbeafe) !important;
    border: 1px solid #93c5fd !important;
    border-radius: var(--radius-sm) !important;
}

/* ===== ڈیٹا ٹیبل ===== */
.stDataFrame {
    border-radius: var(--radius-sm) !important;
    overflow: hidden !important;
    box-shadow: var(--shadow-soft) !important;
}

/* ===== بہترین طالب علم کارڈ ===== */
.best-student-card {
    background: linear-gradient(145deg, #ffffff, #f9f3e3);
    border-radius: 20px;
    padding: 1.8rem 1.2rem;
    text-align: center;
    box-shadow: 0 8px 32px rgba(201,162,39,0.15);
    border: 1px solid rgba(201,162,39,0.2);
    transition: all 0.3s;
    position: relative;
    overflow: hidden;
}

.best-student-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 4px;
    background: linear-gradient(90deg, #c9a227, #f0d060, #c9a227);
}

.best-student-card:hover {
    transform: translateY(-6px);
    box-shadow: 0 16px 48px rgba(201,162,39,0.25);
}

.medal-gold { color: #c9a227; font-size: 3rem; }
.medal-silver { color: #9ca3af; font-size: 3rem; }
.medal-bronze { color: #cd7f32; font-size: 3rem; }

.student-name-card {
    font-size: 1.2rem;
    font-weight: 700;
    color: #1a2535;
    margin: 0.5rem 0 0.2rem;
}

.student-detail-card {
    color: #6b7280;
    font-size: 0.9rem;
    margin: 0.15rem 0;
}

.score-badge {
    display: inline-block;
    background: linear-gradient(135deg, #1e5631, #2d7a47);
    color: white;
    padding: 0.3rem 1rem;
    border-radius: 20px;
    font-size: 0.9rem;
    font-weight: 600;
    margin-top: 0.8rem;
    box-shadow: 0 3px 10px rgba(30,86,49,0.3);
}

/* ===== لاگ ان پیج ===== */
.login-container {
    background: rgba(255,255,255,0.97);
    border-radius: 24px;
    padding: 2.5rem 2rem;
    box-shadow: 0 16px 64px rgba(13,59,43,0.15);
    border: 1px solid rgba(30,86,49,0.1);
    backdrop-filter: blur(10px);
    max-width: 440px;
    margin: 0 auto;
}

.login-logo {
    text-align: center;
    margin-bottom: 1.5rem;
}

.login-logo .mosque-icon {
    font-size: 4rem;
    display: block;
    filter: drop-shadow(0 4px 8px rgba(30,86,49,0.3));
    animation: float 3s ease-in-out infinite;
}

@keyframes float {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-6px); }
}

/* ===== ایکسپانڈر ===== */
.streamlit-expanderHeader {
    background: linear-gradient(135deg, #f0f9f3, #e8f5e9) !important;
    border-radius: var(--radius-sm) !important;
    border: 1px solid rgba(30,86,49,0.12) !important;
}

/* ===== نوٹیفیکیشن بج ===== */
.notif-badge {
    display: inline-block;
    background: #dc2626;
    color: white;
    border-radius: 50%;
    width: 20px;
    height: 20px;
    font-size: 0.75rem;
    text-align: center;
    line-height: 20px;
    margin-right: 4px;
}

/* ===== سائیڈ بار لوگو ===== */
.sidebar-logo {
    text-align: center;
    padding: 1.2rem 0.8rem;
    border-bottom: 1px solid rgba(201,162,39,0.3);
    margin-bottom: 1rem;
}

.sidebar-logo .logo-icon { font-size: 2.8rem; }
.sidebar-logo .logo-title {
    color: #c9a227 !important;
    font-size: 1rem;
    font-weight: 700;
    margin-top: 0.4rem;
    display: block;
}
.sidebar-logo .logo-sub {
    color: rgba(200,230,210,0.8) !important;
    font-size: 0.8rem;
}

/* ===== موبائل ===== */
@media (max-width: 768px) {
    .main-header h1 { font-size: 1.4rem !important; }
    .metric-number { font-size: 2rem; }
    .stButton > button { padding: 0.45rem 1rem !important; font-size: 0.85rem !important; }
}

/* ===== سیکیورٹی بیج ===== */
.security-info {
    background: linear-gradient(135deg, #fef9e7, #fef3c7);
    border: 1px solid #f59e0b;
    border-radius: 10px;
    padding: 0.8rem 1rem;
    font-size: 0.85rem;
    color: #92400e;
    margin-bottom: 1rem;
}

/* ===== ڈیوائیڈر ===== */
.custom-divider {
    height: 2px;
    background: linear-gradient(90deg, transparent, #1e5631, #c9a227, #1e5631, transparent);
    border: none;
    margin: 1.5rem 0;
    border-radius: 2px;
}
</style>
""", unsafe_allow_html=True)

# ==================== 6. ڈیٹا ====================
surahs_urdu = ["الفاتحة","البقرة","آل عمران","النساء","المائدة","الأنعام","الأعراف","الأنفال","التوبة","يونس",
               "هود","يوسف","الرعد","إبراهيم","الحجر","النحل","الإسراء","الكهف","مريم","طه","الأنبياء","الحج",
               "المؤمنون","النور","الفرقان","الشعراء","النمل","القصص","العنكبوت","الروم","لقمان","السجدة","الأحزاب",
               "سبأ","فاطر","يس","الصافات","ص","الزمر","غافر","فصلت","الشورى","الزخرف","الدخان","الجاثية","الأحقاف",
               "محمد","الفتح","الحجرات","ق","الذاريات","الطور","النجم","القمر","الرحمن","الواقعة","الحديد","المجادلة",
               "الحشر","الممتحنة","الصف","الجمعة","المنافقون","التغابن","الطلاق","التحریم","الملک","القلم","الحاقة",
               "المعارج","نوح","الجن","المزمل","المدثر","القیامة","الإنسان","المرسلات","النبأ","النازعات","عبس","التکویر",
               "الإنفطار","المطففین","الإنشقاق","البروج","الطارق","الأعلى","الغاشیة","الفجر","البلد","الشمس","اللیل",
               "الضحى","الشرح","التین","العلق","القدر","البینة","الزلزلة","العادیات","القارعة","التکاثر","العصر","الهمزة",
               "الفیل","قریش","الماعون","الکوثر","الکافرون","النصر","المسد","الإخلاص","الفلق","الناس"]
paras = [f"پارہ {i}" for i in range(1, 31)]
cleanliness_options = ["بہترین", "بہتر", "ناقص"]

# ==================== 7. سیشن چیک ====================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "login_time" not in st.session_state:
    st.session_state.login_time = None

if st.session_state.logged_in and st.session_state.login_time:
    elapsed = (datetime.now() - st.session_state.login_time).total_seconds() / 60
    if elapsed > SESSION_TIMEOUT_MINUTES:
        st.session_state.logged_in = False
        st.warning("سیشن ختم ہو گیا۔ دوبارہ لاگ ان کریں۔")

# ==================== 8. لاگ ان ====================
if not st.session_state.logged_in:
    st.markdown("""
    <div style="text-align:center;padding:2rem 0 0.5rem">
        <div style="display:inline-block;background:linear-gradient(135deg,#0d3b2b,#1e5631);
                    border-radius:20px;padding:2rem 3rem;box-shadow:0 16px 64px rgba(13,59,43,0.25)">
            <span style="font-size:4rem;display:block;filter:drop-shadow(0 4px 8px rgba(0,0,0,0.3))">🕌</span>
            <h1 style="color:#ffffff;margin:0.5rem 0 0.2rem;font-size:1.8rem;text-shadow:0 2px 8px rgba(0,0,0,0.3)">
                جامعہ ملیہ اسلامیہ فیصل آباد
            </h1>
            <p style="color:#c9a227;margin:0;font-size:1rem">اسمارٹ تعلیمی و انتظامی پورٹل</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<div class='login-container'>", unsafe_allow_html=True)
        st.markdown("""
        <h3 style="text-align:center;color:#1e5631;margin-bottom:1.2rem;border-bottom:2px solid #c9a227;
                   padding-bottom:0.8rem">🔐 لاگ ان</h3>
        """, unsafe_allow_html=True)
        
        u = st.text_input("👤 صارف نام", placeholder="اپنا نام درج کریں")
        p = st.text_input("🔑 پاسورڈ", type="password", placeholder="پاسورڈ")
        
        if st.button("▶ داخل ہوں", use_container_width=True):
            if u and p:
                res = verify_login(u, p)
                if res == "locked":
                    st.error(f"⛔ بہت زیادہ غلط کوششیں۔ {LOCKOUT_MINUTES} منٹ بعد کوشش کریں۔")
                elif res:
                    st.session_state.logged_in = True
                    st.session_state.username = u
                    st.session_state.login_time = datetime.now()
                    st.session_state.user_type = "admin" if u == "admin" else "teacher"
                    log_audit(u, "Login", f"User type: {st.session_state.user_type}")
                    st.rerun()
                else:
                    conn = get_db_connection()
                    cutoff = datetime.now() - timedelta(minutes=LOCKOUT_MINUTES)
                    attempts = conn.execute(
                        "SELECT COUNT(*) FROM login_attempts WHERE username=? AND attempt_time>? AND success=0",
                        (u, cutoff)
                    ).fetchone()[0]
                    conn.close()
                    remaining = MAX_LOGIN_ATTEMPTS - attempts
                    if remaining > 0:
                        st.error(f"❌ غلط نام یا پاسورڈ۔ {remaining} کوشش باقی ہیں۔")
                    else:
                        st.error("⛔ اکاؤنٹ عارضی طور پر بند کر دیا گیا۔")
            else:
                st.warning("براہ کرم نام اور پاسورڈ دونوں درج کریں")
        
        st.markdown("""
        <div style="text-align:center;margin-top:1.2rem;padding-top:1rem;border-top:1px solid #e5e7eb">
            <p style="color:#9ca3af;font-size:0.8rem;margin:0">🔒 محفوظ اور خفیہ کاری شدہ کنکشن</p>
        </div>
        </div>
        """, unsafe_allow_html=True)
    st.stop()

# ==================== 9. سائیڈ بار ====================
with st.sidebar:
    st.markdown(f"""
    <div class="sidebar-logo">
        <span class="logo-icon">🕌</span>
        <span class="logo-title">جامعہ ملیہ</span>
        <span class="logo-sub">فیصل آباد</span>
    </div>
    <div style="text-align:center;padding:0.5rem;margin-bottom:1rem;
                background:rgba(201,162,39,0.1);border-radius:10px;
                border:1px solid rgba(201,162,39,0.2)">
        <p style="margin:0;font-size:0.85rem;color:#c9a227 !important">
            👤 {st.session_state.username}
        </p>
        <p style="margin:0;font-size:0.75rem;color:rgba(200,230,210,0.7) !important">
            {'🛡️ ایڈمن' if st.session_state.user_type == 'admin' else '👩‍🏫 استاد'}
        </p>
    </div>
    """, unsafe_allow_html=True)

if st.session_state.user_type == "admin":
    menu = ["📊 ایڈمن ڈیش بورڈ", "📊 یومیہ تعلیمی رپورٹ", "🎓 امتحانی نظام", "📜 ماہانہ رزلٹ کارڈ",
            "📘 پارہ تعلیمی رپورٹ", "🕒 اساتذہ حاضری", "🏛️ رخصت کی منظوری",
            "👥 یوزر مینجمنٹ", "📚 ٹائم ٹیبل مینجمنٹ", "🔑 پاسورڈ تبدیل کریں",
            "📋 عملہ نگرانی و شکایات", "📢 نوٹیفیکیشنز", "📈 تجزیہ و رپورٹس",
            "🏆 ماہانہ بہترین طلباء", "⚙️ بیک اپ & سیٹنگز"]
else:
    menu = ["📝 روزانہ سبق اندراج", "🎓 امتحانی درخواست", "📩 رخصت کی درخواست",
            "🕒 میری حاضری", "📚 میرا ٹائم ٹیبل", "🔑 پاسورڈ تبدیل کریں", "📢 نوٹیفیکیشنز"]

selected = st.sidebar.radio("📌 مینو", menu)

st.sidebar.markdown("<hr style='border:none;border-top:1px solid rgba(201,162,39,0.3);margin:1rem 0'>", unsafe_allow_html=True)
if st.sidebar.button("🚪 لاگ آؤٹ", use_container_width=True):
    log_audit(st.session_state.username, "Logout", "")
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# ==================== 10. ایڈمن ڈیش بورڈ ====================
if selected == "📊 ایڈمن ڈیش بورڈ" and st.session_state.user_type == "admin":
    st.markdown("""
    <div class='main-header'>
        <h1>📊 ایڈمن ڈیش بورڈ</h1>
        <p class='subtitle'>جامعہ ملیہ اسلامیہ فیصل آباد — مکمل جائزہ</p>
        <div class='header-decoration'>
            <div class='header-dot'></div><div class='header-dot'></div><div class='header-dot'></div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    conn = get_db_connection()
    total_students = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    total_teachers = conn.execute("SELECT COUNT(*) FROM teachers WHERE name!='admin'").fetchone()[0]
    today_attendance = conn.execute("SELECT COUNT(*) FROM t_attendance WHERE a_date=?", (date.today(),)).fetchone()[0]
    pending_leaves = conn.execute("SELECT COUNT(*) FROM leave_requests WHERE status LIKE '%پینڈنگ%'").fetchone()[0]
    pending_exams = conn.execute("SELECT COUNT(*) FROM exams WHERE status='پینڈنگ'").fetchone()[0]
    conn.close()
    
    col1, col2, col3, col4 = st.columns(4)
    metrics = [
        (col1, "👨‍🎓", total_students, "کل طلباء"),
        (col2, "👩‍🏫", total_teachers, "کل اساتذہ"),
        (col3, "✅", today_attendance, "آج کی حاضری"),
        (col4, "📋", pending_exams, "پینڈنگ امتحانات"),
    ]
    for col, icon, val, label in metrics:
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <span class="metric-icon">{icon}</span>
                <div class="metric-number">{val}</div>
                <div class="metric-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)
    
    if pending_leaves > 0:
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#fff7ed,#fed7aa);border:1px solid #fb923c;
                    border-radius:12px;padding:0.8rem 1.2rem;margin-top:1rem;display:flex;align-items:center;gap:0.5rem">
            <span>⏳</span>
            <span style="color:#c2410c;font-weight:600">{pending_leaves} رخصت درخواستیں منتظر منظوری ہیں</span>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📅 آج کی حاضری (اساتذہ)")
        conn = get_db_connection()
        today_att = pd.read_sql_query(
            "SELECT t_name as استاد, arrival as آمد, departure as رخصت FROM t_attendance WHERE a_date=?",
            conn, params=(date.today(),)
        )
        conn.close()
        if not today_att.empty:
            st.dataframe(today_att, use_container_width=True)
        else:
            st.info("آج کوئی حاضری ریکارڈ نہیں")
    with col2:
        st.markdown("### 🔔 تازہ نوٹیفیکیشنز")
        conn = get_db_connection()
        notifs = conn.execute(
            "SELECT title, message FROM notifications ORDER BY created_at DESC LIMIT 5"
        ).fetchall()
        conn.close()
        if notifs:
            for n in notifs:
                st.info(f"**{n[0]}**: {n[1][:80]}...")
        else:
            st.info("کوئی نوٹیفیکیشن نہیں")

# ==================== 11. یومیہ تعلیمی رپورٹ ====================
elif selected == "📊 یومیہ تعلیمی رپورٹ" and st.session_state.user_type == "admin":
    st.markdown("<div class='main-header'><h1>📊 یومیہ تعلیمی رپورٹ</h1><p class='subtitle'>روزانہ سبق کا مکمل جائزہ</p></div>", unsafe_allow_html=True)
    
    with st.sidebar:
        d1 = st.date_input("تاریخ آغاز", date.today().replace(day=1))
        d2 = st.date_input("تاریخ اختتام", date.today())
        conn = get_db_connection()
        teachers_list = ["تمام"] + [t[0] for t in conn.execute(
            "SELECT DISTINCT t_name FROM hifz_records UNION SELECT name FROM teachers WHERE name!='admin'"
        ).fetchall()]
        conn.close()
        sel_teacher = st.selectbox("استاد / کلاس", teachers_list)
        dept_filter = st.selectbox("شعبہ", ["تمام", "حفظ", "قاعدہ", "درسِ نظامی", "عصری تعلیم"])
    
    combined_df = pd.DataFrame()
    if dept_filter in ["تمام", "حفظ"]:
        conn = get_db_connection()
        try:
            hifz_df = pd.read_sql_query("""
                SELECT h.r_date as تاریخ, s.name as نام, s.father_name as 'والد کا نام',
                       s.roll_no as 'شناختی نمبر', h.t_name as استاد, 'حفظ' as شعبہ,
                       h.surah as 'سبق', h.lines as 'کل ستر', h.sq_p as 'سبقی',
                       h.sq_m as 'سبقی غلطی', h.m_p as 'منزل', h.m_m as 'منزل غلطی',
                       h.attendance as حاضری, h.cleanliness as صفائی
                FROM hifz_records h JOIN students s ON h.student_id = s.id
                WHERE h.r_date BETWEEN ? AND ?
            """, conn, params=(d1, d2))
            conn.close()
            if not hifz_df.empty and sel_teacher != "تمام":
                hifz_df = hifz_df[hifz_df['استاد'] == sel_teacher]
            combined_df = pd.concat([combined_df, hifz_df], ignore_index=True)
        except Exception as e:
            st.error(f"حفظ ریکارڈ: {str(e)}")
    
    if dept_filter in ["تمام", "قاعدہ"]:
        conn = get_db_connection()
        try:
            qaida_df = pd.read_sql_query("""
                SELECT q.r_date as تاریخ, s.name as نام, s.father_name as 'والد کا نام',
                       s.roll_no as 'شناختی نمبر', q.t_name as استاد, 'قاعدہ' as شعبہ,
                       q.lesson_no as 'سبق', q.total_lines as 'کل لائنیں',
                       q.attendance as حاضری, q.cleanliness as صفائی
                FROM qaida_records q JOIN students s ON q.student_id = s.id
                WHERE q.r_date BETWEEN ? AND ?
            """, conn, params=(d1, d2))
            conn.close()
            if not qaida_df.empty and sel_teacher != "تمام":
                qaida_df = qaida_df[qaida_df['استاد'] == sel_teacher]
            combined_df = pd.concat([combined_df, qaida_df], ignore_index=True)
        except Exception as e:
            st.error(f"قاعدہ ریکارڈ: {str(e)}")
    
    if combined_df.empty:
        st.warning("کوئی ریکارڈ نہیں ملا")
    else:
        st.success(f"✅ کل **{len(combined_df)}** ریکارڈ ملے")
        st.dataframe(combined_df, use_container_width=True)
        html_report = generate_html_report(combined_df, "یومیہ تعلیمی رپورٹ",
                                           start_date=d1.strftime("%Y-%m-%d"), end_date=d2.strftime("%Y-%m-%d"))
        col1, col2 = st.columns(2)
        col1.download_button("📥 HTML رپورٹ", html_report, "daily_report.html", "text/html")
        col2.download_button("📥 CSV ڈاؤن لوڈ", convert_df_to_csv(combined_df), "daily_report.csv", "text/csv")

# ==================== 12. امتحانی نظام ====================
elif selected == "🎓 امتحانی نظام" and st.session_state.user_type == "admin":
    st.markdown("<div class='main-header'><h1>🎓 امتحانی نظام</h1><p class='subtitle'>امتحانات کا انتظام</p></div>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["⏳ پینڈنگ امتحانات", "✅ مکمل شدہ"])
    with tab1:
        conn = get_db_connection()
        pending = conn.execute("""
            SELECT e.id, s.name, s.father_name, s.roll_no, e.dept, e.exam_type,
                   e.from_para, e.to_para, e.book_name, e.amount_read, e.start_date, e.end_date, e.total_days
            FROM exams e JOIN students s ON e.student_id = s.id WHERE e.status=?
        """, ("پینڈنگ",)).fetchall()
        conn.close()
        if not pending:
            st.info("✅ کوئی پینڈنگ امتحان نہیں")
        else:
            for eid, sn, fn, rn, dept, etype, fp, tp, book, amount, sd, ed, tdays in pending:
                with st.expander(f"👤 {sn} ولد {fn} | {rn or '—'} | {dept} | {etype}"):
                    col1, col2, col3 = st.columns(3)
                    col1.write(f"**تاریخ شروع:** {sd}")
                    col2.write(f"**تاریخ اختتام:** {ed}")
                    col3.write(f"**کل دن:** {tdays or '—'}")
                    if etype == "پارہ ٹیسٹ":
                        st.info(f"📖 پارہ نمبر: {fp} تا {tp}")
                    else:
                        st.info(f"📚 کتاب: {book} | مقدار: {amount}")
                    cols = st.columns(5)
                    q = [cols[i].number_input(f"س{i+1}", 0, 20, key=f"q{i+1}_{eid}") for i in range(5)]
                    total = sum(q)
                    if total >= 90: g = "ممتاز"
                    elif total >= 80: g = "جید جداً"
                    elif total >= 70: g = "جید"
                    elif total >= 60: g = "مقبول"
                    else: g = "ناکام"
                    st.markdown(f"**کل نمبر:** `{total}` | **گریڈ:** `{g}`")
                    if st.button("✅ کلیئر کریں", key=f"save_{eid}"):
                        conn = get_db_connection()
                        c = conn.cursor()
                        c.execute("""UPDATE exams SET q1=?,q2=?,q3=?,q4=?,q5=?,total=?,grade=?,status=?,end_date=? WHERE id=?""",
                                  (*q, total, g, "مکمل", date.today(), eid))
                        if g != "ناکام":
                            stud_id = c.execute("SELECT student_id FROM exams WHERE id=?", (eid,)).fetchone()[0]
                            if etype == "پارہ ٹیسٹ" and fp:
                                for para in range(fp, tp+1):
                                    if not c.execute("SELECT 1 FROM passed_paras WHERE student_id=? AND para_no=?", (stud_id, para)).fetchone():
                                        c.execute("INSERT INTO passed_paras (student_id, para_no, passed_date, exam_type, grade, marks) VALUES (?,?,?,?,?,?)",
                                                  (stud_id, para, date.today(), etype, g, total))
                            else:
                                if not c.execute("SELECT 1 FROM passed_paras WHERE student_id=? AND book_name=?", (stud_id, book)).fetchone():
                                    c.execute("INSERT INTO passed_paras (student_id, book_name, passed_date, exam_type, grade, marks) VALUES (?,?,?,?,?,?)",
                                              (stud_id, book, date.today(), etype, g, total))
                        conn.commit()
                        conn.close()
                        log_audit(st.session_state.username, "Exam Cleared", f"Exam ID: {eid}, Grade: {g}")
                        st.success("امتحان کلیئر کر دیا گیا")
                        st.rerun()
    with tab2:
        conn = get_db_connection()
        hist = pd.read_sql_query("""
            SELECT s.name as نام, s.father_name as 'والد', s.roll_no as 'شناختی نمبر',
                   e.dept as شعبہ, e.exam_type as 'امتحان قسم', e.total as کل, e.grade as گریڈ, e.end_date as تاریخ
            FROM exams e JOIN students s ON e.student_id = s.id WHERE e.status='مکمل' ORDER BY e.end_date DESC
        """, conn)
        conn.close()
        if not hist.empty:
            st.dataframe(hist, use_container_width=True)
            st.download_button("📥 CSV", convert_df_to_csv(hist), "exam_history.csv")
        else:
            st.info("کوئی مکمل شدہ امتحان نہیں")

# ==================== 13. ماہانہ رزلٹ کارڈ ====================
elif selected == "📜 ماہانہ رزلٹ کارڈ" and st.session_state.user_type == "admin":
    st.markdown("<div class='main-header'><h1>📜 ماہانہ رزلٹ کارڈ</h1><p class='subtitle'>طالب علم کی ماہانہ کارکردگی</p></div>", unsafe_allow_html=True)
    conn = get_db_connection()
    students_list = conn.execute("SELECT id, name, father_name, roll_no, dept FROM students").fetchall()
    conn.close()
    if not students_list:
        st.warning("کوئی طالب علم نہیں")
    else:
        student_names = [f"{s[1]} ولد {s[2]} ({s[3] or 'بغیر نمبر'}) - {s[4]}" for s in students_list]
        sel = st.selectbox("طالب علم منتخب کریں", student_names)
        idx = student_names.index(sel)
        student_id, s_name, f_name, roll_no, dept = students_list[idx]
        
        col1, col2 = st.columns(2)
        start = col1.date_input("تاریخ آغاز", date.today().replace(day=1))
        end = col2.date_input("تاریخ اختتام", date.today())
        
        if dept == "حفظ":
            conn = get_db_connection()
            df = pd.read_sql_query("""
                SELECT r_date as تاریخ, attendance as حاضری, surah as سبق, lines as ستر,
                       sq_p as سبقی, sq_m as 'سبقی غلطی', m_p as منزل, m_m as 'منزل غلطی', cleanliness as صفائی
                FROM hifz_records WHERE student_id=? AND r_date BETWEEN ? AND ? ORDER BY r_date
            """, conn, params=(student_id, start, end))
            conn.close()
            if not df.empty:
                grades = []
                for _, row in df.iterrows():
                    att = row['حاضری']
                    sn = row['سبق'] in ["ناغہ", "یاد نہیں"]
                    sqn = row['سبقی'] in ["ناغہ", "یاد نہیں"]
                    mn = row['منزل'] in ["ناغہ", "یاد نہیں"]
                    grade = calculate_grade_with_attendance(att, sn, sqn, mn,
                                                           row['سبقی غلطی'] or 0, row['منزل غلطی'] or 0)
                    grades.append(grade)
                df['درجہ'] = grades
                st.dataframe(df, use_container_width=True)
                html = generate_html_report(df, "ماہانہ رزلٹ کارڈ (حفظ)",
                                            student_name=f"{s_name} ولد {f_name}",
                                            start_date=str(start), end_date=str(end))
                st.download_button("📥 ڈاؤن لوڈ", html, f"{s_name}_result.html", "text/html")
        elif dept == "قاعدہ":
            conn = get_db_connection()
            df = pd.read_sql_query("""
                SELECT r_date as تاریخ, lesson_no as 'تختی نمبر', total_lines as لائنیں,
                       attendance as حاضری, cleanliness as صفائی
                FROM qaida_records WHERE student_id=? AND r_date BETWEEN ? AND ? ORDER BY r_date
            """, conn, params=(student_id, start, end))
            conn.close()
            if not df.empty:
                st.dataframe(df, use_container_width=True)
                html = generate_html_report(df, "ماہانہ رزلٹ کارڈ (قاعدہ)",
                                            student_name=f"{s_name} ولد {f_name}",
                                            start_date=str(start), end_date=str(end))
                st.download_button("📥 ڈاؤن لوڈ", html, f"{s_name}_qaida.html", "text/html")
            else:
                st.warning("کوئی ریکارڈ نہیں")
        else:
            conn = get_db_connection()
            df = pd.read_sql_query("""
                SELECT r_date as تاریخ, book_subject as 'کتاب', today_lesson as 'آج کا سبق',
                       performance as کارکردگی, attendance as حاضری, cleanliness as صفائی
                FROM general_education WHERE student_id=? AND dept=? AND r_date BETWEEN ? AND ? ORDER BY r_date
            """, conn, params=(student_id, dept, start, end))
            conn.close()
            if not df.empty:
                st.dataframe(df, use_container_width=True)
                html = generate_html_report(df, "ماہانہ رزلٹ کارڈ",
                                            student_name=f"{s_name} ولد {f_name}",
                                            start_date=str(start), end_date=str(end))
                st.download_button("📥 ڈاؤن لوڈ", html, f"{s_name}_result.html", "text/html")
            else:
                st.warning("کوئی ریکارڈ نہیں")

# ==================== 14. پارہ تعلیمی رپورٹ ====================
elif selected == "📘 پارہ تعلیمی رپورٹ" and st.session_state.user_type == "admin":
    st.markdown("<div class='main-header'><h1>📘 پارہ تعلیمی رپورٹ</h1></div>", unsafe_allow_html=True)
    conn = get_db_connection()
    students_list = conn.execute("SELECT id, name, father_name FROM students WHERE dept='حفظ'").fetchall()
    conn.close()
    if not students_list:
        st.warning("کوئی حفظ کا طالب علم نہیں")
    else:
        student_names = [f"{s[1]} ولد {s[2]}" for s in students_list]
        sel = st.selectbox("طالب علم منتخب کریں", student_names)
        idx = student_names.index(sel)
        student_id, s_name, f_name = students_list[idx]
        conn = get_db_connection()
        passed_df = pd.read_sql_query("""
            SELECT para_no as 'پارہ نمبر', passed_date as 'تاریخ پاس',
                   exam_type as 'امتحان قسم', grade as گریڈ, marks as نمبر
            FROM passed_paras WHERE student_id=? AND para_no IS NOT NULL ORDER BY para_no
        """, conn, params=(student_id,))
        conn.close()
        if passed_df.empty:
            st.info("کوئی پاس شدہ پارہ نہیں")
        else:
            total_paras = 30
            passed_count = len(passed_df)
            progress = passed_count / total_paras
            st.markdown(f"""
            <div class="report-card">
                <p style="color:#1e5631;font-weight:700;margin-bottom:0.5rem">
                    قرآن مجید کی پیشرفت: {passed_count}/30 پارے
                </p>
                <div style="background:#e5e7eb;border-radius:10px;overflow:hidden;height:20px">
                    <div style="width:{progress*100:.0f}%;height:100%;
                                background:linear-gradient(90deg,#1e5631,#c9a227);
                                border-radius:10px;transition:width 0.5s"></div>
                </div>
                <p style="color:#6b7280;font-size:0.85rem;margin-top:0.3rem">
                    {progress*100:.1f}% مکمل
                </p>
            </div>
            """, unsafe_allow_html=True)
            st.dataframe(passed_df, use_container_width=True)
            html = generate_para_report(s_name, f_name, passed_df)
            st.download_button("📥 رپورٹ ڈاؤن لوڈ", html, f"Para_{s_name}.html", "text/html")

# ==================== 15. اساتذہ حاضری ====================
elif selected == "🕒 اساتذہ حاضری" and st.session_state.user_type == "admin":
    st.markdown("<div class='main-header'><h1>🕒 اساتذہ حاضری ریکارڈ</h1></div>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    d1 = col1.date_input("تاریخ سے", date.today().replace(day=1))
    d2 = col2.date_input("تاریخ تک", date.today())
    conn = get_db_connection()
    df = pd.read_sql_query("""
        SELECT a_date as تاریخ, t_name as استاد, arrival as آمد, departure as رخصت
        FROM t_attendance WHERE a_date BETWEEN ? AND ? ORDER BY a_date DESC
    """, conn, params=(d1, d2))
    conn.close()
    if df.empty:
        st.info("کوئی ریکارڈ نہیں")
    else:
        st.dataframe(df, use_container_width=True)
        st.download_button("📥 CSV", convert_df_to_csv(df), "attendance.csv")

# ==================== 16. رخصت کی منظوری ====================
elif selected == "🏛️ رخصت کی منظوری" and st.session_state.user_type == "admin":
    st.markdown("<div class='main-header'><h1>🏛️ رخصت کی منظوری</h1></div>", unsafe_allow_html=True)
    conn = get_db_connection()
    try:
        pending = conn.execute(
            "SELECT id, t_name, l_type, reason, start_date, days FROM leave_requests WHERE status LIKE ?",
            ('%پینڈنگ%',)
        ).fetchall()
    except:
        pending = []
    conn.close()
    if not pending:
        st.markdown("""
        <div style="text-align:center;padding:3rem;color:#16a34a">
            <span style="font-size:3rem">✅</span>
            <p style="font-size:1.2rem;font-weight:600;margin-top:1rem">کوئی پینڈنگ درخواست نہیں</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        for l_id, t_n, l_t, reas, s_d, dys in pending:
            with st.expander(f"👤 {t_n} | 📋 {l_t} | 📅 {dys} دن"):
                st.markdown(f"**وجہ:** {reas}")
                st.markdown(f"**تاریخ شروع:** {s_d}")
                col1, col2 = st.columns(2)
                if col1.button("✅ منظور کریں", key=f"app_{l_id}", use_container_width=True):
                    conn = get_db_connection()
                    conn.execute("UPDATE leave_requests SET status='منظور' WHERE id=?", (l_id,))
                    conn.commit()
                    conn.close()
                    log_audit(st.session_state.username, "Leave Approved", f"ID: {l_id}, Teacher: {t_n}")
                    st.rerun()
                if col2.button("❌ مسترد کریں", key=f"rej_{l_id}", use_container_width=True):
                    conn = get_db_connection()
                    conn.execute("UPDATE leave_requests SET status='مسترد' WHERE id=?", (l_id,))
                    conn.commit()
                    conn.close()
                    log_audit(st.session_state.username, "Leave Rejected", f"ID: {l_id}, Teacher: {t_n}")
                    st.rerun()

# ==================== 17. یوزر مینجمنٹ ====================
elif selected == "👥 یوزر مینجمنٹ" and st.session_state.user_type == "admin":
    st.markdown("<div class='main-header'><h1>👥 یوزر مینجمنٹ</h1><p class='subtitle'>اساتذہ اور طلباء کا انتظام</p></div>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["👩‍🏫 اساتذہ", "👨‍🎓 طلبہ"])
    
    with tab1:
        st.subheader("موجودہ اساتذہ")
        conn = get_db_connection()
        teachers_df = pd.read_sql_query(
            "SELECT id, name, dept, phone, id_card, joining_date FROM teachers WHERE name!='admin'", conn
        )
        conn.close()
        if not teachers_df.empty:
            st.dataframe(teachers_df, use_container_width=True)
        
        with st.expander("➕ نیا استاد رجسٹر کریں"):
            with st.form("new_teacher_form"):
                col1, col2 = st.columns(2)
                name = col1.text_input("استاد کا نام*")
                password = col2.text_input("پاسورڈ*", type="password")
                dept = col1.selectbox("شعبہ", ["حفظ", "قاعدہ", "درسِ نظامی", "عصری تعلیم"])
                phone = col2.text_input("فون نمبر")
                id_card = col1.text_input("شناختی کارڈ نمبر (مثلاً: 35201-1234567-1)")
                joining_date = col2.date_input("تاریخ شمولیت", date.today())
                address = st.text_area("پتہ")
                if st.form_submit_button("✅ رجسٹر کریں"):
                    name = sanitize_input(name, 100)
                    errors = []
                    if not name: errors.append("نام ضروری ہے")
                    if not password: errors.append("پاسورڈ ضروری ہے")
                    else:
                        valid, msg = verify_password_strength(password)
                        if not valid: errors.append(msg)
                    if phone and not validate_phone(phone): errors.append("فون نمبر غلط ہے")
                    if errors:
                        for e in errors: st.error(e)
                    else:
                        conn = get_db_connection()
                        try:
                            conn.execute("""INSERT INTO teachers (name, password, dept, phone, address, id_card, joining_date)
                                          VALUES (?,?,?,?,?,?,?)""",
                                        (name, hash_password(password), dept, phone,
                                         sanitize_input(address), sanitize_input(id_card), joining_date))
                            conn.commit()
                            log_audit(st.session_state.username, "Teacher Added", f"Name: {name}")
                            st.success("استاد کامیابی سے رجسٹر ہو گیا")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("یہ نام پہلے سے موجود ہے")
                        finally:
                            conn.close()
        
        with st.expander("⚠️ استاد غیر فعال کریں"):
            conn = get_db_connection()
            active_teachers = [t[0] for t in conn.execute(
                "SELECT name FROM teachers WHERE name!='admin' AND is_active=1"
            ).fetchall()]
            conn.close()
            if active_teachers:
                deactivate_name = st.selectbox("استاد منتخب کریں", active_teachers, key="deact")
                if st.button("غیر فعال کریں"):
                    conn = get_db_connection()
                    conn.execute("UPDATE teachers SET is_active=0 WHERE name=?", (deactivate_name,))
                    conn.commit()
                    conn.close()
                    log_audit(st.session_state.username, "Teacher Deactivated", f"Name: {deactivate_name}")
                    st.success("استاد غیر فعال کر دیا گیا")
                    st.rerun()
    
    with tab2:
        st.subheader("موجودہ طلبہ")
        conn = get_db_connection()
        students_df = pd.read_sql_query(
            "SELECT id, name, father_name, dept, roll_no, teacher_name FROM students", conn
        )
        conn.close()
        if not students_df.empty:
            st.dataframe(students_df, use_container_width=True)
        
        with st.expander("➕ نیا طالب علم داخل کریں"):
            with st.form("new_student_form"):
                col1, col2 = st.columns(2)
                name = col1.text_input("طالب علم کا نام*")
                father = col2.text_input("والد کا نام*")
                mother = col1.text_input("والدہ کا نام")
                dob = col2.date_input("تاریخ پیدائش", date.today() - timedelta(days=365*10))
                admission_date = col1.date_input("تاریخ داخلہ", date.today())
                roll_no = col2.text_input("شناختی نمبر", placeholder="مثلاً: 2024-001")
                dept = col1.selectbox("شعبہ*", ["حفظ", "قاعدہ", "درسِ نظامی", "عصری تعلیم"])
                conn = get_db_connection()
                teachers_list = [t[0] for t in conn.execute("SELECT name FROM teachers WHERE name!='admin' AND is_active=1").fetchall()]
                conn.close()
                teacher = col2.selectbox("استاد*", teachers_list) if teachers_list else col2.text_input("استاد کا نام*")
                phone = col1.text_input("فون نمبر")
                address = st.text_area("پتہ")
                if st.form_submit_button("✅ داخلہ کریں"):
                    name = sanitize_input(name, 100)
                    father = sanitize_input(father, 100)
                    errors = []
                    if not name: errors.append("نام ضروری ہے")
                    if not father: errors.append("والد کا نام ضروری ہے")
                    if phone and not validate_phone(phone): errors.append("فون نمبر غلط ہے")
                    if errors:
                        for e in errors: st.error(e)
                    else:
                        conn = get_db_connection()
                        try:
                            conn.execute("""INSERT INTO students
                                          (name, father_name, mother_name, dob, admission_date, phone, address,
                                           teacher_name, dept, roll_no) VALUES (?,?,?,?,?,?,?,?,?,?)""",
                                        (name, father, sanitize_input(mother), dob, admission_date,
                                         phone, sanitize_input(address, 300), teacher, dept, roll_no))
                            conn.commit()
                            log_audit(st.session_state.username, "Student Added", f"Name: {name}")
                            st.success("طالب علم کامیابی سے داخل ہو گیا")
                            st.rerun()
                        except Exception as e:
                            st.error(f"خرابی: {str(e)}")
                        finally:
                            conn.close()

# ==================== 18. ٹائم ٹیبل ====================
elif selected == "📚 ٹائم ٹیبل مینجمنٹ" and st.session_state.user_type == "admin":
    st.markdown("<div class='main-header'><h1>📚 ٹائم ٹیبل مینجمنٹ</h1></div>", unsafe_allow_html=True)
    conn = get_db_connection()
    teachers = [t[0] for t in conn.execute("SELECT name FROM teachers WHERE name!='admin' AND is_active=1").fetchall()]
    conn.close()
    if not teachers:
        st.warning("پہلے اساتذہ رجسٹر کریں")
    else:
        sel_t = st.selectbox("استاد منتخب کریں", teachers)
        conn = get_db_connection()
        tt_df = pd.read_sql_query(
            "SELECT id, day as دن, period as وقت, book as کتاب, room as کمرہ FROM timetable WHERE t_name=?",
            conn, params=(sel_t,)
        )
        conn.close()
        if not tt_df.empty:
            st.subheader("موجودہ ٹائم ٹیبل")
            day_order = {"ہفتہ": 0, "اتوار": 1, "پیر": 2, "منگل": 3, "بدھ": 4, "جمعرات": 5}
            tt_df['day_order'] = tt_df['دن'].map(day_order)
            tt_df = tt_df.sort_values(['day_order', 'وقت'])
            st.dataframe(tt_df[['دن', 'وقت', 'کتاب', 'کمرہ']], use_container_width=True)
        with st.expander("➕ نیا پیریڈ شامل کریں"):
            with st.form("add_period"):
                col1, col2 = st.columns(2)
                day = col1.selectbox("دن", ["ہفتہ", "اتوار", "پیر", "منگل", "بدھ", "جمعرات"])
                period = col2.text_input("وقت (مثلاً 08:00-09:00)")
                book = col1.text_input("کتاب / مضمون")
                room = col2.text_input("کمرہ نمبر")
                if st.form_submit_button("✅ شامل کریں"):
                    conn = get_db_connection()
                    conn.execute("INSERT INTO timetable (t_name, day, period, book, room) VALUES (?,?,?,?,?)",
                                 (sel_t, day, sanitize_input(period), sanitize_input(book), sanitize_input(room)))
                    conn.commit()
                    conn.close()
                    st.success("پیریڈ شامل کر دیا گیا")
                    st.rerun()

# ==================== 19. پاسورڈ تبدیل کریں ====================
elif selected == "🔑 پاسورڈ تبدیل کریں":
    st.markdown("<div class='main-header'><h1>🔑 پاسورڈ تبدیل کریں</h1></div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<div class='report-card'>", unsafe_allow_html=True)
        
        if st.session_state.user_type == "admin":
            conn = get_db_connection()
            teachers = [t[0] for t in conn.execute("SELECT name FROM teachers WHERE name!='admin'").fetchall()]
            conn.close()
            if teachers:
                selected_teacher = st.selectbox("استاد منتخب کریں", teachers)
                new_pass = st.text_input("نیا پاسورڈ", type="password")
                confirm_pass = st.text_input("پاسورڈ کی تصدیق", type="password")
                
                if new_pass:
                    valid, msg = verify_password_strength(new_pass)
                    if valid:
                        st.success(f"✅ {msg}")
                    else:
                        st.warning(f"⚠️ {msg}")
                
                if st.button("✅ پاسورڈ تبدیل کریں"):
                    if new_pass and new_pass == confirm_pass:
                        ok, msg = admin_reset_password(selected_teacher, new_pass)
                        if ok:
                            st.success(f"{selected_teacher} کا پاسورڈ تبدیل کر دیا گیا")
                        else:
                            st.error(msg)
                    else:
                        st.error("پاسورڈ میل نہیں کھاتے یا خالی ہیں")
        else:
            old_pass = st.text_input("پرانا پاسورڈ", type="password")
            new_pass = st.text_input("نیا پاسورڈ", type="password")
            confirm_pass = st.text_input("نیا پاسورڈ دوبارہ", type="password")
            
            if new_pass:
                valid, msg = verify_password_strength(new_pass)
                if valid:
                    st.success(f"✅ پاسورڈ مضبوط ہے")
                else:
                    st.warning(f"⚠️ {msg}")
            
            if st.button("✅ پاسورڈ تبدیل کریں"):
                if old_pass and new_pass and new_pass == confirm_pass:
                    ok, msg = change_password(st.session_state.username, old_pass, new_pass)
                    if ok:
                        st.success("پاسورڈ تبدیل ہو گیا۔ دوبارہ لاگ ان کریں۔")
                        st.session_state.logged_in = False
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.error("تمام فیلڈز درج کریں اور پاسورڈ یکساں ہوں")
        
        st.markdown("""
        <div class="security-info">
            🔒 پاسورڈ کی ضروریات: کم از کم 8 حروف، ایک عدد ضرور شامل کریں
        </div>
        </div>
        """, unsafe_allow_html=True)

# ==================== 20. نوٹیفیکیشنز ====================
elif selected == "📢 نوٹیفیکیشنز":
    st.markdown("<div class='main-header'><h1>📢 نوٹیفیکیشن سینٹر</h1></div>", unsafe_allow_html=True)
    if st.session_state.user_type == "admin":
        with st.expander("➕ نیا نوٹیفیکیشن بھیجیں"):
            with st.form("new_notif"):
                title = st.text_input("عنوان")
                msg = st.text_area("پیغام")
                target = st.selectbox("بھیجیں", ["تمام", "اساتذہ", "طلبہ"])
                if st.form_submit_button("📤 بھیجیں"):
                    if title and msg:
                        conn = get_db_connection()
                        conn.execute(
                            "INSERT INTO notifications (title, message, target, created_at) VALUES (?,?,?,?)",
                            (sanitize_input(title), sanitize_input(msg, 1000), target, datetime.now())
                        )
                        conn.commit()
                        conn.close()
                        st.success("نوٹیفیکیشن بھیج دیا گیا")
                    else:
                        st.warning("عنوان اور پیغام ضروری ہیں")
    
    conn = get_db_connection()
    if st.session_state.user_type == "admin":
        notifs = conn.execute(
            "SELECT title, message, target, created_at FROM notifications ORDER BY created_at DESC LIMIT 20"
        ).fetchall()
    else:
        notifs = conn.execute(
            "SELECT title, message, target, created_at FROM notifications WHERE target IN ('تمام','اساتذہ') ORDER BY created_at DESC LIMIT 10"
        ).fetchall()
    conn.close()
    
    if not notifs:
        st.info("کوئی نوٹیفیکیشن نہیں")
    else:
        for n in notifs:
            st.markdown(f"""
            <div class="report-card" style="border-right:4px solid #1e5631">
                <h4 style="color:#1e5631;margin:0 0 0.4rem">🔔 {n[0]}</h4>
                <p style="color:#374151;margin:0 0 0.5rem">{n[1]}</p>
                <small style="color:#9ca3af">📅 {n[3]} | 👥 {n[2]}</small>
            </div>
            """, unsafe_allow_html=True)

# ==================== 21. تجزیہ ====================
elif selected == "📈 تجزیہ و رپورٹس" and st.session_state.user_type == "admin":
    st.markdown("<div class='main-header'><h1>📈 تجزیہ و رپورٹس</h1></div>", unsafe_allow_html=True)
    conn = get_db_connection()
    
    dept_df = pd.read_sql_query("SELECT dept as شعبہ, COUNT(*) as تعداد FROM students GROUP BY dept", conn)
    if not dept_df.empty:
        col1, col2 = st.columns(2)
        with col1:
            fig = px.pie(dept_df, values='تعداد', names='شعبہ', title='طلباء بہ شعبہ',
                         color_discrete_sequence=['#1e5631', '#2d7a47', '#c9a227', '#f0d060'])
            fig.update_layout(font_family="Noto Nastaliq Urdu")
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig2 = px.bar(dept_df, x='شعبہ', y='تعداد', title='شعبہ وار طلباء',
                          color='تعداد', color_continuous_scale=['#e8f5e9', '#1e5631'])
            fig2.update_layout(font_family="Noto Nastaliq Urdu")
            st.plotly_chart(fig2, use_container_width=True)
    
    exam_df = pd.read_sql_query(
        "SELECT grade as گریڈ, COUNT(*) as تعداد FROM exams WHERE status='مکمل' AND grade IS NOT NULL GROUP BY grade",
        conn
    )
    if not exam_df.empty:
        fig3 = px.bar(exam_df, x='گریڈ', y='تعداد', title='امتحانی نتائج',
                      color='گریڈ', color_discrete_sequence=['#1e5631', '#2d7a47', '#c9a227', '#e74c3c', '#f39c12'])
        fig3.update_layout(font_family="Noto Nastaliq Urdu")
        st.plotly_chart(fig3, use_container_width=True)
    
    conn.close()

# ==================== 22. ماہانہ بہترین طلباء ====================
elif selected == "🏆 ماہانہ بہترین طلباء" and st.session_state.user_type == "admin":
    st.markdown("""
    <div class='main-header'>
        <h1>🏆 ماہانہ بہترین طلباء</h1>
        <p class='subtitle'>تعلیمی اور صفائی کی بنیاد پر بہترین کارکردگی</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    month_year = col1.date_input("مہینہ منتخب کریں", date.today().replace(day=1))
    dept_filter = col2.selectbox("شعبہ", ["تمام", "حفظ", "قاعدہ", "درسِ نظامی", "عصری تعلیم"])
    
    start_date = month_year.replace(day=1)
    if month_year.month == 12:
        end_date = month_year.replace(year=month_year.year+1, month=1, day=1) - timedelta(days=1)
    else:
        end_date = month_year.replace(month=month_year.month+1, day=1) - timedelta(days=1)
    
    st.markdown(f"<p style='color:#6b7280'>📅 {start_date.strftime('%B %Y')} کے نتائج</p>", unsafe_allow_html=True)
    
    conn = get_db_connection()
    query = "SELECT id, name, father_name, roll_no, dept FROM students"
    if dept_filter != "تمام":
        query += f" WHERE dept='{dept_filter}'"
    students = conn.execute(query).fetchall()
    conn.close()
    
    if not students:
        st.warning("کوئی طالب علم موجود نہیں")
    else:
        student_scores = []
        for sid, name, father, roll, dept in students:
            conn = get_db_connection()
            if dept == "حفظ":
                records = conn.execute("""
                    SELECT attendance, surah, sq_p, m_p, sq_m, m_m, cleanliness
                    FROM hifz_records WHERE student_id=? AND r_date BETWEEN ? AND ?
                """, (sid, start_date, end_date)).fetchall()
                grade_scores = []
                clean_scores = []
                for rec in records:
                    att, surah, sq_p, m_p, sq_m, m_m, clean = rec
                    sn = surah in ["ناغہ", "یاد نہیں"]
                    sqn = (sq_p or "") in ["ناغہ", "یاد نہیں"]
                    mn = (m_p or "") in ["ناغہ", "یاد نہیں"]
                    grade = calculate_grade_with_attendance(att, sn, sqn, mn, sq_m or 0, m_m or 0)
                    score_map = {"ممتاز": 100, "جید جداً": 85, "جید": 75, "مقبول": 60,
                                 "دوبارہ کوشش کریں": 40, "ناقص (ناغہ)": 30, "کمزور (ناغہ)": 20,
                                 "ناکام (مکمل ناغہ)": 10, "غیر حاضر": 0, "رخصت": 50}
                    grade_scores.append(score_map.get(grade, 0))
                    if clean:
                        clean_scores.append(cleanliness_to_score(clean))
            else:
                records = conn.execute("""
                    SELECT attendance, performance, cleanliness FROM general_education
                    WHERE student_id=? AND dept=? AND r_date BETWEEN ? AND ?
                """, (sid, dept, start_date, end_date)).fetchall()
                grade_scores = []
                clean_scores = []
                for rec in records:
                    att, perf, clean = rec
                    perf_map = {"بہت بہتر": 90, "بہتر": 80, "مناسب": 65, "کمزور": 45}
                    if att == "حاضر":
                        grade_scores.append(perf_map.get(perf or "", 75))
                    elif att == "رخصت":
                        grade_scores.append(50)
                    else:
                        grade_scores.append(0)
                    if clean:
                        clean_scores.append(cleanliness_to_score(clean))
            conn.close()
            
            avg_grade = sum(grade_scores)/len(grade_scores) if grade_scores else 0
            avg_clean = sum(clean_scores)/len(clean_scores) if clean_scores else 0
            student_scores.append({
                "id": sid, "name": name, "father": father, "roll": roll, "dept": dept,
                "avg_grade": avg_grade, "avg_clean": avg_clean, "total_days": len(grade_scores)
            })
        
        sorted_grade = sorted(student_scores, key=lambda x: x["avg_grade"], reverse=True)
        sorted_clean = sorted(student_scores, key=lambda x: x["avg_clean"], reverse=True)
        
        st.markdown("---")
        st.subheader("📚 تعلیمی کارکردگی کے لحاظ سے بہترین طلباء")
        col1, col2, col3 = st.columns(3)
        medals = [("🥇", "medal-gold"), ("🥈", "medal-silver"), ("🥉", "medal-bronze")]
        for i, (col, student) in enumerate(zip([col1, col2, col3], sorted_grade[:3])):
            if student['avg_grade'] > 0:
                medal, medal_class = medals[i]
                with col:
                    st.markdown(f"""
                    <div class="best-student-card">
                        <span class="{medal_class}">{medal}</span>
                        <div class="student-name-card">{student['name']}</div>
                        <div class="student-detail-card">والد: {student['father']}</div>
                        <div class="student-detail-card">🏫 {student['dept']}</div>
                        <div class="student-detail-card">📅 {student['total_days']} دن</div>
                        <div class="score-badge">{student['avg_grade']:.1f}%</div>
                    </div>
                    """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.subheader("🧹 صفائی کے لحاظ سے بہترین طلباء")
        col1, col2, col3 = st.columns(3)
        for i, (col, student) in enumerate(zip([col1, col2, col3], sorted_clean[:3])):
            if student['avg_clean'] > 0:
                medal, medal_class = medals[i]
                with col:
                    clean_percent = (student['avg_clean'] / 3) * 100
                    st.markdown(f"""
                    <div class="best-student-card">
                        <span class="{medal_class}">{medal}</span>
                        <div class="student-name-card">{student['name']}</div>
                        <div class="student-detail-card">والد: {student['father']}</div>
                        <div class="student-detail-card">🏫 {student['dept']}</div>
                        <div class="score-badge">🧹 {clean_percent:.1f}%</div>
                    </div>
                    """, unsafe_allow_html=True)
        
        with st.expander("📊 تمام طلباء کی تفصیل"):
            df_all = pd.DataFrame(student_scores)
            df_all = df_all.rename(columns={
                "name": "نام", "father": "والد", "roll": "شناختی نمبر", "dept": "شعبہ",
                "avg_grade": "تعلیمی %", "avg_clean": "صفائی (0-3)", "total_days": "کل دن"
            })
            df_all["تعلیمی %"] = df_all["تعلیمی %"].round(1)
            df_all["صفائی (0-3)"] = df_all["صفائی (0-3)"].round(2)
            df_all = df_all[["نام", "والد", "شناختی نمبر", "شعبہ", "تعلیمی %", "صفائی (0-3)", "کل دن"]]
            st.dataframe(df_all.sort_values("تعلیمی %", ascending=False), use_container_width=True)
            st.download_button("📥 CSV", convert_df_to_csv(df_all), "best_students.csv")

# ==================== 23. عملہ نگرانی ====================
elif selected == "📋 عملہ نگرانی و شکایات" and st.session_state.user_type == "admin":
    st.markdown("<div class='main-header'><h1>📋 عملہ نگرانی و شکایات</h1></div>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["➕ نیا اندراج", "📜 ریکارڈ دیکھیں"])
    with tab1:
        with st.form("new_monitoring"):
            conn = get_db_connection()
            staff_list = [t[0] for t in conn.execute("SELECT name FROM teachers WHERE name!='admin' AND is_active=1").fetchall()]
            conn.close()
            if not staff_list:
                st.warning("کوئی عملہ موجود نہیں")
            else:
                staff_name = st.selectbox("عملہ کا نام", staff_list)
                note_date = st.date_input("تاریخ", date.today())
                note_type = st.selectbox("نوعیت", ["یادداشت", "شکایت", "تنبیہ", "تعریف", "کارکردگی جائزہ"])
                description = st.text_area("تفصیل", height=150, max_chars=1000)
                action_taken = st.text_area("کیا کارروائی کی گئی؟", height=100, max_chars=500)
                status = st.selectbox("حالت", ["زیر التواء", "حل شدہ", "زیر غور"])
                if st.form_submit_button("✅ محفوظ کریں"):
                    if description:
                        conn = get_db_connection()
                        conn.execute("""INSERT INTO staff_monitoring
                                      (staff_name, date, note_type, description, action_taken, status, created_by, created_at)
                                      VALUES (?,?,?,?,?,?,?,?)""",
                                    (staff_name, note_date, note_type,
                                     sanitize_input(description, 1000), sanitize_input(action_taken, 500),
                                     status, st.session_state.username, datetime.now()))
                        conn.commit()
                        conn.close()
                        log_audit(st.session_state.username, "Staff Monitoring Added", f"{staff_name} - {note_type}")
                        st.success("اندراج محفوظ ہو گیا")
                        st.rerun()
                    else:
                        st.warning("تفصیل ضروری ہے")
    with tab2:
        conn = get_db_connection()
        df = pd.read_sql_query("""
            SELECT staff_name as 'عملہ', date as تاریخ, note_type as نوعیت,
                   description as تفصیل, status as حالت, created_by as داخل کردہ
            FROM staff_monitoring ORDER BY date DESC
        """, conn)
        conn.close()
        if df.empty:
            st.info("کوئی ریکارڈ نہیں")
        else:
            st.dataframe(df, use_container_width=True)
            st.download_button("📥 CSV", convert_df_to_csv(df), "staff_monitoring.csv")

# ==================== 24. بیک اپ ====================
elif selected == "⚙️ بیک اپ & سیٹنگز" and st.session_state.user_type == "admin":
    st.markdown("<div class='main-header'><h1>⚙️ بیک اپ & سیٹنگز</h1></div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<div class='report-card'>", unsafe_allow_html=True)
        st.subheader("📥 ڈیٹا بیس بیک اپ")
        if os.path.exists(DB_NAME):
            with open(DB_NAME, "rb") as f:
                st.download_button(
                    label="💾 مکمل ڈیٹا بیس (.db)",
                    data=f,
                    file_name=f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db",
                    mime="application/x-sqlite3",
                    use_container_width=True
                )
        if st.button("💾 CSV زپ بیک اپ بنائیں", use_container_width=True):
            tables = ["teachers", "students", "hifz_records", "qaida_records", "general_education",
                      "t_attendance", "exams", "passed_paras", "timetable", "leave_requests",
                      "notifications", "audit_log", "staff_monitoring"]
            conn = get_db_connection()
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                for t in tables:
                    try:
                        df = pd.read_sql_query(f"SELECT * FROM {t}", conn)
                        zf.writestr(f"{t}.csv", df.to_csv(index=False).encode('utf-8-sig'))
                    except:
                        pass
            conn.close()
            zip_buffer.seek(0)
            st.download_button("📥 CSV زپ ڈاؤن لوڈ", zip_buffer,
                               f"csv_backup_{datetime.now().strftime('%Y%m%d')}.zip", "application/zip",
                               use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col2:
        st.markdown("<div class='report-card'>", unsafe_allow_html=True)
        st.subheader("🔄 ڈیٹا بیس ریسٹور")
        st.warning("⚠️ موجودہ ڈیٹا ختم ہو جائے گا!")
        uploaded_db = st.file_uploader(".db فائل اپ لوڈ کریں", type=["db"])
        if uploaded_db:
            confirm = st.checkbox("میں سمجھتا/سمجھتی ہوں کہ موجودہ ڈیٹا ختم ہو گا")
            if confirm and st.button("🔄 ریسٹور کریں"):
                if os.path.exists(DB_NAME):
                    shutil.copy(DB_NAME, f"{DB_NAME}_backup_{datetime.now().strftime('%Y%m%d%H%M%S')}.db")
                with open(DB_NAME, "wb") as f:
                    f.write(uploaded_db.getbuffer())
                log_audit(st.session_state.username, "Database Restored", "Full restore")
                st.success("ریسٹور مکمل")
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("<div class='report-card'>", unsafe_allow_html=True)
    st.subheader("📋 آڈٹ لاگ (حالیہ 50 اندراج)")
    conn = get_db_connection()
    logs = pd.read_sql_query(
        "SELECT user as صارف, action as عمل, timestamp as وقت, details as تفصیل FROM audit_log ORDER BY timestamp DESC LIMIT 50",
        conn
    )
    conn.close()
    if not logs.empty:
        st.dataframe(logs, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ==================== 25. استاد: روزانہ سبق ====================
elif selected == "📝 روزانہ سبق اندراج" and st.session_state.user_type == "teacher":
    st.markdown("<div class='main-header'><h1>📝 روزانہ سبق اندراج</h1></div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    entry_date = col1.date_input("تاریخ", date.today())
    dept = col2.selectbox("شعبہ", ["حفظ", "قاعدہ", "درسِ نظامی", "عصری تعلیم"])
    
    if dept == "حفظ":
        conn = get_db_connection()
        students = conn.execute(
            "SELECT id, name, father_name FROM students WHERE teacher_name=? AND dept='حفظ'",
            (st.session_state.username,)
        ).fetchall()
        conn.close()
        if not students:
            st.info("آپ کی کلاس میں کوئی حفظ کا طالب علم نہیں")
        else:
            for sid, s, f in students:
                key = f"{sid}_{s}_{f}"
                st.markdown(f"""
                <div class="report-card">
                    <h4 style="color:#1e5631;margin:0 0 0.8rem">👤 {s} ولد {f}</h4>
                """, unsafe_allow_html=True)
                
                conn = get_db_connection()
                existing = conn.execute(
                    "SELECT 1 FROM hifz_records WHERE r_date=? AND student_id=?",
                    (entry_date, sid)
                ).fetchone()
                conn.close()
                if existing:
                    st.warning(f"⚠️ {s} کا آج ({entry_date}) کا ریکارڈ پہلے سے موجود ہے")
                    st.markdown("</div>", unsafe_allow_html=True)
                    continue
                
                att = st.radio("حاضری", ["حاضر", "غیر حاضر", "رخصت"], key=f"att_{key}", horizontal=True)
                cleanliness = st.selectbox("صفائی", cleanliness_options, key=f"clean_{key}")
                
                if att != "حاضر":
                    grade = calculate_grade_with_attendance(att, False, False, False, 0, 0)
                    st.info(f"**درجہ:** {grade}")
                    if st.button(f"💾 محفوظ کریں ({s})", key=f"save_absent_{key}"):
                        conn = get_db_connection()
                        conn.execute("""INSERT INTO hifz_records
                                       (r_date, student_id, t_name, surah, lines, sq_p, sq_a, sq_m,
                                        m_p, m_a, m_m, attendance, cleanliness)
                                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                                    (entry_date, sid, st.session_state.username, "غائب", 0, "غائب",
                                     0, 0, "غائب", 0, 0, att, cleanliness))
                        conn.commit()
                        conn.close()
                        log_audit(st.session_state.username, "Hifz Absent", f"{s} {entry_date}")
                        st.success("محفوظ ہو گیا")
                else:
                    col1, col2 = st.columns(2)
                    sabaq_nagha = col1.checkbox("سبق ناغہ", key=f"sn_{key}")
                    sabaq_yad_nahi = col2.checkbox("یاد نہیں", key=f"sy_{key}")
                    if not sabaq_nagha and not sabaq_yad_nahi:
                        surah = st.selectbox("سورت", surahs_urdu, key=f"surah_{key}")
                        a_from = st.text_input("آیت (سے)", key=f"af_{key}")
                        a_to = st.text_input("آیت (تک)", key=f"at_{key}")
                        sabaq_text = f"{surah}: {a_from}-{a_to}"
                        lines = st.number_input("ستر (لائنیں)", 0, 50, 0, key=f"lines_{key}")
                    else:
                        sabaq_text = "ناغہ" if sabaq_nagha else "یاد نہیں"
                        lines = 0
                    
                    col1, col2 = st.columns(2)
                    sq_nagha = col1.checkbox("سبقی ناغہ", key=f"sqn_{key}")
                    sq_yad = col2.checkbox("سبقی یاد نہیں", key=f"sqy_{key}")
                    if sq_nagha or sq_yad:
                        sq_text = "ناغہ" if sq_nagha else "یاد نہیں"
                        sq_a = sq_m = 0
                    else:
                        col1, col2, col3, col4 = st.columns(4)
                        sq_para = col1.selectbox("سبقی پارہ", paras, key=f"sqp_{key}")
                        sq_miqdar = col2.selectbox("مقدار", ["مکمل", "آدھا", "پون", "پاؤ"], key=f"sqv_{key}")
                        sq_a = col3.number_input("سبقی اٹکن", 0, key=f"sqa_{key}")
                        sq_m = col4.number_input("سبقی غلطی", 0, key=f"sqe_{key}")
                        sq_text = f"{sq_para}:{sq_miqdar}"
                    
                    col1, col2 = st.columns(2)
                    m_nagha = col1.checkbox("منزل ناغہ", key=f"mn_{key}")
                    m_yad = col2.checkbox("منزل یاد نہیں", key=f"my_{key}")
                    if m_nagha or m_yad:
                        m_text = "ناغہ" if m_nagha else "یاد نہیں"
                        m_a = m_m = 0
                    else:
                        col1, col2, col3, col4 = st.columns(4)
                        m_para = col1.selectbox("منزل پارہ", paras, key=f"mp_{key}")
                        m_miqdar = col2.selectbox("مقدار", ["مکمل", "آدھا", "پون", "پاؤ"], key=f"mv_{key}")
                        m_a = col3.number_input("منزل اٹکن", 0, key=f"ma_{key}")
                        m_m = col4.number_input("منزل غلطی", 0, key=f"me_{key}")
                        m_text = f"{m_para}:{m_miqdar}"
                    
                    sn_bool = sabaq_nagha or sabaq_yad_nahi
                    sqn_bool = sq_nagha or sq_yad
                    mn_bool = m_nagha or m_yad
                    grade = calculate_grade_with_attendance(att, sn_bool, sqn_bool, mn_bool, sq_m, m_m)
                    
                    st.markdown(f"""
                    <div style="background:linear-gradient(135deg,#f0f9f3,#e8f5e9);border-radius:10px;
                                padding:0.7rem 1rem;border-right:4px solid #1e5631;margin:0.5rem 0">
                        <strong>درجہ: {grade}</strong>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button(f"💾 محفوظ کریں ({s})", key=f"save_{key}"):
                        conn = get_db_connection()
                        conn.execute("""INSERT INTO hifz_records
                                       (r_date, student_id, t_name, surah, lines, sq_p, sq_a, sq_m,
                                        m_p, m_a, m_m, attendance, cleanliness)
                                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                                    (entry_date, sid, st.session_state.username, sabaq_text, lines,
                                     sq_text, sq_a, sq_m, m_text, m_a, m_m, att, cleanliness))
                        conn.commit()
                        conn.close()
                        log_audit(st.session_state.username, "Hifz Entry", f"{s} {entry_date}")
                        st.success("✅ محفوظ ہو گیا")
                
                st.markdown("</div>", unsafe_allow_html=True)
    
    elif dept == "قاعدہ":
        conn = get_db_connection()
        students = conn.execute(
            "SELECT id, name, father_name FROM students WHERE teacher_name=? AND dept='قاعدہ'",
            (st.session_state.username,)
        ).fetchall()
        conn.close()
        if not students:
            st.info("آپ کی کلاس میں کوئی طالب علم نہیں")
        else:
            for sid, s, f in students:
                key = f"{sid}_{s}_{f}"
                st.markdown(f"<div class='report-card'><h4 style='color:#1e5631'>👤 {s} ولد {f}</h4>", unsafe_allow_html=True)
                
                conn = get_db_connection()
                existing = conn.execute("SELECT 1 FROM qaida_records WHERE r_date=? AND student_id=?", (entry_date, sid)).fetchone()
                conn.close()
                if existing:
                    st.warning(f"⚠️ ریکارڈ پہلے سے موجود ہے")
                    st.markdown("</div>", unsafe_allow_html=True)
                    continue
                
                att = st.radio("حاضری", ["حاضر", "غیر حاضر", "رخصت"], key=f"att_{key}", horizontal=True)
                cleanliness = st.selectbox("صفائی", cleanliness_options, key=f"clean_{key}")
                
                if att == "حاضر":
                    lesson_no = st.text_input("تختی نمبر", key=f"lesson_{key}")
                    total_lines = st.number_input("کل لائنیں", 0, key=f"lines_{key}")
                    details = st.text_area("نوٹ", key=f"details_{key}")
                    if st.button(f"💾 محفوظ کریں ({s})", key=f"save_{key}"):
                        conn = get_db_connection()
                        conn.execute("""INSERT INTO qaida_records
                                       (r_date, student_id, t_name, lesson_no, total_lines, details, attendance, cleanliness)
                                       VALUES (?,?,?,?,?,?,?,?)""",
                                    (entry_date, sid, st.session_state.username,
                                     sanitize_input(lesson_no), total_lines, sanitize_input(details), att, cleanliness))
                        conn.commit()
                        conn.close()
                        log_audit(st.session_state.username, "Qaida Entry", f"{s} {entry_date}")
                        st.success("✅ محفوظ ہو گیا")
                else:
                    if st.button(f"💾 غیر حاضر محفوظ ({s})", key=f"save_{key}"):
                        conn = get_db_connection()
                        conn.execute("""INSERT INTO qaida_records
                                       (r_date, student_id, t_name, lesson_no, total_lines, attendance, cleanliness)
                                       VALUES (?,?,?,?,?,?,?)""",
                                    (entry_date, sid, st.session_state.username, "غائب", 0, att, cleanliness))
                        conn.commit()
                        conn.close()
                        st.success("✅ محفوظ")
                st.markdown("</div>", unsafe_allow_html=True)
    
    else:  # درسِ نظامی / عصری تعلیم
        conn = get_db_connection()
        students = conn.execute(
            "SELECT id, name, father_name FROM students WHERE teacher_name=? AND dept=?",
            (st.session_state.username, dept)
        ).fetchall()
        conn.close()
        if not students:
            st.info(f"آپ کی {dept} کلاس میں کوئی طالب علم نہیں")
        else:
            with st.form(f"{dept}_form"):
                records = []
                for sid, s, f in students:
                    st.markdown(f"### 👤 {s} ولد {f}")
                    att = st.radio("حاضری", ["حاضر", "غیر حاضر", "رخصت"], key=f"att_{sid}", horizontal=True)
                    cleanliness = st.selectbox("صفائی", cleanliness_options, key=f"clean_{sid}")
                    if att == "حاضر":
                        book = st.text_input("کتاب/مضمون", key=f"book_{sid}", max_chars=100)
                        lesson = st.text_area("آج کا سبق", key=f"lesson_{sid}", max_chars=500)
                        hw = st.text_area("ہوم ورک", key=f"hw_{sid}", max_chars=300)
                        perf = st.select_slider("کارکردگی", ["بہت بہتر", "بہتر", "مناسب", "کمزور"], key=f"perf_{sid}")
                        records.append((entry_date, sid, st.session_state.username, dept,
                                       sanitize_input(book), sanitize_input(lesson, 500),
                                       sanitize_input(hw, 300), perf, att, cleanliness))
                    else:
                        records.append((entry_date, sid, st.session_state.username, dept,
                                       "غائب", "غائب", "", "غائب", att, cleanliness))
                    st.markdown("---")
                if st.form_submit_button("✅ تمام محفوظ کریں"):
                    conn = get_db_connection()
                    for rec in records:
                        conn.execute("""INSERT INTO general_education
                                       (r_date, student_id, t_name, dept, book_subject, today_lesson,
                                        homework, performance, attendance, cleanliness)
                                       VALUES (?,?,?,?,?,?,?,?,?,?)""", rec)
                    conn.commit()
                    conn.close()
                    log_audit(st.session_state.username, f"{dept} Entry", f"{entry_date}")
                    st.success("✅ تمام ریکارڈ محفوظ ہو گئے")

# ==================== 26. استاد: امتحانی درخواست ====================
elif selected == "🎓 امتحانی درخواست" and st.session_state.user_type == "teacher":
    st.markdown("<div class='main-header'><h1>🎓 امتحانی درخواست</h1></div>", unsafe_allow_html=True)
    conn = get_db_connection()
    students = conn.execute(
        "SELECT id, name, father_name, dept FROM students WHERE teacher_name=?",
        (st.session_state.username,)
    ).fetchall()
    conn.close()
    if not students:
        st.warning("آپ کی کلاس میں کوئی طالب علم نہیں")
    else:
        with st.form("exam_request"):
            s_list = [f"{s[1]} ولد {s[2]} ({s[3]})" for s in students]
            sel = st.selectbox("طالب علم منتخب کریں", s_list)
            idx = s_list.index(sel)
            student_id, s_name, f_name, dept = students[idx]
            
            exam_type = st.selectbox("امتحان کی قسم", ["پارہ ٹیسٹ", "ماہانہ", "سہ ماہی", "سالانہ"])
            col1, col2 = st.columns(2)
            start_date = col1.date_input("تاریخ ابتدا", date.today())
            end_date = col2.date_input("تاریخ اختتام", date.today() + timedelta(days=7))
            total_days = (end_date - start_date).days + 1
            st.info(f"📅 کل دن: {total_days}")
            
            from_para = to_para = 0
            book_name = amount_read = ""
            if exam_type == "پارہ ٹیسٹ":
                col1, col2 = st.columns(2)
                from_para = col1.number_input("پارہ (شروع)", 1, 30, 1)
                to_para = col2.number_input("پارہ (اختتام)", from_para, 30, from_para)
            else:
                if dept == "حفظ":
                    col1, col2 = st.columns(2)
                    from_para = col1.number_input("پارہ (شروع)", 1, 30, 1)
                    to_para = col2.number_input("پارہ (اختتام)", from_para, 30, from_para)
                    amount_read = st.text_input("مقدار خواندگی", max_chars=200)
                else:
                    book_name = st.text_input("کتاب کا نام", max_chars=100)
                    amount_read = st.text_input("مقدار خواندگی", max_chars=200)
            
            if st.form_submit_button("📤 درخواست بھیجیں"):
                conn = get_db_connection()
                conn.execute("""INSERT INTO exams
                               (student_id, dept, exam_type, from_para, to_para, book_name, amount_read,
                                start_date, end_date, total_days, status)
                               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                            (student_id, dept, exam_type, from_para, to_para,
                             sanitize_input(book_name), sanitize_input(amount_read),
                             start_date, end_date, total_days, "پینڈنگ"))
                conn.commit()
                conn.close()
                log_audit(st.session_state.username, "Exam Requested", f"{s_name} - {exam_type}")
                st.success("✅ درخواست بھیج دی گئی")

# ==================== 27. رخصت کی درخواست ====================
elif selected == "📩 رخصت کی درخواست" and st.session_state.user_type == "teacher":
    st.markdown("<div class='main-header'><h1>📩 رخصت کی درخواست</h1></div>", unsafe_allow_html=True)
    
    conn = get_db_connection()
    my_leaves = pd.read_sql_query("""
        SELECT l_type as نوعیت, start_date as 'تاریخ شروع', days as دن, status as حالت, request_date as 'تاریخ درخواست'
        FROM leave_requests WHERE t_name=? ORDER BY request_date DESC LIMIT 5
    """, conn, params=(st.session_state.username,))
    conn.close()
    
    if not my_leaves.empty:
        st.subheader("حالیہ درخواستیں")
        st.dataframe(my_leaves, use_container_width=True)
    
    with st.form("leave_form"):
        l_type = st.selectbox("رخصت کی نوعیت", ["بیماری", "ضروری کام", "ہنگامی", "دیگر"])
        col1, col2 = st.columns(2)
        start_date = col1.date_input("تاریخ آغاز", date.today())
        days = col2.number_input("دنوں کی تعداد", 1, 30, 1)
        back_date = start_date + timedelta(days=days-1)
        st.info(f"📅 واپسی کی تاریخ: {back_date}")
        reason = st.text_area("تفصیلی وجہ*", max_chars=500)
        if st.form_submit_button("📤 درخواست بھیجیں"):
            if reason.strip():
                conn = get_db_connection()
                conn.execute("""INSERT INTO leave_requests
                               (t_name, l_type, start_date, days, reason, status, notification_seen, request_date)
                               VALUES (?,?,?,?,?,?,?,?)""",
                            (st.session_state.username, l_type, start_date, days,
                             sanitize_input(reason, 500), "پینڈنگ", 0, date.today()))
                conn.commit()
                conn.close()
                log_audit(st.session_state.username, "Leave Requested", f"{l_type} for {days} days")
                st.success("✅ درخواست بھیج دی گئی")
            else:
                st.error("براہ کرم وجہ تحریر کریں")

# ==================== 28. میری حاضری ====================
elif selected == "🕒 میری حاضری" and st.session_state.user_type == "teacher":
    st.markdown("<div class='main-header'><h1>🕒 میری حاضری</h1></div>", unsafe_allow_html=True)
    today = date.today()
    conn = get_db_connection()
    rec = conn.execute(
        "SELECT arrival, departure FROM t_attendance WHERE t_name=? AND a_date=?",
        (st.session_state.username, today)
    ).fetchone()
    conn.close()
    
    st.markdown(f"""
    <div class="metric-card" style="max-width:400px;margin:0 auto 1.5rem">
        <span class="metric-icon">📅</span>
        <div style="color:#1e5631;font-weight:700">{today.strftime('%A, %d %B %Y')}</div>
        <div style="color:#6b7280;font-size:0.9rem">آج کی حاضری</div>
    </div>
    """, unsafe_allow_html=True)
    
    if not rec:
        arr_time = st.time_input("آمد کا وقت", datetime.now().time())
        if st.button("✅ آمد درج کریں", use_container_width=True):
            time_str = arr_time.strftime("%I:%M %p")
            conn = get_db_connection()
            try:
                conn.execute("INSERT INTO t_attendance (t_name, a_date, arrival, actual_arrival) VALUES (?,?,?,?)",
                             (st.session_state.username, today, time_str, get_pk_time()))
                conn.commit()
                st.success("✅ آمد درج ہو گئی")
                st.rerun()
            except sqlite3.IntegrityError:
                st.warning("آمد پہلے سے درج ہے")
            finally:
                conn.close()
    elif rec and rec[1] is None:
        st.success(f"✅ آمد درج: {rec[0]}")
        dep_time = st.time_input("رخصت کا وقت", datetime.now().time())
        if st.button("✅ رخصت درج کریں", use_container_width=True):
            time_str = dep_time.strftime("%I:%M %p")
            conn = get_db_connection()
            conn.execute("UPDATE t_attendance SET departure=?, actual_departure=? WHERE t_name=? AND a_date=?",
                         (time_str, get_pk_time(), st.session_state.username, today))
            conn.commit()
            conn.close()
            st.success("✅ رخصت درج ہو گئی")
            st.rerun()
    else:
        col1, col2 = st.columns(2)
        col1.metric("🟢 آمد", rec[0])
        col2.metric("🔴 رخصت", rec[1])
    
    st.subheader("ماہانہ حاضری")
    conn = get_db_connection()
    monthly = pd.read_sql_query("""
        SELECT a_date as تاریخ, arrival as آمد, departure as رخصت
        FROM t_attendance WHERE t_name=? AND a_date >= ?
        ORDER BY a_date DESC
    """, conn, params=(st.session_state.username, date.today().replace(day=1)))
    conn.close()
    if not monthly.empty:
        st.dataframe(monthly, use_container_width=True)

# ==================== 29. میرا ٹائم ٹیبل ====================
elif selected == "📚 میرا ٹائم ٹیبل" and st.session_state.user_type == "teacher":
    st.markdown("<div class='main-header'><h1>📚 میرا ٹائم ٹیبل</h1></div>", unsafe_allow_html=True)
    conn = get_db_connection()
    tt_df = pd.read_sql_query(
        "SELECT day as دن, period as وقت, book as کتاب, room as کمرہ FROM timetable WHERE t_name=?",
        conn, params=(st.session_state.username,)
    )
    conn.close()
    if tt_df.empty:
        st.info("ابھی آپ کا ٹائم ٹیبل ترتیب نہیں دیا گیا")
    else:
        day_order = {"ہفتہ": 0, "اتوار": 1, "پیر": 2, "منگل": 3, "بدھ": 4, "جمعرات": 5}
        tt_df['day_order'] = tt_df['دن'].map(day_order)
        tt_df = tt_df.sort_values(['day_order', 'وقت'])
        try:
            pivot = tt_df.pivot(index='وقت', columns='دن', values='کتاب').fillna("—")
            st.dataframe(pivot, use_container_width=True)
        except:
            st.dataframe(tt_df[['دن', 'وقت', 'کتاب', 'کمرہ']], use_container_width=True)
        html_timetable = generate_timetable_html(tt_df)
        st.download_button("📥 ٹائم ٹیبل ڈاؤن لوڈ", html_timetable,
                           f"Timetable_{st.session_state.username}.html", "text/html")
