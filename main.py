"""
جامعہ ملیہ اسلامیہ فیصل آباد
Smart ERP System v3.0
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import sqlite3
import pytz
import hashlib
import os
import io
import zipfile
import shutil

# ═══════════════════════════════════════════════════════
# PAGE CONFIG — سب سے پہلے
# ═══════════════════════════════════════════════════════
st.set_page_config(
    page_title="جامعہ ملیہ | ERP",
    page_icon="🕌",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ═══════════════════════════════════════════════════════
# DATABASE
# ═══════════════════════════════════════════════════════
DB = "jamia_v3.db"

@st.cache_resource
def get_db_connection():
    """ایک ہی کنکشن بنائے رکھنے کے لیے کیش شدہ فنکشن"""
    conn = sqlite3.connect(DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def db():
    return get_db_connection()

def q(sql, params=(), fetch="all"):
    conn = db()
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        if fetch == "all":
            return [dict(r) for r in cur.fetchall()]
        elif fetch == "one":
            r = cur.fetchone()
            return dict(r) if r else None
        elif fetch == "scalar":
            r = cur.fetchone()
            return r[0] if r else None
        return cur.lastrowid
    except Exception as e:
        st.error(f"Query error: {e}")
        return None

def qw(sql, params=()):
    """Write query — returns lastrowid"""
    conn = db()
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    except Exception as e:
        st.error(f"Write error: {e}")
        return None

def col_exists(table, col):
    rows = q(f"PRAGMA table_info({table})")
    return any(r['name'] == col for r in rows)

def add_col(table, col, typ):
    if not col_exists(table, col):
        try:
            qw(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
        except:
            pass

def setup_db():
    qw("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'teacher',
        dept TEXT,
        phone TEXT,
        address TEXT,
        id_card TEXT,
        joining_date TEXT,
        is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    qw("""CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        father_name TEXT NOT NULL,
        mother_name TEXT,
        roll_no TEXT,
        dob TEXT,
        admission_date TEXT,
        exit_date TEXT,
        exit_reason TEXT,
        phone TEXT,
        address TEXT,
        teacher TEXT,
        dept TEXT,
        class_name TEXT,
        section TEXT,
        is_active INTEGER DEFAULT 1
    )""")

    qw("""CREATE TABLE IF NOT EXISTS hifz_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rec_date TEXT NOT NULL,
        student_id INTEGER NOT NULL,
        teacher TEXT NOT NULL,
        attendance TEXT NOT NULL,
        sabaq TEXT,
        sabaq_from TEXT,
        sabaq_to TEXT,
        sabaq_lines INTEGER DEFAULT 0,
        sabaq_atkan INTEGER DEFAULT 0,
        sabaq_mistakes INTEGER DEFAULT 0,
        sabaq_nagha INTEGER DEFAULT 0,
        sabaq_p TEXT,
        sabaq_miqdar TEXT,
        sq_nagha INTEGER DEFAULT 0,
        sq_p TEXT,
        sq_miqdar TEXT,
        sq_atkan INTEGER DEFAULT 0,
        sq_mistakes INTEGER DEFAULT 0,
        manzil_nagha INTEGER DEFAULT 0,
        manzil_p TEXT,
        manzil_miqdar TEXT,
        manzil_atkan INTEGER DEFAULT 0,
        manzil_mistakes INTEGER DEFAULT 0,
        cleanliness TEXT,
        grade TEXT,
        note TEXT,
        FOREIGN KEY(student_id) REFERENCES students(id)
    )""")

    qw("""CREATE TABLE IF NOT EXISTS qaida_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rec_date TEXT NOT NULL,
        student_id INTEGER NOT NULL,
        teacher TEXT NOT NULL,
        attendance TEXT NOT NULL,
        lesson_no TEXT,
        lesson_type TEXT,
        total_lines INTEGER DEFAULT 0,
        details TEXT,
        cleanliness TEXT,
        note TEXT,
        FOREIGN KEY(student_id) REFERENCES students(id)
    )""")

    qw("""CREATE TABLE IF NOT EXISTS general_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rec_date TEXT NOT NULL,
        student_id INTEGER NOT NULL,
        teacher TEXT NOT NULL,
        dept TEXT,
        attendance TEXT NOT NULL,
        subject TEXT,
        lesson TEXT,
        homework TEXT,
        performance TEXT,
        cleanliness TEXT,
        note TEXT,
        FOREIGN KEY(student_id) REFERENCES students(id)
    )""")

    qw("""CREATE TABLE IF NOT EXISTS teacher_attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        att_date TEXT NOT NULL,
        arrival TEXT,
        departure TEXT,
        UNIQUE(username, att_date)
    )""")

    qw("""CREATE TABLE IF NOT EXISTS leave_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        leave_type TEXT,
        start_date TEXT,
        days INTEGER DEFAULT 1,
        reason TEXT,
        status TEXT DEFAULT 'پینڈنگ',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    qw("""CREATE TABLE IF NOT EXISTS exams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        teacher TEXT,
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
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(student_id) REFERENCES students(id)
    )""")

    qw("""CREATE TABLE IF NOT EXISTS passed_paras (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        para_no INTEGER,
        book_name TEXT,
        passed_date TEXT,
        exam_type TEXT,
        grade TEXT,
        marks INTEGER DEFAULT 0,
        FOREIGN KEY(student_id) REFERENCES students(id)
    )""")

    qw("""CREATE TABLE IF NOT EXISTS timetable (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        teacher TEXT NOT NULL,
        day TEXT,
        period TEXT,
        subject TEXT,
        room TEXT
    )""")

    qw("""CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        message TEXT,
        target TEXT DEFAULT 'all',
        created_by TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    qw("""CREATE TABLE IF NOT EXISTS staff_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        staff TEXT NOT NULL,
        note_date TEXT,
        note_type TEXT,
        description TEXT,
        action TEXT,
        status TEXT DEFAULT 'زیر التواء',
        created_by TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    qw("""CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        action TEXT,
        details TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # Default admin
    pw = hash_pw("jamia123")
    existing = q("SELECT id FROM users WHERE username='admin'", fetch="one")
    if not existing:
        qw("INSERT INTO users (username, password, role, dept) VALUES (?,?,?,?)",
           ("admin", pw, "admin", "انتظامیہ"))

    # Migration from old DB if exists
    migrate_old_data()

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def verify_pw(plain, hashed):
    if hashed == plain:
        return True
    if hashed == hashlib.sha256(plain.encode()).hexdigest():
        return True
    return False

def migrate_old_data():
    """Migrate from old jamia_millia_data.db if exists"""
    old_db = "jamia_millia_data.db"
    if not os.path.exists(old_db):
        return
    already = q("SELECT COUNT(*) FROM users", fetch="scalar")
    if already and already > 1:
        return  # already migrated
    try:
        old = sqlite3.connect(old_db)
        old.row_factory = sqlite3.Row
        try:
            teachers = old.execute("SELECT * FROM teachers").fetchall()
            for t in teachers:
                td = dict(t)
                if td.get('name') == 'admin':
                    continue
                existing = q("SELECT id FROM users WHERE username=?", (td.get('name',''),), fetch="one")
                if not existing:
                    qw("INSERT OR IGNORE INTO users (username,password,role,dept,phone,address,id_card,joining_date) VALUES (?,?,?,?,?,?,?,?)",
                       (td.get('name',''), td.get('password',''), 'teacher',
                        td.get('dept',''), td.get('phone',''), td.get('address',''),
                        td.get('id_card',''), td.get('joining_date','')))
        except: pass
        try:
            studs = old.execute("SELECT * FROM students").fetchall()
            for s in studs:
                sd = dict(s)
                existing = q("SELECT id FROM students WHERE name=? AND father_name=?",
                             (sd.get('name',''), sd.get('father_name','')), fetch="one")
                if not existing:
                    qw("""INSERT OR IGNORE INTO students
                          (name,father_name,mother_name,roll_no,dob,admission_date,exit_date,exit_reason,
                           phone,address,teacher,dept,class_name,section)
                          VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                       (sd.get('name',''), sd.get('father_name',''), sd.get('mother_name',''),
                        sd.get('roll_no',''), sd.get('dob',''), sd.get('admission_date',''),
                        sd.get('exit_date',''), sd.get('exit_reason',''), sd.get('phone',''),
                        sd.get('address',''), sd.get('teacher_name',''), sd.get('dept',''),
                        sd.get('class',''), sd.get('section','')))
        except: pass
        old.close()
    except: pass

def audit(user, action, details=""):
    try:
        qw("INSERT INTO audit_log (username,action,details) VALUES (?,?,?)", (user, action, details))
    except: pass

def get_grade_from_mistakes(mistakes):
    if mistakes <= 2: return "ممتاز"
    elif mistakes <= 5: return "جید جداً"
    elif mistakes <= 8: return "جید"
    elif mistakes <= 12: return "مقبول"
    else: return "دوبارہ کوشش"

def pk_time():
    tz = pytz.timezone('Asia/Karachi')
    return datetime.now(tz).strftime("%I:%M %p")

setup_db()

# ═══════════════════════════════════════════════════════
# MASTER CSS
# ═══════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu:wght@400;500;600;700&display=swap');

:root {
    --jade: #0a4d3c;
    --jade2: #0d6b54;
    --jade3: #10856a;
    --gold: #c9982a;
    --gold2: #f0bc50;
    --cream: #fdf8f0;
    --white: #ffffff;
    --dark: #0d1f1a;
    --gray: #6b7280;
    --lightgray: #f1f5f4;
    --danger: #dc2626;
    --success: #16a34a;
    --warning: #d97706;
    --r: 14px;
    --rs: 10px;
    --shadow: 0 4px 24px rgba(10,77,60,0.12);
    --shadow2: 0 8px 40px rgba(10,77,60,0.18);
}

* { font-family: 'Noto Nastaliq Urdu', Georgia, serif !important; direction: rtl; }
html, body, [class*="css"] { direction: rtl; text-align: right; }

.stApp {
    background: linear-gradient(160deg, #f0f8f5 0%, #e8f5f0 40%, #f5f0e8 100%);
    min-height: 100vh;
}

/* ─── HIDE STREAMLIT CHROME ─── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 1rem 1.5rem 2rem !important; max-width: 1400px !important; }

/* ─── SIDEBAR ─── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, var(--dark) 0%, var(--jade) 100%) !important;
    border-left: 3px solid var(--gold) !important;
    width: 260px !important;
}
[data-testid="stSidebar"] * { color: #d4f0e8 !important; }
[data-testid="stSidebarNav"] { display: none; }

/* ─── TOP NAV BAR ─── */
.topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: linear-gradient(135deg, var(--jade) 0%, var(--jade2) 100%);
    border-radius: var(--r);
    padding: 0.75rem 1.5rem;
    margin-bottom: 1.2rem;
    box-shadow: var(--shadow2);
    position: relative;
    overflow: hidden;
}
.topbar::before {
    content: '';
    position: absolute; inset: 0;
    background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.03'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
}
.topbar-brand { display: flex; align-items: center; gap: 0.6rem; }
.topbar-icon { font-size: 1.8rem; }
.topbar-title { color: #ffffff !important; font-size: 1.1rem; font-weight: 700; }
.topbar-sub { color: var(--gold2) !important; font-size: 0.8rem; }
.topbar-user {
    background: rgba(255,255,255,0.12);
    border: 1px solid rgba(255,255,255,0.2);
    border-radius: 30px;
    padding: 0.3rem 0.8rem;
    color: #fff !important;
    font-size: 0.85rem;
    display: flex; align-items: center; gap: 0.4rem;
}

/* ─── NAV BUTTONS ─── */
.nav-grid {
    display: grid;
    gap: 0.5rem;
    margin-bottom: 1.2rem;
}
.nav-grid-2 { grid-template-columns: repeat(2, 1fr); }
.nav-grid-3 { grid-template-columns: repeat(3, 1fr); }
.nav-grid-4 { grid-template-columns: repeat(4, 1fr); }

.nav-btn {
    background: var(--white);
    border: 2px solid transparent;
    border-radius: var(--r);
    padding: 0.8rem 0.6rem;
    text-align: center;
    cursor: pointer;
    transition: all 0.2s cubic-bezier(.34,1.56,.64,1);
    box-shadow: 0 2px 8px rgba(10,77,60,0.08);
    text-decoration: none;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    gap: 0.3rem;
}
.nav-btn:hover {
    border-color: var(--jade3);
    transform: translateY(-3px);
    box-shadow: 0 8px 24px rgba(10,77,60,0.18);
}
.nav-btn.active {
    background: linear-gradient(135deg, var(--jade), var(--jade2));
    border-color: var(--jade);
    color: white !important;
    transform: translateY(-2px);
    box-shadow: var(--shadow2);
}
.nav-btn.active .nav-icon, .nav-btn.active .nav-label { color: white !important; }
.nav-icon { font-size: 1.4rem; display: block; }
.nav-label { font-size: 0.78rem; color: var(--dark); font-weight: 600; line-height: 1.2; }

/* ─── SECTION CARDS ─── */
.section-card {
    background: var(--white);
    border-radius: var(--r);
    padding: 1.5rem;
    box-shadow: var(--shadow);
    margin-bottom: 1rem;
    border: 1px solid rgba(10,77,60,0.06);
    animation: fadeIn 0.35s ease;
}
@keyframes fadeIn { from { opacity:0; transform:translateY(10px); } to { opacity:1; transform:translateY(0); } }

.section-header {
    display: flex; align-items: center; gap: 0.6rem;
    border-bottom: 2px solid var(--lightgray);
    padding-bottom: 0.8rem;
    margin-bottom: 1.2rem;
}
.section-header h2 {
    color: var(--jade) !important;
    font-size: 1.2rem !important;
    margin: 0 !important;
}

/* ─── METRIC CARDS ─── */
.metrics-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.8rem; margin-bottom: 1rem; }
.metric-card {
    background: linear-gradient(145deg, var(--white), var(--lightgray));
    border-radius: var(--r);
    padding: 1.2rem 1rem;
    text-align: center;
    box-shadow: var(--shadow);
    border: 1px solid rgba(10,77,60,0.08);
    position: relative; overflow: hidden;
    transition: transform 0.2s;
}
.metric-card:hover { transform: translateY(-3px); box-shadow: var(--shadow2); }
.metric-card::after {
    content:''; position:absolute; bottom:0; left:0; right:0; height:3px;
    background: linear-gradient(90deg, var(--jade), var(--gold));
}
.metric-icon { font-size: 1.8rem; margin-bottom: 0.3rem; }
.metric-val { font-size: 2.2rem; font-weight: 800; color: var(--jade); line-height:1; }
.metric-lbl { font-size: 0.82rem; color: var(--gray); margin-top: 0.2rem; }

/* ─── BUTTONS ─── */
.stButton > button {
    background: linear-gradient(135deg, var(--jade), var(--jade2)) !important;
    color: white !important; border: none !important;
    border-radius: 10px !important;
    padding: 0.5rem 1.2rem !important;
    font-weight: 600 !important;
    transition: all 0.2s !important;
    box-shadow: 0 3px 12px rgba(10,77,60,0.25) !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(10,77,60,0.35) !important;
    background: linear-gradient(135deg, var(--dark), var(--jade)) !important;
}

/* ─── INPUTS ─── */
.stTextInput > div > div > input,
.stTextArea textarea,
.stNumberInput input,
.stDateInput input,
.stTimeInput input {
    border-radius: var(--rs) !important;
    border: 1.5px solid #d1d5db !important;
    direction: rtl !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}
.stTextInput > div > div > input:focus,
.stTextArea textarea:focus {
    border-color: var(--jade2) !important;
    box-shadow: 0 0 0 3px rgba(13,107,84,0.15) !important;
}

/* ─── SELECT BOXES ─── */
.stSelectbox [data-baseweb="select"] { border-radius: var(--rs) !important; }

/* ─── TABS ─── */
.stTabs [data-baseweb="tab-list"] {
    background: var(--lightgray) !important;
    border-radius: 12px !important; padding: 4px !important; gap: 4px !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 9px !important; border: none !important;
    color: var(--gray) !important; font-weight: 600 !important;
    transition: all 0.2s !important;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, var(--jade), var(--jade2)) !important;
    color: white !important;
    box-shadow: 0 3px 10px rgba(10,77,60,0.3) !important;
}

