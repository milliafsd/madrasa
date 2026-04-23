import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import plotly.express as px
import os
import hashlib
import zipfile
import io
from supabase import create_client

# ==================== 1. Supabase سیٹ اپ ====================
SUPABASE_URL = st.secrets["connections"]["supabase"]["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["connections"]["supabase"]["SUPABASE_KEY"]

@st.cache_resource
def get_supabase_client():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase_client()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def ensure_admin():
    """پہلی بار ایڈمن اکاؤنٹ بنائیں اگر موجود نہ ہو"""
    try:
        res = supabase.table("teachers").select("id").eq("name", "admin").execute()
        if not res.data:
            supabase.table("teachers").insert({
                "name": "admin",
                "password": hash_password("jamia123"),
                "dept": "Admin"
            }).execute()
    except:
        pass

ensure_admin()

# ==================== 2. ہیلپر فنکشنز ====================
def log_audit(user, action, details=""):
    try:
        supabase.table("audit_log").insert({
            "user": user,
            "action": action,
            "timestamp": datetime.now().isoformat(),
            "details": details
        }).execute()
    except:
        pass

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

def flatten_join(data, join_key):
    """Supabase JOIN نتیجے کو flat بنائیں"""
    flat = []
    for row in data:
        r = {k: v for k, v in row.items() if k != join_key}
        if row.get(join_key):
            r.update(row[join_key])
        flat.append(r)
    return flat

def safe_str_date(val):
    """تاریخ کو string میں بدلیں"""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if isinstance(val, (date, datetime)):
        return val.strftime("%Y-%m-%d")
    return str(val) if val else None

# ==================== HTML جنریٹرز ====================
def generate_exam_result_card(exam_row):
    html = f"""
    <!DOCTYPE html>
    <html dir="rtl">
    <head><meta charset="UTF-8"><title>رزلٹ کارڈ - {exam_row.get('s_name','')}</title>
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
            <p><b>نام:</b> {exam_row.get('s_name','')} ولد {exam_row.get('f_name','')}</p>
            <p><b>شناختی نمبر:</b> {exam_row.get('roll_no', '')}</p>
            <p><b>امتحان کی قسم:</b> {exam_row.get('exam_type','')}</p>
            {f"<p><b>پارہ:</b> {exam_row.get('from_para')} تا {exam_row.get('to_para')}</p>" if exam_row.get('from_para') else ""}
            {f"<p><b>کتاب:</b> {exam_row.get('book_name', '')}</p>" if exam_row.get('book_name') else ""}
            {f"<p><b>مقدار خواندگی:</b> {exam_row.get('amount_read', '')}</p>" if exam_row.get('amount_read') else ""}
            <p><b>تاریخ:</b> {exam_row.get('start_date','')} تا {exam_row.get('end_date','')}</p>
            <p><b>کل دن:</b> {exam_row.get('total_days', '')}</p>
            <table>
                <tr><th>سوال</th><th>1</th><th>2</th><th>3</th><th>4</th><th>5</th><th>کل</th></tr>
                <tr>
                <td style="text-align:center">{exam_row.get('q1','')}</td>
                <td>{exam_row.get('q2','')}</td>
                <td>{exam_row.get('q3','')}</td>
                <td>{exam_row.get('q4','')}</td>
                <td>{exam_row.get('q5','')}</td>
                <td>{exam_row.get('total','')}</td>
                </tr>
            </table>
            <p><b>گریڈ:</b> {exam_row.get('grade','')}</p>
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
    .best-student-card {
        background: linear-gradient(135deg, #fff9e6, #ffe6b3);
        border-radius: 20px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 8px 16px rgba(0,0,0,0.1);
        transition: 0.3s;
    }
    .best-student-card:hover { transform: translateY(-5px); }
    .gold { color: #d4af37; }
    .silver { color: #a0a0a0; }
    .bronze { color: #cd7f32; }
    @media (max-width: 768px) {
        .stButton > button { padding: 0.4rem 0.8rem; font-size: 0.8rem; }
        .main-header h1 { font-size: 1.5rem; }
    }
</style>
""", unsafe_allow_html=True)

# ==================== 4. لاگ ان ====================
def verify_login(username, password):
    try:
        res = supabase.table("teachers").select("*").eq("name", username).execute()
        if res.data:
            row = res.data[0]
            stored = row["password"]
            if stored == password or stored == hash_password(password):
                return row
    except:
        pass
    return None

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<div class='main-header'><h1>🕌 جامعہ ملیہ اسلامیہ فیصل آباد</h1><p>اسمارٹ تعلیمی و انتظامی پورٹل</p></div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
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
            "📢 نوٹیفیکیشنز", "📈 تجزیہ و رپورٹس", "🏆 ماہانہ بہترین طلباء", "🔄 ڈیٹا منتقلی", "⚙️ بیک اپ & سیٹنگز"]
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
cleanliness_options = ["بہترین", "بہتر", "ناقص"]

# ==================== 7. پاسورڈ فنکشنز ====================
def verify_password(user, plain_password):
    try:
        res = supabase.table("teachers").select("password").eq("name", user).execute()
        if not res.data:
            return False
        stored = res.data[0]["password"]
        if stored == plain_password or stored == hash_password(plain_password):
            return True
    except:
        pass
    return False

def change_password(user, old_pass, new_pass):
    if not verify_password(user, old_pass):
        return False
    new_hash = hash_password(new_pass)
    supabase.table("teachers").update({"password": new_hash}).eq("name", user).execute()
    log_audit(user, "Password Changed", "Success")
    return True

def admin_reset_password(teacher_name, new_pass):
    new_hash = hash_password(new_pass)
    supabase.table("teachers").update({"password": new_hash}).eq("name", teacher_name).execute()
    log_audit(st.session_state.username, "Admin Reset Password", f"Teacher: {teacher_name}")

# ==================== 8. ایڈمن سیکشنز ====================

# 8.1 ایڈمن ڈیش بورڈ
if selected == "📊 ایڈمن ڈیش بورڈ" and st.session_state.user_type == "admin":
    st.markdown("<div class='main-header'><h1>📊 ایڈمن ڈیش بورڈ</h1></div>", unsafe_allow_html=True)
    try:
        res_s = supabase.table("students").select("id", count="exact").execute()
        res_t = supabase.table("teachers").select("id", count="exact").neq("name", "admin").execute()
        total_students = res_s.count or 0
        total_teachers = res_t.count or 0
    except:
        total_students = 0
        total_teachers = 0
    col1, col2 = st.columns(2)
    col1.metric("کل طلباء", total_students)
    col2.metric("کل اساتذہ", total_teachers)

# 8.2 یومیہ تعلیمی رپورٹ
elif selected == "📊 یومیہ تعلیمی رپورٹ" and st.session_state.user_type == "admin":
    st.header("📊 یومیہ تعلیمی رپورٹ - صرف دیکھیں")
    with st.sidebar:
        d1 = st.date_input("تاریخ آغاز", date.today().replace(day=1))
        d2 = st.date_input("تاریخ اختتام", date.today())
        try:
            r1 = supabase.table("hifz_records").select("t_name").execute()
            r2 = supabase.table("teachers").select("name").neq("name", "admin").execute()
            t_set = set([r["t_name"] for r in r1.data if r.get("t_name")] +
                        [r["name"] for r in r2.data])
            teachers_list = ["تمام"] + sorted(t_set)
        except:
            teachers_list = ["تمام"]
        sel_teacher = st.selectbox("استاد / کلاس", teachers_list)
        dept_filter = st.selectbox("شعبہ", ["تمام", "حفظ", "قاعدہ", "درسِ نظامی", "عصری تعلیم"])

    combined_df = pd.DataFrame()

    if dept_filter in ["تمام", "حفظ"]:
        try:
            q = supabase.table("hifz_records").select(
                "r_date, t_name, surah, lines, sq_p, sq_m, sq_a, m_p, m_m, m_a, attendance, cleanliness, students(name, father_name, roll_no)"
            ).gte("r_date", str(d1)).lte("r_date", str(d2))
            if sel_teacher != "تمام":
                q = q.eq("t_name", sel_teacher)
            res = q.execute()
            if res.data:
                flat = flatten_join(res.data, "students")
                hifz_df = pd.DataFrame(flat)
                hifz_df = hifz_df.rename(columns={
                    "r_date": "تاریخ", "name": "نام", "father_name": "والد کا نام",
                    "roll_no": "شناختی نمبر", "t_name": "استاد",
                    "surah": "سبق", "lines": "کل ستر", "sq_p": "سبقی", "sq_m": "سبقی (غلطی)",
                    "sq_a": "سبقی (اٹکن)", "m_p": "منزل", "m_m": "منزل (غلطی)",
                    "m_a": "منزل (اٹکن)", "attendance": "حاضری", "cleanliness": "صفائی"
                })
                hifz_df["شعبہ"] = "حفظ"
                combined_df = pd.concat([combined_df, hifz_df], ignore_index=True)
        except Exception as e:
            st.error(f"حفظ کے ریکارڈ لوڈ کرتے وقت خرابی: {str(e)}")

    if dept_filter in ["تمام", "قاعدہ"]:
        try:
            q = supabase.table("qaida_records").select(
                "r_date, t_name, lesson_no, total_lines, details, attendance, cleanliness, students(name, father_name, roll_no)"
            ).gte("r_date", str(d1)).lte("r_date", str(d2))
            if sel_teacher != "تمام":
                q = q.eq("t_name", sel_teacher)
            res = q.execute()
            if res.data:
                flat = flatten_join(res.data, "students")
                qaida_df = pd.DataFrame(flat)
                qaida_df = qaida_df.rename(columns={
                    "r_date": "تاریخ", "name": "نام", "father_name": "والد کا نام",
                    "roll_no": "شناختی نمبر", "t_name": "استاد",
                    "lesson_no": "تختی نمبر", "total_lines": "کل لائنیں",
                    "details": "تفصیل", "attendance": "حاضری", "cleanliness": "صفائی"
                })
                qaida_df["شعبہ"] = "قاعدہ"
                combined_df = pd.concat([combined_df, qaida_df], ignore_index=True)
        except Exception as e:
            st.error(f"قاعدہ کے ریکارڈ لوڈ کرتے وقت خرابی: {str(e)}")

    if dept_filter in ["تمام", "درسِ نظامی", "عصری تعلیم"]:
        try:
            q = supabase.table("general_education").select(
                "r_date, t_name, dept, book_subject, today_lesson, homework, performance, attendance, cleanliness, students(name, father_name, roll_no)"
            ).gte("r_date", str(d1)).lte("r_date", str(d2))
            if sel_teacher != "تمام":
                q = q.eq("t_name", sel_teacher)
            if dept_filter not in ["تمام", "درسِ نظامی", "عصری تعلیم"] or dept_filter in ["درسِ نظامی", "عصری تعلیم"]:
                if dept_filter != "تمام":
                    q = q.eq("dept", dept_filter)
            res = q.execute()
            if res.data:
                flat = flatten_join(res.data, "students")
                gen_df = pd.DataFrame(flat)
                gen_df = gen_df.rename(columns={
                    "r_date": "تاریخ", "name": "نام", "father_name": "والد کا نام",
                    "roll_no": "شناختی نمبر", "t_name": "استاد",
                    "dept": "شعبہ", "book_subject": "کتاب/مضمون",
                    "today_lesson": "آج کا سبق", "homework": "ہوم ورک",
                    "performance": "کارکردگی", "attendance": "حاضری", "cleanliness": "صفائی"
                })
                combined_df = pd.concat([combined_df, gen_df], ignore_index=True)
        except Exception as e:
            st.error(f"عمومی تعلیم کے ریکارڈ لوڈ کرتے وقت خرابی: {str(e)}")

    if combined_df.empty:
        st.warning("کوئی ریکارڈ نہیں ملا")
    else:
        st.success(f"کل {len(combined_df)} ریکارڈ ملے")
        st.dataframe(combined_df, use_container_width=True)
        html_report = generate_html_report(combined_df, "یومیہ تعلیمی رپورٹ",
                                           start_date=d1.strftime("%Y-%m-%d"), end_date=d2.strftime("%Y-%m-%d"))
        st.download_button("📥 HTML رپورٹ ڈاؤن لوڈ کریں", html_report, "daily_report.html", "text/html")
        if st.button("🖨️ پرنٹ کریں"):
            st.components.v1.html(f"<script>var w=window.open();w.document.write(`{html_report}`);w.print();</script>", height=0)

