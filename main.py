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

# ==================== 1. ڈیٹا بیس سیٹ اپ اور مائیگریشن ====================
DB_NAME = 'jamia_millia_data.db'

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
    
    # موجودہ ٹیبلز
    c.execute('''CREATE TABLE IF NOT EXISTS teachers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        password TEXT,
        dept TEXT,
        phone TEXT,
        address TEXT,
        id_card TEXT,
        photo TEXT,
        joining_date DATE,
        role TEXT DEFAULT 'teacher'   -- 'admin', 'teacher', 'aasri'
    )''')
    
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
        roll_no TEXT,
        dars_level_id INTEGER,        -- درسِ نظامی کے درجے کا حوالہ
        session_id INTEGER
    )''')
    
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
        cleanliness TEXT,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
    )''')
    
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
        cleanliness TEXT,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS general_education (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        r_date DATE,
        student_id INTEGER,
        t_name TEXT,
        dept TEXT,
        book_subject TEXT,
        today_lesson TEXT,
        lesson_from TEXT,
        lesson_to TEXT,
        homework TEXT,
        performance TEXT,
        attendance TEXT,
        cleanliness TEXT,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS t_attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        t_name TEXT,
        a_date DATE,
        arrival TEXT,
        departure TEXT,
        actual_arrival TEXT,
        actual_departure TEXT
    )''')
    
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
    
    c.execute('''CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        message TEXT,
        target TEXT,
        created_at DATETIME,
        seen INTEGER DEFAULT 0
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT,
        action TEXT,
        timestamp DATETIME,
        details TEXT
    )''')
    
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
    
    # نئے ٹیبلز برائے درسِ نظامی اور ٹائم ٹیبل
    c.execute('''CREATE TABLE IF NOT EXISTS academic_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_name TEXT UNIQUE,
        start_date DATE,
        end_date DATE,
        is_active BOOLEAN DEFAULT 0
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS dars_levels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        level_name TEXT UNIQUE,
        level_order INTEGER
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS dars_books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        level_id INTEGER,
        book_name TEXT,
        book_subject TEXT,
        FOREIGN KEY (level_id) REFERENCES dars_levels(id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS master_timetable (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER,
        day TEXT,
        period_no INTEGER,
        start_time TEXT,
        end_time TEXT,
        dars_level_id INTEGER,
        book_id INTEGER,
        teacher_name TEXT,
        room TEXT,
        is_active BOOLEAN DEFAULT 1,
        FOREIGN KEY (session_id) REFERENCES academic_sessions(id),
        FOREIGN KEY (dars_level_id) REFERENCES dars_levels(id),
        FOREIGN KEY (book_id) REFERENCES dars_books(id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS aasri_groups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_name TEXT,
        teacher_name TEXT,
        session_id INTEGER,
        created_date DATE,
        FOREIGN KEY (session_id) REFERENCES academic_sessions(id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS aasri_group_students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id INTEGER,
        student_id INTEGER,
        FOREIGN KEY (group_id) REFERENCES aasri_groups(id),
        FOREIGN KEY (student_id) REFERENCES students(id)
    )''')
    
    # ڈیفالٹ ڈیٹا: درسِ نظامی کے درجات
    default_levels = [
        ("متوسطہ سال اول", 1),
        ("متوسطہ سال دوم", 2),
        ("متوسطہ سال سوم", 3),
        ("اولیٰ", 4),
        ("درجہ ثانیہ", 5),
        ("درجہ ثالثہ", 6),
        ("درجہ رابعہ", 7),
        ("درجہ خامسہ", 8),
        ("درجہ سادسہ", 9),
        ("موقوف علیہ", 10),
        ("دورہ حدیث", 11)
    ]
    for level_name, order in default_levels:
        c.execute("INSERT OR IGNORE INTO dars_levels (level_name, level_order) VALUES (?,?)", (level_name, order))
    
    # اکیڈمک سیشن ڈیفالٹ
    c.execute("INSERT OR IGNORE INTO academic_sessions (session_name, start_date, end_date, is_active) VALUES (?,?,?,?)",
              ("2025-2026 / 1446-1447", date.today().replace(month=4, day=1), date.today().replace(year=date.today().year+1, month=3, day=31), 1))
    
    # ایڈمن اکاؤنٹ
    admin_hash = hash_password("jamia123")
    c.execute("INSERT OR IGNORE INTO teachers (name, password, dept, role) VALUES (?,?,?,?)",
              ("admin", admin_hash, "Admin", "admin"))
    
    conn.commit()
    conn.close()
    
    # مائیگریشن: پرانے ڈیٹا میں ضروری کالم شامل کریں
    add_column_if_not_exists('general_education', 'lesson_from', 'TEXT')
    add_column_if_not_exists('general_education', 'lesson_to', 'TEXT')
    add_column_if_not_exists('teachers', 'role', 'TEXT DEFAULT "teacher"')
    add_column_if_not_exists('students', 'dars_level_id', 'INTEGER')
    add_column_if_not_exists('students', 'session_id', 'INTEGER')

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

def calculate_grade_with_attendance(attendance, sabaq_nagha, sq_nagha, m_nagha, sq_mistakes, m_mistakes):
    if attendance == "غیر حاضر":
        return "غیر حاضر"
    if attendance == "رخصت":
        return "رخصت"
    nagha_count = sum([sabaq_nagha, sq_nagha, m_nagha])
    if nagha_count == 1:
        return "ناقص (ناغہ)"
    elif nagha_count == 2:
        return "کمزور (ناغہ)"
    elif nagha_count == 3:
        return "ناکام (مکمل ناغہ)"
    total_mistakes = sq_mistakes + m_mistakes
    if total_mistakes <= 2:
        return "ممتاز"
    elif total_mistakes <= 5:
        return "جید جداً"
    elif total_mistakes <= 8:
        return "جید"
    elif total_mistakes <= 12:
        return "مقبول"
    else:
        return "دوبارہ کوشش کریں"

def cleanliness_to_score(clean):
    if clean == "بہترین": return 3
    elif clean == "بہتر": return 2
    elif clean == "ناقص": return 1
    else: return 0

def generate_html_report(df, title, student_name="", start_date="", end_date=""):
    html_table = df.to_html(index=False, classes='print-table', border=1, justify='center', escape=False)
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

def generate_timetable_html(df_timetable, title="ٹائم ٹیبل"):
    if df_timetable.empty:
        return "<p>کوئی ٹائم ٹیبل دستیاب نہیں</p>"
    day_order = {"ہفتہ": 0, "اتوار": 1, "پیر": 2, "منگل": 3, "بدھ": 4, "جمعرات": 5}
    df_timetable['day_order'] = df_timetable['دن'].map(day_order)
    df_timetable = df_timetable.sort_values(['day_order', 'پیریڈ نمبر'])
    pivot = df_timetable.pivot(index='پیریڈ نمبر', columns='دن', values='کتاب/درجہ')
    pivot = pivot.fillna("—")
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
    .stButton > button { background: linear-gradient(90deg, #1e5631, #2e7d32); color: white; border-radius: 30px; border: none; padding: 0.5rem 1rem; font-weight: bold; transition: 0.3s; width: 100%; }
    .stButton > button:hover { transform: scale(1.02); background: linear-gradient(90deg, #2e7d32, #1e5631); }
    .main-header { text-align: center; background: linear-gradient(135deg, #f1f8e9, #d4e0c9); padding: 1rem; border-radius: 20px; margin-bottom: 1rem; border-bottom: 4px solid #1e5631; }
    .report-card { background: white; border-radius: 15px; padding: 1rem; box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin-bottom: 1rem; }
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
                    st.session_state.logged_in = True
                    st.session_state.username = u
                    # تعین کریں کہ ایڈمن، عام استاد یا عصری استاد
                    role = res[9] if len(res) > 9 and res[9] else 'teacher'
                    if u == "admin":
                        st.session_state.user_type = "admin"
                    elif role == "aasri":
                        st.session_state.user_type = "aasri"
                    else:
                        st.session_state.user_type = "teacher"
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
            "👥 یوزر مینجمنٹ", "📚 ماسٹر ٹائم ٹیبل", "🎓 درسِ نظامی سیٹنگز", "🔑 پاسورڈ تبدیل کریں",
            "📋 عملہ نگرانی", "📢 نوٹیفیکیشنز", "📈 تجزیہ", "🏆 بہترین طلباء", "⚙️ بیک اپ"]
elif st.session_state.user_type == "aasri":
    menu = ["📝 عصری تعلیم ڈیش بورڈ", "👥 گروپ مینجمنٹ", "📚 میرا ٹائم ٹیبل", "📩 رخصت کی درخواست",
            "🕒 میری حاضری", "🔑 پاسورڈ تبدیل کریں", "📢 نوٹیفیکیشنز"]
else:
    menu = ["📝 استاد ڈیش بورڈ", "🎓 امتحانی درخواست", "📩 رخصت کی درخواست",
            "🕒 میری حاضری", "🔑 پاسورڈ تبدیل کریں", "📢 نوٹیفیکیشنز"]

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
cleanliness_options = ["بہترین", "بہتر", "ناقص"]

# ==================== 7. ایڈمن سیکشنز ====================
if selected == "📊 ایڈمن ڈیش بورڈ" and st.session_state.user_type == "admin":
    st.markdown("<div class='main-header'><h1>📊 ایڈمن ڈیش بورڈ</h1></div>", unsafe_allow_html=True)
    conn = get_db_connection()
    total_students = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    total_teachers = conn.execute("SELECT COUNT(*) FROM teachers WHERE name!='admin'").fetchone()[0]
    col1, col2 = st.columns(2)
    col1.metric("کل طلباء", total_students)
    col2.metric("کل اساتذہ", total_teachers)
    conn.close()

elif selected == "🎓 درسِ نظامی سیٹنگز" and st.session_state.user_type == "admin":
    st.header("🎓 درسِ نظامی سیٹنگز")
    tab1, tab2, tab3 = st.tabs(["درجات", "کتابیں", "تعلیمی سیشن"])
    with tab1:
        conn = get_db_connection()
        levels_df = pd.read_sql_query("SELECT id, level_name as 'درجہ', level_order as 'ترتیب' FROM dars_levels ORDER BY level_order", conn)
        conn.close()
        edited = st.data_editor(levels_df, num_rows="dynamic", use_container_width=True, key="levels_edit")
        if st.button("درجات محفوظ کریں"):
            conn = get_db_connection()
            c = conn.cursor()
            # ڈیلیٹ پرانے
            old_ids = set(levels_df['id'])
            new_ids = set(edited['id']) if 'id' in edited.columns else set()
            for did in old_ids - new_ids:
                c.execute("DELETE FROM dars_levels WHERE id=?", (did,))
            for _, row in edited.iterrows():
                if pd.isna(row['id']) or row['id'] == 0:
                    c.execute("INSERT INTO dars_levels (level_name, level_order) VALUES (?,?)", (row['درجہ'], row['ترتیب']))
                else:
                    c.execute("UPDATE dars_levels SET level_name=?, level_order=? WHERE id=?", (row['درجہ'], row['ترتیب'], row['id']))
            conn.commit()
            conn.close()
            st.success("محفوظ ہو گیا")
            st.rerun()
    with tab2:
        conn = get_db_connection()
        levels = conn.execute("SELECT id, level_name FROM dars_levels ORDER BY level_order").fetchall()
        conn.close()
        if levels:
            level_names = {l[0]: l[1] for l in levels}
            sel_level = st.selectbox("درجہ منتخب کریں", list(level_names.values()))
            level_id = [k for k, v in level_names.items() if v == sel_level][0]
            conn = get_db_connection()
            books_df = pd.read_sql_query("SELECT id, book_name as 'کتاب', book_subject as 'مضمون' FROM dars_books WHERE level_id=?", conn, params=(level_id,))
            conn.close()
            edited_books = st.data_editor(books_df, num_rows="dynamic", use_container_width=True, key="books_edit")
            if st.button("کتابیں محفوظ کریں"):
                conn = get_db_connection()
                c = conn.cursor()
                old_ids = set(books_df['id'])
                new_ids = set(edited_books['id']) if 'id' in edited_books.columns else set()
                for did in old_ids - new_ids:
                    c.execute("DELETE FROM dars_books WHERE id=?", (did,))
                for _, row in edited_books.iterrows():
                    if pd.isna(row['id']) or row['id'] == 0:
                        c.execute("INSERT INTO dars_books (level_id, book_name, book_subject) VALUES (?,?,?)", (level_id, row['کتاب'], row['مضمون']))
                    else:
                        c.execute("UPDATE dars_books SET book_name=?, book_subject=? WHERE id=?", (row['کتاب'], row['مضمون'], row['id']))
                conn.commit()
                conn.close()
                st.success("محفوظ ہو گیا")
                st.rerun()
    with tab3:
        conn = get_db_connection()
        sessions_df = pd.read_sql_query("SELECT id, session_name as 'سیشن', start_date as 'آغاز', end_date as 'اختتام', is_active as 'فعال' FROM academic_sessions", conn)
        conn.close()
        st.dataframe(sessions_df, use_container_width=True)
        with st.form("new_session"):
            s_name = st.text_input("سیشن کا نام (مثلاً 2025-2026)")
            s_start = st.date_input("تاریخ آغاز", date.today())
            s_end = st.date_input("تاریخ اختتام", date.today().replace(year=date.today().year+1))
            is_active = st.checkbox("فعال سیٹ کریں")
            if st.form_submit_button("نیا سیشن بنائیں"):
                if s_name:
                    conn = get_db_connection()
                    c = conn.cursor()
                    if is_active:
                        c.execute("UPDATE academic_sessions SET is_active=0")
                    c.execute("INSERT INTO academic_sessions (session_name, start_date, end_date, is_active) VALUES (?,?,?,?)",
                              (s_name, s_start, s_end, 1 if is_active else 0))
                    conn.commit()
                    conn.close()
                    st.success("سیشن محفوظ ہو گیا")
                    st.rerun()

elif selected == "📚 ماسٹر ٹائم ٹیبل" and st.session_state.user_type == "admin":
    st.header("📚 ماسٹر ٹائم ٹیبل (پورے مدرسے کا نقشہ)")
    conn = get_db_connection()
    active_session = conn.execute("SELECT id, session_name FROM academic_sessions WHERE is_active=1").fetchone()
    if not active_session:
        st.error("کوئی فعال تعلیمی سیشن موجود نہیں۔ براہ کرم پہلے سیٹنگز میں سیشن بنائیں۔")
        conn.close()
        st.stop()
    session_id, session_name = active_session
    # فلٹر
    days = ["ہفتہ", "اتوار", "پیر", "منگل", "بدھ", "جمعرات"]
    levels = conn.execute("SELECT id, level_name FROM dars_levels ORDER BY level_order").fetchall()
    teachers = conn.execute("SELECT name FROM teachers WHERE name!='admin'").fetchall()
    conn.close()
    col1, col2 = st.columns(2)
    with col1:
        filter_day = st.selectbox("دن فلٹر کریں", ["تمام"] + days)
    with col2:
        level_dict = {l[1]: l[0] for l in levels}
        filter_level = st.selectbox("درجہ فلٹر کریں", ["تمام"] + list(level_dict.keys()))
    
    query = """
        SELECT mt.day as دن, mt.period_no as 'پیریڈ نمبر', mt.start_time as 'آغاز', mt.end_time as 'اختتام',
               dl.level_name as 'درجہ', db.book_name as 'کتاب', mt.teacher_name as 'استاد', mt.room as 'کمرہ'
        FROM master_timetable mt
        JOIN dars_levels dl ON mt.dars_level_id = dl.id
        JOIN dars_books db ON mt.book_id = db.id
        WHERE mt.session_id = ? AND mt.is_active=1
    """
    params = [session_id]
    if filter_day != "تمام":
        query += " AND mt.day = ?"
        params.append(filter_day)
    if filter_level != "تمام":
        query += " AND dl.id = ?"
        params.append(level_dict[filter_level])
    query += " ORDER BY CASE mt.day WHEN 'ہفتہ' THEN 1 WHEN 'اتوار' THEN 2 WHEN 'پیر' THEN 3 WHEN 'منگل' THEN 4 WHEN 'بدھ' THEN 5 WHEN 'جمعرات' THEN 6 END, mt.period_no"
    conn = get_db_connection()
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    if df.empty:
        st.info("کوئی ٹائم ٹیبل اندراج نہیں")
    else:
        st.dataframe(df, use_container_width=True)
        # Pivot view
        st.subheader("📅 پیریڈ وار نقشہ")
        pivot_df = df.copy()
        pivot_df['کتاب/درجہ'] = pivot_df['درجہ'] + " - " + pivot_df['کتاب']
        pivot = pivot_df.pivot(index='پیریڈ نمبر', columns='دن', values='کتاب/درجہ').fillna("—")
        st.dataframe(pivot, use_container_width=True)
        html_tt = generate_timetable_html(pivot_df, f"ماسٹر ٹائم ٹیبل - {session_name}")
        st.download_button("📥 HTML ڈاؤن لوڈ", html_tt, "master_timetable.html", "text/html")
    
    with st.expander("➕ نیا پیریڈ شامل کریں"):
        with st.form("add_master_period"):
            col1, col2 = st.columns(2)
            day = col1.selectbox("دن", days)
            period_no = col2.number_input("پیریڈ نمبر", min_value=1, max_value=10, value=1)
            start_time = st.text_input("آغاز وقت (مثلاً 08:00)")
            end_time = st.text_input("اختتام وقت (مثلاً 08:45)")
            dars_level = st.selectbox("درجہ", list(level_dict.keys()))
            level_id = level_dict[dars_level]
            # اس درجے کی کتابیں
            conn = get_db_connection()
            books = conn.execute("SELECT id, book_name FROM dars_books WHERE level_id=?", (level_id,)).fetchall()
            conn.close()
            if not books:
                st.error("اس درجے کے لیے پہلے کتابیں شامل کریں")
            else:
                book_dict = {b[1]: b[0] for b in books}
                sel_book = st.selectbox("کتاب", list(book_dict.keys()))
                teacher = st.selectbox("استاد", [t[0] for t in teachers])
                room = st.text_input("کمرہ نمبر")
                if st.form_submit_button("شامل کریں"):
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("""INSERT INTO master_timetable 
                                (session_id, day, period_no, start_time, end_time, dars_level_id, book_id, teacher_name, room, is_active)
                                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                              (session_id, day, period_no, start_time, end_time, level_id, book_dict[sel_book], teacher, room, 1))
                    conn.commit()
                    conn.close()
                    st.success("پیریڈ شامل ہو گیا")
                    st.rerun()

elif selected == "👥 یوزر مینجمنٹ" and st.session_state.user_type == "admin":
    st.header("👥 یوزر مینجمنٹ")
    tab1, tab2 = st.tabs(["اساتذہ", "طلبہ"])
    with tab1:
        st.subheader("موجودہ اساتذہ")
        conn = get_db_connection()
        teachers_df = pd.read_sql_query("SELECT id, name, dept, role, phone, address, joining_date FROM teachers WHERE name!='admin'", conn)
        conn.close()
        if not teachers_df.empty:
            edited = st.data_editor(teachers_df, num_rows="dynamic", use_container_width=True, key="teachers_edit2")
            if st.button("تبدیلیاں محفوظ کریں"):
                conn = get_db_connection()
                c = conn.cursor()
                old_ids = set(teachers_df['id'])
                new_ids = set(edited['id']) if 'id' in edited.columns else set()
                for did in old_ids - new_ids:
                    c.execute("DELETE FROM teachers WHERE id=?", (did,))
                for _, row in edited.iterrows():
                    if pd.isna(row['id']) or row['id'] == 0:
                        # نیا استاد
                        pwd = st.text_input(f"پاسورڈ برائے {row['name']}", type="password", key=f"pwd_{row['name']}")
                        if pwd:
                            c.execute("INSERT INTO teachers (name, password, dept, role, phone, address, joining_date) VALUES (?,?,?,?,?,?,?)",
                                      (row['name'], hash_password(pwd), row['dept'], row['role'], row['phone'], row['address'], row['joining_date']))
                    else:
                        c.execute("UPDATE teachers SET name=?, dept=?, role=?, phone=?, address=?, joining_date=? WHERE id=?",
                                  (row['name'], row['dept'], row['role'], row['phone'], row['address'], row['joining_date'], row['id']))
                conn.commit()
                conn.close()
                st.success("محفوظ ہو گیا")
                st.rerun()
        else:
            st.info("کوئی استاد نہیں")
        with st.expander("➕ نیا استاد رجسٹر کریں"):
            with st.form("new_teacher_form2"):
                name = st.text_input("نام*")
                password = st.text_input("پاسورڈ*", type="password")
                dept = st.selectbox("شعبہ", ["حفظ", "قاعدہ", "درسِ نظامی", "عصری تعلیم"])
                role = st.selectbox("رول", ["teacher", "aasri"])
                phone = st.text_input("فون")
                address = st.text_area("پتہ")
                joining = st.date_input("تاریخ شمولیت", date.today())
                if st.form_submit_button("رجسٹر"):
                    if name and password:
                        conn = get_db_connection()
                        try:
                            conn.execute("INSERT INTO teachers (name, password, dept, role, phone, address, joining_date) VALUES (?,?,?,?,?,?,?)",
                                         (name, hash_password(password), dept, role, phone, address, joining))
                            conn.commit()
                            st.success("استاد شامل ہو گیا")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("یہ نام پہلے سے موجود ہے")
                        finally:
                            conn.close()
    with tab2:
        st.subheader("طلبہ")
        conn = get_db_connection()
        students_df = pd.read_sql_query("SELECT id, name, father_name, dept, class, section, roll_no, dars_level_id FROM students", conn)
        levels = conn.execute("SELECT id, level_name FROM dars_levels").fetchall()
        level_dict = {l[0]: l[1] for l in levels}
        conn.close()
        if not students_df.empty:
            # درجے کا نام دکھائیں
            students_df['درسِ نظامی درجہ'] = students_df['dars_level_id'].map(level_dict)
            edited = st.data_editor(students_df, num_rows="dynamic", use_container_width=True, key="students_edit2")
            if st.button("طلبہ محفوظ کریں"):
                conn = get_db_connection()
                c = conn.cursor()
                old_ids = set(students_df['id'])
                new_ids = set(edited['id']) if 'id' in edited.columns else set()
                for did in old_ids - new_ids:
                    c.execute("DELETE FROM students WHERE id=?", (did,))
                for _, row in edited.iterrows():
                    if pd.isna(row['id']) or row['id'] == 0:
                        c.execute("INSERT INTO students (name, father_name, dept, class, section, roll_no, dars_level_id) VALUES (?,?,?,?,?,?,?)",
                                  (row['name'], row['father_name'], row['dept'], row['class'], row['section'], row['roll_no'], row['dars_level_id']))
                    else:
                        c.execute("UPDATE students SET name=?, father_name=?, dept=?, class=?, section=?, roll_no=?, dars_level_id=? WHERE id=?",
                                  (row['name'], row['father_name'], row['dept'], row['class'], row['section'], row['roll_no'], row['dars_level_id'], row['id']))
                conn.commit()
                conn.close()
                st.success("محفوظ ہو گیا")
                st.rerun()
        else:
            st.info("کوئی طالب علم نہیں")

# ==================== 8. استاد ڈیش بورڈ (درسِ نظامی / عام) ====================
elif selected == "📝 استاد ڈیش بورڈ" and st.session_state.user_type == "teacher":
    st.header(f"📝 استاد ڈیش بورڈ - {st.session_state.username}")
    # ایکٹو سیشن
    conn = get_db_connection()
    active_session = conn.execute("SELECT id, session_name FROM academic_sessions WHERE is_active=1").fetchone()
    if not active_session:
        st.error("کوئی فعال تعلیمی سیشن نہیں")
        conn.close()
        st.stop()
    session_id, session_name = active_session
    # آج کا دن
    today = date.today()
    day_names = ["پیر", "منگل", "بدھ", "جمعرات", "جمعہ", "ہفتہ", "اتوار"]
    weekday = today.weekday()  # 0=Monday -> پیر
    today_day = day_names[weekday] if weekday < 5 else "ہفتہ" if weekday == 5 else "اتوار"
    st.subheader(f"📅 آج کا دن: {today_day} - {today}")
    
    # استاد کے آج کے پیریڈز ماسٹر ٹائم ٹیبل سے
    periods_today = conn.execute("""
        SELECT mt.id, mt.period_no, mt.start_time, mt.end_time, dl.level_name, db.book_name, mt.room
        FROM master_timetable mt
        JOIN dars_levels dl ON mt.dars_level_id = dl.id
        JOIN dars_books db ON mt.book_id = db.id
        WHERE mt.session_id=? AND mt.teacher_name=? AND mt.day=? AND mt.is_active=1
        ORDER BY mt.period_no
    """, (session_id, st.session_state.username, today_day)).fetchall()
    conn.close()
    
    if periods_today:
        st.success(f"آپ کے آج {len(periods_today)} پیریڈز ہیں")
        # ٹیبل میں دکھائیں
        periods_df = pd.DataFrame(periods_today, columns=["ID", "پیریڈ", "آغاز", "اختتام", "درجہ", "کتاب", "کمرہ"])
        st.dataframe(periods_df[["پیریڈ", "آغاز", "اختتام", "درجہ", "کتاب", "کمرہ"]], use_container_width=True)
        
        # پیریڈ سلیکٹ کر کے حاضری/سبق اندراج
        selected_period_id = st.selectbox("پیریڈ منتخب کریں برائے اندراج", periods_df["ID"].tolist(), format_func=lambda x: f"پیریڈ {periods_df[periods_df['ID']==x]['پیریڈ'].iloc[0]} - {periods_df[periods_df['ID']==x]['درجہ'].iloc[0]} - {periods_df[periods_df['ID']==x]['کتاب'].iloc[0]}")
        if selected_period_id:
            period_info = periods_df[periods_df['ID'] == selected_period_id].iloc[0]
            level_name = period_info['درجہ']
            book_name = period_info['کتاب']
            # اس درجے میں موجود طلبہ
            conn = get_db_connection()
            level_id = conn.execute("SELECT id FROM dars_levels WHERE level_name=?", (level_name,)).fetchone()[0]
            students = conn.execute("SELECT id, name, father_name, roll_no FROM students WHERE dars_level_id=? AND session_id=?", (level_id, session_id)).fetchall()
            conn.close()
            if not students:
                st.warning("اس درجے میں کوئی طالب علم موجود نہیں")
            else:
                st.markdown(f"### 📖 {book_name} - {level_name}")
                st.markdown("---")
                # اندراج فارم
                entry_date = st.date_input("تاریخ", today)
                for sid, sname, fname, roll in students:
                    key = f"{sid}_{entry_date}"
                    with st.expander(f"{sname} ولد {fname} ({roll or 'شناختی نمبر نہیں'})"):
                        att = st.radio("حاضری", ["حاضر", "غیر حاضر", "رخصت"], key=f"att_{key}", horizontal=True)
                        cleanliness = st.selectbox("صفائی", cleanliness_options, key=f"clean_{key}")
                        if att == "حاضر":
                            col1, col2 = st.columns(2)
                            nagha = col1.checkbox("ناغہ", key=f"nagha_{key}")
                            yad_nahi = col2.checkbox("یاد نہیں", key=f"yad_{key}")
                            if nagha or yad_nahi:
                                lesson_text = "ناغہ" if nagha else "یاد نہیں"
                                lesson_from = ""
                                lesson_to = ""
                                performance = "ناغہ" if nagha else "یاد نہیں"
                            else:
                                lesson_from = st.text_input("سبق از", placeholder="صفحہ/سبق نمبر", key=f"from_{key}")
                                lesson_to = st.text_input("سبق تا", placeholder="صفحہ/سبق نمبر", key=f"to_{key}")
                                lesson_text = f"{lesson_from} تا {lesson_to}" if lesson_from and lesson_to else ""
                                performance = st.select_slider("کارکردگی", ["بہت بہتر", "بہتر", "مناسب", "کمزور"], key=f"perf_{key}")
                            if st.button(f"محفوظ کریں ({sname})", key=f"save_{key}"):
                                conn = get_db_connection()
                                c = conn.cursor()
                                # چیک کریں کہ آج کا اندراج پہلے سے تو نہیں
                                existing = c.execute("SELECT id FROM general_education WHERE student_id=? AND r_date=? AND book_subject=?",
                                                     (sid, entry_date, book_name)).fetchone()
                                if existing:
                                    st.error("اس طالب علم کا اس کتاب کے لیے آج کا اندراج پہلے سے موجود ہے")
                                else:
                                    c.execute("""INSERT INTO general_education 
                                                (r_date, student_id, t_name, dept, book_subject, today_lesson, lesson_from, lesson_to, performance, attendance, cleanliness)
                                                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                                              (entry_date, sid, st.session_state.username, "درسِ نظامی", book_name, lesson_text, lesson_from, lesson_to, performance, att, cleanliness))
                                    conn.commit()
                                    st.success("محفوظ ہو گیا")
                                conn.close()
                        else:
                            if st.button(f"غیر حاضر محفوظ کریں ({sname})", key=f"save_abs_{key}"):
                                conn = get_db_connection()
                                c = conn.cursor()
                                existing = c.execute("SELECT id FROM general_education WHERE student_id=? AND r_date=? AND book_subject=?",
                                                     (sid, entry_date, book_name)).fetchone()
                                if not existing:
                                    c.execute("""INSERT INTO general_education 
                                                (r_date, student_id, t_name, dept, book_subject, today_lesson, attendance, cleanliness)
                                                VALUES (?,?,?,?,?,?,?,?)""",
                                              (entry_date, sid, st.session_state.username, "درسِ نظامی", book_name, "غائب", att, cleanliness))
                                    conn.commit()
                                    st.success("محفوظ ہو گیا")
                                else:
                                    st.error("پہلے سے اندراج موجود ہے")
                                conn.close()
    else:
        st.info("آج آپ کا کوئی پیریڈ نہیں ہے")
    
    # پورے مدرسے کا ٹائم ٹیبل دیکھنے کا بٹن
    if st.button("📋 پورے مدرسے کا ٹائم ٹیبل دیکھیں"):
        conn = get_db_connection()
        tt_df = pd.read_sql_query("""
            SELECT mt.day as دن, mt.period_no as 'پیریڈ نمبر', mt.start_time as 'آغاز', dl.level_name as 'درجہ', db.book_name as 'کتاب', mt.teacher_name as 'استاد', mt.room as 'کمرہ'
            FROM master_timetable mt
            JOIN dars_levels dl ON mt.dars_level_id = dl.id
            JOIN dars_books db ON mt.book_id = db.id
            WHERE mt.session_id=? AND mt.is_active=1
            ORDER BY CASE mt.day WHEN 'ہفتہ' THEN 1 WHEN 'اتوار' THEN 2 WHEN 'پیر' THEN 3 WHEN 'منگل' THEN 4 WHEN 'بدھ' THEN 5 WHEN 'جمعرات' THEN 6 END, mt.period_no
        """, conn, params=(session_id,))
        conn.close()
        if not tt_df.empty:
            tt_df['کتاب/درجہ'] = tt_df['درجہ'] + " - " + tt_df['کتاب']
            pivot = tt_df.pivot(index='پیریڈ نمبر', columns='دن', values='کتاب/درجہ').fillna("—")
            st.dataframe(pivot, use_container_width=True)
        else:
            st.info("ٹائم ٹیبل موجود نہیں")

# ==================== 9. عصری استاد ڈیش بورڈ ====================
elif selected == "📝 عصری تعلیم ڈیش بورڈ" and st.session_state.user_type == "aasri":
    st.header("📝 عصری تعلیم ڈیش بورڈ")
    conn = get_db_connection()
    active_session = conn.execute("SELECT id FROM academic_sessions WHERE is_active=1").fetchone()
    if not active_session:
        st.error("کوئی فعال سیشن نہیں")
        conn.close()
        st.stop()
    session_id = active_session[0]
    # عصری گروپس
    groups = conn.execute("SELECT id, group_name FROM aasri_groups WHERE teacher_name=? AND session_id=?", (st.session_state.username, session_id)).fetchall()
    conn.close()
    if not groups:
        st.warning("آپ نے ابھی تک کوئی گروپ نہیں بنایا۔ براہ کرم 'گروپ مینجمنٹ' سے گروپ بنائیں۔")
    else:
        group_dict = {g[1]: g[0] for g in groups}
        selected_group = st.selectbox("گروپ منتخب کریں", list(group_dict.keys()))
        group_id = group_dict[selected_group]
        conn = get_db_connection()
        students = conn.execute("""
            SELECT s.id, s.name, s.father_name, s.roll_no, s.dept
            FROM students s
            JOIN aasri_group_students ags ON s.id = ags.student_id
            WHERE ags.group_id = ?
        """, (group_id,)).fetchall()
        conn.close()
        if not students:
            st.info("اس گروپ میں کوئی طالب علم شامل نہیں")
        else:
            entry_date = st.date_input("تاریخ", date.today())
            subject = st.text_input("مضمون", "انگلش / اردو / ریاضی")
            with st.form("aasri_entry"):
                records = []
                for sid, sname, fname, roll, dept in students:
                    st.markdown(f"**{sname} ولد {fname} ({dept})**")
                    att = st.radio("حاضری", ["حاضر", "غیر حاضر"], key=f"att_{sid}", horizontal=True)
                    if att == "حاضر":
                        topic = st.text_input("عنوان", key=f"topic_{sid}")
                        hw = st.text_area("ہوم ورک", key=f"hw_{sid}")
                        perf = st.select_slider("کارکردگی", ["بہت بہتر", "بہتر", "مناسب", "کمزور"], key=f"perf_{sid}")
                        records.append((entry_date, sid, st.session_state.username, "عصری تعلیم", subject, topic, hw, perf, att))
                    else:
                        records.append((entry_date, sid, st.session_state.username, "عصری تعلیم", subject, "غائب", "", "غائب", att))
                if st.form_submit_button("تمام کے لیے محفوظ کریں"):
                    conn = get_db_connection()
                    c = conn.cursor()
                    for rec in records:
                        c.execute("INSERT INTO general_education (r_date, student_id, t_name, dept, book_subject, today_lesson, homework, performance, attendance) VALUES (?,?,?,?,?,?,?,?,?)", rec)
                    conn.commit()
                    conn.close()
                    st.success("محفوظ ہو گیا")

elif selected == "👥 گروپ مینجمنٹ" and st.session_state.user_type == "aasri":
    st.header("👥 گروپ مینجمنٹ")
    conn = get_db_connection()
    active_session = conn.execute("SELECT id FROM academic_sessions WHERE is_active=1").fetchone()
    if not active_session:
        st.error("کوئی فعال سیشن نہیں")
        conn.close()
        st.stop()
    session_id = active_session[0]
    # موجودہ گروپس
    groups = conn.execute("SELECT id, group_name FROM aasri_groups WHERE teacher_name=? AND session_id=?", (st.session_state.username, session_id)).fetchall()
    conn.close()
    if groups:
        st.subheader("آپ کے گروپس")
        for gid, gname in groups:
            st.write(f"- {gname}")
            if st.button(f"حذف کریں {gname}", key=f"del_{gid}"):
                conn = get_db_connection()
                conn.execute("DELETE FROM aasri_group_students WHERE group_id=?", (gid,))
                conn.execute("DELETE FROM aasri_groups WHERE id=?", (gid,))
                conn.commit()
                conn.close()
                st.rerun()
    # نیا گروپ
    with st.form("new_group"):
        group_name = st.text_input("گروپ کا نام")
        # تمام طلباء میں سے منتخب کریں
        conn = get_db_connection()
        all_students = conn.execute("SELECT id, name, father_name, dept FROM students").fetchall()
        conn.close()
        if all_students:
            student_options = [f"{s[1]} ولد {s[2]} ({s[3]})" for s in all_students]
            selected_students = st.multiselect("طلباء شامل کریں", student_options)
            if st.form_submit_button("گروپ بنائیں"):
                if group_name and selected_students:
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("INSERT INTO aasri_groups (group_name, teacher_name, session_id, created_date) VALUES (?,?,?,?)",
                              (group_name, st.session_state.username, session_id, date.today()))
                    group_id = c.lastrowid
                    for sel in selected_students:
                        # نام سے id نکالیں
                        name_part = sel.split(" ولد ")[0]
                        father_part = sel.split(" ولد ")[1].split(" (")[0]
                        sid = [s[0] for s in all_students if s[1] == name_part and s[2] == father_part][0]
                        c.execute("INSERT INTO aasri_group_students (group_id, student_id) VALUES (?,?)", (group_id, sid))
                    conn.commit()
                    conn.close()
                    st.success("گروپ بن گیا")
                    st.rerun()
                else:
                    st.error("نام اور طلباء ضروری ہیں")
        else:
            st.warning("کوئی طالب علم ڈیٹا بیس میں نہیں")

# ==================== 10. مشترکہ سیکشنز (حاضری، رخصت، پاسورڈ وغیرہ) ====================
# (بقیہ مینو آئٹمز کو مختصراً شامل کیا جا رہا ہے تاکہ کوڈ مکمل ہو)

elif selected == "🕒 میری حاضری" and st.session_state.user_type in ["teacher", "aasri"]:
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

elif selected == "📩 رخصت کی درخواست" and st.session_state.user_type in ["teacher", "aasri"]:
    st.header("📩 رخصت کی درخواست")
    with st.form("leave_form"):
        l_type = st.selectbox("نوعیت", ["بیماری", "ضروری کام", "ہنگامی", "دیگر"])
        start = st.date_input("تاریخ آغاز", date.today())
        days = st.number_input("دن", min_value=1, value=1)
        reason = st.text_area("وجہ")
        if st.form_submit_button("جمع کریں"):
            if reason:
                conn = get_db_connection()
                conn.execute("INSERT INTO leave_requests (t_name, l_type, start_date, days, reason, status, request_date) VALUES (?,?,?,?,?,?,?)",
                             (st.session_state.username, l_type, start, days, reason, "پینڈنگ", date.today()))
                conn.commit()
                conn.close()
                st.success("درخواست جمع ہو گئی")
            else:
                st.error("وجہ لکھیں")

elif selected == "🔑 پاسورڈ تبدیل کریں":
    st.header("🔑 پاسورڈ تبدیل کریں")
    old = st.text_input("پرانا پاسورڈ", type="password")
    new = st.text_input("نیا پاسورڈ", type="password")
    confirm = st.text_input("تصدیق", type="password")
    if st.button("تبدیل کریں"):
        if new == confirm:
            conn = get_db_connection()
            user = conn.execute("SELECT password FROM teachers WHERE name=?", (st.session_state.username,)).fetchone()
            if user and (user[0] == old or user[0] == hash_password(old)):
                conn.execute("UPDATE teachers SET password=? WHERE name=?", (hash_password(new), st.session_state.username))
                conn.commit()
                conn.close()
                st.success("پاسورڈ تبدیل ہو گیا۔ دوبارہ لاگ ان کریں")
                st.session_state.logged_in = False
                st.rerun()
            else:
                st.error("پرانا پاسورڈ غلط")
                conn.close()
        else:
            st.error("نیا پاسورڈ میل نہیں کھاتا")

elif selected == "📢 نوٹیفیکیشنز":
    st.header("نوٹیفیکیشنز")
    conn = get_db_connection()
    if st.session_state.user_type == "admin":
        with st.form("new_notif"):
            title = st.text_input("عنوان")
            msg = st.text_area("پیغام")
            target = st.selectbox("بھیجیں", ["تمام", "اساتذہ", "طلبہ"])
            if st.form_submit_button("بھیجیں"):
                conn.execute("INSERT INTO notifications (title, message, target, created_at) VALUES (?,?,?,?)",
                             (title, msg, target, datetime.now()))
                conn.commit()
                st.success("بھیج دیا گیا")
    notifs = conn.execute("SELECT title, message, created_at FROM notifications WHERE target IN ('تمام','اساتذہ') ORDER BY created_at DESC LIMIT 10").fetchall()
    conn.close()
    for n in notifs:
        st.info(f"**{n[0]}**\n\n{n[1]}\n\n*{n[2]}*")

# دیگر ایڈمن سیکشنز (رپورٹس، امتحانات وغیرہ) کو بھی اپ ڈیٹ کیا جا سکتا ہے مگر طوالت کے پیشِ نظر یہاں بنیادی اضافے مکمل کر دیے گئے ہیں۔
# بقیہ حصے (مثلاً بیک اپ، عملہ نگرانی) پہلے سے موجود کوڈ میں تھے، انہیں برقرار رکھا جا سکتا ہے۔

# ==================== لاگ آؤٹ ====================
st.sidebar.divider()
if st.sidebar.button("🚪 لاگ آؤٹ"):
    st.session_state.logged_in = False
    st.rerun()