/* ─── ALERTS ─── */
.stSuccess > div { background: #f0fdf4 !important; border-color: #86efac !important; border-radius: var(--rs) !important; }
.stError > div { background: #fff1f2 !important; border-color: #fca5a5 !important; border-radius: var(--rs) !important; }
.stWarning > div { background: #fffbeb !important; border-color: #fcd34d !important; border-radius: var(--rs) !important; }
.stInfo > div { background: #f0f9ff !important; border-color: #93c5fd !important; border-radius: var(--rs) !important; }

/* ─── DATAFRAME ─── */
.stDataFrame { border-radius: var(--rs) !important; overflow: hidden !important; box-shadow: var(--shadow) !important; }
.stDataFrame th { background: var(--jade) !important; color: white !important; }

/* ─── EXPANDER ─── */
.streamlit-expanderHeader {
    background: linear-gradient(135deg, #f0f9f5, #e8f5f0) !important;
    border-radius: var(--rs) !important;
    border: 1px solid rgba(10,77,60,0.1) !important;
}

/* ─── STUDENT CARD ─── */
.student-card {
    background: linear-gradient(145deg, #fff, #f8fffe);
    border: 1px solid rgba(10,77,60,0.1);
    border-radius: var(--r);
    padding: 1rem 1.2rem;
    margin-bottom: 0.7rem;
    border-right: 4px solid var(--jade2);
    transition: all 0.2s;
}
.student-card:hover { box-shadow: var(--shadow2); transform: translateX(-3px); }
.student-card h4 { color: var(--jade) !important; margin: 0 0 0.6rem !important; font-size: 1rem !important; }

/* ─── GRADE BADGE ─── */
.grade-badge {
    display: inline-block;
    padding: 0.2rem 0.8rem;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 700;
}
.grade-mumtaz { background: #d1fae5; color: #065f46; }
.grade-jadid { background: #dbeafe; color: #1e40af; }
.grade-jadid2 { background: #ede9fe; color: #4c1d95; }
.grade-maqbool { background: #fef3c7; color: #92400e; }
.grade-fail { background: #fee2e2; color: #991b1b; }

/* ─── TROPHY CARDS ─── */
.trophy-card {
    background: linear-gradient(145deg, #fffdf0, #fdf3d0);
    border: 2px solid rgba(201,152,42,0.25);
    border-radius: 20px;
    padding: 1.5rem 1rem;
    text-align: center;
    position: relative; overflow: hidden;
    transition: all 0.3s;
    box-shadow: 0 8px 32px rgba(201,152,42,0.12);
}
.trophy-card::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 4px;
    background: linear-gradient(90deg, var(--gold), var(--gold2), var(--gold));
}
.trophy-card:hover { transform: translateY(-6px); box-shadow: 0 16px 48px rgba(201,152,42,0.22); }
.medal { font-size: 2.8rem; display: block; }
.trophy-name { font-size: 1.1rem; font-weight: 700; color: var(--dark); margin: 0.5rem 0 0.2rem; }
.trophy-sub { font-size: 0.82rem; color: var(--gray); }
.trophy-score {
    display: inline-block;
    background: linear-gradient(135deg, var(--jade), var(--jade2));
    color: white; border-radius: 20px;
    padding: 0.25rem 0.9rem; font-size: 0.88rem; font-weight: 700;
    margin-top: 0.7rem;
    box-shadow: 0 3px 10px rgba(10,77,60,0.25);
}

/* ─── LOGIN PAGE ─── */
.login-wrap {
    min-height: 100vh;
    display: flex; align-items: center; justify-content: center;
    background: linear-gradient(145deg, #0a4d3c 0%, #0d6b54 50%, #0a4d3c 100%);
    position: fixed; inset: 0; z-index: 9999;
}
.login-box {
    background: rgba(255,255,255,0.97);
    border-radius: 24px;
    padding: 2.5rem 2rem 2rem;
    width: 100%; max-width: 420px;
    box-shadow: 0 24px 80px rgba(0,0,0,0.3);
    border: 1px solid rgba(255,255,255,0.5);
    text-align: center;
}
.login-icon {
    font-size: 4rem;
    display: inline-block;
    animation: bounce 2s ease-in-out infinite;
}
@keyframes bounce {
    0%,100% { transform: translateY(0); }
    50% { transform: translateY(-8px); }
}
.login-title {
    color: var(--jade) !important;
    font-size: 1.4rem !important;
    font-weight: 800 !important;
    margin: 0.5rem 0 0.2rem !important;
}
.login-sub { color: var(--gold) !important; font-size: 0.9rem; }

/* ─── PROGRESS BAR ─── */
.progress-wrap {
    background: #e5e7eb; border-radius: 10px; overflow: hidden; height: 18px; margin: 0.5rem 0;
}
.progress-bar {
    height: 100%;
    background: linear-gradient(90deg, var(--jade), var(--gold));
    border-radius: 10px;
    transition: width 0.8s ease;
    display: flex; align-items: center; justify-content: center;
}
.progress-text { color: white; font-size: 0.75rem; font-weight: 700; }

/* ─── NOTIFICATION CARD ─── */
.notif-card {
    background: linear-gradient(135deg, #f0f9ff, #e0f2fe);
    border-right: 4px solid #0369a1;
    border-radius: var(--rs);
    padding: 0.8rem 1rem;
    margin-bottom: 0.6rem;
}
.notif-card h5 { color: #0369a1 !important; margin: 0 0 0.3rem !important; }
.notif-card p { color: #374151; margin: 0; font-size: 0.88rem; }
.notif-card small { color: var(--gray); }

/* ─── STATUS PILL ─── */
.status-pill {
    display: inline-block;
    padding: 0.15rem 0.7rem;
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: 700;
}
.status-pending { background: #fef3c7; color: #92400e; }
.status-ok { background: #d1fae5; color: #065f46; }
.status-reject { background: #fee2e2; color: #991b1b; }

/* ─── LEAVE CARD ─── */
.leave-card {
    background: var(--white);
    border-radius: var(--r);
    padding: 1rem 1.2rem;
    margin-bottom: 0.7rem;
    box-shadow: var(--shadow);
    border-right: 4px solid var(--warning);
}

/* ─── TABLE STYLE ─── */
.custom-table {
    width: 100%; border-collapse: collapse; font-size: 0.88rem;
}
.custom-table th {
    background: var(--jade); color: white; padding: 0.6rem 0.8rem;
    text-align: center; font-weight: 600;
}
.custom-table td { padding: 0.5rem 0.8rem; border-bottom: 1px solid #f0f0f0; text-align: center; }
.custom-table tr:hover td { background: #f0f9f5; }
.custom-table tr:nth-child(even) td { background: #f8fffe; }

/* ─── MOBILE ─── */
@media(max-width:768px) {
    .metrics-row { grid-template-columns: repeat(2,1fr); }
    .nav-grid-4 { grid-template-columns: repeat(2,1fr); }
    .block-container { padding: 0.5rem !important; }
}
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════
# SESSION INIT
# ═══════════════════════════════════════════════════════
for k, v in [
    ("logged_in", False), ("username", ""), ("role", ""),
    ("page", "dashboard"), ("dept_filter", "حفظ")
]:
    if k not in st.session_state:
        st.session_state[k] = v

# ═══════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════
SURAHS = ["الفاتحة","البقرة","آل عمران","النساء","المائدة","الأنعام","الأعراف","الأنفال","التوبة","يونس",
          "هود","يوسف","الرعد","إبراهيم","الحجر","النحل","الإسراء","الكهف","مريم","طه","الأنبياء","الحج",
          "المؤمنون","النور","الفرقان","الشعراء","النمل","القصص","العنكبوت","الروم","لقمان","السجدة",
          "الأحزاب","سبأ","فاطر","يس","الصافات","ص","الزمر","غافر","فصلت","الشورى","الزخرف","الدخان",
          "الجاثية","الأحقاف","محمد","الفتح","الحجرات","ق","الذاريات","الطور","النجم","القمر","الرحمن",
          "الواقعة","الحديد","المجادلة","الحشر","الممتحنة","الصف","الجمعة","المنافقون","التغابن","الطلاق",
          "التحریم","الملک","القلم","الحاقة","المعارج","نوح","الجن","المزمل","المدثر","القیامة","الإنسان",
          "المرسلات","النبأ","النازعات","عبس","التکویر","الإنفطار","المطففین","الإنشقاق","البروج","الطارق",
          "الأعلى","الغاشیة","الفجر","البلد","الشمس","اللیل","الضحى","الشرح","التین","العلق","القدر",
          "البینة","الزلزلة","العادیات","القارعة","التکاثر","العصر","الهمزة","الفیل","قریش","الماعون",
          "الکوثر","الکافرون","النصر","المسد","الإخلاص","الفلق","الناس"]
PARAS = [f"پارہ {i}" for i in range(1, 31)]
DAYS = ["پیر","منگل","بدھ","جمعرات","جمعہ","ہفتہ","اتوار"]
CLEANLINESS = ["بہترین","بہتر","ناقص"]
DEPTS = ["حفظ","قاعدہ","درسِ نظامی","عصری تعلیم"]
GRADE_MAP = {"ممتاز":"grade-mumtaz","جید جداً":"grade-jadid2","جید":"grade-jadid","مقبول":"grade-maqbool"}

def calc_grade(att, sn, sqn, mn, sq_m, m_m):
    if att == "غیر حاضر": return "غیر حاضر"
    if att == "رخصت": return "رخصت"
    nagha = sum([sn, sqn, mn])
    if nagha == 1: return "ناقص (ناغہ)"
    if nagha == 2: return "کمزور (ناغہ)"
    if nagha == 3: return "ناکام (مکمل ناغہ)"
    return get_grade_from_mistakes(sq_m + m_m)

def clean_score(c):
    return {"بہترین":3,"بہتر":2,"ناقص":1}.get(c,0)

def gen_html_report(df, title, sub=""):
    tbl = df.to_html(index=False, classes='rpt', border=0, justify='center', escape=False)
    return f"""<!DOCTYPE html><html dir="rtl"><head><meta charset="UTF-8"><title>{title}</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu&display=swap');
*{{font-family:'Noto Nastaliq Urdu',serif;direction:rtl;}}
body{{background:#f8f9fa;margin:20px;}}
.wrap{{background:white;border-radius:12px;padding:20px;max-width:900px;margin:auto;box-shadow:0 4px 20px rgba(0,0,0,0.08);}}
h2{{text-align:center;color:#0a4d3c;border-bottom:2px solid #c9982a;padding-bottom:10px;}}
h3{{text-align:center;color:#555;margin-top:4px;}}
table.rpt{{width:100%;border-collapse:collapse;margin:16px 0;}}
table.rpt th{{background:#0a4d3c;color:white;padding:8px 10px;}}
table.rpt td{{border:1px solid #ddd;padding:7px 10px;text-align:center;}}
table.rpt tr:nth-child(even){{background:#f5fffa;}}
.sig{{display:flex;justify-content:space-between;margin-top:40px;}}
.no-print{{text-align:center;margin-top:20px;}}
button{{padding:10px 30px;background:#0a4d3c;color:white;border:none;border-radius:8px;cursor:pointer;font-size:1rem;}}
@media print{{.no-print{{display:none;}}}}
</style></head><body>
<div class="wrap">
<h2>🕌 جامعہ ملیہ اسلامیہ فیصل آباد</h2>
<h3>{title}</h3>
{f"<p style='text-align:center'>{sub}</p>" if sub else ""}
{tbl}
<div class="sig">
<span>دستخط استاذ: _____________________</span>
<span>دستخط مہتمم: _____________________</span>
</div>
</div>
<div class="no-print"><button onclick="window.print()">🖨️ پرنٹ کریں</button></div>
</body></html>"""

# ═══════════════════════════════════════════════════════
# LOGIN
# ═══════════════════════════════════════════════════════
if not st.session_state.logged_in:
    st.markdown('<div class="login-wrap">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.4, 1])
    with c2:
        st.markdown("""
        <div class="login-box">
            <span class="login-icon">🕌</span>
            <h2 class="login-title">جامعہ ملیہ اسلامیہ</h2>
            <p class="login-sub">فیصل آباد — اسمارٹ تعلیمی پورٹل</p>
            <hr style="border:none;border-top:1px solid #e5e7eb;margin:1rem 0">
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            uname = st.text_input("👤 صارف نام", placeholder="username")
            passw = st.text_input("🔑 پاسورڈ", type="password", placeholder="password")
            submitted = st.form_submit_button("▶  داخل ہوں", use_container_width=True)

        if submitted:
            if uname and passw:
                user = q("SELECT * FROM users WHERE username=? AND is_active=1", (uname,), fetch="one")
                if user and verify_pw(passw, user['password']):
                    st.session_state.logged_in = True
                    st.session_state.username = uname
                    st.session_state.role = user['role']
                    st.session_state.page = "dashboard"
                    audit(uname, "Login", f"role={user['role']}")
                    st.rerun()
                else:
                    st.error("❌ غلط نام یا پاسورڈ")
            else:
                st.warning("براہ کرم نام اور پاسورڈ درج کریں")

        st.markdown("""
        <p style="text-align:center;color:#9ca3af;font-size:0.78rem;margin-top:0.5rem">
        🔒 ڈیفالٹ: admin / jamia123
        </p>
        """, unsafe_allow_html=True)
    st.stop()

# ═══════════════════════════════════════════════════════
# TOP BAR
# ═══════════════════════════════════════════════════════
user_data = q("SELECT * FROM users WHERE username=?", (st.session_state.username,), fetch="one") or {}
role = st.session_state.role
IS_ADMIN = role == "admin"

st.markdown(f"""
<div class="topbar">
    <div class="topbar-brand">
        <span class="topbar-icon">🕌</span>
        <div>
            <div class="topbar-title">جامعہ ملیہ اسلامیہ فیصل آباد</div>
            <div class="topbar-sub">اسمارٹ تعلیمی و انتظامی پورٹل v3.0</div>
        </div>
    </div>
    <div style="display:flex;gap:0.5rem;align-items:center">
        <div class="topbar-user">
            {'🛡️ ایڈمن' if IS_ADMIN else '👩‍🏫 استاد'} — {st.session_state.username}
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════
# NAVIGATION
# ═══════════════════════════════════════════════════════
if IS_ADMIN:
    admin_pages = {
        "dashboard":    ("📊","ڈیش بورڈ"),
        "daily_report": ("📋","یومیہ رپورٹ"),
        "exams":        ("🎓","امتحانات"),
        "result_card":  ("📜","رزلٹ کارڈ"),
        "para_report":  ("📖","پارہ رپورٹ"),
        "teacher_att":  ("🕒","حاضری"),
        "leaves":       ("🏛️","رخصت"),
        "users":        ("👥","یوزرز"),
        "timetable":    ("📚","ٹائم ٹیبل"),
        "monitoring":   ("📋","نگرانی"),
        "notifs":       ("📢","نوٹیفیکیشن"),
        "analytics":    ("📈","تجزیہ"),
        "best_students":("🏆","بہترین"),
        "password":     ("🔑","پاسورڈ"),
        "backup":       ("⚙️","بیک اپ"),
    }
    page_keys = list(admin_pages.keys())
    rows = [page_keys[i:i+5] for i in range(0, len(page_keys), 5)]
    for row in rows:
        cols = st.columns(len(row))
        for col, pk in zip(cols, row):
            icon, label = admin_pages[pk]
            active = st.session_state.page == pk
            cls = "nav-btn active" if active else "nav-btn"
            with col:
                if st.button(f"{icon}\n{label}", key=f"nav_{pk}", use_container_width=True):
                    st.session_state.page = pk
                    st.rerun()
else:
    teacher_pages = {
        "t_entry":    ("📝","سبق اندراج"),
        "t_exam":     ("🎓","امتحان"),
        "t_leave":    ("📩","رخصت"),
        "t_att":      ("🕒","حاضری"),
        "t_timetable":("📚","ٹائم ٹیبل"),
        "notifs":     ("📢","نوٹیفیکیشن"),
        "password":   ("🔑","پاسورڈ"),
    }
    page_keys = list(teacher_pages.keys())
    cols = st.columns(len(page_keys))
    for col, pk in zip(cols, page_keys):
        icon, label = teacher_pages[pk]
        with col:
            if st.button(f"{icon}\n{label}", key=f"nav_{pk}", use_container_width=True):
                st.session_state.page = pk
                st.rerun()

# Logout button
logout_col = st.columns([4,1])[1]
with logout_col:
    if st.button("🚪 لاگ آؤٹ", use_container_width=True):
        audit(st.session_state.username, "Logout")
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

pg = st.session_state.page
st.markdown("---")

# ═══════════════════════════════════════════════════════
# HELPER: page header
# ═══════════════════════════════════════════════════════
def page_header(icon, title, sub=""):
    st.markdown(f"""
    <div class="section-card" style="background:linear-gradient(135deg,var(--jade),var(--jade2));
         padding:1.2rem 1.5rem;margin-bottom:1rem">
        <div style="display:flex;align-items:center;gap:0.7rem">
            <span style="font-size:1.8rem">{icon}</span>
            <div>
                <h2 style="color:white!important;margin:0!important;font-size:1.3rem!important">{title}</h2>
                {f'<p style="color:rgba(255,255,255,0.8);margin:0;font-size:0.85rem">{sub}</p>' if sub else ''}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════
# ─── ADMIN DASHBOARD ───────────────────────────────────
# ═══════════════════════════════════════════════════════
if pg == "dashboard" and IS_ADMIN:
    page_header("📊","ایڈمن ڈیش بورڈ","جامعہ ملیہ کا مکمل جائزہ")

    total_s = q("SELECT COUNT(*) FROM students WHERE is_active=1", fetch="scalar") or 0
    total_t = q("SELECT COUNT(*) FROM users WHERE role='teacher' AND is_active=1", fetch="scalar") or 0
    today_att = q("SELECT COUNT(*) FROM teacher_attendance WHERE att_date=?", (str(date.today()),), fetch="scalar") or 0
    pending_ex = q("SELECT COUNT(*) FROM exams WHERE status='پینڈنگ'", fetch="scalar") or 0
    pending_lv = q("SELECT COUNT(*) FROM leave_requests WHERE status='پینڈنگ'", fetch="scalar") or 0
    total_recs = (q("SELECT COUNT(*) FROM hifz_records", fetch="scalar") or 0) + \
                 (q("SELECT COUNT(*) FROM qaida_records", fetch="scalar") or 0)

    st.markdown(f"""
    <div class="metrics-row">
        <div class="metric-card"><div class="metric-icon">👨‍🎓</div><div class="metric-val">{total_s}</div><div class="metric-lbl">کل طلباء</div></div>
        <div class="metric-card"><div class="metric-icon">👩‍🏫</div><div class="metric-val">{total_t}</div><div class="metric-lbl">کل اساتذہ</div></div>
        <div class="metric-card"><div class="metric-icon">✅</div><div class="metric-val">{today_att}</div><div class="metric-lbl">آج کی حاضری</div></div>
        <div class="metric-card"><div class="metric-icon">📋</div><div class="metric-val">{total_recs}</div><div class="metric-lbl">کل ریکارڈز</div></div>
    </div>
    """, unsafe_allow_html=True)

    if pending_lv > 0:
        st.warning(f"⏳ {pending_lv} رخصت درخواستیں منتظر ہیں")
    if pending_ex > 0:
        st.info(f"🎓 {pending_ex} امتحان پینڈنگ ہیں")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.markdown("### 📅 آج کی اساتذہ حاضری")
        today_t = q("SELECT username, arrival, departure FROM teacher_attendance WHERE att_date=?", (str(date.today()),))
        if today_t:
            df_t = pd.DataFrame(today_t)
            df_t.columns = ["استاد","آمد","رخصت"]
            st.dataframe(df_t, use_container_width=True, hide_index=True)
        else:
            st.info("کوئی حاضری نہیں")
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.markdown("### 🔔 تازہ نوٹیفیکیشنز")
        notifs = q("SELECT title, message FROM notifications ORDER BY created_at DESC LIMIT 5")
        if notifs:
            for n in notifs:
                st.markdown(f"""<div class="notif-card"><h5>{n['title']}</h5><p>{n['message'][:80]}</p></div>""", unsafe_allow_html=True)
        else:
            st.info("کوئی نوٹیفیکیشن نہیں")
        st.markdown("</div>", unsafe_allow_html=True)

    with c3:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.markdown("### 📊 شعبہ وار طلباء")
        dept_data = q("SELECT dept, COUNT(*) as cnt FROM students WHERE is_active=1 GROUP BY dept")
        if dept_data:
            for d in dept_data:
                total = total_s or 1
                pct = int((d['cnt'] / total) * 100)
                st.markdown(f"""
                <div style="margin-bottom:0.6rem">
                    <div style="display:flex;justify-content:space-between">
                        <span style="font-size:0.85rem;font-weight:600">{d['dept']}</span>
                        <span style="font-size:0.85rem;color:var(--jade)">{d['cnt']}</span>
                    </div>
                    <div class="progress-wrap" style="height:12px">
                        <div class="progress-bar" style="width:{pct}%"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════
# ─── DAILY REPORT ──────────────────────────────────────
# ═══════════════════════════════════════════════════════
elif pg == "daily_report" and IS_ADMIN:
    page_header("📋","یومیہ تعلیمی رپورٹ","تمام شعبوں کا روزانہ ریکارڈ")

    c1, c2, c3, c4 = st.columns(4)
    d1 = c1.date_input("تاریخ آغاز", date.today().replace(day=1))
    d2 = c2.date_input("تاریخ اختتام", date.today())
    dept_sel = c3.selectbox("شعبہ", ["تمام","حفظ","قاعدہ","درسِ نظامی","عصری تعلیم"])
    teachers = ["تمام"] + [r['username'] for r in q("SELECT username FROM users WHERE role='teacher' AND is_active=1")]
    t_sel = c4.selectbox("استاد", teachers)

    combined = []

    if dept_sel in ["تمام","حفظ"]:
        rows = q("""SELECT h.rec_date,s.name,s.father_name,s.roll_no,h.teacher,
                   'حفظ' as dept, h.sabaq,h.sabaq_lines,h.sq_p,h.sq_mistakes,
                   h.manzil_p,h.manzil_mistakes,h.attendance,h.cleanliness,h.grade
                   FROM hifz_records h JOIN students s ON h.student_id=s.id
                   WHERE h.rec_date BETWEEN ? AND ?""", (str(d1), str(d2)))
        if t_sel != "تمام":
            rows = [r for r in rows if r['teacher'] == t_sel]
        combined.extend(rows)

    if dept_sel in ["تمام","قاعدہ"]:
        rows = q("""SELECT q.rec_date,s.name,s.father_name,s.roll_no,q.teacher,
                   'قاعدہ' as dept,q.lesson_no as sabaq,q.total_lines as sabaq_lines,
                   '' as sq_p, 0 as sq_mistakes, '' as manzil_p, 0 as manzil_mistakes,
                   q.attendance,q.cleanliness,'' as grade
                   FROM qaida_records q JOIN students s ON q.student_id=s.id
                   WHERE q.rec_date BETWEEN ? AND ?""", (str(d1), str(d2)))
        if t_sel != "تمام":
            rows = [r for r in rows if r['teacher'] == t_sel]
        combined.extend(rows)

    if dept_sel in ["تمام","درسِ نظامی","عصری تعلیم"]:
        d_filter = "" if dept_sel == "تمام" else f" AND g.dept='{dept_sel}'"
        t_filter = "" if t_sel == "تمام" else f" AND g.teacher='{t_sel}'"
        rows = q(f"""SELECT g.rec_date,s.name,s.father_name,s.roll_no,g.teacher,
                    g.dept,g.subject as sabaq,0 as sabaq_lines,'',0,'',0,
                    g.attendance,g.cleanliness,g.performance as grade
                    FROM general_records g JOIN students s ON g.student_id=s.id
                    WHERE g.rec_date BETWEEN ? AND ?{d_filter}{t_filter}""", (str(d1), str(d2)))
        combined.extend(rows)

    if combined:
        df = pd.DataFrame(combined)
        rename = {"rec_date":"تاریخ","name":"نام","father_name":"والد","roll_no":"رول نمبر",
                  "teacher":"استاد","dept":"شعبہ","sabaq":"سبق","sabaq_lines":"ستر",
                  "sq_p":"سبقی","sq_mistakes":"سبقی غلطی","manzil_p":"منزل",
                  "manzil_mistakes":"منزل غلطی","attendance":"حاضری","cleanliness":"صفائی","grade":"درجہ"}
        df = df.rename(columns=rename)
        st.success(f"✅ کل {len(df)} ریکارڈ ملے")
        st.dataframe(df, use_container_width=True, hide_index=True)
        c1, c2 = st.columns(2)
        c1.download_button("📥 CSV ڈاؤن لوڈ", df.to_csv(index=False).encode('utf-8-sig'), "report.csv", "text/csv")
        html = gen_html_report(df, "یومیہ تعلیمی رپورٹ", f"{d1} تا {d2}")
        c2.download_button("📥 HTML رپورٹ", html, "report.html", "text/html")
    else:
        st.info("کوئی ریکارڈ نہیں ملا")

# ═══════════════════════════════════════════════════════
# ─── EXAMS ─────────────────────────────────────────────
# ═══════════════════════════════════════════════════════
elif pg == "exams" and IS_ADMIN:
    page_header("🎓","امتحانی نظام","امتحانات کا انتظام اور نتائج")
    tab1, tab2 = st.tabs(["⏳ پینڈنگ", "✅ مکمل"])

    with tab1:
        pending = q("""SELECT e.*,s.name,s.father_name,s.roll_no FROM exams e
                      JOIN students s ON e.student_id=s.id WHERE e.status='پینڈنگ' ORDER BY e.created_at DESC""")
        if not pending:
            st.markdown("<div style='text-align:center;padding:2rem;color:var(--success);font-size:1.5rem'>✅ کوئی پینڈنگ نہیں</div>", unsafe_allow_html=True)
        for ex in pending:
            with st.expander(f"👤 {ex['name']} ولد {ex['father_name']} | {ex['dept']} | {ex['exam_type']}"):
                c1,c2,c3 = st.columns(3)
                c1.info(f"📅 **شروع:** {ex['start_date']}")
                c2.info(f"📅 **ختم:** {ex['end_date'] or '---'}")
                c3.info(f"🗓️ **کل دن:** {ex['total_days'] or '---'}")
                if ex['from_para']:
                    st.info(f"📖 پارہ: {ex['from_para']} تا {ex['to_para']}")
                if ex['book_name']:
                    st.info(f"📚 کتاب: {ex['book_name']} | مقدار: {ex['amount_read']}")

                cols = st.columns(5)
                qs = [cols[i].number_input(f"س{i+1}", 0, 20, 0, key=f"q{i}_{ex['id']}") for i in range(5)]
                total = sum(qs)
                if total >= 90: g = "ممتاز"
                elif total >= 80: g = "جید جداً"
                elif total >= 70: g = "جید"
                elif total >= 60: g = "مقبول"
                else: g = "ناکام"
                gcls = GRADE_MAP.get(g, "grade-fail")
                st.markdown(f"**کل:** {total}/100 &nbsp; <span class='grade-badge {gcls}'>{g}</span>", unsafe_allow_html=True)

                if st.button("✅ نتیجہ محفوظ کریں", key=f"clr_{ex['id']}"):
                    qw("UPDATE exams SET q1=?,q2=?,q3=?,q4=?,q5=?,total=?,grade=?,status=?,end_date=? WHERE id=?",
                       (*qs, total, g, "مکمل", str(date.today()), ex['id']))
                    if g != "ناکام":
                        sid = ex['student_id']
                        if ex['from_para']:
                            for p in range(int(ex['from_para']), int(ex['to_para'])+1):
                                if not q("SELECT id FROM passed_paras WHERE student_id=? AND para_no=?", (sid,p), fetch="one"):
                                    qw("INSERT INTO passed_paras (student_id,para_no,passed_date,exam_type,grade,marks) VALUES (?,?,?,?,?,?)",
                                       (sid,p,str(date.today()),ex['exam_type'],g,total))
                        elif ex['book_name']:
                            if not q("SELECT id FROM passed_paras WHERE student_id=? AND book_name=?", (sid,ex['book_name']), fetch="one"):
                                qw("INSERT INTO passed_paras (student_id,book_name,passed_date,exam_type,grade,marks) VALUES (?,?,?,?,?,?)",
                                   (sid,ex['book_name'],str(date.today()),ex['exam_type'],g,total))
                    audit(st.session_state.username, "Exam Cleared", f"id={ex['id']},grade={g}")
                    st.success("محفوظ!")
                    st.rerun()

    with tab2:
        done = q("""SELECT s.name,s.father_name,s.roll_no,e.dept,e.exam_type,
                   e.total,e.grade,e.end_date FROM exams e
                   JOIN students s ON e.student_id=s.id WHERE e.status='مکمل' ORDER BY e.end_date DESC""")
        if done:
            df = pd.DataFrame(done)
            df.columns = ["نام","والد","رول","شعبہ","امتحان","نمبر","گریڈ","تاریخ"]
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.download_button("📥 CSV", df.to_csv(index=False).encode('utf-8-sig'), "exams.csv")
        else:
            st.info("کوئی مکمل امتحان نہیں")

# ═══════════════════════════════════════════════════════
# ─── RESULT CARD ───────────────────────────────────────
# ═══════════════════════════════════════════════════════
elif pg == "result_card" and IS_ADMIN:
    page_header("📜","ماہانہ رزلٹ کارڈ","طالب علم کی ماہانہ کارکردگی")
    studs = q("SELECT id,name,father_name,roll_no,dept FROM students WHERE is_active=1 ORDER BY name")
    if not studs:
        st.warning("کوئی طالب علم نہیں"); st.stop()

    c1,c2,c3 = st.columns([2,1,1])
    names = [f"{s['name']} ولد {s['father_name']} ({s['dept']})" for s in studs]
    sel_idx = c1.selectbox("طالب علم", range(len(names)), format_func=lambda i: names[i])
    sel_s = studs[sel_idx]
    d1 = c2.date_input("تاریخ آغاز", date.today().replace(day=1))
    d2 = c3.date_input("تاریخ اختتام", date.today())

    if sel_s['dept'] == "حفظ":
        rows = q("""SELECT rec_date as تاریخ,attendance as حاضری,sabaq as سبق,sabaq_lines as ستر,
                   sq_p as سبقی,sq_mistakes as 'سبقی غلطی',manzil_p as منزل,
                   manzil_mistakes as 'منزل غلطی',cleanliness as صفائی,grade as درجہ
                   FROM hifz_records WHERE student_id=? AND rec_date BETWEEN ? AND ? ORDER BY rec_date""",
                 (sel_s['id'], str(d1), str(d2)))
    elif sel_s['dept'] == "قاعدہ":
        rows = q("""SELECT rec_date as تاریخ,attendance as حاضری,lesson_no as سبق,
                   total_lines as لائنیں,cleanliness as صفائی,note as نوٹ
                   FROM qaida_records WHERE student_id=? AND rec_date BETWEEN ? AND ? ORDER BY rec_date""",
                 (sel_s['id'], str(d1), str(d2)))
    else:
        rows = q("""SELECT rec_date as تاریخ,attendance as حاضری,subject as مضمون,
                   lesson as سبق,performance as کارکردگی,cleanliness as صفائی
                   FROM general_records WHERE student_id=? AND dept=? AND rec_date BETWEEN ? AND ? ORDER BY rec_date""",
                 (sel_s['id'], sel_s['dept'], str(d1), str(d2)))

    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
        html = gen_html_report(df, "ماہانہ رزلٹ کارڈ", f"{sel_s['name']} ولد {sel_s['father_name']} | {d1} تا {d2}")
        c1,c2 = st.columns(2)
        c1.download_button("📥 HTML رپورٹ", html, f"result_{sel_s['name']}.html", "text/html")
        c2.download_button("📥 CSV", df.to_csv(index=False).encode('utf-8-sig'), f"result_{sel_s['name']}.csv")
    else:
        st.info("اس مدت میں کوئی ریکارڈ نہیں")

# ═══════════════════════════════════════════════════════
# ─── PARA REPORT ───────────────────────────────────────
# ═══════════════════════════════════════════════════════
elif pg == "para_report" and IS_ADMIN:
    page_header("📖","پارہ تعلیمی رپورٹ","حفظ کی پیشرفت")
    studs = q("SELECT id,name,father_name FROM students WHERE dept='حفظ' AND is_active=1 ORDER BY name")
    if not studs:
        st.warning("کوئی حفظ کا طالب علم نہیں"); st.stop()
    names = [f"{s['name']} ولد {s['father_name']}" for s in studs]
    idx = st.selectbox("طالب علم", range(len(names)), format_func=lambda i: names[i])
    sel = studs[idx]
    passed = q("""SELECT para_no as 'پارہ نمبر',passed_date as 'تاریخ پاس',
                 exam_type as 'امتحان',grade as گریڈ,marks as نمبر
                 FROM passed_paras WHERE student_id=? AND para_no IS NOT NULL ORDER BY para_no""",
               (sel['id'],))
    cnt = len(passed)
    pct = (cnt/30)*100
    st.markdown(f"""
    <div class="section-card">
        <h4 style="color:var(--jade)">قرآن مجید کی پیشرفت: {cnt}/30 پارے ({pct:.1f}%)</h4>
        <div class="progress-wrap">
            <div class="progress-bar" style="width:{pct:.0f}%">
                <span class="progress-text">{pct:.0f}%</span>
            </div>
        </div>
        <p style="color:var(--gray);font-size:0.82rem">{30-cnt} پارے باقی ہیں</p>
    </div>
    """, unsafe_allow_html=True)
    if passed:
        df = pd.DataFrame(passed)
        st.dataframe(df, use_container_width=True, hide_index=True)
        html = gen_html_report(df, "پارہ تعلیمی رپورٹ", f"{sel['name']} ولد {sel['father_name']}")
        st.download_button("📥 رپورٹ ڈاؤن لوڈ", html, f"para_{sel['name']}.html", "text/html")
    else:
        st.info("کوئی پاس شدہ پارہ نہیں")

# ═══════════════════════════════════════════════════════
# ─── TEACHER ATTENDANCE (ADMIN VIEW) ───────────────────
# ═══════════════════════════════════════════════════════
elif pg == "teacher_att" and IS_ADMIN:
    page_header("🕒","اساتذہ حاضری","حاضری کا مکمل ریکارڈ")
    c1,c2,c3 = st.columns(3)
    d1 = c1.date_input("تاریخ آغاز", date.today().replace(day=1))
    d2 = c2.date_input("تاریخ اختتام", date.today())
    teachers = ["تمام"] + [r['username'] for r in q("SELECT username FROM users WHERE role='teacher' AND is_active=1")]
    t_sel = c3.selectbox("استاد", teachers)

    t_filter = "" if t_sel == "تمام" else f" AND username='{t_sel}'"
    rows = q(f"SELECT username as استاد,att_date as تاریخ,arrival as آمد,departure as رخصت FROM teacher_attendance WHERE att_date BETWEEN ? AND ?{t_filter} ORDER BY att_date DESC", (str(d1),str(d2)))
    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button("📥 CSV", df.to_csv(index=False).encode('utf-8-sig'), "teacher_att.csv")
    else:
        st.info("کوئی ریکارڈ نہیں")

    st.markdown("---")
    st.subheader("✏️ حاضری درج/تبدیل کریں (ایڈمن)")
    with st.form("admin_att_form"):
        c1,c2,c3,c4 = st.columns(4)
        at_teacher = c1.selectbox("استاد", teachers[1:])
        at_date = c2.date_input("تاریخ", date.today())
        at_arr = c3.text_input("آمد", placeholder="09:00 AM")
        at_dep = c4.text_input("رخصت", placeholder="03:00 PM")
        if st.form_submit_button("💾 محفوظ کریں"):
            existing = q("SELECT id FROM teacher_attendance WHERE username=? AND att_date=?", (at_teacher, str(at_date)), fetch="one")
            if existing:
                qw("UPDATE teacher_attendance SET arrival=?,departure=? WHERE username=? AND att_date=?", (at_arr, at_dep, at_teacher, str(at_date)))
            else:
                qw("INSERT INTO teacher_attendance (username,att_date,arrival,departure) VALUES (?,?,?,?)", (at_teacher, str(at_date), at_arr, at_dep))
            st.success("✅ محفوظ")
            st.rerun()

# ═══════════════════════════════════════════════════════
# ─── LEAVES ────────────────────────────────────────────
# ═══════════════════════════════════════════════════════
elif pg == "leaves" and IS_ADMIN:
    page_header("🏛️","رخصت کی منظوری","درخواستوں کا انتظام")
    tab1, tab2 = st.tabs(["⏳ پینڈنگ", "📜 تمام ریکارڈ"])

    with tab1:
        pending = q("SELECT * FROM leave_requests WHERE status='پینڈنگ' ORDER BY created_at DESC")
        if not pending:
            st.markdown("<div style='text-align:center;padding:2rem;color:var(--success);font-size:1.3rem'>✅ کوئی پینڈنگ نہیں</div>", unsafe_allow_html=True)
        for lv in pending:
            st.markdown(f"""
            <div class="leave-card">
                <div style="display:flex;justify-content:space-between;align-items:center">
                    <div>
                        <strong>👤 {lv['username']}</strong> &nbsp;
                        <span class="status-pill status-pending">{lv['leave_type']}</span>
                    </div>
                    <div>📅 {lv['start_date']} | {lv['days']} دن</div>
                </div>
                <p style="color:var(--gray);font-size:0.88rem;margin-top:0.4rem">وجہ: {lv['reason']}</p>
            </div>
            """, unsafe_allow_html=True)
            c1,c2 = st.columns(2)
            if c1.button("✅ منظور", key=f"apr_{lv['id']}", use_container_width=True):
                qw("UPDATE leave_requests SET status='منظور' WHERE id=?", (lv['id'],))
                audit(st.session_state.username, "Leave Approved", f"id={lv['id']}")
                st.rerun()
            if c2.button("❌ مسترد", key=f"rej_{lv['id']}", use_container_width=True):
                qw("UPDATE leave_requests SET status='مسترد' WHERE id=?", (lv['id'],))
                st.rerun()

    with tab2:
        all_lv = q("""SELECT username as استاد,leave_type as نوعیت,start_date as تاریخ,
                      days as دن,reason as وجہ,status as حالت FROM leave_requests ORDER BY created_at DESC""")
        if all_lv:
            df = pd.DataFrame(all_lv)
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.download_button("📥 CSV", df.to_csv(index=False).encode('utf-8-sig'), "leaves.csv")

# ═══════════════════════════════════════════════════════
# ─── USER MANAGEMENT ───────────────────────────────────
# ═══════════════════════════════════════════════════════
elif pg == "users" and IS_ADMIN:
    page_header("👥","یوزر مینجمنٹ","اساتذہ اور طلباء کا مکمل انتظام")
    tab1, tab2 = st.tabs(["👩‍🏫 اساتذہ", "👨‍🎓 طلبہ"])

    with tab1:
        teachers_all = q("SELECT * FROM users WHERE role='teacher' ORDER BY username")
        if teachers_all:
            st.markdown("### موجودہ اساتذہ — ترمیم کریں")
            df_t = pd.DataFrame(teachers_all)
            display_cols = ['id','username','dept','phone','id_card','joining_date','is_active']
            display_cols = [c for c in display_cols if c in df_t.columns]
            df_show = df_t[display_cols].copy()
            col_rename = {'id':'ID','username':'نام','dept':'شعبہ','phone':'فون',
                         'id_card':'شناختی کارڈ','joining_date':'تاریخ شمولیت','is_active':'فعال'}
            df_show = df_show.rename(columns=col_rename)
            edited = st.data_editor(df_show, use_container_width=True, num_rows="dynamic", key="teachers_edit")
            if st.button("💾 تبدیلیاں محفوظ کریں (اساتذہ)"):
                for _, row in edited.iterrows():
                    if pd.notna(row.get('ID')) and row.get('ID'):
                        qw("UPDATE users SET dept=?,phone=?,id_card=?,joining_date=?,is_active=? WHERE id=?",
                           (row.get('شعبہ',''), row.get('فون',''), row.get('شناختی کارڈ',''),
                            row.get('تاریخ شمولیت',''), int(row.get('فعال',1)), int(row['ID'])))
                st.success("✅ تبدیلیاں محفوظ!")
                st.rerun()

        with st.expander("➕ نیا استاد رجسٹر کریں"):
            with st.form("add_teacher"):
                c1,c2 = st.columns(2)
                t_name = c1.text_input("نام*")
                t_pass = c2.text_input("پاسورڈ*", type="password")
                t_dept = c1.selectbox("شعبہ", DEPTS)
                t_phone = c2.text_input("فون")
                t_idcard = c1.text_input("شناختی کارڈ")
                t_join = c2.date_input("تاریخ شمولیت", date.today())
                t_addr = st.text_area("پتہ")
                if st.form_submit_button("✅ رجسٹر کریں"):
                    if t_name and t_pass:
                        try:
                            qw("INSERT INTO users (username,password,role,dept,phone,id_card,joining_date,address) VALUES (?,?,?,?,?,?,?,?)",
                               (t_name.strip(), hash_pw(t_pass), 'teacher', t_dept, t_phone, t_idcard, str(t_join), t_addr))
                            audit(st.session_state.username, "Teacher Added", t_name)
                            st.success(f"✅ {t_name} کامیابی سے رجسٹر!")
                            st.rerun()
                        except:
                            st.error("یہ نام پہلے سے موجود ہے")
                    else:
                        st.error("نام اور پاسورڈ ضروری ہیں")

    with tab2:
        students_all = q("SELECT * FROM students ORDER BY name")
        if students_all:
            st.markdown("### موجودہ طلبہ — ترمیم کریں")
            df_s = pd.DataFrame(students_all)
            display_cols = ['id','name','father_name','roll_no','dept','teacher','phone','is_active']
            display_cols = [c for c in display_cols if c in df_s.columns]
            df_show = df_s[display_cols].copy()
            col_rename = {'id':'ID','name':'نام','father_name':'والد','roll_no':'رول نمبر',
                         'dept':'شعبہ','teacher':'استاد','phone':'فون','is_active':'فعال'}
            df_show = df_show.rename(columns=col_rename)
            edited_s = st.data_editor(df_show, use_container_width=True, num_rows="dynamic", key="students_edit")
            if st.button("💾 تبدیلیاں محفوظ کریں (طلبہ)"):
                for _, row in edited_s.iterrows():
                    if pd.notna(row.get('ID')) and row.get('ID'):
                        qw("UPDATE students SET name=?,father_name=?,roll_no=?,dept=?,teacher=?,phone=?,is_active=? WHERE id=?",
                           (row.get('نام',''), row.get('والد',''), row.get('رول نمبر',''),
                            row.get('شعبہ',''), row.get('استاد',''), row.get('فون',''),
                            int(row.get('فعال',1)), int(row['ID'])))
                st.success("✅ تبدیلیاں محفوظ!")
                st.rerun()

        with st.expander("➕ نیا طالب علم داخل کریں"):
            with st.form("add_student"):
                c1,c2 = st.columns(2)
                s_name = c1.text_input("نام*")
                s_father = c2.text_input("والد کا نام*")
                s_mother = c1.text_input("والدہ کا نام")
                s_roll = c2.text_input("رول نمبر", placeholder="مثلاً 2024-001")
                s_dob = c1.date_input("تاریخ پیدائش", date.today()-timedelta(days=365*10))
                s_adm = c2.date_input("تاریخ داخلہ", date.today())
                s_dept = c1.selectbox("شعبہ*", DEPTS)
                t_list = [r['username'] for r in q("SELECT username FROM users WHERE role='teacher' AND is_active=1")]
                s_teacher = c2.selectbox("استاد*", t_list) if t_list else c2.text_input("استاد")
                s_class = c1.text_input("کلاس")
                s_section = c2.text_input("سیکشن")
                s_phone = c1.text_input("فون")
                s_addr = st.text_area("پتہ")
                if st.form_submit_button("✅ داخلہ کریں"):
                    if s_name and s_father:
                        qw("""INSERT INTO students (name,father_name,mother_name,roll_no,dob,admission_date,
                              phone,address,teacher,dept,class_name,section) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                           (s_name.strip(), s_father.strip(), s_mother, s_roll, str(s_dob), str(s_adm),
                            s_phone, s_addr, s_teacher, s_dept, s_class, s_section))
                        audit(st.session_state.username, "Student Added", s_name)
                        st.success(f"✅ {s_name} کامیابی سے داخل!")
                        st.rerun()
                    else:
                        st.error("نام اور والد کا نام ضروری ہیں")

# ═══════════════════════════════════════════════════════
# ─── TIMETABLE ─────────────────────────────────────────
# ═══════════════════════════════════════════════════════
elif pg == "timetable" and IS_ADMIN:
    page_header("📚","ٹائم ٹیبل مینجمنٹ","اساتذہ کا ٹائم ٹیبل")
    t_list = [r['username'] for r in q("SELECT username FROM users WHERE role='teacher' AND is_active=1")]
    if not t_list:
        st.warning("پہلے اساتذہ رجسٹر کریں"); st.stop()

    sel_t = st.selectbox("استاد منتخب کریں", t_list)
    tt = q("SELECT id,day,period,subject,room FROM timetable WHERE teacher=? ORDER BY day,period", (sel_t,))

    if tt:
        df_tt = pd.DataFrame(tt)
        df_tt.columns = ["ID","دن","وقت","مضمون","کمرہ"]
        edited_tt = st.data_editor(df_tt, use_container_width=True, key="tt_edit", num_rows="dynamic")
        c1,c2 = st.columns(2)
        if c1.button("💾 تبدیلیاں محفوظ کریں"):
            for _, row in edited_tt.iterrows():
                if pd.notna(row.get('ID')) and row.get('ID'):
                    qw("UPDATE timetable SET day=?,period=?,subject=?,room=? WHERE id=?",
                       (row.get('دن',''), row.get('وقت',''), row.get('مضمون',''), row.get('کمرہ',''), int(row['ID'])))
                elif pd.isna(row.get('ID')) or not row.get('ID'):
                    qw("INSERT INTO timetable (teacher,day,period,subject,room) VALUES (?,?,?,?,?)",
                       (sel_t, row.get('دن',''), row.get('وقت',''), row.get('مضمون',''), row.get('کمرہ','')))
            st.success("✅ محفوظ!"); st.rerun()
        if c2.button("🗑️ اس استاد کا ٹائم ٹیبل حذف کریں"):
            qw("DELETE FROM timetable WHERE teacher=?", (sel_t,))
            st.success("حذف کر دیا"); st.rerun()

    with st.expander("➕ نیا پیریڈ شامل کریں"):
        with st.form("add_period"):
            c1,c2,c3,c4 = st.columns(4)
            day = c1.selectbox("دن", DAYS)
            period = c2.text_input("وقت", placeholder="08:00-09:00")
            subject = c3.text_input("مضمون")
            room = c4.text_input("کمرہ")
            if st.form_submit_button("➕ شامل کریں"):
                qw("INSERT INTO timetable (teacher,day,period,subject,room) VALUES (?,?,?,?,?)",
                   (sel_t, day, period, subject, room))
                st.success("✅ شامل!"); st.rerun()

# ═══════════════════════════════════════════════════════
# ─── STAFF MONITORING ──────────────────────────────────
# ═══════════════════════════════════════════════════════
elif pg == "monitoring" and IS_ADMIN:
    page_header("📋","عملہ نگرانی و شکایات","اساتذہ کی کارکردگی کا ریکارڈ")
    tab1, tab2 = st.tabs(["➕ نیا اندراج", "📜 ریکارڈ"])

    with tab1:
        t_list = [r['username'] for r in q("SELECT username FROM users WHERE role='teacher' AND is_active=1")]
        with st.form("mon_form"):
            c1,c2 = st.columns(2)
            staff = c1.selectbox("عملہ", t_list) if t_list else c1.text_input("عملہ")
            n_date = c2.date_input("تاریخ", date.today())
            n_type = c1.selectbox("نوعیت", ["یادداشت","شکایت","تنبیہ","تعریف","کارکردگی جائزہ"])
            status = c2.selectbox("حالت", ["زیر التواء","حل شدہ","زیر غور"])
            desc = st.text_area("تفصیل*", max_chars=1000)
            action = st.text_area("کارروائی", max_chars=500)
            if st.form_submit_button("✅ محفوظ کریں"):
                if desc:
                    qw("INSERT INTO staff_notes (staff,note_date,note_type,description,action,status,created_by) VALUES (?,?,?,?,?,?,?)",
                       (staff, str(n_date), n_type, desc, action, status, st.session_state.username))
                    audit(st.session_state.username, "Staff Note Added", f"{staff}-{n_type}")
                    st.success("✅ محفوظ!"); st.rerun()
                else:
                    st.error("تفصیل ضروری ہے")

    with tab2:
        notes = q("""SELECT id,staff as عملہ,note_date as تاریخ,note_type as نوعیت,
                    description as تفصیل,action as کارروائی,status as حالت,created_by as 'داخل کردہ'
                    FROM staff_notes ORDER BY note_date DESC""")
        if notes:
            df = pd.DataFrame(notes)
            edited_n = st.data_editor(df, use_container_width=True, num_rows="dynamic", key="notes_edit")
            c1,c2 = st.columns(2)
            if c1.button("💾 تبدیلیاں محفوظ کریں"):
                for _, row in edited_n.iterrows():
                    if pd.notna(row.get('id')) and row.get('id'):
                        qw("UPDATE staff_notes SET status=?,action=? WHERE id=?",
                           (row.get('حالت',''), row.get('کارروائی',''), int(row['id'])))
                st.success("✅ محفوظ!"); st.rerun()
            st.download_button("📥 CSV", df.to_csv(index=False).encode('utf-8-sig'), "monitoring.csv", use_container_width=True)
        else:
            st.info("کوئی ریکارڈ نہیں")

# ═══════════════════════════════════════════════════════
# ─── NOTIFICATIONS ─────────────────────────════════════
# ═══════════════════════════════════════════════════════
elif pg == "notifs":
    page_header("📢","نوٹیفیکیشن سینٹر","اعلانات اور پیغامات")
    if IS_ADMIN:
        with st.expander("➕ نیا نوٹیفیکیشن"):
            with st.form("notif_form"):
                title = st.text_input("عنوان*")
                msg = st.text_area("پیغام*")
                target = st.selectbox("وصول کنندہ", ["تمام","اساتذہ","طلبہ"])
                if st.form_submit_button("📤 بھیجیں"):
                    if title and msg:
                        qw("INSERT INTO notifications (title,message,target,created_by) VALUES (?,?,?,?)",
                           (title, msg, target, st.session_state.username))
                        st.success("✅ بھیج دیا!"); st.rerun()
                    else:
                        st.error("عنوان اور پیغام ضروری ہیں")

    notifs = q("SELECT title,message,target,created_by,created_at FROM notifications ORDER BY created_at DESC LIMIT 20")
    if notifs:
        for n in notifs:
            st.markdown(f"""
            <div class="notif-card">
                <h5>🔔 {n['title']} &nbsp; <small style="color:var(--gray)">({n['target']})</small></h5>
                <p>{n['message']}</p>
                <small>از: {n['created_by']} | {n['created_at'][:16]}</small>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("کوئی نوٹیفیکیشن نہیں")

# ═══════════════════════════════════════════════════════
# ─── ANALYTICS ─────────────────────────────────────────
# ═══════════════════════════════════════════════════════
elif pg == "analytics" and IS_ADMIN:
    try:
        import plotly.express as px
        import plotly.graph_objects as go
    except ImportError:
        st.error("براہ کرم plotly انسٹال کریں: pip install plotly")
        st.stop()
    page_header("📈","تجزیہ و رپورٹس","اعداد و شمار کا تجزیہ")

    c1,c2 = st.columns(2)
    with c1:
        dept_data = q("SELECT dept, COUNT(*) as cnt FROM students WHERE is_active=1 GROUP BY dept")
        if dept_data:
            fig = px.pie(pd.DataFrame(dept_data), values='cnt', names='dept',
                        title='شعبہ وار طلباء',
                        color_discrete_sequence=['#0a4d3c','#0d6b54','#c9982a','#f0bc50'])
            fig.update_layout(font_family="serif",title_x=0.5)
            st.plotly_chart(fig, use_container_width=True)

    with c2:
        exam_data = q("SELECT grade, COUNT(*) as cnt FROM exams WHERE status='مکمل' AND grade IS NOT NULL GROUP BY grade")
        if exam_data:
            fig2 = px.bar(pd.DataFrame(exam_data), x='grade', y='cnt',
                         title='امتحانی نتائج',
                         color='cnt', color_continuous_scale=['#e8f5f0','#0a4d3c'])
            fig2.update_layout(font_family="serif",title_x=0.5)
            st.plotly_chart(fig2, use_container_width=True)

    att_trend = q("""SELECT att_date, COUNT(*) as cnt FROM teacher_attendance
                    WHERE att_date >= ? GROUP BY att_date ORDER BY att_date""",
                 (str(date.today()-timedelta(days=30)),))
    if att_trend:
        fig3 = px.line(pd.DataFrame(att_trend), x='att_date', y='cnt',
                      title='ماہانہ حاضری رجحان (گزشتہ 30 دن)',
                      line_shape='spline', markers=True,
                      color_discrete_sequence=['#0a4d3c'])
        fig3.update_layout(font_family="serif",title_x=0.5)
        st.plotly_chart(fig3, use_container_width=True)

# ═══════════════════════════════════════════════════════
# ─── BEST STUDENTS ─────────────────────────────────────
# ═══════════════════════════════════════════════════════
elif pg == "best_students" and IS_ADMIN:
    page_header("🏆","ماہانہ بہترین طلباء","تعلیمی اور صفائی کی بنیاد پر")

    c1,c2 = st.columns(2)
    month = c1.date_input("مہینہ", date.today().replace(day=1))
    dept_f = c2.selectbox("شعبہ", ["تمام"]+DEPTS)

    d1 = month.replace(day=1)
    if month.month == 12:
        d2 = month.replace(year=month.year+1, month=1, day=1) - timedelta(days=1)
    else:
        d2 = month.replace(month=month.month+1, day=1) - timedelta(days=1)

    dept_where = "" if dept_f == "تمام" else f" AND dept='{dept_f}'"
    studs = q(f"SELECT id,name,father_name,roll_no,dept FROM students WHERE is_active=1{dept_where}")

    scores = []
    for s in studs:
        grade_scores = []
        clean_scores = []
        if s['dept'] == "حفظ":
            recs = q("SELECT attendance,sabaq_nagha,sq_nagha,manzil_nagha,sq_mistakes,manzil_mistakes,cleanliness FROM hifz_records WHERE student_id=? AND rec_date BETWEEN ? AND ?",
                    (s['id'], str(d1), str(d2)))
            for r in recs:
                gr = calc_grade(r['attendance'], r['sabaq_nagha'], r['sq_nagha'], r['manzil_nagha'],
                               r['sq_mistakes'], r['manzil_mistakes'])
                gmap = {"ممتاز":100,"جید جداً":85,"جید":75,"مقبول":60,"دوبارہ کوشش":40,
                        "ناقص (ناغہ)":30,"کمزور (ناغہ)":20,"ناکام (مکمل ناغہ)":10,"غیر حاضر":0,"رخصت":50}
                grade_scores.append(gmap.get(gr, 0))
                if r['cleanliness']:
                    clean_scores.append(clean_score(r['cleanliness']))
        else:
            recs = q("SELECT attendance,performance,cleanliness FROM general_records WHERE student_id=? AND rec_date BETWEEN ? AND ?",
                    (s['id'], str(d1), str(d2)))
            for r in recs:
                pmap = {"بہت بہتر":90,"بہتر":80,"مناسب":65,"کمزور":45}
                if r['attendance'] == "حاضر":
                    grade_scores.append(pmap.get(r['performance'] or '', 75))
                elif r['attendance'] == "رخصت":
                    grade_scores.append(50)
                else:
                    grade_scores.append(0)
                if r['cleanliness']:
                    clean_scores.append(clean_score(r['cleanliness']))

        if grade_scores:
            scores.append({
                "name": s['name'], "father": s['father_name'],
                "roll": s['roll_no'] or "—", "dept": s['dept'],
                "grade_avg": sum(grade_scores)/len(grade_scores),
                "clean_avg": (sum(clean_scores)/len(clean_scores)) if clean_scores else 0,
                "days": len(grade_scores)
            })

    if not scores:
        st.warning("اس مدت میں کوئی ریکارڈ نہیں")
    else:
        by_grade = sorted(scores, key=lambda x: x['grade_avg'], reverse=True)
        by_clean = sorted(scores, key=lambda x: x['clean_avg'], reverse=True)

        st.markdown("---")
        st.subheader("📚 تعلیمی کارکردگی")
        medals = [("🥇","#c9982a"),("🥈","#9ca3af"),("🥉","#cd7f32")]
        cols = st.columns(3)
        for i,(col,st_) in enumerate(zip(cols, by_grade[:3])):
            medal, color = medals[i]
            with col:
                st.markdown(f"""
                <div class="trophy-card">
                    <span class="medal">{medal}</span>
                    <div class="trophy-name">{st_['name']}</div>
                    <div class="trophy-sub">والد: {st_['father']}</div>
                    <div class="trophy-sub">🏫 {st_['dept']} | 📅 {st_['days']} دن</div>
                    <div class="trophy-score">{st_['grade_avg']:.1f}%</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("🧹 صفائی کے لحاظ سے")
        cols2 = st.columns(3)
        for i,(col,st_) in enumerate(zip(cols2, by_clean[:3])):
            medal, _ = medals[i]
            with col:
                pct = (st_['clean_avg']/3)*100
                st.markdown(f"""
                <div class="trophy-card">
                    <span class="medal">{medal}</span>
                    <div class="trophy-name">{st_['name']}</div>
                    <div class="trophy-sub">والد: {st_['father']}</div>
                    <div class="trophy-sub">🏫 {st_['dept']}</div>
                    <div class="trophy-score">🧹 {pct:.1f}%</div>
                </div>
                """, unsafe_allow_html=True)

        with st.expander("📊 تمام طلباء کی تفصیل"):
            df_all = pd.DataFrame(scores)
            df_all.columns = ["نام","والد","رول","شعبہ","تعلیمی %","صفائی","کل دن"]
            df_all["تعلیمی %"] = df_all["تعلیمی %"].round(1)
            df_all["صفائی"] = ((df_all["صفائی"]/3)*100).round(1)
            st.dataframe(df_all.sort_values("تعلیمی %", ascending=False), use_container_width=True, hide_index=True)
            st.download_button("📥 CSV", df_all.to_csv(index=False).encode('utf-8-sig'), "best_students.csv")

# ═══════════════════════════════════════════════════════
# ─── PASSWORD ──────────────────────────────────────────
# ═══════════════════════════════════════════════════════
elif pg == "password":
    page_header("🔑","پاسورڈ تبدیل کریں","")
    _, c2, _ = st.columns([1,2,1])
    with c2:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        if IS_ADMIN:
            st.subheader("استاد کا پاسورڈ ری سیٹ کریں")
            t_list = [r['username'] for r in q("SELECT username FROM users WHERE role='teacher'")]
            with st.form("admin_pw"):
                sel_t = st.selectbox("استاد", t_list)
                new_pw = st.text_input("نیا پاسورڈ*", type="password")
                c_pw = st.text_input("تصدیق*", type="password")
                if st.form_submit_button("✅ تبدیل کریں"):
                    if new_pw and new_pw == c_pw and len(new_pw) >= 6:
                        qw("UPDATE users SET password=? WHERE username=?", (hash_pw(new_pw), sel_t))
                        audit(st.session_state.username, "Password Reset", sel_t)
                        st.success(f"✅ {sel_t} کا پاسورڈ تبدیل!")
                    elif len(new_pw) < 6:
                        st.error("پاسورڈ کم از کم 6 حروف")
                    else:
                        st.error("پاسورڈ میل نہیں کھاتے")
            st.markdown("---")
            st.subheader("اپنا پاسورڈ تبدیل کریں")

        with st.form("my_pw"):
            old_pw = st.text_input("پرانا پاسورڈ*", type="password")
            new_pw = st.text_input("نیا پاسورڈ*", type="password")
            c_pw2 = st.text_input("تصدیق*", type="password")
            if st.form_submit_button("✅ اپنا پاسورڈ تبدیل کریں"):
                user = q("SELECT password FROM users WHERE username=?", (st.session_state.username,), fetch="one")
                if user and verify_pw(old_pw, user['password']):
                    if new_pw == c_pw2 and len(new_pw) >= 6:
                        qw("UPDATE users SET password=? WHERE username=?", (hash_pw(new_pw), st.session_state.username))
                        audit(st.session_state.username, "Password Changed")
                        st.success("✅ پاسورڈ تبدیل! دوبارہ لاگ ان کریں")
                        for k in list(st.session_state.keys()):
                            del st.session_state[k]
                        st.rerun()
                    elif len(new_pw) < 6:
                        st.error("پاسورڈ کم از کم 6 حروف")
                    else:
                        st.error("پاسورڈ میل نہیں کھاتے")
                else:
                    st.error("❌ پرانا پاسورڈ غلط ہے")
        st.markdown("</div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════
# ─── BACKUP ────────────────────────────────────────────
# ═══════════════════════════════════════════════════════
elif pg == "backup" and IS_ADMIN:
    page_header("⚙️","بیک اپ & سیٹنگز","ڈیٹا محفوظ رکھیں")
    c1,c2 = st.columns(2)
    with c1:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.subheader("📥 ڈیٹا بیس بیک اپ")
        if os.path.exists(DB):
            with open(DB,"rb") as f:
                st.download_button("💾 مکمل ڈیٹا بیس (.db)", f,
                                  f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db",
                                  "application/x-sqlite3", use_container_width=True)
        if st.button("📦 CSV زپ بنائیں", use_container_width=True):
            tables = ["users","students","hifz_records","qaida_records","general_records",
                      "teacher_attendance","leave_requests","exams","passed_paras","timetable",
                      "notifications","staff_notes","audit_log"]
            buf = io.BytesIO()
            with zipfile.ZipFile(buf,'w') as zf:
                for t in tables:
                    try:
                        rows = q(f"SELECT * FROM {t}")
                        if rows:
                            df = pd.DataFrame(rows)
                            zf.writestr(f"{t}.csv", df.to_csv(index=False).encode('utf-8-sig'))
                    except: pass
            buf.seek(0)
            st.download_button("📥 CSV زپ", buf, f"csv_{datetime.now().strftime('%Y%m%d')}.zip",
                              "application/zip", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.subheader("🔄 ری سٹور")
        st.warning("⚠️ موجودہ ڈیٹا بدل جائے گا!")
        uploaded = st.file_uploader(".db فائل", type=["db"])
        if uploaded:
            if st.checkbox("میں سمجھتا/سمجھتی ہوں") and st.button("🔄 ری سٹور کریں"):
                if os.path.exists(DB):
                    shutil.copy(DB, f"{DB}.bak_{datetime.now().strftime('%Y%m%d%H%M%S')}")
                with open(DB,"wb") as f:
                    f.write(uploaded.getbuffer())
                st.success("✅ ری سٹور مکمل"); st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.subheader("📋 آڈٹ لاگ (آخری 50)")
    logs = q("SELECT username as صارف,action as عمل,details as تفصیل,created_at as وقت FROM audit_log ORDER BY created_at DESC LIMIT 50")
    if logs:
        st.dataframe(pd.DataFrame(logs), use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════
# ─── TEACHER: DAILY ENTRY ──────────────────────────────
# ═══════════════════════════════════════════════════════
elif pg == "t_entry" and not IS_ADMIN:
    page_header("📝","روزانہ سبق اندراج","آج کے سبق کا ریکارڈ")
    c1,c2 = st.columns(2)
    entry_date = c1.date_input("تاریخ", date.today())
    dept = c2.selectbox("شعبہ", DEPTS)

    my_students = q("SELECT id,name,father_name FROM students WHERE teacher=? AND dept=? AND is_active=1",
                   (st.session_state.username, dept))
    if not my_students:
        st.info(f"آپ کی {dept} کلاس میں کوئی طالب علم نہیں"); st.stop()

    st.markdown(f"**{len(my_students)} طلباء | تاریخ: {entry_date}**")

    if dept == "حفظ":
        for s in my_students:
            existing = q("SELECT id FROM hifz_records WHERE student_id=? AND rec_date=?", (s['id'], str(entry_date)), fetch="one")
            st.markdown(f"""<div class="student-card">
                <h4>{'✅' if existing else '📝'} {s['name']} ولد {s['father_name']}</h4>""", unsafe_allow_html=True)

            if existing:
                st.success("آج کا ریکارڈ پہلے سے موجود ہے")
                st.markdown("</div>", unsafe_allow_html=True)
                continue

            k = str(s['id'])
            att = st.radio("حاضری", ["حاضر","غیر حاضر","رخصت"], key=f"att_{k}", horizontal=True)
            cleanliness = st.selectbox("صفائی", CLEANLINESS, key=f"cln_{k}")

            sabaq_nagha = sq_nagha = m_nagha = 0
            sabaq_text = sq_text = manzil_text = ""
            sabaq_lines = sq_atk = sq_mis = m_atk = m_mis = 0

            if att == "حاضر":
                st.markdown("**📖 سبق**")
                c1,c2 = st.columns(2)
                sn = c1.checkbox("ناغہ", key=f"sn_{k}")
                sy = c2.checkbox("یاد نہیں", key=f"sy_{k}")
                if sn or sy:
                    sabaq_nagha = 1
                    sabaq_text = "ناغہ" if sn else "یاد نہیں"
                else:
                    c1,c2,c3 = st.columns(3)
                    surah = c1.selectbox("سورت", SURAHS, key=f"sur_{k}")
                    a_from = c2.text_input("سے", key=f"af_{k}")
                    a_to = c3.text_input("تک", key=f"at_{k}")
                    sabaq_lines = st.number_input("ستر (لائنیں)", 0, 50, 0, key=f"sl_{k}")
                    sabaq_text = f"{surah}:{a_from}-{a_to}"

                st.markdown("**📚 سبقی**")
                c1,c2 = st.columns(2)
                sqn = c1.checkbox("ناغہ", key=f"sqn_{k}")
                sqy = c2.checkbox("یاد نہیں", key=f"sqy_{k}")
                if sqn or sqy:
                    sq_nagha = 1
                    sq_text = "ناغہ" if sqn else "یاد نہیں"
                else:
                    c1,c2,c3,c4 = st.columns(4)
                    sq_p = c1.selectbox("پارہ", PARAS, key=f"sqp_{k}")
                    sq_m = c2.selectbox("مقدار", ["مکمل","آدھا","پون","پاؤ"], key=f"sqm_{k}")
                    sq_atk = c3.number_input("اٹکن", 0, key=f"sqat_{k}")
                    sq_mis = c4.number_input("غلطی", 0, key=f"sqms_{k}")
                    sq_text = f"{sq_p}:{sq_m}"

                st.markdown("**🌙 منزل**")
                c1,c2 = st.columns(2)
                mn = c1.checkbox("ناغہ", key=f"mn_{k}")
                my_ = c2.checkbox("یاد نہیں", key=f"my_{k}")
                if mn or my_:
                    m_nagha = 1
                    manzil_text = "ناغہ" if mn else "یاد نہیں"
                else:
                    c1,c2,c3,c4 = st.columns(4)
                    m_p = c1.selectbox("پارہ", PARAS, key=f"mp_{k}")
                    m_mq = c2.selectbox("مقدار", ["مکمل","آدھا","پون","پاؤ"], key=f"mmq_{k}")
                    m_atk = c3.number_input("اٹکن", 0, key=f"mat_{k}")
                    m_mis = c4.number_input("غلطی", 0, key=f"mms_{k}")
                    manzil_text = f"{m_p}:{m_mq}"

                grade = calc_grade(att, sabaq_nagha, sq_nagha, m_nagha, sq_mis, m_mis)
                gcls = GRADE_MAP.get(grade, "grade-fail")
                st.markdown(f"**درجہ:** <span class='grade-badge {gcls}'>{grade}</span>", unsafe_allow_html=True)

            note = st.text_input("نوٹ (اختیاری)", key=f"note_{k}")

            if st.button(f"💾 محفوظ کریں", key=f"save_{k}", use_container_width=True):
                grade = calc_grade(att, sabaq_nagha, sq_nagha, m_nagha, sq_mis, m_mis)
                qw("""INSERT INTO hifz_records
                      (rec_date,student_id,teacher,attendance,sabaq,sabaq_lines,sabaq_nagha,sabaq_p,
                       sq_nagha,sq_p,sq_atkan,sq_mistakes,manzil_nagha,manzil_p,manzil_atkan,manzil_mistakes,
                       cleanliness,grade,note)
                      VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                   (str(entry_date), s['id'], st.session_state.username, att,
                    sabaq_text, sabaq_lines, sabaq_nagha, sq_text,
                    sq_nagha, sq_text, sq_atk, sq_mis,
                    m_nagha, manzil_text, m_atk, m_mis,
                    cleanliness, grade, note))
                audit(st.session_state.username, "Hifz Entry", f"{s['name']} {entry_date}")
                st.success(f"✅ {s['name']} کا ریکارڈ محفوظ!")
                st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)

    elif dept == "قاعدہ":
        for s in my_students:
            existing = q("SELECT id FROM qaida_records WHERE student_id=? AND rec_date=?", (s['id'], str(entry_date)), fetch="one")
            st.markdown(f"<div class='student-card'><h4>{'✅' if existing else '📝'} {s['name']} ولد {s['father_name']}</h4>", unsafe_allow_html=True)
            if existing:
                st.success("ریکارڈ پہلے سے موجود ہے")
                st.markdown("</div>", unsafe_allow_html=True)
                continue
            k = str(s['id'])
            att = st.radio("حاضری", ["حاضر","غیر حاضر","رخصت"], key=f"att_{k}", horizontal=True)
            cleanliness = st.selectbox("صفائی", CLEANLINESS, key=f"cln_{k}")
            lesson_no = lines = 0
            details = ""
            if att == "حاضر":
                lesson_type = st.radio("نوعیت", ["نورانی قاعدہ","نماز"], key=f"lt_{k}", horizontal=True)
                lesson_no = st.text_input("تختی/سبق نمبر", key=f"ln_{k}")
                lines = st.number_input("کل لائنیں", 0, key=f"lns_{k}")
                details = st.text_area("تفصیل", key=f"det_{k}")
            if st.button("💾 محفوظ کریں", key=f"save_{k}", use_container_width=True):
                qw("INSERT INTO qaida_records (rec_date,student_id,teacher,attendance,lesson_no,total_lines,details,cleanliness) VALUES (?,?,?,?,?,?,?,?)",
                   (str(entry_date), s['id'], st.session_state.username, att, lesson_no, lines, details, cleanliness))
                st.success(f"✅ {s['name']} محفوظ!"); st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    else:  # درسِ نظامی / عصری تعلیم
        with st.form(f"gen_form_{dept}"):
            recs = []
            for s in my_students:
                st.markdown(f"**👤 {s['name']} ولد {s['father_name']}**")
                k = str(s['id'])
                att = st.radio("حاضری", ["حاضر","غیر حاضر","رخصت"], key=f"att_{k}", horizontal=True)
                cln = st.selectbox("صفائی", CLEANLINESS, key=f"cln_{k}")
                sub = lesson = hw = perf = ""
                if att == "حاضر":
                    sub = st.text_input("مضمون/کتاب", key=f"sub_{k}")
                    lesson = st.text_area("سبق", key=f"les_{k}")
                    hw = st.text_input("ہوم ورک", key=f"hw_{k}")
                    perf = st.select_slider("کارکردگی", ["بہت بہتر","بہتر","مناسب","کمزور"], key=f"prf_{k}")
                recs.append((str(entry_date), s['id'], st.session_state.username, dept, att, sub, lesson, hw, perf, cln))
                st.markdown("---")
            if st.form_submit_button("✅ تمام محفوظ کریں"):
                for r in recs:
                    qw("INSERT INTO general_records (rec_date,student_id,teacher,dept,attendance,subject,lesson,homework,performance,cleanliness) VALUES (?,?,?,?,?,?,?,?,?,?)", r)
                audit(st.session_state.username, f"{dept} Entry", str(entry_date))
                st.success("✅ تمام ریکارڈ محفوظ!"); st.rerun()

# ═══════════════════════════════════════════════════════
# ─── TEACHER: EXAM REQUEST ─────────────────────────────
# ═══════════════════════════════════════════════════════
elif pg == "t_exam" and not IS_ADMIN:
    page_header("🎓","امتحانی درخواست","طالب علم کو امتحان کے لیے نامزد کریں")
    my_studs = q("SELECT id,name,father_name,dept FROM students WHERE teacher=? AND is_active=1", (st.session_state.username,))
    if not my_studs:
        st.warning("آپ کی کلاس میں کوئی طالب علم نہیں"); st.stop()

    with st.form("exam_req"):
        names = [f"{s['name']} ولد {s['father_name']} ({s['dept']})" for s in my_studs]
        idx = st.selectbox("طالب علم", range(len(names)), format_func=lambda i: names[i])
        sel = my_studs[idx]
        e_type = st.selectbox("امتحان", ["پارہ ٹیسٹ","ماہانہ","سہ ماہی","سالانہ"])
        c1,c2 = st.columns(2)
        s_date = c1.date_input("شروع", date.today())
        e_date = c2.date_input("ختم", date.today()+timedelta(days=7))
        tdays = (e_date - s_date).days + 1
        st.info(f"📅 کل دن: {tdays}")
        fp = tp = 0
        bk = amt = ""
        if e_type == "پارہ ٹیسٹ" or sel['dept'] == "حفظ":
            c1,c2 = st.columns(2)
            fp = c1.number_input("پارہ (شروع)", 1, 30, 1)
            tp = c2.number_input("پارہ (ختم)", int(fp), 30, int(fp))
        if e_type != "پارہ ٹیسٹ" and sel['dept'] != "حفظ":
            bk = st.text_input("کتاب")
        amt = st.text_input("مقدار خواندگی")
        if st.form_submit_button("📤 درخواست بھیجیں"):
            qw("INSERT INTO exams (student_id,teacher,dept,exam_type,from_para,to_para,book_name,amount_read,start_date,end_date,total_days) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
               (sel['id'], st.session_state.username, sel['dept'], e_type, fp, tp, bk, amt, str(s_date), str(e_date), tdays))
            audit(st.session_state.username, "Exam Requested", f"{sel['name']}-{e_type}")
            st.success("✅ درخواست بھیج دی گئی")

# ═══════════════════════════════════════════════════════
# ─── TEACHER: LEAVE ────────────────────────────────────
# ═══════════════════════════════════════════════════════
elif pg == "t_leave" and not IS_ADMIN:
    page_header("📩","رخصت کی درخواست","")
    my_leaves = q("""SELECT leave_type as نوعیت,start_date as 'تاریخ شروع',days as دن,
                    status as حالت,created_at as 'تاریخ درخواست'
                    FROM leave_requests WHERE username=? ORDER BY created_at DESC LIMIT 10""",
                 (st.session_state.username,))
    if my_leaves:
        st.subheader("میری حالیہ درخواستیں")
        for lv in my_leaves:
            scls = "status-ok" if lv['حالت'] == "منظور" else ("status-reject" if lv['حالت'] == "مسترد" else "status-pending")
            st.markdown(f"""
            <div class="leave-card">
                <span class="status-pill {scls}">{lv['حالت']}</span> &nbsp;
                <strong>{lv['نوعیت']}</strong> | {lv['تاریخ شروع']} | {lv['دن']} دن
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")
    with st.form("leave_form"):
        c1,c2 = st.columns(2)
        l_type = c1.selectbox("نوعیت", ["بیماری","ضروری کام","ہنگامی","دیگر"])
        s_date = c2.date_input("تاریخ شروع", date.today())
        days = c1.number_input("دن", 1, 30, 1)
        back = s_date + timedelta(days=int(days)-1)
        c2.info(f"واپسی: {back}")
        reason = st.text_area("وجہ*", max_chars=500)
        if st.form_submit_button("📤 بھیجیں"):
            if reason.strip():
                qw("INSERT INTO leave_requests (username,leave_type,start_date,days,reason) VALUES (?,?,?,?,?)",
                   (st.session_state.username, l_type, str(s_date), days, reason))
                audit(st.session_state.username, "Leave Requested", f"{l_type},{days}d")
                st.success("✅ درخواست بھیج دی گئی"); st.rerun()
            else:
                st.error("وجہ ضروری ہے")

# ═══════════════════════════════════════════════════════
# ─── TEACHER: ATTENDANCE ───────────────────────────────
# ═══════════════════════════════════════════════════════
elif pg == "t_att" and not IS_ADMIN:
    page_header("🕒","میری حاضری","")
    today = date.today()
    today_rec = q("SELECT * FROM teacher_attendance WHERE username=? AND att_date=?",
                  (st.session_state.username, str(today)), fetch="one")

    st.markdown(f"""
    <div class="section-card" style="text-align:center">
        <div style="font-size:1.2rem;color:var(--jade);font-weight:700">📅 {today.strftime('%A, %d %B %Y')}</div>
    </div>
    """, unsafe_allow_html=True)

    if not today_rec:
        arr = st.time_input("آمد کا وقت", datetime.now().time())
        if st.button("✅ آمد درج کریں", use_container_width=True):
            qw("INSERT OR IGNORE INTO teacher_attendance (username,att_date,arrival) VALUES (?,?,?)",
               (st.session_state.username, str(today), arr.strftime("%I:%M %p")))
            st.success("✅ آمد درج!"); st.rerun()
    elif not today_rec.get('departure'):
        st.success(f"✅ آمد: {today_rec['arrival']}")
        dep = st.time_input("رخصت کا وقت", datetime.now().time())
        if st.button("✅ رخصت درج کریں", use_container_width=True):
            qw("UPDATE teacher_attendance SET departure=? WHERE username=? AND att_date=?",
               (dep.strftime("%I:%M %p"), st.session_state.username, str(today)))
            st.success("✅ رخصت درج!"); st.rerun()
    else:
        c1,c2 = st.columns(2)
        c1.metric("🟢 آمد", today_rec['arrival'])
        c2.metric("🔴 رخصت", today_rec['departure'])

    st.markdown("---")
    st.subheader("ماہانہ ریکارڈ")
    monthly = q("""SELECT att_date as تاریخ,arrival as آمد,departure as رخصت
                   FROM teacher_attendance WHERE username=? AND att_date >= ?
                   ORDER BY att_date DESC""",
                (st.session_state.username, str(date.today().replace(day=1))))
    if monthly:
        st.dataframe(pd.DataFrame(monthly), use_container_width=True, hide_index=True)

# ═══════════════════════════════════════════════════════
# ─── TEACHER: TIMETABLE ────────────────────────────────
# ═══════════════════════════════════════════════════════
elif pg == "t_timetable" and not IS_ADMIN:
    page_header("📚","میرا ٹائم ٹیبل","")
    tt = q("SELECT day as دن,period as وقت,subject as مضمون,room as کمرہ FROM timetable WHERE teacher=? ORDER BY day,period",
           (st.session_state.username,))
    if tt:
        df = pd.DataFrame(tt)
        try:
            pivot = df.pivot(index='وقت', columns='دن', values='مضمون').fillna("—")
            st.dataframe(pivot, use_container_width=True)
        except:
            st.dataframe(df, use_container_width=True, hide_index=True)
        html = gen_html_report(df, "ٹائم ٹیبل", st.session_state.username)
        st.download_button("📥 ڈاؤن لوڈ", html, "timetable.html", "text/html")
    else:
        st.info("ابھی آپ کا ٹائم ٹیبل ترتیب نہیں دیا گیا")

# ═══════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════
st.markdown("""
<div style="text-align:center;padding:1.5rem 0 0.5rem;color:#9ca3af;font-size:0.78rem;
            border-top:1px solid #e5e7eb;margin-top:2rem">
    🕌 جامعہ ملیہ اسلامیہ فیصل آباد — اسمارٹ ERP v3.0
    &nbsp;|&nbsp; تمام حقوق محفوظ ہیں
</div>
""", unsafe_allow_html=True)