# 8.3 امتحانی نظام
elif selected == "🎓 امتحانی نظام" and st.session_state.user_type == "admin":
    st.header("🎓 امتحانی نظام")
    tab1, tab2 = st.tabs(["پینڈنگ امتحانات", "مکمل شدہ"])
    with tab1:
        try:
            res = supabase.table("exams").select(
                "id, dept, exam_type, from_para, to_para, book_name, amount_read, start_date, end_date, total_days, student_id, students(name, father_name, roll_no)"
            ).eq("status", "پینڈنگ").execute()
            pending = res.data
        except Exception as e:
            st.error(f"خرابی: {e}")
            pending = []
        if not pending:
            st.info("کوئی پینڈنگ امتحان نہیں")
        else:
            for exam in pending:
                eid = exam["id"]
                stud = exam.get("students") or {}
                sn = stud.get("name", "")
                fn = stud.get("father_name", "")
                rn = stud.get("roll_no", "")
                stud_id = exam["student_id"]
                dept = exam["dept"]
                etype = exam["exam_type"]
                fp = exam["from_para"] or 0
                tp = exam["to_para"] or 0
                book = exam["book_name"] or ""
                amount = exam["amount_read"] or ""
                sd = exam["start_date"]
                ed = exam["end_date"]
                tdays = exam["total_days"]
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
                    total = q1 + q2 + q3 + q4 + q5
                    if total >= 90: g = "ممتاز"
                    elif total >= 80: g = "جید جداً"
                    elif total >= 70: g = "جید"
                    elif total >= 60: g = "مقبول"
                    else: g = "ناکام"
                    st.write(f"کل: {total} | گریڈ: {g}")
                    if st.button("کلیئر کریں", key=f"save_{eid}"):
                        supabase.table("exams").update({
                            "q1": q1, "q2": q2, "q3": q3, "q4": q4, "q5": q5,
                            "total": total, "grade": g, "status": "مکمل",
                            "end_date": str(date.today())
                        }).eq("id", eid).execute()
                        if g != "ناکام":
                            if etype == "پارہ ٹیسٹ" and fp:
                                for para in range(int(fp), int(tp) + 1):
                                    chk = supabase.table("passed_paras").select("id").eq("student_id", stud_id).eq("para_no", para).execute()
                                    if not chk.data:
                                        supabase.table("passed_paras").insert({
                                            "student_id": stud_id, "para_no": para,
                                            "passed_date": str(date.today()),
                                            "exam_type": etype, "grade": g, "marks": total
                                        }).execute()
                            else:
                                chk = supabase.table("passed_paras").select("id").eq("student_id", stud_id).eq("book_name", book).execute()
                                if not chk.data:
                                    supabase.table("passed_paras").insert({
                                        "student_id": stud_id, "book_name": book,
                                        "passed_date": str(date.today()),
                                        "exam_type": etype, "grade": g, "marks": total
                                    }).execute()
                        st.success("امتحان کلیئر کر دیا گیا")
                        st.rerun()
    with tab2:
        try:
            res = supabase.table("exams").select(
                "dept, exam_type, from_para, to_para, book_name, amount_read, start_date, end_date, total, grade, students(name, father_name, roll_no)"
            ).eq("status", "مکمل").order("end_date", desc=True).execute()
            if res.data:
                flat = flatten_join(res.data, "students")
                hist = pd.DataFrame(flat)
                st.dataframe(hist, use_container_width=True)
                st.download_button("ہسٹری CSV", convert_df_to_csv(hist), "exam_history.csv")
            else:
                st.info("کوئی مکمل شدہ امتحان نہیں")
        except Exception as e:
            st.error(f"خرابی: {e}")

# 8.4 عملہ نگرانی و شکایات
elif selected == "📋 عملہ نگرانی و شکایات" and st.session_state.user_type == "admin":
    st.header("📋 عملہ نگرانی و شکایات")
    tab1, tab2 = st.tabs(["➕ نیا اندراج", "📜 ریکارڈ دیکھیں"])
    with tab1:
        with st.form("new_monitoring"):
            try:
                res = supabase.table("teachers").select("name").neq("name", "admin").execute()
                staff_list = [r["name"] for r in res.data]
            except:
                staff_list = []
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
                    supabase.table("staff_monitoring").insert({
                        "staff_name": staff_name,
                        "date": str(note_date),
                        "note_type": note_type,
                        "description": description,
                        "action_taken": action_taken,
                        "status": status,
                        "created_by": st.session_state.username,
                        "created_at": datetime.now().isoformat()
                    }).execute()
                    log_audit(st.session_state.username, "Staff Monitoring Added", f"{staff_name} - {note_type}")
                    st.success("اندراج محفوظ ہو گیا")
                    st.rerun()
    with tab2:
        st.subheader("فلٹرز")
        try:
            res = supabase.table("teachers").select("name").neq("name", "admin").execute()
            staff_names = ["تمام"] + [r["name"] for r in res.data]
        except:
            staff_names = ["تمام"]
        filter_staff = st.selectbox("عملہ فلٹر کریں", staff_names)
        filter_type = st.selectbox("نوعیت فلٹر کریں", ["تمام", "یادداشت", "شکایت", "تنبیہ", "تعریف", "کارکردگی جائزہ"])
        start_date = st.date_input("تاریخ از", date.today() - timedelta(days=30))
        end_date = st.date_input("تاریخ تا", date.today())
        try:
            q = supabase.table("staff_monitoring").select("*").gte("date", str(start_date)).lte("date", str(end_date))
            if filter_staff != "تمام":
                q = q.eq("staff_name", filter_staff)
            if filter_type != "تمام":
                q = q.eq("note_type", filter_type)
            res = q.order("date", desc=True).execute()
            df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        except Exception as e:
            st.error(f"خرابی: {e}")
            df = pd.DataFrame()
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
                    supabase.table("staff_monitoring").delete().eq("id", int(record_id)).execute()
                    st.success("ریکارڈ حذف کر دیا گیا")
                    st.rerun()

# 8.5 ماہانہ رزلٹ کارڈ
elif selected == "📜 ماہانہ رزلٹ کارڈ" and st.session_state.user_type == "admin":
    st.header("📜 ماہانہ رزلٹ کارڈ")
    try:
        res = supabase.table("students").select("id, name, father_name, roll_no, dept").execute()
        students_list = res.data
    except:
        students_list = []
    if not students_list:
        st.warning("کوئی طالب علم نہیں")
    else:
        student_names = [f"{s['name']} ولد {s['father_name']} (شناختی نمبر: {s['roll_no'] or ''}) - {s['dept']}" for s in students_list]
        sel = st.selectbox("طالب علم منتخب کریں", student_names)
        parts = sel.split(" ولد ")
        s_name = parts[0]
        rest = parts[1]
        f_name, rest2 = rest.split(" (شناختی نمبر: ")
        roll_no, dept = rest2.split(") - ")
        start = st.date_input("تاریخ آغاز", date.today().replace(day=1))
        end = st.date_input("تاریخ اختتام", date.today())
        student_id = next((s["id"] for s in students_list if s["name"] == s_name and s["father_name"] == f_name), None)
        if student_id and dept == "حفظ":
            res = supabase.table("hifz_records").select(
                "r_date, attendance, surah, lines, sq_p, sq_m, sq_a, m_p, m_m, m_a, cleanliness"
            ).eq("student_id", student_id).gte("r_date", str(start)).lte("r_date", str(end)).order("r_date").execute()
            if res.data:
                df = pd.DataFrame(res.data)
                df = df.rename(columns={
                    "r_date": "تاریخ", "attendance": "حاضری", "surah": "سبق", "lines": "کل ستر",
                    "sq_p": "سبقی", "sq_m": "سبقی (غلطی)", "sq_a": "سبقی (اٹکن)",
                    "m_p": "منزل", "m_m": "منزل (غلطی)", "m_a": "منزل (اٹکن)", "cleanliness": "صفائی"
                })
                grades = []
                for _, row in df.iterrows():
                    att = row['حاضری']
                    sabaq_nagha = (row['سبق'] in ["ناغہ", "یاد نہیں"])
                    sq_nagha = (row['سبقی'] in ["ناغہ", "یاد نہیں"])
                    m_nagha = (row['منزل'] in ["ناغہ", "یاد نہیں"])
                    sq_m = row['سبقی (غلطی)'] if pd.notna(row['سبقی (غلطی)']) else 0
                    m_m = row['منزل (غلطی)'] if pd.notna(row['منزل (غلطی)']) else 0
                    grades.append(calculate_grade_with_attendance(att, sabaq_nagha, sq_nagha, m_nagha, sq_m, m_m))
                df['درجہ'] = grades
                st.dataframe(df[['تاریخ', 'حاضری', 'سبق', 'سبقی', 'منزل', 'صفائی', 'درجہ']], use_container_width=True)
                html = generate_html_report(df, "ماہانہ رزلٹ کارڈ (حفظ)",
                                            student_name=f"{s_name} ولد {f_name}",
                                            start_date=start.strftime("%Y-%m-%d"), end_date=end.strftime("%Y-%m-%d"))
                st.download_button("📥 HTML ڈاؤن لوڈ", html, f"{s_name}_result.html", "text/html")
                if st.button("🖨️ پرنٹ کریں"):
                    st.components.v1.html(f"<script>var w=window.open();w.document.write(`{html}`);w.print();</script>", height=0)
        elif student_id and dept == "قاعدہ":
            res = supabase.table("qaida_records").select(
                "r_date, lesson_no, total_lines, details, attendance, cleanliness"
            ).eq("student_id", student_id).gte("r_date", str(start)).lte("r_date", str(end)).order("r_date").execute()
            if not res.data:
                st.warning("کوئی ریکارڈ نہیں")
            else:
                df = pd.DataFrame(res.data)
                df = df.rename(columns={
                    "r_date": "تاریخ", "lesson_no": "تختی نمبر", "total_lines": "کل لائنیں",
                    "details": "تفصیل", "attendance": "حاضری", "cleanliness": "صفائی"
                })
                st.dataframe(df, use_container_width=True)
                html = generate_html_report(df, "ماہانہ رزلٹ کارڈ (قاعدہ)",
                                            student_name=f"{s_name} ولد {f_name}",
                                            start_date=start.strftime("%Y-%m-%d"), end_date=end.strftime("%Y-%m-%d"))
                st.download_button("📥 HTML ڈاؤن لوڈ", html, f"{s_name}_qaida_result.html", "text/html")
                if st.button("🖨️ پرنٹ کریں"):
                    st.components.v1.html(f"<script>var w=window.open();w.document.write(`{html}`);w.print();</script>", height=0)
        elif student_id:
            res = supabase.table("general_education").select(
                "r_date, book_subject, today_lesson, homework, performance, cleanliness"
            ).eq("student_id", student_id).eq("dept", dept).gte("r_date", str(start)).lte("r_date", str(end)).order("r_date").execute()
            if res.data:
                df = pd.DataFrame(res.data)
                df = df.rename(columns={
                    "r_date": "تاریخ", "book_subject": "کتاب/مضمون", "today_lesson": "آج کا سبق",
                    "homework": "ہوم ورک", "performance": "کارکردگی", "cleanliness": "صفائی"
                })
                st.dataframe(df, use_container_width=True)
                html = generate_html_report(df, "ماہانہ رزلٹ کارڈ",
                                            student_name=f"{s_name} ولد {f_name}",
                                            start_date=start.strftime("%Y-%m-%d"), end_date=end.strftime("%Y-%m-%d"))
                st.download_button("📥 HTML ڈاؤن لوڈ", html, f"{s_name}_result.html", "text/html")
                if st.button("🖨️ پرنٹ کریں"):
                    st.components.v1.html(f"<script>var w=window.open();w.document.write(`{html}`);w.print();</script>", height=0)

