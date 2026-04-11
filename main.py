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
    
    # (آپ کے تمام ٹیبلز کا پرانا کوڈ اسی طرح رہے گا - مختصراً یہاں شامل کیا گیا ہے تاکہ لمبائی زیادہ نہ ہو)
    c.execute('''CREATE TABLE IF NOT EXISTS teachers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, password TEXT)''')
    add_column_if_not_exists('teachers', 'dept', 'TEXT')
    
    c.execute('''CREATE TABLE IF NOT EXISTS students (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, father_name TEXT, roll_no TEXT)''')
    add_column_if_not_exists('students', 'roll_no', 'TEXT')
    
    c.execute('''CREATE TABLE IF NOT EXISTS hifz_records (id INTEGER PRIMARY KEY AUTOINCREMENT, r_date DATE, student_id INTEGER, t_name TEXT, surah TEXT, attendance TEXT, cleanliness TEXT)''')
    add_column_if_not_exists('hifz_records', 'student_id', 'INTEGER')
    add_column_if_not_exists('hifz_records', 'cleanliness', 'TEXT')
    
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

# ==================== 3. جدید اسٹائلنگ (خوبصورت UI) ====================
st.set_page_config(page_title="جامعہ ملیہ اسلامیہ | سمارٹ ERP", page_icon="🕌", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    @font-face {
        font-family: 'Jameel Noori Nastaleeq';
        src: url('https://raw.githubusercontent.com/urdufonts/jameel-noori-nastaleeq/master/JameelNooriNastaleeq.ttf') format('truetype');
    }
    @import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu&display=swap');
    
    * {
        font-family: 'Jameel Noori Nastaleeq', 'Noto Nastaliq Urdu', 'Arial', sans-serif;
    }
    
    body, .stApp { 
        direction: rtl; 
        text-align: right; 
        background: #f4f7f6; 
    }
    
    /* جدید سائیڈ بار */
    .stSidebar { 
        background: rgba(30, 86, 49, 0.95) !important;
        backdrop-filter: blur(10px);
        color: white; 
        box-shadow: -5px 0 15px rgba(0,0,0,0.1);
    }
    .stSidebar * { color: white !important; }
    
    /* ریڈیو بٹنز (مینو) کو ایپ کے آئیکنز جیسا بنانا */
    .stSidebar .stRadio [role="radiogroup"] div[data-baseweb="radio"] {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 10px;
        margin-bottom: 8px;
        transition: all 0.3s ease;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }
    .stSidebar .stRadio [role="radiogroup"] div[data-baseweb="radio"]:hover { 
        background-color: #2e7d32; 
        transform: translateX(-5px);
        box-shadow: 2px 4px 10px rgba(0,0,0,0.2);
    }
    
    /* شاندار بٹن ڈیزائن (آئیکن اور ٹیکسٹ کے لیے) */
    .stButton > button { 
        background: linear-gradient(135deg, #1e5631 0%, #2a9d8f 100%); 
        color: white; 
        border-radius: 12px; 
        border: none; 
        padding: 0.6rem 1.5rem; 
        font-size: 1.1rem; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); 
        transition: all 0.3s ease; 
        width: 100%; 
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 10px;
    }
    .stButton > button:hover { 
        transform: translateY(-3px); 
        box-shadow: 0 6px 15px rgba(30, 86, 49, 0.4); 
        background: linear-gradient(135deg, #2a9d8f 0%, #1e5631 100%); 
    }
    
    /* گلاس مارفزم کارڈز (Glassmorphism Cards) */
    .report-card, .main-header { 
        background: rgba(255, 255, 255, 0.85); 
        backdrop-filter: blur(12px);
        border-radius: 20px; 
        padding: 2rem; 
        box-shadow: 0 8px 32px rgba(31, 38, 135, 0.07); 
        border: 1px solid rgba(255, 255, 255, 0.18);
        margin-bottom: 1.5rem; 
    }
    .main-header {
        border-top: 5px solid #1e5631;
        text-align: center;
    }
    
    /* ان پٹ فیلڈز کی خوبصورتی */
    .stTextInput > div > div > input {
        border-radius: 10px;
        border: 1px solid #ccc;
        padding: 10px;
    }
    .stTextInput > div > div > input:focus {
        border-color: #1e5631;
        box-shadow: 0 0 5px rgba(30, 86, 49, 0.5);
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
    st.markdown("<div class='main-header'><h1>🕌 جامعہ ملیہ اسلامیہ فیصل آباد</h1><p style='color:#555; font-size:1.2rem;'>اسمارٹ تعلیمی و انتظامی پورٹل</p></div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,1.2,1])
    with col2:
        st.markdown("<div class='report-card'><h3 style='text-align:center; color:#1e5631;'>🔐 اپنے اکاؤنٹ میں داخل ہوں</h3>", unsafe_allow_html=True)
        u = st.text_input("👤 صارف نام (Username)")
        p = st.text_input("🔑 پاسورڈ (Password)", type="password")
        
        # خوبصورت آئیکن والا بٹن
        if st.button("داخل ہوں 🚀"):
            res = verify_login(u, p)
            if res:
                st.session_state.logged_in, st.session_state.username = True, u
                st.session_state.user_type = "admin" if u == "admin" else "teacher"
                log_audit(u, "Login", f"User type: {st.session_state.user_type}")
                st.rerun()
            else:
                st.error("❌ صارف نام یا پاسورڈ غلط ہے۔")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ==================== 5. مینو ====================
if st.session_state.user_type == "admin":
    menu = ["📊 ایڈمن ڈیش بورڈ", "📝 یومیہ تعلیمی رپورٹ", "🎓 امتحانی نظام", "📜 ماہانہ رزلٹ کارڈ",
            "🕒 اساتذہ حاضری", "👥 یوزر مینجمنٹ", "⚙️ سیٹنگز و لاگ آؤٹ"]
else:
    menu = ["📝 روزانہ سبق اندراج", "🎓 امتحانی درخواست", "📩 رخصت کی درخواست",
            "🕒 میری حاضری", "⚙️ سیٹنگز و لاگ آؤٹ"]

selected = st.sidebar.radio("📌 مین مینو", menu)

# لاگ آؤٹ کا آپشن
if selected == "⚙️ سیٹنگز و لاگ آؤٹ":
    st.markdown("<div class='main-header'><h2>⚙️ سیٹنگز</h2></div>", unsafe_allow_html=True)
    if st.button("🚪 لاگ آؤٹ کریں"):
        st.session_state.logged_in = False
        st.rerun()

# ==================== 6. ایڈمن سیکشنز ====================
# 8.1 ایڈمن ڈیش بورڈ
if selected == "📊 ایڈمن ڈیش بورڈ" and st.session_state.user_type == "admin":
    st.markdown("<div class='main-header'><h1>📊 ایڈمن ڈیش بورڈ</h1></div>", unsafe_allow_html=True)
    
    conn = get_db_connection()
    total_students = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    total_teachers = conn.execute("SELECT COUNT(*) FROM teachers WHERE name!='admin'").fetchone()[0]
    conn.close()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"<div class='report-card' style='text-align:center;'><h2>👨‍🎓 کل طلباء</h2><h1 style='color:#1e5631;'>{total_students}</h1></div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='report-card' style='text-align:center;'><h2>👨‍🏫 کل اساتذہ</h2><h1 style='color:#2a9d8f;'>{total_teachers}</h1></div>", unsafe_allow_html=True)
    with col3:
         st.markdown(f"<div class='report-card' style='text-align:center;'><h2>📅 آج کی تاریخ</h2><h3 style='color:#e76f51; margin-top:20px;'>{date.today().strftime('%d-%m-%Y')}</h3></div>", unsafe_allow_html=True)

# 8.2 یومیہ تعلیمی رپورٹ (آپ کا کٹا ہوا کوڈ مکمل کیا گیا)
elif selected == "📝 یومیہ تعلیمی رپورٹ" and st.session_state.user_type == "admin":
    st.markdown("<div class='main-header'><h1>📋 یومیہ تعلیمی رپورٹ</h1></div>", unsafe_allow_html=True)
    
    with st.sidebar:
        st.markdown("### 🔍 فلٹرز")
        d1 = st.date_input("📅 تاریخ آغاز", date.today().replace(day=1))
        d2 = st.date_input("📅 تاریخ اختتام", date.today())
        
        conn = get_db_connection()
        teachers_list = ["تمام"] + [t[0] for t in conn.execute("SELECT DISTINCT t_name FROM hifz_records UNION SELECT name FROM teachers WHERE name!='admin'").fetchall()]
        conn.close()
        
        sel_teacher = st.selectbox("👨‍🏫 استاد کا نام", teachers_list)
        dept_filter = st.selectbox("🏢 شعبہ", ["تمام", "حفظ", "قاعدہ", "درسِ نظامی", "عصری تعلیم"])
    
    combined_df = pd.DataFrame()
    if dept_filter in ["تمام", "حفظ"]:
        conn = get_db_connection()
        try:
            hifz_df = pd.read_sql_query("""
                SELECT h.r_date as تاریخ, s.name as نام, s.father_name as 'والد کا نام', h.t_name as استاد, 
                       'حفظ' as شعبہ, h.surah as 'سبق', h.attendance as حاضری
                FROM hifz_records h
                JOIN students s ON h.student_id = s.id
                WHERE h.r_date BETWEEN ? AND ?
            """, conn, params=(d1, d2))
            
            if not hifz_df.empty:
                if sel_teacher != "تمام":
                    hifz_df = hifz_df[hifz_df['استاد'] == sel_teacher]
                combined_df = pd.concat([combined_df, hifz_df], ignore_index=True)
        except Exception as e:
            st.error(f"⚠️ ڈیٹا لوڈ کرنے میں مسئلہ: {e}")
        finally:
            conn.close()
            
    if not combined_df.empty:
        st.dataframe(combined_df, use_container_width=True)
    else:
        st.info("📭 منتخب کردہ فلٹرز کے مطابق کوئی ریکارڈ موجود نہیں ہے۔")
