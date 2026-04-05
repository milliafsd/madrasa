import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import sqlite3
import pytz
import plotly.express as px
import os
import hashlib
import shutil
import zipfile
import io

# ==================== 1. ڈیٹا بیس سیٹ اپ ====================
DB_NAME = 'jamia_millia_v1 (1).db'

def get_db_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

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
    
    # اساتذہ ٹیبل
    c.execute('''CREATE TABLE IF NOT EXISTS teachers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        password TEXT
    )''')
    add_column_if_not_exists('teachers', 'dept', 'TEXT')
    add_column_if_not_exists('teachers', 'phone', 'TEXT')
    add_column_if_not_exists('teachers', 'address', 'TEXT')
    add_column_if_not_exists('teachers', 'id_card', 'TEXT')
    add_column_if_not_exists('teachers', 'photo', 'TEXT')
    add_column_if_not_exists('teachers', 'joining_date', 'DATE')
    
    # طلبہ ٹیبل (نیا کالم roll_no)
    c.execute('''CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        father_name TEXT,
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
    add_column_if_not_exists('students', 'roll_no', 'TEXT')
    
    # حفظ ریکارڈ
    c.execute('''CREATE TABLE IF NOT EXISTS hifz_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        r_date DATE,
        student_id INTEGER,
        t_name TEXT,
        surah TEXT,
        a_from TEXT,
        a_to TEXT,
        sq_p TEXT,
        sq_a INTEGER,
        sq_m INTEGER,
        m_p TEXT,
        m_a INTEGER,
        m_m INTEGER,
        attendance TEXT,
        principal_note TEXT,
        lines INTEGER,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
    )''')
    add_column_if_not_exists('hifz_records', 'student_id', 'INTEGER')
    add_column_if_not_exists('hifz_records', 'lines', 'INTEGER')
    
    # قاعدہ ریکارڈ
    c.execute('''CREATE TABLE IF NOT EXISTS qaida_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        r_date DATE,
        student_id INTEGER,
        t_name TEXT,
        lesson_no TEXT,
        total_lines INTEGER,
        details TEXT,
        attendance TEXT,
        principal_note TEXT,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
    )''')
    add_column_if_not_exists('qaida_records', 'student_id', 'INTEGER')
    
    # عمومی تعلیم
    c.execute('''CREATE TABLE IF NOT EXISTS general_education (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        r_date DATE,
        student_id INTEGER,
        t_name TEXT,
        dept TEXT,
        book_subject TEXT,
        today_lesson TEXT,
        homework TEXT,
        performance TEXT,
        attendance TEXT,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
    )''')
    add_column_if_not_exists('general_education', 'student_id', 'INTEGER')
    
    # اساتذہ حاضری
    c.execute('''CREATE TABLE IF NOT EXISTS t_attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        t_name TEXT,
        a_date DATE,
        arrival TEXT,
        departure TEXT,
        actual_arrival TEXT,
        actual_departure TEXT
    )''')
    
    # رخصت درخواستیں
    c.execute('''CREATE TABLE IF NOT EXISTS leave_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        t_name TEXT,
        reason TEXT,
        start_date DATE,
        back_date DATE,
        status TEXT,
        request_date DATE,
        l_type TEXT,
        days INTEGER,
        notification_seen INTEGER DEFAULT 0
    )''')
    
    # امتحانات
    c.execute('''CREATE TABLE IF NOT EXISTS exams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        dept TEXT,
        exam_type TEXT,
        from_para INTEGER,
        to_para INTEGER,
        book_name TEXT,
        amount_read TEXT,
        start_date TEXT,
        end_date TEXT,
        total_days INTEGER,
        q1 INTEGER,
        q2 INTEGER,
        q3 INTEGER,
        q4 INTEGER,
        q5 INTEGER,
        total INTEGER,
        grade TEXT,
        status TEXT,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
    )''')
    add_column_if_not_exists('exams', 'student_id', 'INTEGER')
    add_column_if_not_exists('exams', 'amount_read', 'TEXT')
    add_column_if_not_exists('exams', 'total_days', 'INTEGER')
    
    # پاس شدہ پارے
    c.execute('''CREATE TABLE IF NOT EXISTS passed_paras (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        para_no INTEGER,
        book_name TEXT,
        passed_date DATE,
        exam_type TEXT,
        grade TEXT,
        marks INTEGER,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
    )''')
    add_column_if_not_exists('passed_paras', 'student_id', 'INTEGER')
    add_column_if_not_exists('passed_paras', 'book_name', 'TEXT')
    add_column_if_not_exists('passed_paras', 'marks', 'INTEGER')
    
    # ٹائم ٹیبل
    c.execute('''CREATE TABLE IF NOT EXISTS timetable (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        t_name TEXT,
        day TEXT,
        period TEXT,
        book TEXT,
        room TEXT
    )''')
    
    # نوٹیفیکیشنز
    c.execute('''CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        message TEXT,
        target TEXT,
        created_at DATETIME,
        seen INTEGER DEFAULT 0
    )''')
    
    # آڈٹ لاگ
    c.execute('''CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT,
        action TEXT,
        timestamp DATETIME,
        details TEXT
    )''')
    
    # عملہ نگرانی
    c.execute('''CREATE TABLE IF NOT EXISTS staff_monitoring (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        staff_name TEXT,
        date DATE,
        note_type TEXT,
        description TEXT,
        action_taken TEXT,
        status TEXT,
        created_by TEXT,
        created_at DATETIME
    )''')
    
    conn.commit()
    
    # ========== مائیگریشن: پرانے ریکارڈز کو student_id سے منسلک کریں ==========
    if column_exists('hifz_records', 's_name') and column_exists('hifz_records', 'f_name'):
        c.execute("SELECT id, s_name, f_name FROM hifz_records WHERE student_id IS NULL")
        old_records = c.fetchall()
        for rec_id, s_name, f_name in old_records:
            student = c.execute("SELECT id FROM students WHERE name=? AND father_name=?", (s_name, f_name)).fetchone()
            if student:
                c.execute("UPDATE hifz_records SET student_id=? WHERE id=?", (student[0], rec_id))
            else:
                c.execute("INSERT INTO students (name, father_name) VALUES (?,?)", (s_name, f_name))
                new_id = c.lastrowid
                c.execute("UPDATE hifz_records SET student_id=? WHERE id=?", (new_id, rec_id))
        conn.commit()
    
    if column_exists('qaida_records', 's_name') and column_exists('qaida_records', 'f_name'):
        c.execute("SELECT id, s_name, f_name FROM qaida_records WHERE student_id IS NULL")
        old_records = c.fetchall()
        for rec_id, s_name, f_name in old_records:
            student = c.execute("SELECT id FROM students WHERE name=? AND father_name=?", (s_name, f_name)).fetchone()
            if student:
                c.execute("UPDATE qaida_records SET student_id=? WHERE id=?", (student[0], rec_id))
            else:
                c.execute("INSERT INTO students (name, father_name) VALUES (?,?)", (s_name, f_name))
                new_id = c.lastrowid
                c.execute("UPDATE qaida_records SET student_id=? WHERE id=?", (new_id, rec_id))
        conn.commit()
    
    if column_exists('general_education', 's_name') and column_exists('general_education', 'f_name'):
        c.execute("SELECT id, s_name, f_name FROM general_education WHERE student_id IS NULL")
        old_records = c.fetchall()
        for rec_id, s_name, f_name in old_records:
            student = c.execute("SELECT id FROM students WHERE name=? AND father_name=?", (s_name, f_name)).fetchone()
            if student:
                c.execute("UPDATE general_education SET student_id=? WHERE id=?", (student[0], rec_id))
            else:
                c.execute("INSERT INTO students (name, father_name) VALUES (?,?)", (s_name, f_name))
                new_id = c.lastrowid
                c.execute("UPDATE general_education SET student_id=? WHERE id=?", (new_id, rec_id))
        conn.commit()
    
    if column_exists('exams', 's_name') and column_exists('exams', 'f_name'):
        c.execute("SELECT id, s_name, f_name FROM exams WHERE student_id IS NULL")
        old_records = c.fetchall()
        for rec_id, s_name, f_name in old_records:
            student = c.execute("SELECT id FROM students WHERE name=? AND father_name=?", (s_name, f_name)).fetchone()
            if student:
                c.execute("UPDATE exams SET student_id=? WHERE id=?", (student[0], rec_id))
            else:
                c.execute("INSERT INTO students (name, father_name) VALUES (?,?)", (s_name, f_name))
                new_id = c.lastrowid
                c.execute("UPDATE exams SET student_id=? WHERE id=?", (new_id, rec_id))
        conn.commit()
    
    if column_exists('passed_paras', 's_name') and column_exists('passed_paras', 'f_name'):
        c.execute("SELECT id, s_name, f_name FROM passed_paras WHERE student_id IS NULL")
        old_records = c.fetchall()
        for rec_id, s_name, f_name in old_records:
            student = c.execute("SELECT id FROM students WHERE name=? AND father_name=?", (s_name, f_name)).fetchone()
            if student:
                c.execute("UPDATE passed_paras SET student_id=? WHERE id=?", (student[0], rec_id))
            else:
                c.execute("INSERT INTO students (name, father_name) VALUES (?,?)", (s_name, f_name))
                new_id = c.lastrowid
                c.execute("UPDATE passed_paras SET student_id=? WHERE id=?", (new_id, rec_id))
        conn.commit()
    
    # ڈیفالٹ ایڈمن
    admin_hash = hash_password("jamia123")
    admin_exists = c.execute("SELECT 1 FROM teachers WHERE name='admin'").fetchone()
    if not admin_exists:
        c.execute("INSERT INTO teachers (name, password, dept) VALUES (?,?,?)", ("admin", admin_hash, "Admin"))
    conn.commit()
    conn.close()

init_db()

# ==================== 2. ہیلپر فنکشنز ====================
def log_audit(user, action, details=""):
    try:
        conn = get_db_connection()
        conn.execute("INSERT INTO audit_log (user, action, timestamp, details) VALUES (?,?,?,?)",
                     (user, action, datetime.now(), details))
        conn.commit()
        conn.close()
    except: pass

def get_pk_time():
    tz = pytz.timezone('Asia/Karachi')
    return datetime.now(tz).strftime("%I:%M %p")

def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8-sig')

def get_grade_from_mistakes(total_mistakes):
    if total_mistakes <= 2: return "ممتاز"
    elif total_mistakes <= 5: return "جید جداً"
    elif total_mistakes <= 8: return "جید"
    elif total_mistakes <= 12: return "مقبول"
    else: return "دوبارہ کوشش کریں"

def generate_exam_result_card(exam_row):
    html = f"""
    <!DOCTYPE html>
    <html dir="rtl">
    <head><meta charset="UTF-8"><title>رزلٹ کارڈ - {exam_row['s_name']}</title>
    <style>
        @font-face {{ font-family: 'Jameel Noori Nastaleeq'; src: url('https://fonts.cdnfonts.com/css/jameel-noori-nastaleeq'); }}
        body {{ font-family: 'Jameel Noori Nastaleeq', 'Noto Nastaliq Urdu', Arial, sans-serif; margin: 20px; direction: rtl; text-align: right; }}
        .card {{ border: 2px solid #1e5631; border-radius: 15px; padding: 20px; max-width: 600px; margin: auto; }}
        h2 {{ text-align: center; color: #1e5631; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
        th {{ background-color: #f2f2f2; }}
        .footer {{ margin-top: 20px; display: flex; justify-content: space-between; }}
    </style>
    </head>
    <body>
        <div class="card">
            <h2>جامعہ ملیہ اسلامیہ فیصل آباد</h2>
            <h3>رزلٹ کارڈ</h3>
            <p><b>نام:</b> {exam_row['s_name']} ولد {exam_row['f_name']}</p>
            <p><b>شناختی نمبر:</b> {exam_row.get('roll_no', '')}</p>
            <p><b>امتحان کی قسم:</b> {exam_row['exam_type']}</p>
            {f"<p><b>پارہ:</b> {exam_row['from_para']} تا {exam_row['to_para']}</p>" if exam_row.get('from_para') else ""}
            {f"<p><b>کتاب:</b> {exam_row.get('book_name', '')}</p>" if exam_row.get('book_name') else ""}
            {f"<p><b>مقدار خواندگی:</b> {exam_row.get('amount_read', '')}</p>" if exam_row.get('amount_read') else ""}
            <p><b>تاریخ:</b> {exam_row['start_date']} تا {exam_row['end_date']}</p>
            <p><b>کل دن:</b> {exam_row.get('total_days', '')}</p>
            <table>
                <tr><th>سوال</th><th>1</th><th>2</th><th>3</th><th>4</th><th>5</th><th>کل</th></tr>
                <tr><td style="text-align:center">{exam_row['q1']}</td>
                <td>{exam_row['q2']}</td>
                <td>{exam_row['q3']}</td>
                <td>{exam_row['q4']}</td>
                <td>{exam_row['q5']}</td>
                <td>{exam_row['total']}</td>
                </tr>
            </table>
            <p><b>گریڈ:</b> {exam_row['grade']}</p>
            <div class="footer">
                <span>دستخط استاذ: _________________</span>
                <span>دستخط مہتمم: _________________</span>
            </div>
        </div>
        <div class="no-print" style="text-align:center; margin-top:20px;">
            <button onclick="window.print()">🖨️ پرنٹ کریں</button>
        </div>
    </body>
    </html>
    """
    return html

def generate_para_report(student_name, father_name, passed_paras_df):
    if passed_paras_df.empty:
        return "<p>کوئی پاس شدہ پارہ نہیں</p>"
    html_table = passed_paras_df.to_html(index=False, classes='print-table', border=1, justify='center', escape=False)
    html = f"""
    <!DOCTYPE html>
    <html dir="rtl">
    <head><meta charset="UTF-8"><title>پارہ تعلیمی رپورٹ - {student_name}</title>
    <style>
        @font-face {{ font-family: 'Jameel Noori Nastaleeq'; src: url('https://fonts.cdnfonts.com/css/jameel-noori-nastaleeq'); }}
        body {{ font-family: 'Jameel Noori Nastaleeq', 'Noto Nastaliq Urdu', Arial, sans-serif; margin: 20px; direction: rtl; text-align: right; }}
        h2, h3 {{ text-align: center; color: #1e5631; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
        th {{ background-color: #f2f2f2; }}
        @media print {{ body {{ margin: 0; }} .no-print {{ display: none; }} }}
    </style>
    </head>
    <body>
        <div class="header">
            <h2>جامعہ ملیہ اسلامیہ فیصل آباد</h2>
            <h3>پارہ تعلیمی رپورٹ</h3>
            <p><b>طالب علم:</b> {student_name} ولد {father_name}</p>
        </div>
        {html_table}
        <div class="signatures" style="display:flex; justify-content:space-between; margin-top:50px;">
            <span>دستخط استاذ: _______________________</span>
            <span>دستخط مہتمم: _______________________</span>
        </div>
        <div class="no-print" style="text-align:center; margin-top:30px;">
            <button onclick="window.print()">🖨️ پرنٹ کریں</button>
        </div>
    </body>
    </html>
    """
    return html

def generate_html_report(df, title, student_name="", start_date="", end_date="", passed_paras=None):
    html_table = df.to_html(index=False, classes='print-table', border=1, justify='center', escape=False)
    passed_html = ""
    if passed_paras:
        passed_html = f"<div style='margin-top:20px'><b>پاس شدہ پارے:</b> {', '.join(map(str, passed_paras))}</div>"
    html = f"""
    <!DOCTYPE html>
    <html dir="rtl">
    <head><meta charset="UTF-8"><title>{title}</title>
    <style>
        @font-face {{ font-family: 'Jameel Noori Nastaleeq'; src: url('https://fonts.cdnfonts.com/css/jameel-noori-nastaleeq'); }}
        body {{ font-family: 'Jameel Noori Nastaleeq', 'Noto Nastaliq Urdu', Arial, sans-serif; margin: 20px; direction: rtl; text-align: right; }}
        h2, h3 {{ text-align: center; color: #1e5631; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
        th {{ background-color: #f2f2f2; }}
        @media print {{ body {{ margin: 0; }} .no-print {{ display: none; }} }}
    </style>
    </head>
    <body>
        <div class="header">
            <h2>جامعہ ملیہ اسلامیہ فیصل آباد</h2>
            <h3>{title}</h3>
            {f"<p><b>طالب علم:</b> {student_name} &nbsp;&nbsp; <b>تاریخ:</b> {start_date} تا {end_date}</p>" if student_name else ""}
        </div>
        {html_table}
        {passed_html}
        <div class="signatures" style="display:flex; justify-content:space-between; margin-top:50px;">
            <span>دستخط استاذ: _______________________</span>
            <span>دستخط مہتمم: _______________________</span>
        </div>
        <div class="no-print" style="text-align:center; margin-top:30px;">
            <button onclick="window.print()">🖨️ پرنٹ کریں</button>
        </div>
    </body>
    </html>
    """
    return html

def generate_timetable_html(df_timetable):
    if df_timetable.empty:
        return "<p>کوئی ٹائم ٹیبل دستیاب نہیں</p>"
    day_order = {"ہفتہ": 0, "اتوار": 1, "پیر": 2, "منگل": 3, "بدھ": 4, "جمعرات": 5}
    df_timetable['day_order'] = df_timetable['دن'].map(day_order)
    df_timetable = df_timetable.sort_values(['day_order', 'وقت'])
    pivot = df_timetable.pivot(index='وقت', columns='دن', values='کتاب')
    pivot = pivot.fillna("—")
    html = f"""
    <!DOCTYPE html>
    <html dir="rtl">
    <head><meta charset="UTF-8"><title>ٹائم ٹیبل</title>
    <style>
        @font-face {{ font-family: 'Jameel Noori Nastaleeq'; src: url('https://fonts.cdnfonts.com/css/jameel-noori-nastaleeq'); }}
        body {{ font-family: 'Jameel Noori Nastaleeq', 'Noto Nastaliq Urdu', Arial, sans-serif; margin: 20px; direction: rtl; text-align: right; }}
        h2, h3 {{ text-align: center; color: #1e5631; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
        th {{ background-color: #f2f2f2; }}
        @media print {{ body {{ margin: 0; }} .no-print {{ display: none; }} }}
    </style>
    </head>
    <body>
        <div class="header">
            <h2>جامعہ ملیہ اسلامیہ فیصل آباد</h2>
            <h3>ٹائم ٹیبل</h3>
        </div>
        {pivot.to_html(classes='print-table', border=1, justify='center', escape=False)}
        <div class="signatures" style="display:flex; justify-content:space-between; margin-top:50px;">
            <span>دستخط استاذ: _______________________</span>
            <span>دستخط مہتمم: _______________________</span>
        </div>
        <div class="no-print" style="text-align:center; margin-top:30px;">
            <button onclick="window.print()">🖨️ پرنٹ کریں</button>
        </div>
    </body>
    </html>
    """
    return html

# ==================== 3. اسٹائلنگ ====================
st.set_page_config(page_title="جامعہ ملیہ اسلامیہ فیصل آباد | سمارٹ ERP", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
    @font-face {
        font-family: 'Jameel Noori Nastaleeq';
        src: url('https://raw.githubusercontent.com/urdufonts/jameel-noori-nastaleeq/master/JameelNooriNastaleeq.ttf') format('truetype');
        font-weight: normal;
        font-style: normal;
    }
    @import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu&display=swap');
    * {
        font-family: 'Jameel Noori Nastaleeq', 'Noto Nastaliq Urdu', 'Arial', sans-serif;
    }
    body { direction: rtl; text-align: right; background: linear-gradient(135deg, #f5f7fa 0%, #e9ecef 100%); }
    .stSidebar { background: linear-gradient(180deg, #1e5631 0%, #0b2b1a 100%); color: white; }
    .stSidebar * { color: white !important; }
    .stSidebar .stRadio label { color: white !important; font-weight: bold; font-size: 1rem; }
    .stSidebar .stRadio [role="radiogroup"] div { color: white !important; }
    .stSidebar .stRadio [role="radiogroup"] div[data-baseweb="radio"]:hover { background-color: #2e7d32; border-radius: 5px; }
    .stButton > button { background: linear-gradient(90deg, #1e5631, #2e7d32); color: white; border-radius: 30px; border: none; padding: 0.5rem 1rem; font-weight: bold; transition: 0.3s; width: 100%; }
    .stButton > button:hover { transform: scale(1.02); background: linear-gradient(90deg, #2e7d32, #1e5631); }
    .main-header { text-align: center; background: linear-gradient(135deg, #f1f8e9, #d4e0c9); padding: 1rem; border-radius: 20px; margin-bottom: 1rem; border-bottom: 4px solid #1e5631; }
    .report-card { background: white; border-radius: 15px; padding: 1rem; box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin-bottom: 1rem; }
    .stTabs [data-baseweb="tab"] { border-radius: 30px; padding: 0.5rem 1rem; background-color: #e0e0e0; }
    .stTabs [aria-selected="true"] { background: linear-gradient(90deg, #1e5631, #2e7d32); color: white; }
    @media (max-width: 768px) {
        .stButton > button { padding: 0.4rem 0.8rem; font-size: 0.8rem; }
        .main-header h1 { font-size: 1.5rem; }
    }
</style>
""", unsafe_allow_html=True)

# ==================== 4. لاگ ان ====================
def verify_login(username, password):
    conn = get_db_connection()
    res = conn.execute("SELECT * FROM teachers WHERE name=? AND password=?", (username, password)).fetchone()
    if not res:
        hashed = hash_password(password)
        res = conn.execute("SELECT * FROM teachers WHERE name=? AND password=?", (username, hashed)).fetchone()
    conn.close()
    return res

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<div class='main-header'><h1>🕌 جامعہ ملیہ اسلامیہ فیصل آباد</h1><p>اسمارٹ تعلیمی و انتظامی پورٹل</p></div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        with st.container():
            st.markdown("<div class='report-card'><h3>🔐 لاگ ان</h3>", unsafe_allow_html=True)
            u = st.text_input("صارف نام")
            p = st.text_input("پاسورڈ", type="password")
            if st.button("داخل ہوں"):
                res = verify_login(u, p)
                if res:
                    st.session_state.logged_in, st.session_state.username = True, u
                    st.session_state.user_type = "admin" if u == "admin" else "teacher"
                    log_audit(u, "Login", f"User type: {st.session_state.user_type}")
                    st.rerun()
                else:
                    st.error("غلط معلومات")
            st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ==================== 5. مینو ====================
if st.session_state.user_type == "admin":
    menu = ["📊 ایڈمن ڈیش بورڈ", "📊 یومیہ تعلیمی رپورٹ", "🎓 امتحانی نظام", "📜 ماہانہ رزلٹ کارڈ",
            "📘 پارہ تعلیمی رپورٹ", "🕒 اساتذہ حاضری", "🏛️ رخصت کی منظوری",
            "👥 یوزر مینجمنٹ", "📚 ٹائم ٹیبل مینجمنٹ", "🔑 پاسورڈ تبدیل کریں", "📋 عملہ نگرانی و شکایات",
            "📢 نوٹیفیکیشنز", "📈 تجزیہ و رپورٹس", "⚙️ بیک اپ & سیٹنگز"]
else:
    menu = ["📝 روزانہ سبق اندراج", "🎓 امتحانی درخواست", "📩 رخصت کی درخواست",
            "🕒 میری حاضری", "📚 میرا ٹائم ٹیبل", "🔑 پاسورڈ تبدیل کریں", "📢 نوٹیفیکیشنز"]

selected = st.sidebar.radio("📌 مینو", menu)

# ==================== 6. ڈیٹا ====================
surahs_urdu = ["الفاتحة", "البقرة", "آل عمران", "النساء", "المائدة", "الأنعام", "الأعراف", "الأنفال", "التوبة", "يونس",
               "هود", "يوسف", "الرعد", "إبراهيم", "الحجر", "النحل", "الإسراء", "الكهف", "مريم", "طه", "الأنبياء", "الحج",
               "المؤمنون", "النور", "الفرقان", "الشعراء", "النمل", "القصص", "العنكبوت", "الروم", "لقمان", "السجدة", "الأحزاب",
               "سبأ", "فاطر", "يس", "الصافات", "ص", "الزمر", "غافر", "فصلت", "الشورى", "الزخرف", "الدخان", "الجاثية", "الأحقاف",
               "محمد", "الفتح", "الحجرات", "ق", "الذاريات", "الطور", "النجم", "القمر", "الرحمن", "الواقعة", "الحديد", "المجادلة",
               "الحشر", "الممتحنة", "الصف", "الجمعة", "المنافقون", "التغابن", "الطلاق", "التحریم", "الملک", "القلم", "الحاقة",
               "المعارج", "نوح", "الجن", "المزمل", "المدثر", "القیامة", "الإنسان", "المرسلات", "النبأ", "النازعات", "عبس", "التکویر",
               "الإنفطار", "المطففین", "الإنشقاق", "البروج", "الطارق", "الأعلى", "الغاشیة", "الفجر", "البلد", "الشمس", "اللیل",
               "الضحى", "الشرح", "التین", "العلق", "القدر", "البینة", "الزلزلة", "العادیات", "القارعة", "التکاثر", "العصر", "الهمزة",
               "الفیل", "قریش", "الماعون", "الکوثر", "الکافرون", "النصر", "المسد", "الإخلاص", "الفلق", "الناس"]
paras = [f"پارہ {i}" for i in range(1, 31)]

# ==================== 7. پاسورڈ تبدیل کرنے کے فنکشنز ====================
def verify_password(user, plain_password):
    conn = get_db_connection()
    res = conn.execute("SELECT password FROM teachers WHERE name=?", (user,)).fetchone()
    conn.close()
    if not res:
        return False
    stored = res[0]
    if stored == plain_password:
        return True
    if stored == hash_password(plain_password):
        return True
    return False

def change_password(user, old_pass, new_pass):
    if not verify_password(user, old_pass):
        return False
    conn = get_db_connection()
    new_hash = hash_password(new_pass)
    conn.execute("UPDATE teachers SET password=? WHERE name=?", (new_hash, user))
    conn.commit()
    conn.close()
    log_audit(user, "Password Changed", "Success")
    return True

def admin_reset_password(teacher_name, new_pass):
    conn = get_db_connection()
    new_hash = hash_password(new_pass)
    conn.execute("UPDATE teachers SET password=? WHERE name=?", (new_hash, teacher_name))
    conn.commit()
    conn.close()
    log_audit(st.session_state.username, "Admin Reset Password", f"Teacher: {teacher_name}")

# ==================== 8. ایڈمن سیکشنز ====================
# 8.1 ایڈمن ڈیش بورڈ
if selected == "📊 ایڈمن ڈیش بورڈ" and st.session_state.user_type == "admin":
    st.markdown("<div class='main-header'><h1>📊 ایڈمن ڈیش بورڈ</h1></div>", unsafe_allow_html=True)
    conn = get_db_connection()
    total_students = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    total_teachers = conn.execute("SELECT COUNT(*) FROM teachers WHERE name!='admin'").fetchone()[0]
    col1, col2 = st.columns(2)
    col1.metric("کل طلباء", total_students)
    col2.metric("کل اساتذہ", total_teachers)
    conn.close()

# 8.2 یومیہ تعلیمی رپورٹ
elif selected == "📊 یومیہ تعلیمی رپورٹ" and st.session_state.user_type == "admin":
    st.header("📊 یومیہ تعلیمی رپورٹ - ترمیم، حذف، اضافہ")
    
    with st.sidebar:
        d1 = st.date_input("تاریخ آغاز", date.today().replace(day=1))
        d2 = st.date_input("تاریخ اختتام", date.today())
        conn = get_db_connection()
        teachers_list = ["تمام"] + [t[0] for t in conn.execute("SELECT DISTINCT t_name FROM hifz_records UNION SELECT name FROM teachers WHERE name!='admin'").fetchall()]
        conn.close()
        sel_teacher = st.selectbox("استاد / کلاس", teachers_list)
        dept_filter = st.selectbox("شعبہ", ["تمام", "حفظ", "قاعدہ", "درسِ نظامی", "عصری تعلیم"])
    
    combined_df = pd.DataFrame()
    
    # حفظ
    if dept_filter in ["تمام", "حفظ"]:
        conn = get_db_connection()
        try:
            hifz_df = pd.read_sql_query("""
                SELECT h.r_date as تاریخ, s.name as نام, s.father_name as 'والد کا نام', s.roll_no as 'شناختی نمبر', h.t_name as استاد, 
                       'حفظ' as شعبہ, h.surah as 'سبق (آیت تا آیت)', h.lines as 'کل ستر',
                       h.sq_p as 'سبقی (پارہ)', h.sq_m as 'سبقی (غلطی)', h.sq_a as 'سبقی (اٹکن)',
                       h.m_p as 'منزل (پارہ)', h.m_m as 'منزل (غلطی)', h.m_a as 'منزل (اٹکن)',
                       h.attendance as حاضری
                FROM hifz_records h
                JOIN students s ON h.student_id = s.id
                WHERE h.r_date BETWEEN ? AND ?
            """, conn, params=(d1, d2))
            conn.close()
            if not hifz_df.empty:
                if 'سبقی (غلطی)' in hifz_df.columns and 'منزل (غلطی)' in hifz_df.columns:
                    hifz_df['کل_غلطیاں'] = hifz_df['سبقی (غلطی)'].fillna(0) + hifz_df['منزل (غلطی)'].fillna(0)
                    hifz_df['درجہ'] = hifz_df['کل_غلطیاں'].apply(get_grade_from_mistakes)
                if sel_teacher != "تمام":
                    hifz_df = hifz_df[hifz_df['استاد'] == sel_teacher]
                combined_df = pd.concat([combined_df, hifz_df], ignore_index=True)
        except Exception as e:
            st.error(f"حفظ کے ریکارڈ لوڈ کرتے وقت خرابی: {str(e)}")
    
    # قاعدہ
    if dept_filter in ["تمام", "قاعدہ"]:
        conn = get_db_connection()
        try:
            qaida_df = pd.read_sql_query("""
                SELECT q.r_date as تاریخ, s.name as نام, s.father_name as 'والد کا نام', s.roll_no as 'شناختی نمبر', q.t_name as استاد,
                       'قاعدہ' as شعبہ, q.lesson_no as 'تختی نمبر', q.total_lines as 'کل لائنیں',
                       q.details as تفصیل, q.attendance as حاضری
                FROM qaida_records q
                JOIN students s ON q.student_id = s.id
                WHERE q.r_date BETWEEN ? AND ?
            """, conn, params=(d1, d2))
            conn.close()
            if not qaida_df.empty:
                qaida_df['کل_غلطیاں'] = ''
                qaida_df['درجہ'] = ''
                if sel_teacher != "تمام":
                    qaida_df = qaida_df[qaida_df['استاد'] == sel_teacher]
                combined_df = pd.concat([combined_df, qaida_df], ignore_index=True)
        except Exception as e:
            st.error(f"قاعدہ کے ریکارڈ لوڈ کرتے وقت خرابی: {str(e)}")
    
    # درسِ نظامی اور عصری
    if dept_filter in ["تمام", "درسِ نظامی", "عصری تعلیم"]:
        conn = get_db_connection()
        try:
            gen_df = pd.read_sql_query("""
                SELECT g.r_date as تاریخ, s.name as نام, s.father_name as 'والد کا نام', s.roll_no as 'شناختی نمبر', g.t_name as استاد,
                       g.dept as شعبہ, g.book_subject as 'کتاب/مضمون', g.today_lesson as 'آج کا سبق',
                       g.homework as 'ہوم ورک', g.performance as کارکردگی, g.attendance as حاضری
                FROM general_education g
                JOIN students s ON g.student_id = s.id
                WHERE g.r_date BETWEEN ? AND ?
            """, conn, params=(d1, d2))
            conn.close()
            if not gen_df.empty:
                gen_df['کل_غلطیاں'] = ''
                gen_df['درجہ'] = ''
                if sel_teacher != "تمام":
                    gen_df = gen_df[gen_df['استاد'] == sel_teacher]
                if dept_filter != "تمام":
                    gen_df = gen_df[gen_df['شعبہ'] == dept_filter]
                combined_df = pd.concat([combined_df, gen_df], ignore_index=True)
        except Exception as e:
            st.error(f"عمومی تعلیم کے ریکارڈ لوڈ کرتے وقت خرابی: {str(e)}")
    
    if combined_df.empty:
        st.warning("کوئی ریکارڈ نہیں ملا")
    else:
        st.success(f"کل {len(combined_df)} ریکارڈ ملے")
        st.dataframe(combined_df, use_container_width=True)
        html_report = generate_html_report(combined_df, "یومیہ تعلیمی رپورٹ", start_date=d1.strftime("%Y-%m-%d"), end_date=d2.strftime("%Y-%m-%d"))
        st.download_button("📥 HTML رپورٹ ڈاؤن لوڈ کریں", html_report, "daily_report.html", "text/html")
        if st.button("🖨️ پرنٹ کریں"):
            st.components.v1.html(f"<script>var w=window.open();w.document.write(`{html_report}`);w.print();</script>", height=0)

# 8.3 امتحانی نظام
elif selected == "🎓 امتحانی نظام" and st.session_state.user_type == "admin":
    st.header("🎓 امتحانی نظام")
    tab1, tab2 = st.tabs(["پینڈنگ امتحانات", "مکمل شدہ"])
    with tab1:
        conn = get_db_connection()
        pending = conn.execute("""
            SELECT e.id, s.name, s.father_name, s.roll_no, e.dept, e.exam_type, e.from_para, e.to_para, e.book_name, e.amount_read, e.start_date, e.end_date, e.total_days
            FROM exams e
            JOIN students s ON e.student_id = s.id
            WHERE e.status=?
        """, ("پینڈنگ",)).fetchall()
        conn.close()
        if not pending:
            st.info("کوئی پینڈنگ امتحان نہیں")
        else:
            for eid, sn, fn, rn, dept, etype, fp, tp, book, amount, sd, ed, tdays in pending:
                with st.expander(f"{sn} ولد {fn} | شناختی نمبر: {rn} | {dept} | {etype}"):
                    st.write(f"**تاریخ ابتدا:** {sd}")
                    st.write(f"**تاریخ اختتام:** {ed}")
                    st.write(f"**کل دن:** {tdays if tdays else '-'}")
                    if etype == "پارہ ٹیسٹ":
                        st.info(f"پارہ نمبر: {fp} تا {tp}")
                    else:
                        st.info(f"کتاب: {book}")
                        st.info(f"مقدار خواندگی: {amount}")
                    cols = st.columns(5)
                    q1 = cols[0].number_input("س1", 0, 20, key=f"q1_{eid}")
                    q2 = cols[1].number_input("س2", 0, 20, key=f"q2_{eid}")
                    q3 = cols[2].number_input("س3", 0, 20, key=f"q3_{eid}")
                    q4 = cols[3].number_input("س4", 0, 20, key=f"q4_{eid}")
                    q5 = cols[4].number_input("س5", 0, 20, key=f"q5_{eid}")
                    total = q1+q2+q3+q4+q5
                    if total >= 90: g = "ممتاز"
                    elif total >= 80: g = "جید جداً"
                    elif total >= 70: g = "جید"
                    elif total >= 60: g = "مقبول"
                    else: g = "ناکام"
                    st.write(f"کل: {total} | گریڈ: {g}")
                    if st.button("کلیئر کریں", key=f"save_{eid}"):
                        conn = get_db_connection()
                        c = conn.cursor()
                        c.execute("""UPDATE exams SET q1=?, q2=?, q3=?, q4=?, q5=?, total=?, grade=?, status=?, end_date=? WHERE id=?""",
                                  (q1,q2,q3,q4,q5,total,g,"مکمل", date.today(), eid))
                        if g != "ناکام":
                            stud_id = c.execute("SELECT student_id FROM exams WHERE id=?", (eid,)).fetchone()[0]
                            if etype == "پارہ ٹیسٹ" and fp:
                                for para in range(fp, tp+1):
                                    existing = c.execute("SELECT 1 FROM passed_paras WHERE student_id=? AND para_no=?", (stud_id, para)).fetchone()
                                    if not existing:
                                        c.execute("INSERT INTO passed_paras (student_id, para_no, passed_date, exam_type, grade, marks) VALUES (?,?,?,?,?,?)",
                                                  (stud_id, para, date.today(), etype, g, total))
                            else:
                                existing = c.execute("SELECT 1 FROM passed_paras WHERE student_id=? AND book_name=?", (stud_id, book)).fetchone()
                                if not existing:
                                    c.execute("INSERT INTO passed_paras (student_id, book_name, passed_date, exam_type, grade, marks) VALUES (?,?,?,?,?,?)",
                                              (stud_id, book, date.today(), etype, g, total))
                        conn.commit()
                        conn.close()
                        st.success("امتحان کلیئر کر دیا گیا")
                        st.rerun()
    with tab2:
        conn = get_db_connection()
        hist = pd.read_sql_query("""
            SELECT s.name, s.father_name, s.roll_no, e.dept, e.exam_type, e.from_para, e.to_para, e.book_name, e.amount_read, e.start_date, e.end_date, e.total, e.grade
            FROM exams e
            JOIN students s ON e.student_id = s.id
            WHERE e.status='مکمل'
            ORDER BY e.end_date DESC
        """, conn)
        conn.close()
        if not hist.empty:
            st.dataframe(hist, use_container_width=True)
            st.download_button("ہسٹری CSV", convert_df_to_csv(hist), "exam_history.csv")
        else:
            st.info("کوئی مکمل شدہ امتحان نہیں")

# 8.4 عملہ نگرانی و شکایات
elif selected == "📋 عملہ نگرانی و شکایات" and st.session_state.user_type == "admin":
    st.header("📋 عملہ نگرانی و شکایات")
    tab1, tab2 = st.tabs(["➕ نیا اندراج", "📜 ریکارڈ دیکھیں"])
    with tab1:
        with st.form("new_monitoring"):
            conn = get_db_connection()
            staff_list = [t[0] for t in conn.execute("SELECT name FROM teachers WHERE name!='admin'").fetchall()]
            conn.close()
            if not staff_list:
                st.warning("کوئی استاد/عملہ موجود نہیں۔ پہلے اساتذہ رجسٹر کریں۔")
            else:
                staff_name = st.selectbox("عملہ کا نام", staff_list)
                note_date = st.date_input("تاریخ", date.today())
                note_type = st.selectbox("نوعیت", ["یادداشت", "شکایت", "تنبیہ", "تعریف", "کارکردگی جائزہ"])
                description = st.text_area("تفصیل", height=150)
                action_taken = st.text_area("کیا کارروائی کی گئی؟", height=100)
                status = st.selectbox("حالت", ["زیر التواء", "حل شدہ", "زیر غور"])
                if st.form_submit_button("محفوظ کریں"):
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("""INSERT INTO staff_monitoring 
                                (staff_name, date, note_type, description, action_taken, status, created_by, created_at)
                                VALUES (?,?,?,?,?,?,?,?)""",
                              (staff_name, note_date, note_type, description, action_taken, status, st.session_state.username, datetime.now()))
                    conn.commit()
                    conn.close()
                    log_audit(st.session_state.username, "Staff Monitoring Added", f"{staff_name} - {note_type}")
                    st.success("اندراج محفوظ ہو گیا")
                    st.rerun()
    with tab2:
        st.subheader("فلٹرز")
        conn = get_db_connection()
        staff_names = ["تمام"] + [t[0] for t in conn.execute("SELECT name FROM teachers WHERE name!='admin'").fetchall()]
        conn.close()
        filter_staff = st.selectbox("عملہ فلٹر کریں", staff_names)
        filter_type = st.selectbox("نوعیت فلٹر کریں", ["تمام", "یادداشت", "شکایت", "تنبیہ", "تعریف", "کارکردگی جائزہ"])
        start_date = st.date_input("تاریخ از", date.today() - timedelta(days=30))
        end_date = st.date_input("تاریخ تا", date.today())
        query = "SELECT id, staff_name as 'عملہ کا نام', date as تاریخ, note_type as نوعیت, description as تفصیل, action_taken as 'کارروائی', status as حالت, created_by as 'داخل کردہ', created_at as 'داخل کردہ تاریخ' FROM staff_monitoring WHERE date BETWEEN ? AND ?"
        params = [start_date, end_date]
        if filter_staff != "تمام":
            query += " AND staff_name = ?"
            params.append(filter_staff)
        if filter_type != "تمام":
            query += " AND note_type = ?"
            params.append(filter_type)
        query += " ORDER BY date DESC"
        conn = get_db_connection()
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        if df.empty:
            st.info("کوئی ریکارڈ موجود نہیں")
        else:
            st.dataframe(df, use_container_width=True)
            csv = convert_df_to_csv(df)
            st.download_button("📥 CSV ڈاؤن لوڈ کریں", csv, "staff_monitoring.csv", "text/csv")
            html_report = generate_html_report(df, "عملہ نگرانی و شکایات رپورٹ")
            st.download_button("📥 HTML رپورٹ ڈاؤن لوڈ کریں", html_report, "staff_monitoring_report.html", "text/html")
            if st.button("🖨️ پرنٹ کریں"):
                st.components.v1.html(f"<script>var w=window.open();w.document.write(`{html_report}`);w.print();</script>", height=0)
            with st.expander("⚠️ ریکارڈ حذف کریں"):
                record_id = st.number_input("ریکارڈ ID درج کریں", min_value=1, step=1)
                if st.button("حذف کریں"):
                    conn = get_db_connection()
                    conn.execute("DELETE FROM staff_monitoring WHERE id=?", (record_id,))
                    conn.commit()
                    conn.close()
                    st.success("ریکارڈ حذف کر دیا گیا")
                    st.rerun()

# 8.5 ماہانہ رزلٹ کارڈ
elif selected == "📜 ماہانہ رزلٹ کارڈ" and st.session_state.user_type == "admin":
    st.header("📜 ماہانہ رزلٹ کارڈ")
    conn = get_db_connection()
    students_list = conn.execute("SELECT id, name, father_name, roll_no, dept FROM students").fetchall()
    conn.close()
    if not students_list:
        st.warning("کوئی طالب علم نہیں")
    else:
        student_names = [f"{s[1]} ولد {s[2]} (شناختی نمبر: {s[3]}) - {s[4]}" for s in students_list]
        sel = st.selectbox("طالب علم منتخب کریں", student_names)
        parts = sel.split(" ولد ")
        s_name = parts[0]
        rest = parts[1]
        f_name, rest2 = rest.split(" (شناختی نمبر: ")
        roll_no, dept = rest2.split(") - ")
        start = st.date_input("تاریخ آغاز", date.today().replace(day=1))
        end = st.date_input("تاریخ اختتام", date.today())
        student_id = [s[0] for s in students_list if s[1] == s_name and s[2] == f_name][0]
        
        if dept == "حفظ":
            conn = get_db_connection()
            df = pd.read_sql_query("""SELECT r_date as تاریخ, attendance as حاضری, surah as 'سبق (آیت تا آیت)', lines as 'کل ستر',
                                      sq_p as 'سبقی (پارہ)', sq_m as 'سبقی (غلطی)', sq_a as 'سبقی (اٹکن)',
                                      m_p as 'منزل (پارہ)', m_m as 'منزل (غلطی)', m_a as 'منزل (اٹکن)'
                                      FROM hifz_records WHERE student_id=? AND r_date BETWEEN ? AND ?
                                      ORDER BY r_date ASC""", conn, params=(student_id, start, end))
            conn.close()
            if not df.empty:
                df['کل_غلطیاں'] = df['سبقی (غلطی)'] + df['منزل (غلطی)']
                df['درجہ'] = df['کل_غلطیاں'].apply(get_grade_from_mistakes)
                avg_mistakes = df['کل_غلطیاں'].mean()
                st.info(f"**اوسط غلطیاں:** {round(avg_mistakes, 1)} | **مجموعی درجہ:** {get_grade_from_mistakes(avg_mistakes)}")
        elif dept == "قاعدہ":
            conn = get_db_connection()
            df = pd.read_sql_query("""SELECT r_date as تاریخ, lesson_no as 'تختی نمبر', total_lines as 'کل لائنیں',
                                      details as تفصیل, attendance as حاضری
                                      FROM qaida_records WHERE student_id=? AND r_date BETWEEN ? AND ?
                                      ORDER BY r_date ASC""", conn, params=(student_id, start, end))
            conn.close()
            if df.empty:
                st.warning("کوئی ریکارڈ نہیں")
            else:
                st.dataframe(df, use_container_width=True)
                html = generate_html_report(df, "ماہانہ رزلٹ کارڈ (قاعدہ)", student_name=f"{s_name} ولد {f_name}",
                                            start_date=start.strftime("%Y-%m-%d"), end_date=end.strftime("%Y-%m-%d"))
                st.download_button("📥 HTML ڈاؤن لوڈ", html, f"{s_name}_qaida_result.html", "text/html")
                if st.button("🖨️ پرنٹ کریں"):
                    st.components.v1.html(f"<script>var w=window.open();w.document.write(`{html}`);w.print();</script>", height=0)
        else:
            conn = get_db_connection()
            df = pd.read_sql_query("""SELECT r_date as تاریخ, book_subject as 'کتاب/مضمون', today_lesson as 'آج کا سبق',
                                      homework as 'ہوم ورک', performance as کارکردگی
                                      FROM general_education WHERE student_id=? AND dept=? AND r_date BETWEEN ? AND ?
                                      ORDER BY r_date ASC""", conn, params=(student_id, dept, start, end))
            conn.close()
        
        if dept not in ["قاعدہ"] and not df.empty:
            st.dataframe(df, use_container_width=True)
            passed = []
            if dept == "حفظ":
                conn = get_db_connection()
                passed = conn.execute("SELECT para_no, passed_date, grade FROM passed_paras WHERE student_id=? ORDER BY para_no", (student_id,)).fetchall()
                conn.close()
                if passed:
                    st.write("**پاس شدہ پارے:**")
                    for p in passed:
                        st.write(f"پارہ {p[0]} - تاریخ: {p[1]} - گریڈ: {p[2]}")
            html = generate_html_report(df, "ماہانہ رزلٹ کارڈ", student_name=f"{s_name} ولد {f_name}",
                                        start_date=start.strftime("%Y-%m-%d"), end_date=end.strftime("%Y-%m-%d"),
                                        passed_paras=[p[0] for p in passed] if passed else None)
            st.download_button("📥 HTML ڈاؤن لوڈ", html, f"{s_name}_result.html", "text/html")
            if st.button("🖨️ پرنٹ کریں"):
                st.components.v1.html(f"<script>var w=window.open();w.document.write(`{html}`);w.print();</script>", height=0)

# 8.6 پارہ تعلیمی رپورٹ
elif selected == "📘 پارہ تعلیمی رپورٹ" and st.session_state.user_type == "admin":
    st.header("📘 پارہ تعلیمی رپورٹ")
    conn = get_db_connection()
    students_list = conn.execute("SELECT id, name, father_name FROM students WHERE dept='حفظ'").fetchall()
    conn.close()
    if not students_list:
        st.warning("کوئی حفظ کا طالب علم نہیں")
    else:
        student_names = [f"{s[1]} ولد {s[2]}" for s in students_list]
        sel = st.selectbox("طالب علم منتخب کریں", student_names)
        s_name, f_name = sel.split(" ولد ")
        student_id = [s[0] for s in students_list if s[1] == s_name and s[2] == f_name][0]
        conn = get_db_connection()
        passed_df = pd.read_sql_query("""SELECT para_no as 'پارہ نمبر', passed_date as 'تاریخ پاس', 
                                         exam_type as 'امتحان قسم', grade as 'گریڈ', marks as 'نمبر'
                                         FROM passed_paras WHERE student_id=? AND para_no IS NOT NULL
                                         ORDER BY para_no""", conn, params=(student_id,))
        conn.close()
        if passed_df.empty:
            st.info("اس طالب علم کا کوئی پاس شدہ پارہ نہیں")
        else:
            st.dataframe(passed_df, use_container_width=True)
            html = generate_para_report(s_name, f_name, passed_df)
            st.download_button("📥 رپورٹ ڈاؤن لوڈ کریں", html, f"Para_Report_{s_name}.html", "text/html")
            if st.button("🖨️ پرنٹ کریں"):
                st.components.v1.html(f"<script>var w=window.open();w.document.write(`{html}`);w.print();</script>", height=0)

# 8.7 اساتذہ حاضری
elif selected == "🕒 اساتذہ حاضری" and st.session_state.user_type == "admin":
    st.header("اساتذہ حاضری ریکارڈ")
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT a_date as تاریخ, t_name as استاد, arrival as آمد, departure as رخصت FROM t_attendance ORDER BY a_date DESC", conn)
    conn.close()
    st.dataframe(df, use_container_width=True)

# 8.8 رخصت کی منظوری
elif selected == "🏛️ رخصت کی منظوری" and st.session_state.user_type == "admin":
    st.header("رخصت کی منظوری")
    conn = get_db_connection()
    try:
        pending = conn.execute("SELECT id, t_name, l_type, reason, start_date, days FROM leave_requests WHERE status LIKE ?", ('%پینڈنگ%',)).fetchall()
    except:
        pending = []
    conn.close()
    if not pending:
        st.info("کوئی پینڈنگ درخواست نہیں")
    else:
        for l_id, t_n, l_t, reas, s_d, dys in pending:
            with st.expander(f"{t_n} | {l_t} | {dys} دن"):
                st.write(f"وجہ: {reas}")
                col1, col2 = st.columns(2)
                if col1.button("✅ منظور", key=f"app_{l_id}"):
                    conn = get_db_connection()
                    conn.execute("UPDATE leave_requests SET status='منظور' WHERE id=?", (l_id,))
                    conn.commit()
                    conn.close()
                    st.rerun()
                if col2.button("❌ مسترد", key=f"rej_{l_id}"):
                    conn = get_db_connection()
                    conn.execute("UPDATE leave_requests SET status='مسترد' WHERE id=?", (l_id,))
                    conn.commit()
                    conn.close()
                    st.rerun()

# 8.9 یوزر مینجمنٹ
elif selected == "👥 یوزر مینجمنٹ" and st.session_state.user_type == "admin":
    st.header("👥 یوزر مینجمنٹ")
    tab1, tab2 = st.tabs(["اساتذہ", "طلبہ"])
    with tab1:
        st.subheader("موجودہ اساتذہ")
        conn = get_db_connection()
        columns = ["id", "name", "password", "dept", "phone", "address", "id_card", "joining_date"]
        existing_cols = []
        for col in columns:
            if column_exists("teachers", col):
                existing_cols.append(col)
        query = f"SELECT {', '.join(existing_cols)} FROM teachers WHERE name!='admin'"
        teachers_df = pd.read_sql_query(query, conn)
        conn.close()
        if not teachers_df.empty:
            edited_teachers = st.data_editor(teachers_df, num_rows="dynamic", use_container_width=True, key="teachers_edit")
            if st.button("اساتذہ میں تبدیلیاں محفوظ کریں"):
                conn = get_db_connection()
                c = conn.cursor()
                c.execute("DELETE FROM teachers WHERE name!='admin'")
                for _, row in edited_teachers.iterrows():
                    placeholders = ",".join(["?" for _ in existing_cols])
                    c.execute(f"INSERT INTO teachers ({','.join(existing_cols)}) VALUES ({placeholders})", tuple(row[col] for col in existing_cols))
                conn.commit()
                conn.close()
                st.success("تبدیلیاں محفوظ ہو گئیں")
                st.rerun()
        else:
            st.info("کوئی استاد موجود نہیں")
        with st.expander("➕ نیا استاد رجسٹر کریں"):
            with st.form("new_teacher_form"):
                name = st.text_input("استاد کا نام*")
                password = st.text_input("پاسورڈ*", type="password")
                dept = st.selectbox("شعبہ", ["حفظ", "قاعدہ", "درسِ نظامی", "عصری تعلیم"])
                phone = st.text_input("فون نمبر")
                address = st.text_area("پتہ")
                id_card = st.text_input("شناختی کارڈ نمبر")
                joining_date = st.date_input("تاریخ شمولیت", date.today())
                photo = st.file_uploader("تصویر (اختیاری)", type=["jpg", "png", "jpeg"])
                if st.form_submit_button("رجسٹر کریں"):
                    if name and password:
                        conn = get_db_connection()
                        c = conn.cursor()
                        try:
                            photo_path = None
                            if photo:
                                os.makedirs("uploads", exist_ok=True)
                                photo_path = f"uploads/teacher_{name}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
                                with open(photo_path, "wb") as f:
                                    f.write(photo.getbuffer())
                            c.execute("INSERT INTO teachers (name, password, dept, phone, address, id_card, joining_date, photo) VALUES (?,?,?,?,?,?,?,?)",
                                      (name, hash_password(password), dept, phone, address, id_card, joining_date, photo_path))
                            conn.commit()
                            st.success("استاد کامیابی سے رجسٹر ہو گیا")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("یہ نام پہلے سے موجود ہے")
                        finally:
                            conn.close()
                    else:
                        st.error("نام اور پاسورڈ ضروری ہیں")
    with tab2:
        st.subheader("موجودہ طلبہ (شناختی نمبر تبدیل کریں)")
        conn = get_db_connection()
        columns = ["id", "name", "father_name", "mother_name", "dob", "admission_date", "exit_date", "exit_reason",
                   "id_card", "phone", "address", "teacher_name", "dept", "class", "section", "roll_no"]
        existing_cols = []
        for col in columns:
            if column_exists("students", col):
                existing_cols.append(col)
        query = f"SELECT {', '.join(existing_cols)} FROM students"
        students_df = pd.read_sql_query(query, conn)
        conn.close()
        if not students_df.empty:
            edited_students = st.data_editor(students_df, num_rows="dynamic", use_container_width=True, key="students_edit")
            if st.button("طلبہ میں تبدیلیاں محفوظ کریں (شناختی نمبر تبدیل کرنے سے پرانا ریکارڈ بھی اپ ڈیٹ ہو جائے گا)"):
                conn = get_db_connection()
                c = conn.cursor()
                for _, row in edited_students.iterrows():
                    c.execute("""UPDATE students SET 
                                name=?, father_name=?, mother_name=?, dob=?, admission_date=?, exit_date=?, exit_reason=?,
                                id_card=?, phone=?, address=?, teacher_name=?, dept=?, class=?, section=?, roll_no=?
                                WHERE id=?""",
                              (row['name'], row['father_name'], row['mother_name'], row['dob'], row['admission_date'],
                               row['exit_date'], row['exit_reason'], row['id_card'], row['phone'], row['address'],
                               row['teacher_name'], row['dept'], row['class'], row['section'], row['roll_no'], row['id']))
                conn.commit()
                conn.close()
                st.success("تبدیلیاں محفوظ ہو گئیں (پرانا ریکارڈ برقرار ہے، شناختی نمبر اپ ڈیٹ ہو گیا)")
                st.rerun()
        else:
            st.info("کوئی طالب علم موجود نہیں")
        with st.expander("➕ نیا طالب علم داخل کریں"):
            with st.form("new_student_form"):
                col1, col2 = st.columns(2)
                with col1:
                    name = st.text_input("طالب علم کا نام*")
                    father = st.text_input("والد کا نام*")
                    mother = st.text_input("والدہ کا نام")
                    dob = st.date_input("تاریخ پیدائش", date.today() - timedelta(days=365*10))
                    admission_date = st.date_input("تاریخ داخلہ", date.today())
                    roll_no = st.text_input("شناختی نمبر (اختیاری)", placeholder="مثلاً: 2024-001")
                with col2:
                    dept = st.selectbox("شعبہ*", ["حفظ", "قاعدہ", "درسِ نظامی", "عصری تعلیم"])
                    class_name = st.text_input("کلاس (عصری تعلیم کے لیے)")
                    section = st.text_input("سیکشن")
                    conn = get_db_connection()
                    teachers_list = [t[0] for t in conn.execute("SELECT name FROM teachers WHERE name!='admin'").fetchall()]
                    conn.close()
                    teacher = st.selectbox("استاد*", teachers_list) if teachers_list else st.text_input("استاد کا نام*")
                id_card = st.text_input("B-Form / شناختی کارڈ نمبر")
                phone = st.text_input("فون نمبر")
                address = st.text_area("پتہ")
                photo = st.file_uploader("تصویر (اختیاری)", type=["jpg", "png", "jpeg"])
                st.markdown("---")
                st.markdown("**اگر طالب علم مدرسہ چھوڑ چکا ہے تو درج ذیل معلومات بھریں (ورنہ خالی چھوڑیں):**")
                exit_date = st.date_input("تاریخ خارج", value=None)
                exit_reason = st.text_area("وجہ خارج")
                if st.form_submit_button("داخلہ کریں"):
                    if name and father and teacher and dept:
                        conn = get_db_connection()
                        c = conn.cursor()
                        try:
                            photo_path = None
                            if photo:
                                os.makedirs("uploads", exist_ok=True)
                                photo_path = f"uploads/student_{name}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
                                with open(photo_path, "wb") as f:
                                    f.write(photo.getbuffer())
                            c.execute("""INSERT INTO students 
                                        (name, father_name, mother_name, dob, admission_date, exit_date, exit_reason,
                                         id_card, phone, address, teacher_name, dept, class, section, photo, roll_no)
                                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                                      (name, father, mother, dob, admission_date, exit_date, exit_reason,
                                       id_card, phone, address, teacher, dept, class_name, section, photo_path, roll_no))
                            conn.commit()
                            st.success("طالب علم کامیابی سے داخل ہو گیا")
                            st.rerun()
                        except Exception as e:
                            st.error(f"خرابی: {str(e)}")
                        finally:
                            conn.close()
                    else:
                        st.error("نام، ولدیت، استاد اور شعبہ ضروری ہیں")

# 8.10 ٹائم ٹیبل مینجمنٹ
elif selected == "📚 ٹائم ٹیبل مینجمنٹ" and st.session_state.user_type == "admin":
    st.header("📚 ٹائم ٹیبل مینجمنٹ")
    conn = get_db_connection()
    teachers = [t[0] for t in conn.execute("SELECT name FROM teachers WHERE name!='admin'").fetchall()]
    conn.close()
    if not teachers:
        st.warning("پہلے اساتذہ رجسٹر کریں")
    else:
        sel_t = st.selectbox("استاد منتخب کریں", teachers)
        conn = get_db_connection()
        tt_df = pd.read_sql_query("SELECT id, day as دن, period as وقت, book as کتاب, room as کمرہ FROM timetable WHERE t_name=?", conn, params=(sel_t,))
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
                book = st.text_input("کتاب / مضمون")
                room = st.text_input("کمرہ نمبر")
                if st.form_submit_button("شامل کریں"):
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("INSERT INTO timetable (t_name, day, period, book, room) VALUES (?,?,?,?,?)",
                              (sel_t, day, period, book, room))
                    conn.commit()
                    conn.close()
                    st.success("پیریڈ شامل کر دیا گیا")
                    st.rerun()
        if not tt_df.empty:
            with st.expander("🔄 پورے ہفتے میں نقل کریں"):
                source_day = st.selectbox("منبع دن", ["ہفتہ", "اتوار", "پیر", "منگل", "بدھ", "جمعرات"], key="copy_source")
                target_days = st.multiselect("نقل کرنے کے لیے دن", ["ہفتہ", "اتوار", "پیر", "منگل", "بدھ", "جمعرات"], default=["ہفتہ", "اتوار", "پیر", "منگل", "بدھ", "جمعرات"])
                if st.button("نقل کریں"):
                    conn = get_db_connection()
                    source_periods = conn.execute("SELECT period, book, room FROM timetable WHERE t_name=? AND day=?", (sel_t, source_day)).fetchall()
                    if source_periods:
                        for d in target_days:
                            conn.execute("DELETE FROM timetable WHERE t_name=? AND day=?", (sel_t, d))
                        for d in target_days:
                            for period, book, room in source_periods:
                                conn.execute("INSERT INTO timetable (t_name, day, period, book, room) VALUES (?,?,?,?,?)",
                                            (sel_t, d, period, book, room))
                        conn.commit()
                        st.success(f"{source_day} کے پیریڈز {', '.join(target_days)} میں نقل ہو گئے")
                    else:
                        st.warning(f"{source_day} کے لیے کوئی پیریڈ نہیں")
                    conn.close()
                    st.rerun()

# 8.11 پاسورڈ تبدیل کریں
elif selected == "🔑 پاسورڈ تبدیل کریں":
    st.header("🔑 پاسورڈ تبدیل کریں")
    if st.session_state.user_type == "admin":
        conn = get_db_connection()
        teachers = [t[0] for t in conn.execute("SELECT name FROM teachers WHERE name!='admin'").fetchall()]
        conn.close()
        if teachers:
            selected_teacher = st.selectbox("استاد منتخب کریں", teachers)
            new_pass = st.text_input("نیا پاسورڈ", type="password")
            confirm_pass = st.text_input("پاسورڈ کی تصدیق کریں", type="password")
            if st.button("پاسورڈ تبدیل کریں"):
                if new_pass and new_pass == confirm_pass:
                    admin_reset_password(selected_teacher, new_pass)
                    st.success(f"{selected_teacher} کا پاسورڈ تبدیل کر دیا گیا")
                else:
                    st.error("پاسورڈ میل نہیں کھاتے")
        else:
            st.info("کوئی دوسرا استاد موجود نہیں")
    else:
        old_pass = st.text_input("پرانا پاسورڈ", type="password")
        new_pass = st.text_input("نیا پاسورڈ", type="password")
        confirm_pass = st.text_input("نیا پاسورڈ دوبارہ", type="password")
        if st.button("اپنا پاسورڈ تبدیل کریں"):
            if old_pass and new_pass and new_pass == confirm_pass:
                if change_password(st.session_state.username, old_pass, new_pass):
                    st.success("پاسورڈ تبدیل ہو گیا۔ براہ کرم دوبارہ لاگ ان کریں")
                    st.session_state.logged_in = False
                    st.rerun()
                else:
                    st.error("پرانا پاسورڈ غلط ہے")
            else:
                st.error("نیا پاسورڈ اور تصدیق ایک جیسی ہونی چاہیے")

# 8.12 نوٹیفیکیشنز
elif selected == "📢 نوٹیفیکیشنز":
    st.header("نوٹیفیکیشن سینٹر")
    if st.session_state.user_type == "admin":
        with st.form("new_notif"):
            title = st.text_input("عنوان")
            msg = st.text_area("پیغام")
            target = st.selectbox("بھیجیں", ["تمام", "اساتذہ", "طلبہ"])
            if st.form_submit_button("بھیجیں"):
                conn = get_db_connection()
                conn.execute("INSERT INTO notifications (title, message, target, created_at) VALUES (?,?,?,?)",
                             (title, msg, target, datetime.now()))
                conn.commit()
                conn.close()
                st.success("نوٹیفکیشن بھیج دیا گیا")
    conn = get_db_connection()
    if st.session_state.user_type == "admin":
        notifs = conn.execute("SELECT title, message, created_at FROM notifications ORDER BY created_at DESC LIMIT 10").fetchall()
    else:
        notifs = conn.execute("SELECT title, message, created_at FROM notifications WHERE target IN ('تمام','اساتذہ') ORDER BY created_at DESC LIMIT 10").fetchall()
    conn.close()
    for n in notifs:
        st.info(f"**{n[0]}**\n\n{n[1]}\n\n*{n[2]}*")

# 8.13 تجزیہ و رپورٹس
elif selected == "📈 تجزیہ و رپورٹس" and st.session_state.user_type == "admin":
    st.header("تجزیہ")
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT a_date as تاریخ FROM t_attendance", conn)
    if not df.empty:
        fig = px.bar(df, x='تاریخ', title="اساتذہ کی حاضری")
        st.plotly_chart(fig)
    conn.close()

# 8.14 بیک اپ & سیٹنگز
elif selected == "⚙️ بیک اپ & سیٹنگز" and st.session_state.user_type == "admin":
    st.header("بیک اپ اور سیٹنگز")
    st.subheader("📥 مکمل ڈیٹا بیس بیک اپ")
    if os.path.exists(DB_NAME):
        with open(DB_NAME, "rb") as f:
            st.download_button(
                label="💾 ڈیٹا بیس فائل ڈاؤن لوڈ کریں (.db)",
                data=f,
                file_name=f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db",
                mime="application/x-sqlite3"
            )
    else:
        st.warning("ڈیٹا بیس فائل موجود نہیں")
    st.markdown("---")
    st.subheader("🔄 ڈیٹا بیس ریسٹور کریں")
    st.warning("⚠️ احتیاط: موجودہ ڈیٹا ختم ہو جائے گا! پہلے بیک اپ ضرور لیں۔")
    uploaded_file = st.file_uploader("پہلے سے محفوظ کردہ .db فائل منتخب کریں", type=["db"])
    if uploaded_file is not None:
        confirm = st.checkbox("میں سمجھ گیا ہوں کہ موجودہ ڈیٹا ختم ہو جائے گا")
        if confirm and st.button("ریسٹور کریں"):
            if os.path.exists(DB_NAME):
                shutil.copy(DB_NAME, f"{DB_NAME}_before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
            with open(DB_NAME, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success("ڈیٹا بیس ریسٹور کر دیا گیا۔ براہ کرم ایپ کو دوبارہ چلائیں (ری لوڈ کریں)۔")
            st.rerun()
    st.markdown("---")
    st.subheader("📄 CSV فائلوں کا بیک اپ (زپ میں ڈاؤن لوڈ)")
    if st.button("💾 تمام ٹیبلز کی CSV بیک اپ (زپ) بنائیں"):
        tables = ["teachers", "students", "hifz_records", "qaida_records", "general_education", "t_attendance", "exams", "passed_paras", "timetable", "leave_requests", "notifications", "audit_log", "staff_monitoring"]
        conn = get_db_connection()
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for t in tables:
                try:
                    df = pd.read_sql_query(f"SELECT * FROM {t}", conn)
                    csv_data = df.to_csv(index=False).encode('utf-8-sig')
                    zip_file.writestr(f"{t}.csv", csv_data)
                except Exception as e:
                    st.warning(f"ٹیبل {t} کی بیک اپ میں خرابی: {str(e)}")
        conn.close()
        zip_buffer.seek(0)
        st.download_button(
            label="📥 CSV بیک اپ زپ ڈاؤن لوڈ کریں",
            data=zip_buffer,
            file_name=f"backup_tables_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
            mime="application/zip"
        )
    with st.expander("آڈٹ لاگ"):
        conn = get_db_connection()
        logs = pd.read_sql_query("SELECT user, action, timestamp, details FROM audit_log ORDER BY timestamp DESC LIMIT 50", conn)
        conn.close()
        st.dataframe(logs)

# ==================== 9. استاد کے سیکشن ====================
# 9.1 روزانہ سبق اندراج
if selected == "📝 روزانہ سبق اندراج" and st.session_state.user_type == "teacher":
    st.header("📝 روزانہ سبق اندراج")
    entry_date = st.date_input("تاریخ (جس دن کا اندراج کرنا ہے)", date.today())
    dept = st.selectbox("شعبہ منتخب کریں", ["حفظ", "قاعدہ", "درسِ نظامی", "عصری تعلیم"])
    
    if dept == "حفظ":
        st.subheader("حفظ کا اندراج")
        conn = get_db_connection()
        students = conn.execute("SELECT id, name, father_name FROM students WHERE teacher_name=? AND dept='حفظ'", (st.session_state.username,)).fetchall()
        conn.close()
        if not students:
            st.info("آپ کی کلاس میں کوئی طالب علم نہیں")
        else:
            for sid, s, f in students:
                key = f"{sid}_{s}_{f}"
                st.markdown(f"### 👤 {s} ولد {f}")
                att = st.radio("حاضری", ["حاضر", "غیر حاضر", "رخصت"], key=f"att_{key}", horizontal=True)
                if att == "حاضر":
                    sabaq_nagha = st.checkbox("سبق ناغہ", key=f"sabaq_nagha_{key}")
                    if not sabaq_nagha:
                        surah = st.selectbox("سورت", surahs_urdu, key=f"surah_{key}")
                        a_from = st.text_input("آیت (سے)", key=f"af_{key}")
                        a_to = st.text_input("آیت (تک)", key=f"at_{key}")
                        sabq = f"{surah}: {a_from}-{a_to}"
                        lines = st.number_input("کل ستر (لائنوں کی تعداد)", min_value=0, value=0, key=f"lines_{key}")
                    else:
                        sabq = "ناغہ"
                        lines = 0
                    sq_nagha = st.checkbox("سبقی ناغہ", key=f"sq_nagha_{key}")
                    if not sq_nagha:
                        if f"sq_rows_{key}" not in st.session_state:
                            st.session_state[f"sq_rows_{key}"] = 1
                        st.write("**سبقی**")
                        sq_parts = []; sq_a = 0; sq_m = 0
                        for i in range(st.session_state[f"sq_rows_{key}"]):
                            cols = st.columns([2,2,1,1])
                            p = cols[0].selectbox("پارہ", paras, key=f"sqp_{key}_{i}")
                            v = cols[1].selectbox("مقدار", ["مکمل", "آدھا", "پون", "پاؤ"], key=f"sqv_{key}_{i}")
                            a = cols[2].number_input("اٹکن", 0, key=f"sqa_{key}_{i}")
                            e = cols[3].number_input("غلطی", 0, key=f"sqe_{key}_{i}")
                            sq_parts.append(f"{p}:{v}")
                            sq_a += a; sq_m += e
                        if st.button("➕", key=f"add_sq_{key}", help="مزید سبقی پارہ شامل کریں"):
                            st.session_state[f"sq_rows_{key}"] += 1
                            st.rerun()
                    else:
                        sq_parts = ["ناغہ"]
                        sq_a = sq_m = 0
                    m_nagha = st.checkbox("منزل ناغہ", key=f"m_nagha_{key}")
                    if not m_nagha:
                        if f"m_rows_{key}" not in st.session_state:
                            st.session_state[f"m_rows_{key}"] = 1
                        st.write("**منزل**")
                        m_parts = []; m_a = 0; m_m = 0
                        for j in range(st.session_state[f"m_rows_{key}"]):
                            cols = st.columns([2,2,1,1])
                            p = cols[0].selectbox("پارہ", paras, key=f"mp_{key}_{j}")
                            v = cols[1].selectbox("مقدار", ["مکمل", "آدھا", "پون", "پاؤ"], key=f"mv_{key}_{j}")
                            a = cols[2].number_input("اٹکن", 0, key=f"ma_{key}_{j}")
                            e = cols[3].number_input("غلطی", 0, key=f"me_{key}_{j}")
                            m_parts.append(f"{p}:{v}")
                            m_a += a; m_m += e
                        if st.button("➕", key=f"add_m_{key}", help="مزید منزل پارہ شامل کریں"):
                            st.session_state[f"m_rows_{key}"] += 1
                            st.rerun()
                    else:
                        m_parts = ["ناغہ"]
                        m_a = m_m = 0
                    if st.button(f"محفوظ کریں ({s})", key=f"save_{key}"):
                        conn = get_db_connection()
                        c = conn.cursor()
                        chk = c.execute("SELECT 1 FROM hifz_records WHERE r_date=? AND student_id=?", (entry_date, sid)).fetchone()
                        if chk:
                            st.error(f"{s} کا ریکارڈ پہلے سے موجود ہے (تاریخ {entry_date})")
                        else:
                            c.execute("""INSERT INTO hifz_records 
                                        (r_date, student_id, t_name, surah, lines, sq_p, sq_a, sq_m, m_p, m_a, m_m, attendance)
                                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                                      (entry_date, sid, st.session_state.username, sabq, lines,
                                       " | ".join(sq_parts), sq_a, sq_m,
                                       " | ".join(m_parts), m_a, m_m, att))
                            conn.commit()
                            log_audit(st.session_state.username, "Hifz Entry", f"{s} {entry_date}")
                            st.success("محفوظ ہو گیا")
                        conn.close()
                else:
                    if st.button(f"محفوظ کریں ({s})", key=f"save_absent_{key}"):
                        conn = get_db_connection()
                        c = conn.cursor()
                        chk = c.execute("SELECT 1 FROM hifz_records WHERE r_date=? AND student_id=?", (entry_date, sid)).fetchone()
                        if chk:
                            st.error(f"{s} کا ریکارڈ پہلے سے موجود ہے (تاریخ {entry_date})")
                        else:
                            c.execute("""INSERT INTO hifz_records 
                                        (r_date, student_id, t_name, surah, lines, sq_p, sq_a, sq_m, m_p, m_a, m_m, attendance)
                                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                                      (entry_date, sid, st.session_state.username, "ناغہ", 0, "ناغہ", 0, 0, "ناغہ", 0, 0, att))
                            conn.commit()
                            st.success("محفوظ ہو گیا")
                        conn.close()
                st.markdown("---")
    
    elif dept == "قاعدہ":
        st.subheader("قاعدہ (نورانی قاعدہ / نماز) کا اندراج")
        conn = get_db_connection()
        students = conn.execute("SELECT id, name, father_name FROM students WHERE teacher_name=? AND dept='قاعدہ'", (st.session_state.username,)).fetchall()
        conn.close()
        if not students:
            st.info("آپ کی کلاس میں کوئی طالب علم نہیں")
        else:
            for sid, s, f in students:
                key = f"{sid}_{s}_{f}"
                st.markdown(f"### 👤 {s} ولد {f}")
                att = st.radio("حاضری", ["حاضر", "غیر حاضر", "رخصت"], key=f"att_{key}", horizontal=True)
                if att == "حاضر":
                    nagha = st.checkbox("ناغہ", key=f"nagha_{key}")
                    if not nagha:
                        lesson_type = st.radio("نوعیت", ["نورانی قاعدہ", "نماز (حنفی)"], key=f"lesson_type_{key}", horizontal=True)
                        if lesson_type == "نورانی قاعدہ":
                            lesson_no = st.text_input("تختی نمبر / سبق نمبر", key=f"lesson_{key}")
                            total_lines = st.number_input("کل لائنیں", min_value=0, value=0, key=f"lines_{key}")
                            details = ""
                        else:  # نماز حنفی
                            lesson_no = st.selectbox("سبق منتخب کریں", [
                                "وضو کا طریقہ", "غسل کا طریقہ", "تیمم کا طریقہ",
                                "اذان و اقامت", "نماز کا طریقہ (مسنون)", "دعائے ثنا",
                                "سورہ فاتحہ", "سورہ اخلاص", "قنوت دعا", "تشہد", "درود شریف", "دعائے ختم نماز"
                            ], key=f"lesson_{key}")
                            total_lines = st.number_input("کل لائنیں (اگر کوئی ہوں)", min_value=0, value=0, key=f"lines_{key}")
                            details = st.text_area("تفصیل / نوٹ", key=f"details_{key}")
                    else:
                        lesson_no = "ناغہ"
                        total_lines = 0
                        details = ""
                    if st.button(f"محفوظ کریں ({s})", key=f"save_{key}"):
                        conn = get_db_connection()
                        c = conn.cursor()
                        chk = c.execute("SELECT 1 FROM qaida_records WHERE r_date=? AND student_id=?", (entry_date, sid)).fetchone()
                        if chk:
                            st.error(f"{s} کا ریکارڈ پہلے سے موجود ہے (تاریخ {entry_date})")
                        else:
                            c.execute("""INSERT INTO qaida_records 
                                        (r_date, student_id, t_name, lesson_no, total_lines, details, attendance)
                                        VALUES (?,?,?,?,?,?,?)""",
                                      (entry_date, sid, st.session_state.username, lesson_no, total_lines, details, att))
                            conn.commit()
                            log_audit(st.session_state.username, "Qaida Entry", f"{s} {entry_date}")
                            st.success("محفوظ ہو گیا")
                        conn.close()
                else:
                    if st.button(f"غیر حاضر / رخصت محفوظ کریں ({s})", key=f"save_absent_{key}"):
                        conn = get_db_connection()
                        c = conn.cursor()
                        chk = c.execute("SELECT 1 FROM qaida_records WHERE r_date=? AND student_id=?", (entry_date, sid)).fetchone()
                        if chk:
                            st.error(f"{s} کا ریکارڈ پہلے سے موجود ہے (تاریخ {entry_date})")
                        else:
                            c.execute("""INSERT INTO qaida_records 
                                        (r_date, student_id, t_name, lesson_no, total_lines, details, attendance)
                                        VALUES (?,?,?,?,?,?,?)""",
                                      (entry_date, sid, st.session_state.username, "ناغہ", 0, "", att))
                            conn.commit()
                            st.success("محفوظ ہو گیا")
                        conn.close()
                st.markdown("---")
    
    elif dept == "درسِ نظامی":
        st.subheader("درسِ نظامی سبق ریکارڈ")
        conn = get_db_connection()
        students = conn.execute("SELECT id, name, father_name FROM students WHERE teacher_name=? AND dept='درسِ نظامی'", (st.session_state.username,)).fetchall()
        conn.close()
        if not students:
            st.info("کوئی طالب علم نہیں")
        else:
            with st.form("dars_form"):
                records = []
                for sid, s, f in students:
                    st.markdown(f"### {s} ولد {f}")
                    att = st.radio("حاضری", ["حاضر", "غیر حاضر", "رخصت"], key=f"att_dars_{sid}", horizontal=True)
                    if att == "حاضر":
                        book = st.text_input("کتاب کا نام", key=f"book_{sid}")
                        lesson = st.text_area("آج کا سبق", key=f"lesson_{sid}")
                        perf = st.select_slider("کارکردگی", ["بہت بہتر", "بہتر", "مناسب", "کمزور"], key=f"perf_{sid}")
                        records.append((entry_date, sid, st.session_state.username, "درسِ نظامی", book, lesson, "", perf, att))
                    else:
                        records.append((entry_date, sid, st.session_state.username, "درسِ نظامی", "ناغہ", "ناغہ", "", "ناغہ", att))
                if st.form_submit_button("محفوظ کریں"):
                    conn = get_db_connection()
                    c = conn.cursor()
                    for rec in records:
                        c.execute("INSERT INTO general_education (r_date, student_id, t_name, dept, book_subject, today_lesson, performance, attendance) VALUES (?,?,?,?,?,?,?,?)",
                                  rec)
                    conn.commit()
                    conn.close()
                    st.success("محفوظ ہو گیا")
    
    elif dept == "عصری تعلیم":
        st.subheader("عصری تعلیم ڈائری")
        conn = get_db_connection()
        students = conn.execute("SELECT id, name, father_name FROM students WHERE teacher_name=? AND dept='عصری تعلیم'", (st.session_state.username,)).fetchall()
        conn.close()
        if not students:
            st.info("کوئی طالب علم نہیں")
        else:
            with st.form("school_form"):
                records = []
                for sid, s, f in students:
                    st.markdown(f"### {s} ولد {f}")
                    att = st.radio("حاضری", ["حاضر", "غیر حاضر", "رخصت"], key=f"att_school_{sid}", horizontal=True)
                    if att == "حاضر":
                        subject = st.selectbox("مضمون", ["اردو", "انگلش", "ریاضی", "سائنس", "اسلامیات", "سماجی علوم"], key=f"sub_{sid}")
                        topic = st.text_input("عنوان", key=f"topic_{sid}")
                        hw = st.text_area("ہوم ورک", key=f"hw_{sid}")
                        records.append((entry_date, sid, st.session_state.username, "عصری تعلیم", subject, topic, hw, "", att))
                    else:
                        records.append((entry_date, sid, st.session_state.username, "عصری تعلیم", "ناغہ", "ناغہ", "ناغہ", "", att))
                if st.form_submit_button("محفوظ کریں"):
                    conn = get_db_connection()
                    c = conn.cursor()
                    for rec in records:
                        c.execute("INSERT INTO general_education (r_date, student_id, t_name, dept, book_subject, today_lesson, homework, attendance) VALUES (?,?,?,?,?,?,?,?)",
                                  rec)
                    conn.commit()
                    conn.close()
                    st.success("محفوظ ہو گیا")

# 9.2 امتحانی درخواست
elif selected == "🎓 امتحانی درخواست" and st.session_state.user_type == "teacher":
    st.subheader("امتحان کے لیے طالب علم نامزد کریں")
    conn = get_db_connection()
    students = conn.execute("SELECT id, name, father_name, dept FROM students WHERE teacher_name=?", (st.session_state.username,)).fetchall()
    conn.close()
    if not students:
        st.warning("کوئی طالب علم نہیں")
    else:
        with st.form("exam_request"):
            s_list = [f"{s[1]} ولد {s[2]} ({s[3]})" for s in students]
            sel = st.selectbox("طالب علم", s_list)
            s_name, rest = sel.split(" ولد ")
            f_name, dept = rest.split(" (")
            dept = dept.replace(")", "")
            student_id = [s[0] for s in students if s[1] == s_name and s[2] == f_name][0]
            exam_type = st.selectbox("امتحان کی قسم", ["پارہ ٹیسٹ", "ماہانہ", "سہ ماہی", "سالانہ"])
            start_date = st.date_input("تاریخ ابتدا", date.today())
            end_date = st.date_input("تاریخ اختتام", date.today() + timedelta(days=7))
            total_days = (end_date - start_date).days + 1
            st.write(f"**کل دن:** {total_days}")
            from_para = 0
            to_para = 0
            book_name = ""
            amount_read = ""
            if exam_type == "پارہ ٹیسٹ":
                col1, col2 = st.columns(2)
                from_para = col1.number_input("پارہ نمبر (شروع)", min_value=1, max_value=30, value=1)
                to_para = col2.number_input("پارہ نمبر (اختتام)", min_value=from_para, max_value=30, value=from_para)
            else:
                if dept == "حفظ":
                    col1, col2 = st.columns(2)
                    from_para = col1.number_input("پارہ نمبر (شروع)", min_value=1, max_value=30, value=1)
                    to_para = col2.number_input("پارہ نمبر (اختتام)", min_value=from_para, max_value=30, value=min(from_para+4,30))
                    amount_read = st.text_input("مقدار خواندگی (مثلاً: 5 پارے, 10 سورتیں)", placeholder="مقدار")
                else:
                    col1, col2 = st.columns(2)
                    book_name = col1.text_input("کتاب کا نام", placeholder="مثلاً: نحو میر, قدوری")
                    amount_read = col2.text_input("مقدار خواندگی", placeholder="مثلاً: باب اول تا باب پنجم")
            if st.form_submit_button("بھیجیں"):
                conn = get_db_connection()
                c = conn.cursor()
                c.execute("""INSERT INTO exams 
                            (student_id, dept, exam_type, from_para, to_para, book_name, amount_read, start_date, end_date, total_days, status)
                            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                          (student_id, dept, exam_type, from_para, to_para, book_name, amount_read, start_date, end_date, total_days, "پینڈنگ"))
                conn.commit()
                conn.close()
                st.success("درخواست بھیج دی گئی")

# 9.3 رخصت کی درخواست
elif selected == "📩 رخصت کی درخواست" and st.session_state.user_type == "teacher":
    st.header("📩 رخصت کی درخواست")
    with st.form("leave_request_form"):
        l_type = st.selectbox("رخصت کی نوعیت", ["بیماری", "ضروری کام", "ہنگامی", "دیگر"])
        start_date = st.date_input("تاریخ آغاز", date.today())
        days = st.number_input("دنوں کی تعداد", min_value=1, max_value=30, value=1)
        back_date = start_date + timedelta(days=days-1)
        st.write(f"واپسی کی تاریخ: {back_date}")
        reason = st.text_area("تفصیلی وجہ")
        if st.form_submit_button("درخواست جمع کریں"):
            if reason:
                conn = get_db_connection()
                c = conn.cursor()
                c.execute("""INSERT INTO leave_requests 
                            (t_name, l_type, start_date, days, reason, status, notification_seen, request_date)
                            VALUES (?,?,?,?,?,?,?,?)""",
                          (st.session_state.username, l_type, start_date, days, reason, "پینڈنگ", 0, date.today()))
                conn.commit()
                conn.close()
                log_audit(st.session_state.username, "Leave Requested", f"{l_type} for {days} days")
                st.success("درخواست بھیج دی گئی۔ منتظمین جلد جواب دیں گے۔")
            else:
                st.error("براہ کرم وجہ تحریر کریں")

# 9.4 میری حاضری
elif selected == "🕒 میری حاضری" and st.session_state.user_type == "teacher":
    st.header("🕒 میری حاضری")
    today = date.today()
    conn = get_db_connection()
    rec = conn.execute("SELECT arrival, departure FROM t_attendance WHERE t_name=? AND a_date=?", (st.session_state.username, today)).fetchone()
    conn.close()
    if not rec:
        col1, col2 = st.columns(2)
        arr_date = col1.date_input("تاریخ", today)
        arr_time = col2.time_input("آمد کا وقت", datetime.now().time())
        if st.button("آمد درج کریں"):
            time_str = arr_time.strftime("%I:%M %p")
            conn = get_db_connection()
            conn.execute("INSERT INTO t_attendance (t_name, a_date, arrival, actual_arrival) VALUES (?,?,?,?)",
                         (st.session_state.username, arr_date, time_str, get_pk_time()))
            conn.commit()
            conn.close()
            st.success("آمد درج ہو گئی")
            st.rerun()
    elif rec and rec[1] is None:
        st.success(f"آمد: {rec[0]}")
        dep_time = st.time_input("رخصت کا وقت", datetime.now().time())
        if st.button("رخصت درج کریں"):
            time_str = dep_time.strftime("%I:%M %p")
            conn = get_db_connection()
            conn.execute("UPDATE t_attendance SET departure=?, actual_departure=? WHERE t_name=? AND a_date=?",
                         (time_str, get_pk_time(), st.session_state.username, today))
            conn.commit()
            conn.close()
            st.success("رخصت درج ہو گئی")
            st.rerun()
    else:
        st.success(f"آمد: {rec[0]} | رخصت: {rec[1]}")

# 9.5 میرا ٹائم ٹیبل
elif selected == "📚 میرا ٹائم ٹیبل" and st.session_state.user_type == "teacher":
    st.header("📚 میرا ٹائم ٹیبل")
    conn = get_db_connection()
    tt_df = pd.read_sql_query("SELECT day as دن, period as وقت, book as کتاب, room as کمرہ FROM timetable WHERE t_name=?", conn, params=(st.session_state.username,))
    conn.close()
    if tt_df.empty:
        st.info("ابھی آپ کا ٹائم ٹیبل ترتیب نہیں دیا گیا")
    else:
        day_order = {"ہفتہ": 0, "اتوار": 1, "پیر": 2, "منگل": 3, "بدھ": 4, "جمعرات": 5}
        tt_df['day_order'] = tt_df['دن'].map(day_order)
        tt_df = tt_df.sort_values(['day_order', 'وقت'])
        pivot = tt_df.pivot(index='وقت', columns='دن', values='کتاب').fillna("—")
        st.dataframe(pivot, use_container_width=True)
        html_timetable = generate_timetable_html(tt_df)
        st.download_button("📥 HTML ڈاؤن لوڈ کریں", html_timetable, f"Timetable_{st.session_state.username}.html", "text/html")
        if st.button("🖨️ پرنٹ کریں"):
            st.components.v1.html(f"<script>var w=window.open();w.document.write(`{html_timetable}`);w.print();</script>", height=0)

# ==================== 10. لاگ آؤٹ ====================
st.sidebar.divider()
if st.sidebar.button("🚪 لاگ آؤٹ"):
    st.session_state.logged_in = False
    st.rerun()