# 8.6 پارہ تعلیمی رپورٹ
elif selected == "📘 پارہ تعلیمی رپورٹ" and st.session_state.user_type == "admin":
    st.header("📘 پارہ تعلیمی رپورٹ")
    try:
        res = supabase.table("students").select("id, name, father_name").eq("dept", "حفظ").execute()
        students_list = res.data
    except:
        students_list = []
    if not students_list:
        st.warning("کوئی حفظ کا طالب علم نہیں")
    else:
        student_names = [f"{s['name']} ولد {s['father_name']}" for s in students_list]
        sel = st.selectbox("طالب علم منتخب کریں", student_names)
        s_name, f_name = sel.split(" ولد ")
        student_id = next((s["id"] for s in students_list if s["name"] == s_name and s["father_name"] == f_name), None)
        if student_id:
            res = supabase.table("passed_paras").select(
                "para_no, passed_date, exam_type, grade, marks"
            ).eq("student_id", student_id).not_.is_("para_no", "null").order("para_no").execute()
            if not res.data:
                st.info("اس طالب علم کا کوئی پاس شدہ پارہ نہیں")
            else:
                passed_df = pd.DataFrame(res.data)
                passed_df = passed_df.rename(columns={
                    "para_no": "پارہ نمبر", "passed_date": "تاریخ پاس",
                    "exam_type": "امتحان قسم", "grade": "گریڈ", "marks": "نمبر"
                })
                st.dataframe(passed_df, use_container_width=True)
                html = generate_para_report(s_name, f_name, passed_df)
                st.download_button("📥 رپورٹ ڈاؤن لوڈ کریں", html, f"Para_Report_{s_name}.html", "text/html")
                if st.button("🖨️ پرنٹ کریں"):
                    st.components.v1.html(f"<script>var w=window.open();w.document.write(`{html}`);w.print();</script>", height=0)

# 8.7 اساتذہ حاضری
elif selected == "🕒 اساتذہ حاضری" and st.session_state.user_type == "admin":
    st.header("اساتذہ حاضری ریکارڈ")
    try:
        res = supabase.table("t_attendance").select("a_date, t_name, arrival, departure").order("a_date", desc=True).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            df = df.rename(columns={"a_date": "تاریخ", "t_name": "استاد", "arrival": "آمد", "departure": "رخصت"})
            st.dataframe(df, use_container_width=True)
        else:
            st.info("کوئی حاضری ریکارڈ نہیں")
    except Exception as e:
        st.error(f"خرابی: {e}")

# 8.8 رخصت کی منظوری
elif selected == "🏛️ رخصت کی منظوری" and st.session_state.user_type == "admin":
    st.header("رخصت کی منظوری")
    try:
        res = supabase.table("leave_requests").select("id, t_name, l_type, reason, start_date, days").eq("status", "پینڈنگ").execute()
        pending = res.data
    except:
        pending = []
    if not pending:
        st.info("کوئی پینڈنگ درخواست نہیں")
    else:
        for lr in pending:
            l_id = lr["id"]
            t_n = lr["t_name"]
            l_t = lr["l_type"]
            reas = lr["reason"]
            s_d = lr["start_date"]
            dys = lr["days"]
            with st.expander(f"{t_n} | {l_t} | {dys} دن"):
                st.write(f"وجہ: {reas}")
                col1, col2 = st.columns(2)
                if col1.button("✅ منظور", key=f"app_{l_id}"):
                    supabase.table("leave_requests").update({"status": "منظور"}).eq("id", l_id).execute()
                    st.rerun()
                if col2.button("❌ مسترد", key=f"rej_{l_id}"):
                    supabase.table("leave_requests").update({"status": "مسترد"}).eq("id", l_id).execute()
                    st.rerun()

# 8.9 یوزر مینجمنٹ
elif selected == "👥 یوزر مینجمنٹ" and st.session_state.user_type == "admin":
    st.header("👥 یوزر مینجمنٹ")
    tab1, tab2 = st.tabs(["اساتذہ", "طلبہ"])
    with tab1:
        st.subheader("موجودہ اساتذہ")
        try:
            res = supabase.table("teachers").select("id, name, password, dept, phone, address, id_card, joining_date").neq("name", "admin").execute()
            teachers_df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        except Exception as e:
            st.error(f"خرابی: {e}")
            teachers_df = pd.DataFrame()
        if not teachers_df.empty:
            edited_teachers = st.data_editor(teachers_df, num_rows="dynamic", use_container_width=True, key="teachers_edit")
            if st.button("اساتذہ میں تبدیلیاں محفوظ کریں"):
                try:
                    old_ids = set(teachers_df['id'].dropna().astype(int))
                    new_ids = set(edited_teachers['id'].dropna().astype(float).astype(int)) if 'id' in edited_teachers.columns else set()
                    for did in old_ids - new_ids:
                        supabase.table("teachers").delete().eq("id", int(did)).execute()
                    for _, row in edited_teachers.iterrows():
                        row_id = row.get('id')
                        if pd.isna(row_id) or row_id == 0 or row_id == '':
                            data = {
                                "name": row.get("name"), "dept": row.get("dept"),
                                "phone": row.get("phone"), "address": row.get("address"),
                                "id_card": row.get("id_card"),
                                "joining_date": safe_str_date(row.get("joining_date"))
                            }
                            pwd = row.get("password")
                            data["password"] = hash_password(str(pwd)) if pwd else hash_password("jamia123")
                            supabase.table("teachers").insert(data).execute()
                        else:
                            data = {
                                "name": row.get("name"), "dept": row.get("dept"),
                                "phone": row.get("phone"), "address": row.get("address"),
                                "id_card": row.get("id_card"),
                                "joining_date": safe_str_date(row.get("joining_date"))
                            }
                            pwd = row.get("password")
                            if pwd and len(str(pwd)) != 64:
                                data["password"] = hash_password(str(pwd))
                            supabase.table("teachers").update(data).eq("id", int(row_id)).execute()
                    st.success("تبدیلیاں محفوظ ہو گئیں")
                    st.rerun()
                except Exception as e:
                    st.error(f"خرابی: {e}")
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
                st.file_uploader("تصویر (اختیاری)", type=["jpg", "png", "jpeg"])
                if st.form_submit_button("رجسٹر کریں"):
                    if name and password:
                        try:
                            chk = supabase.table("teachers").select("id").eq("name", name).execute()
                            if chk.data:
                                st.error("یہ نام پہلے سے موجود ہے")
                            else:
                                supabase.table("teachers").insert({
                                    "name": name, "password": hash_password(password),
                                    "dept": dept, "phone": phone, "address": address,
                                    "id_card": id_card, "joining_date": str(joining_date)
                                }).execute()
                                st.success("استاد کامیابی سے رجسٹر ہو گیا")
                                st.rerun()
                        except Exception as e:
                            st.error(f"خرابی: {str(e)}")
                    else:
                        st.error("نام اور پاسورڈ ضروری ہیں")
    with tab2:
        st.subheader("موجودہ طلبہ")
        try:
            res = supabase.table("students").select(
                "id, name, father_name, mother_name, dob, admission_date, exit_date, exit_reason, id_card, phone, address, teacher_name, dept, class, section, roll_no"
            ).execute()
            students_df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        except Exception as e:
            st.error(f"خرابی: {e}")
            students_df = pd.DataFrame()
        if not students_df.empty:
            edited_students = st.data_editor(students_df, num_rows="dynamic", use_container_width=True, key="students_edit")
            if st.button("طلبہ میں تبدیلیاں محفوظ کریں"):
                try:
                    old_ids = set(students_df['id'].dropna().astype(int))
                    new_ids = set(edited_students['id'].dropna().astype(float).astype(int)) if 'id' in edited_students.columns else set()
                    for did in old_ids - new_ids:
                        supabase.table("students").delete().eq("id", int(did)).execute()
                    for _, row in edited_students.iterrows():
                        row_id = row.get('id')
                        data = {
                            "name": row.get("name"), "father_name": row.get("father_name"),
                            "mother_name": row.get("mother_name"),
                            "dob": safe_str_date(row.get("dob")),
                            "admission_date": safe_str_date(row.get("admission_date")),
                            "exit_date": safe_str_date(row.get("exit_date")),
                            "exit_reason": row.get("exit_reason"),
                            "id_card": row.get("id_card"), "phone": row.get("phone"),
                            "address": row.get("address"), "teacher_name": row.get("teacher_name"),
                            "dept": row.get("dept"), "class": row.get("class"),
                            "section": row.get("section"), "roll_no": row.get("roll_no")
                        }
                        if pd.isna(row_id) or row_id == 0 or row_id == '':
                            supabase.table("students").insert(data).execute()
                        else:
                            supabase.table("students").update(data).eq("id", int(row_id)).execute()
                    st.success("تبدیلیاں محفوظ ہو گئیں")
                    st.rerun()
                except Exception as e:
                    st.error(f"خرابی: {e}")
        else:
            st.info("کوئی طالب علم موجود نہیں")
        with st.expander("➕ نیا طالب علم داخل کریں"):
            with st.form("new_student_form"):
                col1, col2 = st.columns(2)
                with col1:
                    name = st.text_input("طالب علم کا نام*")
                    father = st.text_input("والد کا نام*")
                    mother = st.text_input("والدہ کا نام")
                    dob = st.date_input("تاریخ پیدائش", date.today() - timedelta(days=365 * 10))
                    admission_date = st.date_input("تاریخ داخلہ", date.today())
                    roll_no = st.text_input("شناختی نمبر (اختیاری)", placeholder="مثلاً: 2024-001")
                with col2:
                    dept = st.selectbox("شعبہ*", ["حفظ", "قاعدہ", "درسِ نظامی", "عصری تعلیم"])
                    class_name = st.text_input("کلاس (عصری تعلیم کے لیے)")
                    section = st.text_input("سیکشن")
                    try:
                        tres = supabase.table("teachers").select("name").neq("name", "admin").execute()
                        teachers_list = [r["name"] for r in tres.data]
                    except:
                        teachers_list = []
                    teacher = st.selectbox("استاد*", teachers_list) if teachers_list else st.text_input("استاد کا نام*")
                id_card = st.text_input("B-Form / شناختی کارڈ نمبر")
                phone = st.text_input("فون نمبر")
                address = st.text_area("پتہ")
                st.file_uploader("تصویر (اختیاری)", type=["jpg", "png", "jpeg"])
                st.markdown("---")
                st.markdown("**اگر طالب علم مدرسہ چھوڑ چکا ہے:**")
                exit_date_val = st.date_input("تاریخ خارج", value=None)
                exit_reason = st.text_area("وجہ خارج")
                if st.form_submit_button("داخلہ کریں"):
                    if name and father and teacher and dept:
                        try:
                            supabase.table("students").insert({
                                "name": name, "father_name": father, "mother_name": mother,
                                "dob": str(dob), "admission_date": str(admission_date),
                                "exit_date": str(exit_date_val) if exit_date_val else None,
                                "exit_reason": exit_reason, "id_card": id_card,
                                "phone": phone, "address": address,
                                "teacher_name": teacher, "dept": dept,
                                "class": class_name, "section": section, "roll_no": roll_no
                            }).execute()
                            st.success("طالب علم کامیابی سے داخل ہو گیا")
                            st.rerun()
                        except Exception as e:
                            st.error(f"خرابی: {str(e)}")
                    else:
                        st.error("نام، ولدیت، استاد اور شعبہ ضروری ہیں")

# 8.10 ٹائم ٹیبل مینجمنٹ
elif selected == "📚 ٹائم ٹیبل مینجمنٹ" and st.session_state.user_type == "admin":
    st.header("📚 ٹائم ٹیبل مینجمنٹ")
    try:
        res = supabase.table("teachers").select("name").neq("name", "admin").execute()
        teachers = [r["name"] for r in res.data]
    except:
        teachers = []
    if not teachers:
        st.warning("پہلے اساتذہ رجسٹر کریں")
    else:
        sel_t = st.selectbox("استاد منتخب کریں", teachers)
        try:
            res = supabase.table("timetable").select("id, day, period, book, room").eq("t_name", sel_t).execute()
            tt_data = res.data
        except:
            tt_data = []
        if tt_data:
            tt_df = pd.DataFrame(tt_data)
            tt_df = tt_df.rename(columns={"day": "دن", "period": "وقت", "book": "کتاب", "room": "کمرہ"})
            st.subheader("موجودہ ٹائم ٹیبل")
            day_order = {"ہفتہ": 0, "اتوار": 1, "پیر": 2, "منگل": 3, "بدھ": 4, "جمعرات": 5}
            tt_df['day_order'] = tt_df['دن'].map(day_order)
            tt_df = tt_df.sort_values(['day_order', 'وقت'])
            st.dataframe(tt_df[['دن', 'وقت', 'کتاب', 'کمرہ']], use_container_width=True)
        else:
            tt_df = pd.DataFrame()
        with st.expander("➕ نیا پیریڈ شامل کریں"):
            with st.form("add_period"):
                col1, col2 = st.columns(2)
                day = col1.selectbox("دن", ["ہفتہ", "اتوار", "پیر", "منگل", "بدھ", "جمعرات"])
                period = col2.text_input("وقت (مثلاً 08:00-09:00)")
                book = st.text_input("کتاب / مضمون")
                room = st.text_input("کمرہ نمبر")
                if st.form_submit_button("شامل کریں"):
                    supabase.table("timetable").insert({
                        "t_name": sel_t, "day": day, "period": period, "book": book, "room": room
                    }).execute()
                    st.success("پیریڈ شامل کر دیا گیا")
                    st.rerun()
        if not tt_df.empty:
            with st.expander("🔄 پورے ہفتے میں نقل کریں"):
                source_day = st.selectbox("منبع دن", ["ہفتہ", "اتوار", "پیر", "منگل", "بدھ", "جمعرات"], key="copy_source")
                target_days = st.multiselect("نقل کرنے کے لیے دن",
                                             ["ہفتہ", "اتوار", "پیر", "منگل", "بدھ", "جمعرات"],
                                             default=["ہفتہ", "اتوار", "پیر", "منگل", "بدھ", "جمعرات"])
                if st.button("نقل کریں"):
                    src = supabase.table("timetable").select("period, book, room").eq("t_name", sel_t).eq("day", source_day).execute()
                    if src.data:
                        for d in target_days:
                            supabase.table("timetable").delete().eq("t_name", sel_t).eq("day", d).execute()
                        for d in target_days:
                            for p in src.data:
                                supabase.table("timetable").insert({
                                    "t_name": sel_t, "day": d,
                                    "period": p["period"], "book": p["book"], "room": p["room"]
                                }).execute()
                        st.success(f"{source_day} کے پیریڈز {', '.join(target_days)} میں نقل ہو گئے")
                        st.rerun()
                    else:
                        st.warning(f"{source_day} کے لیے کوئی پیریڈ نہیں")

# 8.11 پاسورڈ تبدیل کریں
elif selected == "🔑 پاسورڈ تبدیل کریں":
    st.header("🔑 پاسورڈ تبدیل کریں")
    if st.session_state.user_type == "admin":
        try:
            res = supabase.table("teachers").select("name").neq("name", "admin").execute()
            teachers = [r["name"] for r in res.data]
        except:
            teachers = []
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
                supabase.table("notifications").insert({
                    "title": title, "message": msg,
                    "target": target, "created_at": datetime.now().isoformat()
                }).execute()
                st.success("نوٹیفکیشن بھیج دیا گیا")
    try:
        if st.session_state.user_type == "admin":
            res = supabase.table("notifications").select("title, message, created_at").order("created_at", desc=True).limit(10).execute()
        else:
            res = supabase.table("notifications").select("title, message, created_at").in_("target", ["تمام", "اساتذہ"]).order("created_at", desc=True).limit(10).execute()
        notifs = res.data
    except:
        notifs = []
    for n in notifs:
        st.info(f"**{n.get('title','')}**\n\n{n.get('message','')}\n\n*{n.get('created_at','')}*")

# 8.13 تجزیہ و رپورٹس
elif selected == "📈 تجزیہ و رپورٹس" and st.session_state.user_type == "admin":
    st.header("تجزیہ")
    try:
        res = supabase.table("t_attendance").select("a_date").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            df = df.rename(columns={"a_date": "تاریخ"})
            fig = px.bar(df, x='تاریخ', title="اساتذہ کی حاضری")
            st.plotly_chart(fig)
    except Exception as e:
        st.error(f"خرابی: {e}")

# 8.14 ماہانہ بہترین طلباء
elif selected == "🏆 ماہانہ بہترین طلباء" and st.session_state.user_type == "admin":
    st.markdown("<div class='main-header'><h1>🏆 ماہانہ بہترین طلباء</h1><p>تعلیمی اور صفائی کی بنیاد پر بہترین کارکردگی</p></div>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        month_year = st.date_input("مہینہ منتخب کریں", date.today().replace(day=1), key="month_picker")
    start_date = month_year.replace(day=1)
    if month_year.month == 12:
        end_date = month_year.replace(year=month_year.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        end_date = month_year.replace(month=month_year.month + 1, day=1) - timedelta(days=1)
    st.markdown(f"### 📅 {start_date.strftime('%B %Y')} کے لیے نتائج")
    try:
        res = supabase.table("students").select("id, name, father_name, roll_no, dept").execute()
        students = res.data
    except:
        students = []
    if not students:
        st.warning("کوئی طالب علم موجود نہیں")
    else:
        student_scores = []
        for stud in students:
            sid = stud["id"]
            name = stud["name"]
            father = stud["father_name"]
            roll = stud["roll_no"]
            dept = stud["dept"]
            try:
                if dept == "حفظ":
                    res = supabase.table("hifz_records").select(
                        "attendance, surah, sq_p, m_p, sq_m, m_m"
                    ).eq("student_id", sid).gte("r_date", str(start_date)).lte("r_date", str(end_date)).execute()
                    records = res.data
                    grade_scores = []
                    for rec in records:
                        att = rec["attendance"]
                        sabaq_nagha = rec["surah"] in ["ناغہ", "یاد نہیں"]
                        sq_nagha = rec["sq_p"] in ["ناغہ", "یاد نہیں"]
                        m_nagha = rec["m_p"] in ["ناغہ", "یاد نہیں"]
                        sq_m = rec["sq_m"] or 0
                        m_m = rec["m_m"] or 0
                        grade = calculate_grade_with_attendance(att, sabaq_nagha, sq_nagha, m_nagha, sq_m, m_m)
                        grade_map = {"ممتاز": 100, "جید جداً": 85, "جید": 75, "مقبول": 60,
                                     "دوبارہ کوشش کریں": 40, "ناقص (ناغہ)": 30, "کمزور (ناغہ)": 20,
                                     "ناکام (مکمل ناغہ)": 10, "غیر حاضر": 0, "رخصت": 50}
                        grade_scores.append(grade_map.get(grade, 0))
                    avg_grade = sum(grade_scores) / len(grade_scores) if grade_scores else 0
                    res_c = supabase.table("hifz_records").select("cleanliness").eq("student_id", sid).gte("r_date", str(start_date)).lte("r_date", str(end_date)).not_.is_("cleanliness", "null").execute()
                    clean_scores = [cleanliness_to_score(r["cleanliness"]) for r in res_c.data if r.get("cleanliness")]
                    avg_clean = sum(clean_scores) / len(clean_scores) if clean_scores else 0
                elif dept == "قاعدہ":
                    res = supabase.table("qaida_records").select("attendance").eq("student_id", sid).gte("r_date", str(start_date)).lte("r_date", str(end_date)).execute()
                    grade_scores = [85 if r["attendance"] == "حاضر" else 50 if r["attendance"] == "رخصت" else 0 for r in res.data]
                    avg_grade = sum(grade_scores) / len(grade_scores) if grade_scores else 0
                    res_c = supabase.table("qaida_records").select("cleanliness").eq("student_id", sid).gte("r_date", str(start_date)).lte("r_date", str(end_date)).not_.is_("cleanliness", "null").execute()
                    clean_scores = [cleanliness_to_score(r["cleanliness"]) for r in res_c.data if r.get("cleanliness")]
                    avg_clean = sum(clean_scores) / len(clean_scores) if clean_scores else 0
                else:
                    res = supabase.table("general_education").select("attendance, performance").eq("student_id", sid).eq("dept", dept).gte("r_date", str(start_date)).lte("r_date", str(end_date)).execute()
                    grade_scores = []
                    perf_map = {"بہت بہتر": 90, "بہتر": 80, "مناسب": 65, "کمزور": 45}
                    for rec in res.data:
                        att = rec["attendance"]
                        if att == "حاضر":
                            grade_scores.append(perf_map.get(rec.get("performance", ""), 75))
                        elif att == "رخصت":
                            grade_scores.append(50)
                        else:
                            grade_scores.append(0)
                    avg_grade = sum(grade_scores) / len(grade_scores) if grade_scores else 0
                    res_c = supabase.table("general_education").select("cleanliness").eq("student_id", sid).gte("r_date", str(start_date)).lte("r_date", str(end_date)).not_.is_("cleanliness", "null").execute()
                    clean_scores = [cleanliness_to_score(r["cleanliness"]) for r in res_c.data if r.get("cleanliness")]
                    avg_clean = sum(clean_scores) / len(clean_scores) if clean_scores else 0
                student_scores.append({"id": sid, "name": name, "father": father, "roll": roll, "dept": dept, "avg_grade": avg_grade, "avg_clean": avg_clean})
            except:
                pass
        sorted_grade = sorted(student_scores, key=lambda x: x["avg_grade"], reverse=True)
        sorted_clean = sorted(student_scores, key=lambda x: x["avg_clean"], reverse=True)
        st.markdown("---")
        st.subheader("📚 تعلیمی کارکردگی کے لحاظ سے بہترین طلباء")
        col1, col2, col3 = st.columns(3)
        for i, student in enumerate(sorted_grade[:3]):
            with [col1, col2, col3][i]:
                medal = ["🥇", "🥈", "🥉"][i]
                color_class = ["gold", "silver", "bronze"][i]
                st.markdown(f"""
                <div class="best-student-card">
                    <h2 class="{color_class}">{medal}</h2>
                    <h3>{student['name']}</h3>
                    <p>والد: {student['father']}</p>
                    <p>شناختی نمبر: {student['roll'] or '-'}</p>
                    <p>شعبہ: {student['dept']}</p>
                    <p>اوسط نمبر: {student['avg_grade']:.1f}%</p>
                </div>
                """, unsafe_allow_html=True)
        st.markdown("---")
        st.subheader("🧼 صفائی کے لحاظ سے بہترین طلباء")
        col1, col2, col3 = st.columns(3)
        for i, student in enumerate(sorted_clean[:3]):
            with [col1, col2, col3][i]:
                medal = ["🥇", "🥈", "🥉"][i]
                color_class = ["gold", "silver", "bronze"][i]
                clean_percent = (student['avg_clean'] / 3) * 100
                st.markdown(f"""
                <div class="best-student-card">
                    <h2 class="{color_class}">{medal}</h2>
                    <h3>{student['name']}</h3>
                    <p>والد: {student['father']}</p>
                    <p>شناختی نمبر: {student['roll'] or '-'}</p>
                    <p>شعبہ: {student['dept']}</p>
                    <p>صفائی اوسط: {clean_percent:.1f}%</p>
                </div>
                """, unsafe_allow_html=True)
        with st.expander("📊 تمام طلباء کی تفصیلی کارکردگی"):
            df_all = pd.DataFrame(student_scores)
            if not df_all.empty:
                df_all = df_all.rename(columns={
                    "name": "نام", "father": "والد کا نام", "roll": "شناختی نمبر", "dept": "شعبہ",
                    "avg_grade": "تعلیمی اوسط (%)", "avg_clean": "صفائی اوسط (0-3)"
                })
                df_all["تعلیمی اوسط (%)"] = df_all["تعلیمی اوسط (%)"].round(1)
                df_all["صفائی اوسط (0-3)"] = df_all["صفائی اوسط (0-3)"].round(2)
                st.dataframe(df_all, use_container_width=True)
                st.download_button("📥 CSV ڈاؤن لوڈ کریں", convert_df_to_csv(df_all), "monthly_best_students.csv")

# 8.15 بیک اپ & سیٹنگز
elif selected == "⚙️ بیک اپ & سیٹنگز" and st.session_state.user_type == "admin":
    st.header("بیک اپ اور سیٹنگز")
    st.subheader("📄 CSV فائلوں کا بیک اپ (زپ میں ڈاؤن لوڈ)")
    tables = ["teachers", "students", "hifz_records", "qaida_records", "general_education",
              "t_attendance", "exams", "passed_paras", "timetable", "leave_requests",
              "notifications", "audit_log", "staff_monitoring"]
    if st.button("💾 تمام ٹیبلز کی CSV بیک اپ (زپ) بنائیں"):
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for t in tables:
                try:
                    res = supabase.table(t).select("*").execute()
                    df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
                    csv_data = df.to_csv(index=False).encode('utf-8-sig')
                    zip_file.writestr(f"{t}.csv", csv_data)
                except Exception as e:
                    st.warning(f"ٹیبل {t} کی بیک اپ میں خرابی: {str(e)}")
        zip_buffer.seek(0)
        st.download_button(label="📥 CSV بیک اپ زپ ڈاؤن لوڈ کریں", data=zip_buffer,
                           file_name=f"backup_tables_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                           mime="application/zip")
    st.markdown("---")
    st.subheader("📤 CSV فائل اپ لوڈ کر کے ڈیٹا ریسٹور کریں")
    st.info("یہاں آپ کسی ایک ٹیبل کی CSV فائل اپ لوڈ کر سکتے ہیں۔ ڈیٹا خود بخود Supabase ٹیبل میں شامل ہو جائے گا۔")
    table_options = {
        "اساتذہ (teachers)": "teachers",
        "طلبہ (students)": "students",
        "حفظ ریکارڈ (hifz_records)": "hifz_records",
        "قاعدہ ریکارڈ (qaida_records)": "qaida_records",
        "عمومی تعلیم (general_education)": "general_education",
        "امتحانات (exams)": "exams",
        "پاس شدہ پارے (passed_paras)": "passed_paras",
        "ٹائم ٹیبل (timetable)": "timetable",
        "رخصت درخواستیں (leave_requests)": "leave_requests",
        "نوٹیفیکیشنز (notifications)": "notifications",
        "عملہ نگرانی (staff_monitoring)": "staff_monitoring"
    }
    selected_table_display = st.selectbox("ٹیبل منتخب کریں", list(table_options.keys()))
    selected_table = table_options[selected_table_display]
    uploaded_csv = st.file_uploader("CSV فائل منتخب کریں (UTF-8 encoding)", type=["csv"], key="csv_upload")
    if uploaded_csv is not None:
        try:
            df = pd.read_csv(uploaded_csv)
            st.write("اپ لوڈ کی گئی CSV میں پہلی 5 قطاریں:")
            st.dataframe(df.head())
            upload_mode = st.radio("اپ لوڈ موڈ:", ["موجودہ ڈیٹا میں شامل کریں (Append)", "موجودہ ڈیٹا کو حذف کر کے نیا ڈالیں (Replace)"])
            if st.button("ڈیٹا ریسٹور کریں"):
                if upload_mode == "موجودہ ڈیٹا کو حذف کر کے نیا ڈالیں (Replace)":
                    supabase.table(selected_table).delete().neq("id", 0).execute()
                    st.warning(f"{selected_table_display} کا پرانا ڈیٹا حذف کر دیا گیا۔")
                # id کالم ہٹائیں تاکہ Supabase خود ID دے
                if 'id' in df.columns:
                    df = df.drop(columns=['id'])
                records = df.where(pd.notna(df), None).to_dict(orient='records')
                # بیچز میں داخل کریں
                batch_size = 100
                for i in range(0, len(records), batch_size):
                    batch = records[i:i + batch_size]
                    supabase.table(selected_table).insert(batch).execute()
                log_audit(st.session_state.username, "CSV Restore", f"Table: {selected_table}, Mode: {upload_mode}")
                st.success(f"ڈیٹا کامیابی سے {selected_table_display} میں محفوظ ہو گیا۔")
                st.rerun()
        except Exception as e:
            st.error(f"خرابی: {str(e)}")
    st.markdown("---")
    with st.expander("آڈٹ لاگ"):
        try:
            res = supabase.table("audit_log").select("user, action, timestamp, details").order("timestamp", desc=True).limit(50).execute()
            logs = pd.DataFrame(res.data) if res.data else pd.DataFrame()
            st.dataframe(logs)
        except Exception as e:
            st.error(f"خرابی: {e}")

# ==================== 9. استاد کے سیکشن ====================

# 9.1 روزانہ سبق اندراج
if selected == "📝 روزانہ سبق اندراج" and st.session_state.user_type == "teacher":
    st.header("📝 روزانہ سبق اندراج")
    entry_date = st.date_input("تاریخ (جس دن کا اندراج کرنا ہے)", date.today())
    dept = st.selectbox("شعبہ منتخب کریں", ["حفظ", "قاعدہ", "درسِ نظامی", "عصری تعلیم"])

    if dept == "حفظ":
        st.subheader("حفظ کا اندراج")
        try:
            res = supabase.table("students").select("id, name, father_name").eq("teacher_name", st.session_state.username).eq("dept", "حفظ").execute()
            students = res.data
        except:
            students = []
        if not students:
            st.info("آپ کی کلاس میں کوئی طالب علم نہیں")
        else:
            for stud in students:
                sid = stud["id"]
                s = stud["name"]
                f = stud["father_name"]
                key = f"{sid}_{s}_{f}"
                st.markdown(f"### 👤 {s} ولد {f}")
                att = st.radio("حاضری", ["حاضر", "غیر حاضر", "رخصت"], key=f"att_{key}", horizontal=True)
                cleanliness = st.selectbox("صفائی کا معیار", cleanliness_options, key=f"clean_{key}")
                if att != "حاضر":
                    grade = calculate_grade_with_attendance(att, False, False, False, 0, 0)
                    st.info(f"**اس طالب علم کا درجہ:** {grade}")
                    if st.button(f"محفوظ کریں ({s})", key=f"save_absent_{key}"):
                        chk = supabase.table("hifz_records").select("id").eq("r_date", str(entry_date)).eq("student_id", sid).execute()
                        if chk.data:
                            st.error(f"{s} کا ریکارڈ پہلے سے موجود ہے (تاریخ {entry_date})")
                        else:
                            supabase.table("hifz_records").insert({
                                "r_date": str(entry_date), "student_id": sid,
                                "t_name": st.session_state.username, "surah": "غائب",
                                "lines": 0, "sq_p": "غائب", "sq_a": 0, "sq_m": 0,
                                "m_p": "غائب", "m_a": 0, "m_m": 0, "attendance": att, "cleanliness": cleanliness
                            }).execute()
                            st.success("محفوظ ہو گیا")
                    st.markdown("---")
                    continue
                # سبق
                st.write("**سبق**")
                col1, col2 = st.columns(2)
                sabaq_nagha = col1.checkbox("ناغہ", key=f"sabaq_nagha_{key}")
                sabaq_yad_nahi = col2.checkbox("یاد نہیں", key=f"sabaq_yad_{key}")
                if sabaq_nagha or sabaq_yad_nahi:
                    sabaq_text = "ناغہ" if sabaq_nagha else "یاد نہیں"
                    lines = 0
                else:
                    surah = st.selectbox("سورت", surahs_urdu, key=f"surah_{key}")
                    a_from = st.text_input("آیت (سے)", key=f"af_{key}")
                    a_to = st.text_input("آیت (تک)", key=f"at_{key}")
                    sabaq_text = f"{surah}: {a_from}-{a_to}"
                    lines = st.number_input("کل ستر (لائنوں کی تعداد)", min_value=0, value=0, key=f"lines_{key}")
                # سبقی
                st.write("**سبقی**")
                col1, col2 = st.columns(2)
                sq_nagha = col1.checkbox("ناغہ", key=f"sq_nagha_{key}")
                sq_yad_nahi = col2.checkbox("یاد نہیں", key=f"sq_yad_{key}")
                if sq_nagha or sq_yad_nahi:
                    sq_text = "ناغہ" if sq_nagha else "یاد نہیں"
                    sq_parts = [sq_text]
                    sq_a = 0
                    sq_m = 0
                else:
                    if f"sq_rows_{key}" not in st.session_state:
                        st.session_state[f"sq_rows_{key}"] = 1
                    sq_parts = []
                    sq_a = 0
                    sq_m = 0
                    for i in range(st.session_state[f"sq_rows_{key}"]):
                        cols = st.columns([2, 2, 1, 1])
                        p = cols[0].selectbox("پارہ", paras, key=f"sqp_{key}_{i}")
                        v = cols[1].selectbox("مقدار", ["مکمل", "آدھا", "پون", "پاؤ"], key=f"sqv_{key}_{i}")
                        a = cols[2].number_input("اٹکن", 0, key=f"sqa_{key}_{i}")
                        e = cols[3].number_input("غلطی", 0, key=f"sqe_{key}_{i}")
                        sq_parts.append(f"{p}:{v}")
                        sq_a += a
                        sq_m += e
                    if st.button("➕", key=f"add_sq_{key}", help="مزید سبقی پارہ شامل کریں"):
                        st.session_state[f"sq_rows_{key}"] += 1
                        st.rerun()
                # منزل
                st.write("**منزل**")
                col1, col2 = st.columns(2)
                m_nagha = col1.checkbox("ناغہ", key=f"m_nagha_{key}")
                m_yad_nahi = col2.checkbox("یاد نہیں", key=f"m_yad_{key}")
                if m_nagha or m_yad_nahi:
                    m_text = "ناغہ" if m_nagha else "یاد نہیں"
                    m_parts = [m_text]
                    m_a = 0
                    m_m = 0
                else:
                    if f"m_rows_{key}" not in st.session_state:
                        st.session_state[f"m_rows_{key}"] = 1
                    m_parts = []
                    m_a = 0
                    m_m = 0
                    for j in range(st.session_state[f"m_rows_{key}"]):
                        cols = st.columns([2, 2, 1, 1])
                        p = cols[0].selectbox("پارہ", paras, key=f"mp_{key}_{j}")
                        v = cols[1].selectbox("مقدار", ["مکمل", "آدھا", "پون", "پاؤ"], key=f"mv_{key}_{j}")
                        a = cols[2].number_input("اٹکن", 0, key=f"ma_{key}_{j}")
                        e = cols[3].number_input("غلطی", 0, key=f"me_{key}_{j}")
                        m_parts.append(f"{p}:{v}")
                        m_a += a
                        m_m += e
                    if st.button("➕", key=f"add_m_{key}", help="مزید منزل پارہ شامل کریں"):
                        st.session_state[f"m_rows_{key}"] += 1
                        st.rerun()
                sabaq_nagha_bool = sabaq_nagha or sabaq_yad_nahi
                sq_nagha_bool = sq_nagha or sq_yad_nahi
                m_nagha_bool = m_nagha or m_yad_nahi
                grade = calculate_grade_with_attendance(att, sabaq_nagha_bool, sq_nagha_bool, m_nagha_bool, sq_m, m_m)
                st.info(f"**اس طالب علم کا درجہ:** {grade}")
                if st.button(f"محفوظ کریں ({s})", key=f"save_{key}"):
                    chk = supabase.table("hifz_records").select("id").eq("r_date", str(entry_date)).eq("student_id", sid).execute()
                    if chk.data:
                        st.error(f"{s} کا ریکارڈ پہلے سے موجود ہے (تاریخ {entry_date})")
                    else:
                        supabase.table("hifz_records").insert({
                            "r_date": str(entry_date), "student_id": sid,
                            "t_name": st.session_state.username, "surah": sabaq_text,
                            "lines": int(lines), "sq_p": " | ".join(sq_parts),
                            "sq_a": int(sq_a), "sq_m": int(sq_m),
                            "m_p": " | ".join(m_parts), "m_a": int(m_a), "m_m": int(m_m),
                            "attendance": att, "cleanliness": cleanliness
                        }).execute()
                        log_audit(st.session_state.username, "Hifz Entry", f"{s} {entry_date}")
                        st.success("محفوظ ہو گیا")
                st.markdown("---")

    elif dept == "قاعدہ":
        st.subheader("قاعدہ (نورانی قاعدہ / نماز) کا اندراج")
        try:
            res = supabase.table("students").select("id, name, father_name").eq("teacher_name", st.session_state.username).eq("dept", "قاعدہ").execute()
            students = res.data
        except:
            students = []
        if not students:
            st.info("آپ کی کلاس میں کوئی طالب علم نہیں")
        else:
            for stud in students:
                sid = stud["id"]
                s = stud["name"]
                f = stud["father_name"]
                key = f"{sid}_{s}_{f}"
                st.markdown(f"### 👤 {s} ولد {f}")
                att = st.radio("حاضری", ["حاضر", "غیر حاضر", "رخصت"], key=f"att_{key}", horizontal=True)
                cleanliness = st.selectbox("صفائی کا معیار", cleanliness_options, key=f"clean_{key}")
                if att == "حاضر":
                    col1, col2 = st.columns(2)
                    nagha = col1.checkbox("ناغہ", key=f"nagha_{key}")
                    yad_nahi = col2.checkbox("یاد نہیں", key=f"yad_nahi_{key}")
                    if nagha or yad_nahi:
                        lesson_no = "ناغہ" if nagha else "یاد نہیں"
                        total_lines = 0
                        details = ""
                    else:
                        lesson_type = st.radio("نوعیت", ["نورانی قاعدہ", "نماز (حنفی)"], key=f"lesson_type_{key}", horizontal=True)
                        if lesson_type == "نورانی قاعدہ":
                            lesson_no = st.text_input("تختی نمبر / سبق نمبر", key=f"lesson_{key}")
                            total_lines = st.number_input("کل لائنیں", min_value=0, value=0, key=f"lines_{key}")
                            details = st.text_area("تفصیل / نوٹ", key=f"details_{key}")
                        else:
                            lesson_no = st.selectbox("سبق", [
                                "اذان و اقامت", "نماز کا طریقہ (مسنون)", "دعائے ثنا",
                                "سورہ فاتحہ", "سورہ اخلاص", "قنوت دعا", "تشہد",
                                "درود شریف", "دعائے ختم نماز"
                            ], key=f"lesson_{key}")
                            total_lines = st.number_input("کل لائنیں (اگر کوئی ہوں)", min_value=0, value=0, key=f"lines_{key}")
                            details = st.text_area("تفصیل / نوٹ", key=f"details_{key}")
                    if st.button(f"محفوظ کریں ({s})", key=f"save_{key}"):
                        chk = supabase.table("qaida_records").select("id").eq("r_date", str(entry_date)).eq("student_id", sid).execute()
                        if chk.data:
                            st.error(f"{s} کا ریکارڈ پہلے سے موجود ہے (تاریخ {entry_date})")
                        else:
                            supabase.table("qaida_records").insert({
                                "r_date": str(entry_date), "student_id": sid,
                                "t_name": st.session_state.username, "lesson_no": lesson_no,
                                "total_lines": int(total_lines), "details": details,
                                "attendance": att, "cleanliness": cleanliness
                            }).execute()
                            log_audit(st.session_state.username, "Qaida Entry", f"{s} {entry_date}")
                            st.success("محفوظ ہو گیا")
                else:
                    if st.button(f"غیر حاضر / رخصت محفوظ کریں ({s})", key=f"save_absent_{key}"):
                        chk = supabase.table("qaida_records").select("id").eq("r_date", str(entry_date)).eq("student_id", sid).execute()
                        if chk.data:
                            st.error(f"{s} کا ریکارڈ پہلے سے موجود ہے (تاریخ {entry_date})")
                        else:
                            supabase.table("qaida_records").insert({
                                "r_date": str(entry_date), "student_id": sid,
                                "t_name": st.session_state.username, "lesson_no": "غائب",
                                "total_lines": 0, "details": "", "attendance": att, "cleanliness": cleanliness
                            }).execute()
                            st.success("محفوظ ہو گیا")
                st.markdown("---")

    elif dept == "درسِ نظامی":
        st.subheader("درسِ نظامی سبق ریکارڈ")
        try:
            res = supabase.table("students").select("id, name, father_name").eq("teacher_name", st.session_state.username).eq("dept", "درسِ نظامی").execute()
            students = res.data
        except:
            students = []
        if not students:
            st.info("کوئی طالب علم نہیں")
        else:
            with st.form("dars_form"):
                records = []
                for stud in students:
                    sid = stud["id"]
                    s = stud["name"]
                    f = stud["father_name"]
                    st.markdown(f"### {s} ولد {f}")
                    att = st.radio("حاضری", ["حاضر", "غیر حاضر", "رخصت"], key=f"att_dars_{sid}", horizontal=True)
                    cleanliness = st.selectbox("صفائی کا معیار", cleanliness_options, key=f"clean_dars_{sid}")
                    if att == "حاضر":
                        col1, col2 = st.columns(2)
                        nagha = col1.checkbox("ناغہ", key=f"nagha_dars_{sid}")
                        yad_nahi = col2.checkbox("یاد نہیں", key=f"yad_dars_{sid}")
                        if nagha or yad_nahi:
                            book = "ناغہ" if nagha else "یاد نہیں"
                            lesson = "ناغہ" if nagha else "یاد نہیں"
                            perf = "ناغہ" if nagha else "یاد نہیں"
                        else:
                            book = st.text_input("کتاب کا نام", key=f"book_{sid}")
                            lesson = st.text_area("آج کا سبق", key=f"lesson_{sid}")
                            perf = st.select_slider("کارکردگی", ["بہت بہتر", "بہتر", "مناسب", "کمزور"], key=f"perf_{sid}")
                        records.append({"r_date": str(entry_date), "student_id": sid,
                                        "t_name": st.session_state.username, "dept": "درسِ نظامی",
                                        "book_subject": book, "today_lesson": lesson,
                                        "homework": "", "performance": perf,
                                        "attendance": att, "cleanliness": cleanliness})
                    else:
                        records.append({"r_date": str(entry_date), "student_id": sid,
                                        "t_name": st.session_state.username, "dept": "درسِ نظامی",
                                        "book_subject": "غائب", "today_lesson": "غائب",
                                        "homework": "", "performance": "غائب",
                                        "attendance": att, "cleanliness": cleanliness})
                if st.form_submit_button("محفوظ کریں"):
                    for rec in records:
                        supabase.table("general_education").insert(rec).execute()
                    st.success("محفوظ ہو گیا")

    elif dept == "عصری تعلیم":
        st.subheader("عصری تعلیم ڈائری")
        try:
            res = supabase.table("students").select("id, name, father_name").eq("teacher_name", st.session_state.username).eq("dept", "عصری تعلیم").execute()
            students = res.data
        except:
            students = []
        if not students:
            st.info("کوئی طالب علم نہیں")
        else:
            with st.form("school_form"):
                records = []
                for stud in students:
                    sid = stud["id"]
                    s = stud["name"]
                    f = stud["father_name"]
                    st.markdown(f"### {s} ولد {f}")
                    att = st.radio("حاضری", ["حاضر", "غیر حاضر", "رخصت"], key=f"att_school_{sid}", horizontal=True)
                    cleanliness = st.selectbox("صفائی کا معیار", cleanliness_options, key=f"clean_school_{sid}")
                    if att == "حاضر":
                        col1, col2 = st.columns(2)
                        nagha = col1.checkbox("ناغہ", key=f"nagha_school_{sid}")
                        yad_nahi = col2.checkbox("یاد نہیں", key=f"yad_school_{sid}")
                        if nagha or yad_nahi:
                            subject = "ناغہ" if nagha else "یاد نہیں"
                            topic = "ناغہ" if nagha else "یاد نہیں"
                            hw = "ناغہ" if nagha else "یاد نہیں"
                        else:
                            subject = st.selectbox("مضمون", ["اردو", "انگلش", "ریاضی", "سائنس", "اسلامیات", "سماجی علوم"], key=f"sub_{sid}")
                            topic = st.text_input("عنوان", key=f"topic_{sid}")
                            hw = st.text_area("ہوم ورک", key=f"hw_{sid}")
                        records.append({"r_date": str(entry_date), "student_id": sid,
                                        "t_name": st.session_state.username, "dept": "عصری تعلیم",
                                        "book_subject": subject, "today_lesson": topic,
                                        "homework": hw, "performance": "",
                                        "attendance": att, "cleanliness": cleanliness})
                    else:
                        records.append({"r_date": str(entry_date), "student_id": sid,
                                        "t_name": st.session_state.username, "dept": "عصری تعلیم",
                                        "book_subject": "غائب", "today_lesson": "غائب",
                                        "homework": "غائب", "performance": "",
                                        "attendance": att, "cleanliness": cleanliness})
                if st.form_submit_button("محفوظ کریں"):
                    for rec in records:
                        supabase.table("general_education").insert(rec).execute()
                    st.success("محفوظ ہو گیا")

# 9.2 امتحانی درخواست
elif selected == "🎓 امتحانی درخواست" and st.session_state.user_type == "teacher":
    st.subheader("امتحان کے لیے طالب علم نامزد کریں")
    try:
        res = supabase.table("students").select("id, name, father_name, dept").eq("teacher_name", st.session_state.username).execute()
        students = res.data
    except:
        students = []
    if not students:
        st.warning("کوئی طالب علم نہیں")
    else:
        with st.form("exam_request"):
            s_list = [f"{s['name']} ولد {s['father_name']} ({s['dept']})" for s in students]
            sel = st.selectbox("طالب علم", s_list)
            s_name, rest = sel.split(" ولد ")
            f_name, dept = rest.split(" (")
            dept = dept.replace(")", "")
            student_id = next((s["id"] for s in students if s["name"] == s_name and s["father_name"] == f_name), None)
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
                    to_para = col2.number_input("پارہ نمبر (اختتام)", min_value=from_para, max_value=30, value=min(from_para + 4, 30))
                    amount_read = st.text_input("مقدار خواندگی (مثلاً: 5 پارے, 10 سورتیں)", placeholder="مقدار")
                else:
                    col1, col2 = st.columns(2)
                    book_name = col1.text_input("کتاب کا نام", placeholder="مثلاً: نحو میر, قدوری")
                    amount_read = col2.text_input("مقدار خواندگی", placeholder="مثلاً: باب اول تا باب پنجم")
            if st.form_submit_button("بھیجیں"):
                if student_id:
                    supabase.table("exams").insert({
                        "student_id": student_id, "dept": dept, "exam_type": exam_type,
                        "from_para": int(from_para), "to_para": int(to_para),
                        "book_name": book_name, "amount_read": amount_read,
                        "start_date": str(start_date), "end_date": str(end_date),
                        "total_days": total_days, "status": "پینڈنگ"
                    }).execute()
                    st.success("درخواست بھیج دی گئی")

# 9.3 رخصت کی درخواست
elif selected == "📩 رخصت کی درخواست" and st.session_state.user_type == "teacher":
    st.header("📩 رخصت کی درخواست")
    with st.form("leave_request_form"):
        l_type = st.selectbox("رخصت کی نوعیت", ["بیماری", "ضروری کام", "ہنگامی", "دیگر"])
        start_date = st.date_input("تاریخ آغاز", date.today())
        days = st.number_input("دنوں کی تعداد", min_value=1, max_value=30, value=1)
        back_date = start_date + timedelta(days=days - 1)
        st.write(f"واپسی کی تاریخ: {back_date}")
        reason = st.text_area("تفصیلی وجہ")
        if st.form_submit_button("درخواست جمع کریں"):
            if reason:
                supabase.table("leave_requests").insert({
                    "t_name": st.session_state.username, "l_type": l_type,
                    "start_date": str(start_date), "days": int(days),
                    "reason": reason, "status": "پینڈنگ",
                    "notification_seen": 0, "request_date": str(date.today())
                }).execute()
                log_audit(st.session_state.username, "Leave Requested", f"{l_type} for {days} days")
                st.success("درخواست بھیج دی گئی۔ منتظمین جلد جواب دیں گے۔")
            else:
                st.error("براہ کرم وجہ تحریر کریں")

# 9.4 میری حاضری
elif selected == "🕒 میری حاضری" and st.session_state.user_type == "teacher":
    st.header("🕒 میری حاضری")
    today = date.today()
    try:
        res = supabase.table("t_attendance").select("arrival, departure").eq("t_name", st.session_state.username).eq("a_date", str(today)).execute()
        rec = res.data[0] if res.data else None
    except:
        rec = None
    if not rec:
        col1, col2 = st.columns(2)
        arr_date = col1.date_input("تاریخ", today)
        arr_time = col2.time_input("آمد کا وقت", datetime.now().time())
        if st.button("آمد درج کریں"):
            time_str = arr_time.strftime("%I:%M %p")
            supabase.table("t_attendance").insert({
                "t_name": st.session_state.username, "a_date": str(arr_date),
                "arrival": time_str, "actual_arrival": get_pk_time()
            }).execute()
            st.success("آمد درج ہو گئی")
            st.rerun()
    elif rec and rec.get("departure") is None:
        st.success(f"آمد: {rec['arrival']}")
        dep_time = st.time_input("رخصت کا وقت", datetime.now().time())
        if st.button("رخصت درج کریں"):
            time_str = dep_time.strftime("%I:%M %p")
            supabase.table("t_attendance").update({
                "departure": time_str, "actual_departure": get_pk_time()
            }).eq("t_name", st.session_state.username).eq("a_date", str(today)).execute()
            st.success("رخصت درج ہو گئی")
            st.rerun()
    else:
        st.success(f"آمد: {rec['arrival']} | رخصت: {rec['departure']}")

# 9.5 میرا ٹائم ٹیبل
elif selected == "📚 میرا ٹائم ٹیبل" and st.session_state.user_type == "teacher":
    st.header("📚 میرا ٹائم ٹیبل")
    try:
        res = supabase.table("timetable").select("day, period, book, room").eq("t_name", st.session_state.username).execute()
        if not res.data:
            st.info("ابھی آپ کا ٹائم ٹیبل ترتیب نہیں دیا گیا")
        else:
            tt_df = pd.DataFrame(res.data)
            tt_df = tt_df.rename(columns={"day": "دن", "period": "وقت", "book": "کتاب", "room": "کمرہ"})
            day_order = {"ہفتہ": 0, "اتوار": 1, "پیر": 2, "منگل": 3, "بدھ": 4, "جمعرات": 5}
            tt_df['day_order'] = tt_df['دن'].map(day_order)
            tt_df = tt_df.sort_values(['day_order', 'وقت'])
            pivot = tt_df.pivot(index='وقت', columns='دن', values='کتاب').fillna("—")
            st.dataframe(pivot, use_container_width=True)
            html_timetable = generate_timetable_html(tt_df)
            st.download_button("📥 HTML ڈاؤن لوڈ کریں", html_timetable,
                               f"Timetable_{st.session_state.username}.html", "text/html")
            if st.button("🖨️ پرنٹ کریں"):
                st.components.v1.html(f"<script>var w=window.open();w.document.write(`{html_timetable}`);w.print();</script>", height=0)
    except Exception as e:
        st.error(f"خرابی: {e}")

# ==================== مائیگریشن سیکشن ====================
if selected == "🔄 ڈیٹا منتقلی" and st.session_state.user_type == "admin":
    st.header("🔄 SQLite سے Supabase ڈیٹا منتقلی")
    st.warning("⚠️ یہ Supabase کا موجودہ ڈیٹا مٹا کر نئے سے بھر دے گا!")

    # ------------------ Supabase کلائنٹ تیار کریں ------------------
    try:
        from supabase import create_client, Client
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        supabase: Client = create_client(url, key)
    except Exception as e:
        st.error(f"❌ Supabase سے رابطہ نہیں ہو سکا: {e}")
        st.stop()

    # ------------------ SQLite فائل اپ لوڈ کریں ------------------
    db_file = st.file_uploader("پرانی .db فائل اپ لوڈ کریں", type=["db"])

    if db_file:
        st.info(f"فائل: {db_file.name} ({db_file.size // 1024} KB)")
        confirm = st.checkbox("میں سمجھتا ہوں کہ موجودہ Supabase ڈیٹا ختم ہو جائے گا")

        if confirm and st.button("🚀 منتقلی شروع کریں"):
            import sqlite3
            import os
            import hashlib

            # فائل کو /tmp میں عارضی طور پر محفوظ کریں
            tmp_path = "/tmp/migration_db.db"
            with open(tmp_path, "wb") as f:
                f.write(db_file.getvalue())

            # SQLite کنکشن قائم کریں
            try:
                mig_conn = sqlite3.connect(tmp_path)
                mig_conn.row_factory = sqlite3.Row
                mig_c = mig_conn.cursor()
                st.success("✅ فائل کھل گئی")
            except Exception as e:
                st.error(f"❌ فائل نہیں کھلی: {e}")
                st.stop()

            # ------------------ ڈیٹا کو محفوظ شکل دینے والا فنکشن ------------------
            def safe(val):
                """SQLite سے آنے والی قیمت کو Supabase کے لیے محفوظ بنائیں"""
                if val is None:
                    return None
                if isinstance(val, str) and val.strip() == "":
                    return None
                # تاریخ DD-MM-YYYY کو YYYY-MM-DD میں بدلیں (اگر ضروری ہو)
                if isinstance(val, str) and len(val) == 10 and val[2] == '-' and val[5] == '-':
                    try:
                        parts = val.split('-')
                        return f"{parts[2]}-{parts[1]}-{parts[0]}"
                    except:
                        pass
                return val

            # ------------------ Supabase میں ریکارڈ داخل کرنے کا فنکشن ------------------
            def do_insert(table_name, records, progress_bar, status_text):
                """
                table_name: Supabase ٹیبل کا نام
                records: ڈکشنریوں کی فہرست
                """
                if not records:
                    status_text.text(f"⚠️ {table_name}: کوئی ریکارڈ نہیں ملا")
                    return 0, 0

                total = len(records)
                inserted = 0
                failed = 0

                # بیچوں میں ڈیٹا بھیجیں (ہر بیچ میں زیادہ سے زیادہ 50 ریکارڈ)
                batch_size = 50
                for i in range(0, total, batch_size):
                    batch = records[i:i + batch_size]
                    try:
                        # پہلے پورے بیچ کو ایک ساتھ داخل کرنے کی کوشش کریں
                        supabase.table(table_name).insert(batch).execute()
                        inserted += len(batch)
                    except Exception as e:
                        # اگر بیچ ناکام ہو تو ایک ایک ریکارڈ کر کے آزمائیں
                        for rec in batch:
                            try:
                                supabase.table(table_name).insert(rec).execute()
                                inserted += 1
                            except Exception as inner_e:
                                failed += 1
                                # st.warning(f"{table_name}: ریکارڈ داخل نہ ہو سکا - {inner_e}")

                return inserted, failed

            # مائیگریشن کی بنیادی معلومات
            log_lines = []
            progress = st.progress(0)
            status = st.empty()

            try:
                # ── 1. TEACHERS ──
                status.info("اساتذہ...")
                rows = mig_c.execute("SELECT * FROM teachers").fetchall()
                recs = []
                for row in rows:
                    row = dict(row)
                    pwd = str(row.get("password") or "jamia123")
                    hashed = hashlib.sha256(pwd.encode()).hexdigest() if len(pwd) != 64 else pwd
                    recs.append({
                        "name": safe(row.get("name")),
                        "password": hashed,
                        "dept": safe(row.get("dept")),
                        "phone": safe(row.get("phone")),
                        "address": safe(row.get("address")),
                        "id_card": safe(row.get("id_card")),
                        "joining_date": safe(row.get("joining_date")),
                    })
                log_lines.append(do_insert("teachers", recs, progress, status))
                progress.progress(10)

                # ── 2. STUDENTS (ID محفوظ رکھیں) ──
                status.info("طلباء...")
                rows = mig_c.execute("SELECT * FROM students").fetchall()
                sqlite_students = {dict(r)["id"]: dict(r) for r in rows}
                sqlite_to_sb = {}  # SQLite ID → Supabase ID

                total_s = len(sqlite_students)
                for idx, (sqlite_id, row) in enumerate(sqlite_students.items()):
                    try:
                        res = supabase.table("students").insert({
                            "name": safe(row.get("name")),
                            "father_name": safe(row.get("father_name")),
                            "mother_name": safe(row.get("mother_name")),
                            "dob": safe(row.get("dob")),
                            "admission_date": safe(row.get("admission_date")),
                            "exit_date": safe(row.get("exit_date")),
                            "exit_reason": safe(row.get("exit_reason")),
                            "id_card": safe(row.get("id_card")),
                            "phone": safe(row.get("phone")),
                            "address": safe(row.get("address")),
                            "teacher_name": safe(row.get("teacher_name")),
                            "dept": safe(row.get("dept")),
                            "class": safe(row.get("class")),
                            "section": safe(row.get("section")),
                            "roll_no": safe(row.get("roll_no")),
                        }).execute()
                        new_id = res.data[0]["id"]
                        sqlite_to_sb[sqlite_id] = new_id
                        status.info(f"طلباء: {idx+1}/{total_s}")
                    except Exception as e:
                        log_lines.append(f"⚠️ طالب علم skip {sqlite_id}: {e}")

                log_lines.append(f"✅ students: {len(sqlite_to_sb)}/{total_s}")
                progress.progress(22)

                # ── 3. HIFZ RECORDS ──
                status.info("حفظ ریکارڈ... (665 ریکارڈ، تھوڑا وقت لگے گا)")
                rows = mig_c.execute("SELECT * FROM hifz_records").fetchall()
                recs = []
                for row in rows:
                    row = dict(row)
                    sb_sid = sqlite_to_sb.get(row.get("student_id"))
                    if not sb_sid:
                        continue
                    recs.append({
                        "r_date": safe(row.get("r_date")),
                        "student_id": sb_sid,
                        "t_name": safe(row.get("t_name")),
                        "surah": safe(row.get("surah")),
                        "a_from": safe(row.get("a_from")),
                        "a_to": safe(row.get("a_to")),
                        "sq_p": safe(row.get("sq_p")),
                        "sq_a": int(row.get("sq_a") or 0),
                        "sq_m": int(row.get("sq_m") or 0),
                        "m_p": safe(row.get("m_p")),
                        "m_a": int(row.get("m_a") or 0),
                        "m_m": int(row.get("m_m") or 0),
                        "attendance": safe(row.get("attendance")),
                        "principal_note": safe(row.get("principal_note")),
                        "lines": int(row.get("lines") or 0),
                        "cleanliness": safe(row.get("cleanliness")),
                    })
                log_lines.append(do_insert("hifz_records", recs, progress, status))
                progress.progress(55)

                # ── 4. QAIDA RECORDS ──
                status.info("قاعدہ ریکارڈ...")
                rows = mig_c.execute("SELECT * FROM qaida_records").fetchall()
                recs = []
                for row in rows:
                    row = dict(row)
                    sb_sid = sqlite_to_sb.get(row.get("student_id"))
                    if not sb_sid:
                        continue
                    recs.append({
                        "r_date": safe(row.get("r_date")),
                        "student_id": sb_sid,
                        "t_name": safe(row.get("t_name")),
                        "lesson_no": safe(row.get("lesson_no")),
                        "total_lines": int(row.get("total_lines") or 0),
                        "details": safe(row.get("details")),
                        "attendance": safe(row.get("attendance")),
                        "principal_note": safe(row.get("principal_note")),
                        "cleanliness": safe(row.get("cleanliness")),
                    })
                log_lines.append(do_insert("qaida_records", recs, progress, status))
                progress.progress(70)

                # ── 5. TIMETABLE ──
                status.info("ٹائم ٹیبل...")
                rows = mig_c.execute("SELECT * FROM timetable").fetchall()
                recs = [
                    {
                        "t_name": safe(dict(r).get("t_name")),
                        "day": safe(dict(r).get("day")),
                        "period": safe(dict(r).get("period")),
                        "book": safe(dict(r).get("book")),
                        "room": safe(dict(r).get("room"))
                    }
                    for r in rows
                ]
                log_lines.append(do_insert("timetable", recs, progress, status))
                progress.progress(78)

                # ── 6. EXAMS ──
                status.info("امتحانات...")
                rows = mig_c.execute("SELECT * FROM exams").fetchall()
                recs = []
                for row in rows:
                    row = dict(row)
                    sb_sid = sqlite_to_sb.get(row.get("student_id"))
                    if not sb_sid:
                        continue
                    recs.append({
                        "student_id": sb_sid,
                        "dept": safe(row.get("dept")),
                        "exam_type": safe(row.get("exam_type")),
                        "from_para": int(row.get("from_para") or 0),
                        "to_para": int(row.get("to_para") or 0),
                        "book_name": safe(row.get("book_name")),
                        "amount_read": safe(row.get("amount_read")),
                        "start_date": safe(row.get("start_date")),
                        "end_date": safe(row.get("end_date")),
                        "total_days": int(row.get("total_days") or 0),
                        "q1": int(row.get("q1") or 0),
                        "q2": int(row.get("q2") or 0),
                        "q3": int(row.get("q3") or 0),
                        "q4": int(row.get("q4") or 0),
                        "q5": int(row.get("q5") or 0),
                        "total": int(row.get("total") or 0),
                        "grade": safe(row.get("grade")),
                        "status": safe(row.get("status")),
                    })
                log_lines.append(do_insert("exams", recs, progress, status))
                progress.progress(84)

                # ── 7. PASSED PARAS ──
                status.info("پاس شدہ پارے...")
                rows = mig_c.execute("SELECT * FROM passed_paras").fetchall()
                recs = []
                for row in rows:
                    row = dict(row)
                    sb_sid = sqlite_to_sb.get(row.get("student_id"))
                    if not sb_sid:
                        continue
                    recs.append({
                        "student_id": sb_sid,
                        "para_no": row.get("para_no"),
                        "book_name": safe(row.get("book_name")),
                        "passed_date": safe(row.get("passed_date")),
                        "exam_type": safe(row.get("exam_type")),
                        "grade": safe(row.get("grade")),
                        "marks": int(row.get("marks") or 0),
                    })
                log_lines.append(do_insert("passed_paras", recs, progress, status))
                progress.progress(89)

                # ── 8. T_ATTENDANCE ──
                status.info("اساتذہ حاضری...")
                rows = mig_c.execute("SELECT * FROM t_attendance").fetchall()
                recs = [
                    {
                        "t_name": safe(dict(r).get("t_name")),
                        "a_date": safe(dict(r).get("a_date")),
                        "arrival": safe(dict(r).get("arrival")),
                        "departure": safe(dict(r).get("departure"))
                    }
                    for r in rows
                ]
                log_lines.append(do_insert("t_attendance", recs, progress, status))
                progress.progress(93)

                # ── 9. LEAVE REQUESTS ──
                status.info("رخصت درخواستیں...")
                rows = mig_c.execute("SELECT * FROM leave_requests").fetchall()
                recs = []
                for row in rows:
                    row = dict(row)
                    recs.append({
                        "t_name": safe(row.get("t_name")),
                        "reason": safe(row.get("reason")),
                        "start_date": safe(row.get("start_date")),
                        "back_date": safe(row.get("back_date")),
                        "status": safe(row.get("status")),
                        "request_date": safe(row.get("request_date")),
                        "l_type": safe(row.get("l_type")) or "دیگر",
                        "days": int(row.get("days") or 1),
                        "notification_seen": int(row.get("notification_seen") or 0),
                    })
                log_lines.append(do_insert("leave_requests", recs, progress, status))
                progress.progress(96)

                # ── 10. STAFF MONITORING ──
                status.info("عملہ نگرانی...")
                rows = mig_c.execute("SELECT * FROM staff_monitoring").fetchall()
                recs = []
                for row in rows:
                    row = dict(row)
                    recs.append({
                        "staff_name": safe(row.get("staff_name")),
                        "date": safe(row.get("date")),
                        "note_type": safe(row.get("note_type")),
                        "description": safe(row.get("description")),
                        "action_taken": safe(row.get("action_taken")),
                        "status": safe(row.get("status")),
                        "created_by": safe(row.get("created_by")),
                        "created_at": safe(row.get("created_at")),
                    })
                log_lines.append(do_insert("staff_monitoring", recs, progress, status))
                progress.progress(100)

                mig_conn.close()
                try:
                    os.remove(tmp_path)
                except:
                    pass

                status.success("✅ منتقلی مکمل!")
                st.text_area("نتیجہ:", "\n".join(log_lines), height=300)

            except Exception as e:
                st.error(f"❌ خرابی: {e}")
                import traceback
                st.code(traceback.format_exc())
                try:
                    mig_conn.close()
                    os.remove(tmp_path)
                except:
                    pass
# ==================== 10. لاگ آؤٹ ====================
st.sidebar.divider()
if st.sidebar.button("🚪 لاگ آؤٹ"):
    st.session_state.logged_in = False
    st.rerun()
