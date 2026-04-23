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
# یہی URL/KEY لڑکوں والی ایپ کی طرح — ٹیبلز g_ سے شروع ہوتی ہیں
SUPABASE_URL = st.secrets["connections"]["supabase"]["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["connections"]["supabase"]["SUPABASE_KEY"]

@st.cache_resource
def get_supabase_client():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase_client()

# تمام ٹیبل نام g_ سے شروع
T_TEACHERS     = "g_teachers"
T_STUDENTS     = "g_students"
T_HIFZ         = "g_hifz_records"
T_QAIDA        = "g_qaida_records"
T_GENERAL      = "g_general_education"
T_ATTENDANCE   = "g_t_attendance"
T_LEAVE        = "g_leave_requests"
T_EXAMS        = "g_exams"
T_PARAS        = "g_passed_paras"
T_TIMETABLE    = "g_timetable"
T_NOTIFS       = "g_notifications"
T_AUDIT        = "g_audit_log"
T_MONITORING   = "g_staff_monitoring"

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def ensure_admin():
    try:
        res = supabase.table(T_TEACHERS).select("id").eq("name", "admin").execute()
        if not res.data:
            supabase.table(T_TEACHERS).insert({
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
        supabase.table(T_AUDIT).insert({
            "user": user, "action": action,
            "timestamp": datetime.now().isoformat(), "details": details
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
    if attendance == "غیر حاضر": return "غیر حاضر"
    if attendance == "رخصت": return "رخصت"
    nagha_count = sum([sabaq_nagha, sq_nagha, m_nagha])
    if nagha_count == 1: return "ناقص (ناغہ)"
    elif nagha_count == 2: return "کمزور (ناغہ)"
    elif nagha_count == 3: return "ناکام (مکمل ناغہ)"
    total_mistakes = sq_mistakes + m_mistakes
    if total_mistakes <= 2: return "ممتاز"
    elif total_mistakes <= 5: return "جید جداً"
    elif total_mistakes <= 8: return "جید"
    elif total_mistakes <= 12: return "مقبول"
    else: return "دوبارہ کوشش کریں"

def cleanliness_to_score(clean):
    if clean == "بہترین": return 3
    elif clean == "بہتر": return 2
    elif clean == "ناقص": return 1
    else: return 0

def flatten_join(data, join_key):
    flat = []
    for row in data:
        r = {k: v for k, v in row.items() if k != join_key}
        if row.get(join_key):
            r.update(row[join_key])
        flat.append(r)
    return flat

def safe_str_date(val):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if isinstance(val, (date, datetime)):
        return val.strftime("%Y-%m-%d")
    return str(val) if val else None

def verify_login(username, password):
    try:
        res = supabase.table(T_TEACHERS).select("*").eq("name", username).execute()
        if res.data:
            row = res.data[0]
            stored = row["password"]
            if stored == password or stored == hash_password(password):
                return row
    except:
        pass
    return None

def change_password(user, old_pass, new_pass):
    try:
        res = supabase.table(T_TEACHERS).select("password").eq("name", user).execute()
        if not res.data:
            return False
        stored = res.data[0]["password"]
        if stored != old_pass and stored != hash_password(old_pass):
            return False
        supabase.table(T_TEACHERS).update({"password": hash_password(new_pass)}).eq("name", user).execute()
        log_audit(user, "Password Changed", "Success")
        return True
    except:
        return False

def admin_reset_password(teacher_name, new_pass):
    supabase.table(T_TEACHERS).update({"password": hash_password(new_pass)}).eq("name", teacher_name).execute()
    log_audit(st.session_state.username, "Admin Reset Password", f"Teacher: {teacher_name}")

# ==================== HTML جنریٹرز (للبنات) ====================
def generate_para_report(student_name, father_name, passed_paras_df):
    if passed_paras_df.empty:
        return "<p>کوئی پاس شدہ پارہ نہیں</p>"
    html_table = passed_paras_df.to_html(index=False, border=1, justify='center', escape=False)
    return f"""<!DOCTYPE html><html dir="rtl">
    <head><meta charset="UTF-8">
    <style>
        body{{font-family:'Noto Nastaliq Urdu',Arial,sans-serif;direction:rtl;text-align:right;margin:20px}}
        h2,h3{{text-align:center;color:#8B008B}}
        table{{width:100%;border-collapse:collapse;margin:20px 0}}
        th,td{{border:1px solid #ddd;padding:8px;text-align:center}}
        th{{background-color:#fce4ec}}
        @media print{{.no-print{{display:none}}}}
    </style></head>
    <body>
        <h2>جامعہ ملیہ اسلامیہ للبنات</h2>
        <h3>پارہ تعلیمی رپورٹ</h3>
        <p><b>طالبہ:</b> {student_name} بنت {father_name}</p>
        {html_table}
        <div style="display:flex;justify-content:space-between;margin-top:50px">
            <span>دستخط معلمہ: _______________________</span>
            <span>دستخط مہتممہ: _______________________</span>
        </div>
        <div class="no-print" style="text-align:center;margin-top:30px">
            <button onclick="window.print()">🖨️ پرنٹ کریں</button>
        </div>
    </body></html>"""

def generate_html_report(df, title, student_name="", start_date="", end_date="", passed_paras=None):
    html_table = df.to_html(index=False, border=1, justify='center', escape=False)
    passed_html = f"<div><b>پاس شدہ پارے:</b> {', '.join(map(str, passed_paras))}</div>" if passed_paras else ""
    return f"""<!DOCTYPE html><html dir="rtl">
    <head><meta charset="UTF-8"><title>{title}</title>
    <style>
        body{{font-family:'Noto Nastaliq Urdu',Arial,sans-serif;direction:rtl;text-align:right;margin:20px}}
        h2,h3{{text-align:center;color:#8B008B}}
        table{{width:100%;border-collapse:collapse;margin:20px 0}}
        th,td{{border:1px solid #ddd;padding:8px;text-align:center}}
        th{{background-color:#fce4ec}}
        @media print{{.no-print{{display:none}}}}
    </style></head>
    <body>
        <h2>جامعہ ملیہ اسلامیہ للبنات</h2>
        <h3>{title}</h3>
        {f'<p><b>طالبہ:</b> {student_name} &nbsp; <b>تاریخ:</b> {start_date} تا {end_date}</p>' if student_name else ''}
        {html_table}{passed_html}
        <div style="display:flex;justify-content:space-between;margin-top:50px">
            <span>دستخط معلمہ: _______________________</span>
            <span>دستخط مہتممہ: _______________________</span>
        </div>
        <div class="no-print" style="text-align:center;margin-top:30px">
            <button onclick="window.print()">🖨️ پرنٹ کریں</button>
        </div>
    </body></html>"""

def generate_timetable_html(df_timetable):
    if df_timetable.empty:
        return "<p>کوئی ٹائم ٹیبل دستیاب نہیں</p>"
    day_order = {"ہفتہ": 0, "اتوار": 1, "پیر": 2, "منگل": 3, "بدھ": 4, "جمعرات": 5}
    df_timetable['day_order'] = df_timetable['دن'].map(day_order)
    df_timetable = df_timetable.sort_values(['day_order', 'وقت'])
    pivot = df_timetable.pivot(index='وقت', columns='دن', values='کتاب').fillna("—")
    return f"""<!DOCTYPE html><html dir="rtl">
    <head><meta charset="UTF-8">
    <style>
        body{{font-family:'Noto Nastaliq Urdu',Arial,sans-serif;direction:rtl;text-align:right;margin:20px}}
        h2,h3{{text-align:center;color:#8B008B}}
        table{{width:100%;border-collapse:collapse;margin:20px 0}}
        th,td{{border:1px solid #ddd;padding:8px;text-align:center}}
        th{{background-color:#fce4ec}}
        @media print{{.no-print{{display:none}}}}
    </style></head>
    <body>
        <h2>جامعہ ملیہ اسلامیہ للبنات</h2>
        <h3>ٹائم ٹیبل</h3>
        {pivot.to_html(border=1, justify='center', escape=False)}
        <div style="display:flex;justify-content:space-between;margin-top:50px">
            <span>دستخط معلمہ: _______________________</span>
            <span>دستخط مہتممہ: _______________________</span>
        </div>
        <div class="no-print" style="text-align:center;margin-top:30px">
            <button onclick="window.print()">🖨️ پرنٹ کریں</button>
        </div>
    </body></html>"""

# ==================== 3. اسٹائلنگ (نسائی رنگ) ====================
st.set_page_config(page_title="جامعہ ملیہ اسلامیہ للبنات | سمارٹ ERP", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu&display=swap');
    * { font-family: 'Noto Nastaliq Urdu', Arial, sans-serif; }
    body { direction: rtl; text-align: right; background: linear-gradient(135deg, #fdf8f5, #fce4ec); }
    .stSidebar { background: linear-gradient(180deg, #8B008B, #4A004A); color: white; }
    .stSidebar * { color: white !important; }
    .stButton > button { background: linear-gradient(90deg, #8B008B, #C71585); color: white; border-radius: 30px; border: none; padding: 0.5rem 1rem; font-weight: bold; transition: 0.3s; width: 100%; }
    .stButton > button:hover { transform: scale(1.02); }
    .main-header { text-align: center; background: linear-gradient(135deg, #fce4ec, #f8bbd0); padding: 1rem; border-radius: 20px; margin-bottom: 1rem; border-bottom: 4px solid #8B008B; }
    .report-card { background: white; border-radius: 15px; padding: 1rem; box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin-bottom: 1rem; }
    .stTabs [data-baseweb="tab"] { border-radius: 30px; background-color: #f8bbd0; }
    .stTabs [aria-selected="true"] { background: linear-gradient(90deg, #8B008B, #C71585); color: white; }
    .best-student-card { background: linear-gradient(135deg, #fff9e6, #ffe6f0); border-radius: 20px; padding: 20px; text-align: center; box-shadow: 0 8px 16px rgba(0,0,0,0.1); transition: 0.3s; }
    .best-student-card:hover { transform: translateY(-5px); }
    .gold { color: #d4af37; } .silver { color: #a0a0a0; } .bronze { color: #cd7f32; }
</style>
""", unsafe_allow_html=True)

# ==================== 4. لاگ ان ====================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<div class='main-header'><h1>🕌 جامعہ ملیہ اسلامیہ للبنات</h1><p>اسمارٹ تعلیمی و انتظامی پورٹل</p></div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<div class='report-card'><h3>🔐 لاگ ان</h3>", unsafe_allow_html=True)
        u = st.text_input("صارف نام")
        p = st.text_input("پاسورڈ", type="password")
        if st.button("داخل ہوں"):
            res = verify_login(u, p)
            if res:
                st.session_state.logged_in = True
                st.session_state.username = u
                st.session_state.user_type = "admin" if u == "admin" else "teacher"
                log_audit(u, "Login")
                st.rerun()
            else:
                st.error("غلط معلومات")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ==================== 5. مینو ====================
surahs_urdu = ["الفاتحة","البقرة","آل عمران","النساء","المائدة","الأنعام","الأعراف","الأنفال","التوبة","يونس","هود","يوسف","الرعد","إبراهيم","الحجر","النحل","الإسراء","الكهف","مريم","طه","الأنبياء","الحج","المؤمنون","النور","الفرقان","الشعراء","النمل","القصص","العنكبوت","الروم","لقمان","السجدة","الأحزاب","سبأ","فاطر","يس","الصافات","ص","الزمر","غافر","فصلت","الشورى","الزخرف","الدخان","الجاثية","الأحقاف","محمد","الفتح","الحجرات","ق","الذاريات","الطور","النجم","القمر","الرحمن","الواقعة","الحديد","المجادلة","الحشر","الممتحنة","الصف","الجمعة","المنافقون","التغابن","الطلاق","التحریم","الملک","القلم","الحاقة","المعارج","نوح","الجن","المزمل","المدثر","القیامة","الإنسان","المرسلات","النبأ","النازعات","عبس","التکویر","الإنفطار","المطففین","الإنشقاق","البروج","الطارق","الأعلى","الغاشیة","الفجر","البلد","الشمس","اللیل","الضحى","الشرح","التین","العلق","القدر","البینة","الزلزلة","العادیات","القارعة","التکاثر","العصر","الهمزة","الفیل","قریش","الماعون","الکوثر","الکافرون","النصر","المسد","الإخلاص","الفلق","الناس"]
paras = [f"پارہ {i}" for i in range(1, 31)]
cleanliness_options = ["بہترین", "بہتر", "ناقص"]

if st.session_state.user_type == "admin":
    menu = ["📊 ایڈمن ڈیش بورڈ", "📊 یومیہ تعلیمی رپورٹ", "🎓 امتحانی نظام", "📜 ماہانہ رزلٹ کارڈ",
            "📘 پارہ تعلیمی رپورٹ", "🕒 معلمات حاضری", "🏛️ رخصت کی منظوری",
            "👥 یوزر مینجمنٹ", "📚 ٹائم ٹیبل مینجمنٹ", "🔑 پاسورڈ تبدیل کریں",
            "📋 عملہ نگرانی و شکایات", "📢 نوٹیفیکیشنز", "📈 تجزیہ و رپورٹس",
            "🏆 ماہانہ بہترین طالبات", "⚙️ بیک اپ & سیٹنگز", "🔄 ڈیٹا منتقلی"]
else:
    menu = ["📝 روزانہ سبق اندراج", "🎓 امتحانی درخواست", "📩 رخصت کی درخواست",
            "🕒 میری حاضری", "📚 میرا ٹائم ٹیبل", "🔑 پاسورڈ تبدیل کریں", "📢 نوٹیفیکیشنز"]

selected = st.sidebar.radio("📌 مینو", menu)

# ==================== 6. ایڈمن ڈیش بورڈ ====================
if selected == "📊 ایڈمن ڈیش بورڈ" and st.session_state.user_type == "admin":
    st.markdown("<div class='main-header'><h1>📊 ایڈمن ڈیش بورڈ - للبنات</h1></div>", unsafe_allow_html=True)
    try:
        rs = supabase.table(T_STUDENTS).select("id", count="exact").execute()
        rt = supabase.table(T_TEACHERS).select("id", count="exact").neq("name", "admin").execute()
        st.metric("کل طالبات", rs.count or 0)
        st.metric("کل معلمات", rt.count or 0)
    except Exception as e:
        st.error(f"خرابی: {e}")

# ==================== 7. یومیہ تعلیمی رپورٹ ====================
elif selected == "📊 یومیہ تعلیمی رپورٹ" and st.session_state.user_type == "admin":
    st.header("📊 یومیہ تعلیمی رپورٹ")
    with st.sidebar:
        d1 = st.date_input("تاریخ آغاز", date.today().replace(day=1))
        d2 = st.date_input("تاریخ اختتام", date.today())
        dept_filter = st.selectbox("شعبہ", ["تمام", "حفظ", "قاعدہ", "درسِ نظامی", "عصری تعلیم"])
    combined_df = pd.DataFrame()
    if dept_filter in ["تمام", "حفظ"]:
        try:
            res = supabase.table(T_HIFZ).select(
                "r_date,t_name,surah,lines,sq_p,sq_m,sq_a,m_p,m_m,m_a,attendance,cleanliness,g_students(name,father_name,roll_no)"
            ).gte("r_date", str(d1)).lte("r_date", str(d2)).execute()
            if res.data:
                flat = flatten_join(res.data, "g_students")
                df = pd.DataFrame(flat)
                df["شعبہ"] = "حفظ"
                combined_df = pd.concat([combined_df, df], ignore_index=True)
        except Exception as e:
            st.error(f"حفظ: {e}")
    if dept_filter in ["تمام", "قاعدہ"]:
        try:
            res = supabase.table(T_QAIDA).select(
                "r_date,t_name,lesson_no,total_lines,details,attendance,cleanliness,g_students(name,father_name,roll_no)"
            ).gte("r_date", str(d1)).lte("r_date", str(d2)).execute()
            if res.data:
                flat = flatten_join(res.data, "g_students")
                df = pd.DataFrame(flat)
                df["شعبہ"] = "قاعدہ"
                combined_df = pd.concat([combined_df, df], ignore_index=True)
        except Exception as e:
            st.error(f"قاعدہ: {e}")
    if combined_df.empty:
        st.warning("کوئی ریکارڈ نہیں ملا")
    else:
        st.success(f"کل {len(combined_df)} ریکارڈ")
        st.dataframe(combined_df, use_container_width=True)
        html = generate_html_report(combined_df, "یومیہ تعلیمی رپورٹ - للبنات",
                                    start_date=str(d1), end_date=str(d2))
        st.download_button("📥 HTML رپورٹ", html, "daily_report_girls.html", "text/html")

# ==================== 8. امتحانی نظام ====================
elif selected == "🎓 امتحانی نظام" and st.session_state.user_type == "admin":
    st.header("🎓 امتحانی نظام - للبنات")
    tab1, tab2 = st.tabs(["پینڈنگ", "مکمل"])
    with tab1:
        try:
            res = supabase.table(T_EXAMS).select(
                "id,dept,exam_type,from_para,to_para,book_name,amount_read,start_date,end_date,total_days,student_id,g_students(name,father_name,roll_no)"
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
                stud = exam.get("g_students") or {}
                sn = stud.get("name", "")
                fn = stud.get("father_name", "")
                rn = stud.get("roll_no", "")
                stud_id = exam["student_id"]
                etype = exam["exam_type"]
                fp = exam["from_para"] or 0
                tp = exam["to_para"] or 0
                book = exam["book_name"] or ""
                with st.expander(f"{sn} بنت {fn} | {etype}"):
                    cols = st.columns(5)
                    q1 = cols[0].number_input("س1", 0, 20, key=f"q1_{eid}")
                    q2 = cols[1].number_input("س2", 0, 20, key=f"q2_{eid}")
                    q3 = cols[2].number_input("س3", 0, 20, key=f"q3_{eid}")
                    q4 = cols[3].number_input("س4", 0, 20, key=f"q4_{eid}")
                    q5 = cols[4].number_input("س5", 0, 20, key=f"q5_{eid}")
                    total = q1 + q2 + q3 + q4 + q5
                    g = "ممتاز" if total >= 90 else "جید جداً" if total >= 80 else "جید" if total >= 70 else "مقبول" if total >= 60 else "ناکام"
                    st.write(f"کل: {total} | گریڈ: {g}")
                    if st.button("کلیئر کریں", key=f"save_{eid}"):
                        supabase.table(T_EXAMS).update({
                            "q1": q1, "q2": q2, "q3": q3, "q4": q4, "q5": q5,
                            "total": total, "grade": g, "status": "مکمل",
                            "end_date": str(date.today())
                        }).eq("id", eid).execute()
                        if g != "ناکام" and etype == "پارہ ٹیسٹ" and fp:
                            for para in range(int(fp), int(tp) + 1):
                                chk = supabase.table(T_PARAS).select("id").eq("student_id", stud_id).eq("para_no", para).execute()
                                if not chk.data:
                                    supabase.table(T_PARAS).insert({
                                        "student_id": stud_id, "para_no": para,
                                        "passed_date": str(date.today()),
                                        "exam_type": etype, "grade": g, "marks": total
                                    }).execute()
                        st.success("کلیئر ہو گیا")
                        st.rerun()
    with tab2:
        try:
            res = supabase.table(T_EXAMS).select(
                "dept,exam_type,from_para,to_para,book_name,start_date,end_date,total,grade,g_students(name,father_name,roll_no)"
            ).eq("status", "مکمل").order("end_date", desc=True).execute()
            if res.data:
                flat = flatten_join(res.data, "g_students")
                st.dataframe(pd.DataFrame(flat), use_container_width=True)
            else:
                st.info("کوئی مکمل امتحان نہیں")
        except Exception as e:
            st.error(f"خرابی: {e}")

# ==================== 9. ماہانہ رزلٹ کارڈ ====================
elif selected == "📜 ماہانہ رزلٹ کارڈ" and st.session_state.user_type == "admin":
    st.header("📜 ماہانہ رزلٹ کارڈ - للبنات")
    try:
        res = supabase.table(T_STUDENTS).select("id,name,father_name,roll_no,dept").execute()
        students_list = res.data
    except:
        students_list = []
    if not students_list:
        st.warning("کوئی طالبہ نہیں")
    else:
        student_names = [f"{s['name']} بنت {s['father_name']} ({s['dept']})" for s in students_list]
        sel = st.selectbox("طالبہ منتخب کریں", student_names)
        s_name = sel.split(" بنت ")[0]
        rest = sel.split(" بنت ")[1]
        f_name = rest.split(" (")[0]
        dept = rest.split(" (")[1].replace(")", "")
        start = st.date_input("تاریخ آغاز", date.today().replace(day=1))
        end = st.date_input("تاریخ اختتام", date.today())
        student_id = next((s["id"] for s in students_list if s["name"] == s_name and s["father_name"] == f_name), None)
        if student_id and dept == "حفظ":
            res = supabase.table(T_HIFZ).select(
                "r_date,attendance,surah,sq_p,m_p,sq_m,m_m,cleanliness"
            ).eq("student_id", student_id).gte("r_date", str(start)).lte("r_date", str(end)).order("r_date").execute()
            if res.data:
                df = pd.DataFrame(res.data)
                st.dataframe(df, use_container_width=True)
                html = generate_html_report(df, "ماہانہ رزلٹ کارڈ (حفظ)",
                                            student_name=f"{s_name} بنت {f_name}",
                                            start_date=str(start), end_date=str(end))
                st.download_button("📥 HTML ڈاؤن لوڈ", html, f"{s_name}_result.html", "text/html")
        elif student_id and dept == "قاعدہ":
            res = supabase.table(T_QAIDA).select(
                "r_date,lesson_no,total_lines,details,attendance,cleanliness"
            ).eq("student_id", student_id).gte("r_date", str(start)).lte("r_date", str(end)).order("r_date").execute()
            if res.data:
                df = pd.DataFrame(res.data)
                st.dataframe(df, use_container_width=True)
                html = generate_html_report(df, "ماہانہ رزلٹ کارڈ (قاعدہ)",
                                            student_name=f"{s_name} بنت {f_name}",
                                            start_date=str(start), end_date=str(end))
                st.download_button("📥 HTML ڈاؤن لوڈ", html, f"{s_name}_qaida_result.html", "text/html")

# ==================== 10. پارہ تعلیمی رپورٹ ====================
elif selected == "📘 پارہ تعلیمی رپورٹ" and st.session_state.user_type == "admin":
    st.header("📘 پارہ تعلیمی رپورٹ - للبنات")
    try:
        res = supabase.table(T_STUDENTS).select("id,name,father_name").eq("dept", "حفظ").execute()
        students_list = res.data
    except:
        students_list = []
    if not students_list:
        st.warning("کوئی حفظ کی طالبہ نہیں")
    else:
        student_names = [f"{s['name']} بنت {s['father_name']}" for s in students_list]
        sel = st.selectbox("طالبہ منتخب کریں", student_names)
        s_name, f_name = sel.split(" بنت ")
        student_id = next((s["id"] for s in students_list if s["name"] == s_name and s["father_name"] == f_name), None)
        if student_id:
            res = supabase.table(T_PARAS).select(
                "para_no,passed_date,exam_type,grade,marks"
            ).eq("student_id", student_id).not_.is_("para_no", "null").order("para_no").execute()
            if not res.data:
                st.info("کوئی پاس شدہ پارہ نہیں")
            else:
                passed_df = pd.DataFrame(res.data)
                passed_df.columns = ["پارہ نمبر", "تاریخ پاس", "امتحان قسم", "گریڈ", "نمبر"]
                st.dataframe(passed_df, use_container_width=True)
                html = generate_para_report(s_name, f_name, passed_df)
                st.download_button("📥 رپورٹ ڈاؤن لوڈ", html, f"Para_{s_name}.html", "text/html")

# ==================== 11. معلمات حاضری ====================
elif selected == "🕒 معلمات حاضری" and st.session_state.user_type == "admin":
    st.header("معلمات حاضری ریکارڈ")
    try:
        res = supabase.table(T_ATTENDANCE).select("a_date,t_name,arrival,departure").order("a_date", desc=True).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            df.columns = ["تاریخ", "معلمہ", "آمد", "رخصت"]
            st.dataframe(df, use_container_width=True)
        else:
            st.info("کوئی ریکارڈ نہیں")
    except Exception as e:
        st.error(f"خرابی: {e}")

# ==================== 12. رخصت کی منظوری ====================
elif selected == "🏛️ رخصت کی منظوری" and st.session_state.user_type == "admin":
    st.header("رخصت کی منظوری - للبنات")
    try:
        res = supabase.table(T_LEAVE).select("id,t_name,l_type,reason,start_date,days").eq("status", "پینڈنگ").execute()
        pending = res.data
    except:
        pending = []
    if not pending:
        st.info("کوئی پینڈنگ درخواست نہیں")
    else:
        for lr in pending:
            l_id = lr["id"]
            with st.expander(f"{lr['t_name']} | {lr['l_type']} | {lr['days']} دن"):
                st.write(f"وجہ: {lr['reason']}")
                col1, col2 = st.columns(2)
                if col1.button("✅ منظور", key=f"app_{l_id}"):
                    supabase.table(T_LEAVE).update({"status": "منظور"}).eq("id", l_id).execute()
                    st.rerun()
                if col2.button("❌ مسترد", key=f"rej_{l_id}"):
                    supabase.table(T_LEAVE).update({"status": "مسترد"}).eq("id", l_id).execute()
                    st.rerun()

# ==================== 13. یوزر مینجمنٹ ====================
elif selected == "👥 یوزر مینجمنٹ" and st.session_state.user_type == "admin":
    st.header("👥 یوزر مینجمنٹ - للبنات")
    tab1, tab2 = st.tabs(["معلمات", "طالبات"])
    with tab1:
        try:
            res = supabase.table(T_TEACHERS).select("id,name,dept,phone,joining_date").neq("name", "admin").execute()
            teachers_df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        except Exception as e:
            st.error(f"خرابی: {e}")
            teachers_df = pd.DataFrame()
        if not teachers_df.empty:
            st.dataframe(teachers_df, use_container_width=True)
        with st.expander("➕ نئی معلمہ رجسٹر کریں"):
            with st.form("new_teacher_form"):
                name = st.text_input("معلمہ کا نام*")
                password = st.text_input("پاسورڈ*", type="password")
                dept = st.selectbox("شعبہ", ["حفظ", "قاعدہ", "درسِ نظامی", "عصری تعلیم"])
                phone = st.text_input("فون نمبر")
                address = st.text_area("پتہ")
                joining_date = st.date_input("تاریخ شمولیت", date.today())
                if st.form_submit_button("رجسٹر کریں"):
                    if name and password:
                        try:
                            supabase.table(T_TEACHERS).insert({
                                "name": name, "password": hash_password(password),
                                "dept": dept, "phone": phone, "address": address,
                                "joining_date": str(joining_date)
                            }).execute()
                            st.success("معلمہ رجسٹر ہو گئی")
                            st.rerun()
                        except Exception as e:
                            st.error(f"خرابی: {e}")
                    else:
                        st.error("نام اور پاسورڈ ضروری ہیں")
    with tab2:
        try:
            res = supabase.table(T_STUDENTS).select("id,name,father_name,dept,teacher_name,roll_no").execute()
            students_df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        except Exception as e:
            st.error(f"خرابی: {e}")
            students_df = pd.DataFrame()
        if not students_df.empty:
            edited = st.data_editor(students_df, num_rows="dynamic", use_container_width=True, key="students_edit")
            if st.button("تبدیلیاں محفوظ کریں"):
                try:
                    for _, row in edited.iterrows():
                        row_id = row.get("id")
                        data = {
                            "name": row.get("name"), "father_name": row.get("father_name"),
                            "dept": row.get("dept"), "teacher_name": row.get("teacher_name"),
                            "roll_no": row.get("roll_no")
                        }
                        if pd.isna(row_id) or row_id == 0:
                            supabase.table(T_STUDENTS).insert(data).execute()
                        else:
                            supabase.table(T_STUDENTS).update(data).eq("id", int(row_id)).execute()
                    st.success("محفوظ ہو گیا")
                    st.rerun()
                except Exception as e:
                    st.error(f"خرابی: {e}")
        with st.expander("➕ نئی طالبہ داخل کریں"):
            with st.form("new_student_form"):
                col1, col2 = st.columns(2)
                with col1:
                    name = st.text_input("طالبہ کا نام*")
                    father = st.text_input("والد کا نام*")
                    mother = st.text_input("والدہ کا نام")
                    dob = st.date_input("تاریخ پیدائش", date.today() - timedelta(days=365*10))
                    admission_date = st.date_input("تاریخ داخلہ", date.today())
                    roll_no = st.text_input("شناختی نمبر")
                with col2:
                    dept = st.selectbox("شعبہ*", ["حفظ", "قاعدہ", "درسِ نظامی", "عصری تعلیم"])
                    try:
                        tres = supabase.table(T_TEACHERS).select("name").neq("name", "admin").execute()
                        teachers_list = [r["name"] for r in tres.data]
                    except:
                        teachers_list = []
                    teacher = st.selectbox("معلمہ*", teachers_list) if teachers_list else st.text_input("معلمہ کا نام*")
                    phone = st.text_input("فون نمبر")
                    address = st.text_area("پتہ")
                if st.form_submit_button("داخلہ کریں"):
                    if name and father and teacher and dept:
                        try:
                            supabase.table(T_STUDENTS).insert({
                                "name": name, "father_name": father, "mother_name": mother,
                                "dob": str(dob), "admission_date": str(admission_date),
                                "teacher_name": teacher, "dept": dept,
                                "phone": phone, "address": address, "roll_no": roll_no
                            }).execute()
                            st.success("طالبہ کامیابی سے داخل ہو گئی")
                            st.rerun()
                        except Exception as e:
                            st.error(f"خرابی: {e}")
                    else:
                        st.error("نام، ولدیت، معلمہ اور شعبہ ضروری ہیں")

# ==================== 14. ٹائم ٹیبل ====================
elif selected == "📚 ٹائم ٹیبل مینجمنٹ" and st.session_state.user_type == "admin":
    st.header("📚 ٹائم ٹیبل مینجمنٹ - للبنات")
    try:
        res = supabase.table(T_TEACHERS).select("name").neq("name", "admin").execute()
        teachers = [r["name"] for r in res.data]
    except:
        teachers = []
    if not teachers:
        st.warning("پہلے معلمات رجسٹر کریں")
    else:
        sel_t = st.selectbox("معلمہ منتخب کریں", teachers)
        try:
            res = supabase.table(T_TIMETABLE).select("id,day,period,book,room").eq("t_name", sel_t).execute()
            if res.data:
                df = pd.DataFrame(res.data)
                df.columns = ["id", "دن", "وقت", "کتاب", "کمرہ"]
                st.dataframe(df[["دن", "وقت", "کتاب", "کمرہ"]], use_container_width=True)
        except Exception as e:
            st.error(f"خرابی: {e}")
        with st.expander("➕ نیا پیریڈ شامل کریں"):
            with st.form("add_period"):
                col1, col2 = st.columns(2)
                day = col1.selectbox("دن", ["ہفتہ", "اتوار", "پیر", "منگل", "بدھ", "جمعرات"])
                period = col2.text_input("وقت (مثلاً 08:00-09:00)")
                book = st.text_input("کتاب / مضمون")
                room = st.text_input("کمرہ نمبر")
                if st.form_submit_button("شامل کریں"):
                    supabase.table(T_TIMETABLE).insert({
                        "t_name": sel_t, "day": day, "period": period, "book": book, "room": room
                    }).execute()
                    st.success("پیریڈ شامل کر دیا گیا")
                    st.rerun()

# ==================== 15. پاسورڈ تبدیل کریں ====================
elif selected == "🔑 پاسورڈ تبدیل کریں":
    st.header("🔑 پاسورڈ تبدیل کریں")
    if st.session_state.user_type == "admin":
        try:
            res = supabase.table(T_TEACHERS).select("name").neq("name", "admin").execute()
            teachers = [r["name"] for r in res.data]
        except:
            teachers = []
        if teachers:
            sel_t = st.selectbox("معلمہ منتخب کریں", teachers)
            new_pass = st.text_input("نیا پاسورڈ", type="password")
            confirm = st.text_input("تصدیق کریں", type="password")
            if st.button("پاسورڈ تبدیل کریں"):
                if new_pass and new_pass == confirm:
                    admin_reset_password(sel_t, new_pass)
                    st.success(f"{sel_t} کا پاسورڈ تبدیل کر دیا گیا")
                else:
                    st.error("پاسورڈ میل نہیں کھاتے")
    else:
        old_pass = st.text_input("پرانا پاسورڈ", type="password")
        new_pass = st.text_input("نیا پاسورڈ", type="password")
        confirm = st.text_input("نیا پاسورڈ دوبارہ", type="password")
        if st.button("اپنا پاسورڈ تبدیل کریں"):
            if new_pass and new_pass == confirm:
                if change_password(st.session_state.username, old_pass, new_pass):
                    st.success("پاسورڈ تبدیل ہو گیا")
                    st.session_state.logged_in = False
                    st.rerun()
                else:
                    st.error("پرانا پاسورڈ غلط ہے")
            else:
                st.error("نئے پاسورڈ میل نہیں کھاتے")

# ==================== 16. نوٹیفیکیشنز ====================
elif selected == "📢 نوٹیفیکیشنز":
    st.header("نوٹیفیکیشن سینٹر - للبنات")
    if st.session_state.user_type == "admin":
        with st.form("new_notif"):
            title = st.text_input("عنوان")
            msg = st.text_area("پیغام")
            target = st.selectbox("بھیجیں", ["تمام", "اساتذہ", "طلبہ"])
            if st.form_submit_button("بھیجیں"):
                supabase.table(T_NOTIFS).insert({
                    "title": title, "message": msg,
                    "target": target, "created_at": datetime.now().isoformat()
                }).execute()
                st.success("نوٹیفکیشن بھیج دیا گیا")
    try:
        res = supabase.table(T_NOTIFS).select("title,message,created_at").order("created_at", desc=True).limit(10).execute()
        for n in res.data:
            st.info(f"**{n.get('title','')}**\n\n{n.get('message','')}")
    except:
        pass

# ==================== 17. عملہ نگرانی ====================
elif selected == "📋 عملہ نگرانی و شکایات" and st.session_state.user_type == "admin":
    st.header("📋 عملہ نگرانی - للبنات")
    tab1, tab2 = st.tabs(["➕ نیا اندراج", "📜 ریکارڈ"])
    with tab1:
        with st.form("monitoring_form"):
            try:
                res = supabase.table(T_TEACHERS).select("name").neq("name", "admin").execute()
                staff_list = [r["name"] for r in res.data]
            except:
                staff_list = []
            if staff_list:
                staff_name = st.selectbox("معلمہ کا نام", staff_list)
                note_date = st.date_input("تاریخ", date.today())
                note_type = st.selectbox("نوعیت", ["یادداشت", "شکایت", "تنبیہ", "تعریف", "کارکردگی جائزہ"])
                description = st.text_area("تفصیل")
                action_taken = st.text_area("کارروائی")
                status = st.selectbox("حالت", ["زیر التواء", "حل شدہ", "زیر غور"])
                if st.form_submit_button("محفوظ کریں"):
                    supabase.table(T_MONITORING).insert({
                        "staff_name": staff_name, "date": str(note_date),
                        "note_type": note_type, "description": description,
                        "action_taken": action_taken, "status": status,
                        "created_by": st.session_state.username,
                        "created_at": datetime.now().isoformat()
                    }).execute()
                    st.success("محفوظ ہو گیا")
    with tab2:
        try:
            res = supabase.table(T_MONITORING).select("*").order("date", desc=True).execute()
            if res.data:
                st.dataframe(pd.DataFrame(res.data), use_container_width=True)
            else:
                st.info("کوئی ریکارڈ نہیں")
        except Exception as e:
            st.error(f"خرابی: {e}")

# ==================== 18. ماہانہ بہترین طالبات ====================
elif selected == "🏆 ماہانہ بہترین طالبات" and st.session_state.user_type == "admin":
    st.markdown("<div class='main-header'><h1>🏆 ماہانہ بہترین طالبات</h1></div>", unsafe_allow_html=True)
    month_year = st.date_input("مہینہ منتخب کریں", date.today().replace(day=1))
    start_date = month_year.replace(day=1)
    end_date = (month_year.replace(month=month_year.month % 12 + 1, day=1) if month_year.month < 12
                else month_year.replace(year=month_year.year + 1, month=1, day=1)) - timedelta(days=1)
    try:
        res = supabase.table(T_STUDENTS).select("id,name,father_name,roll_no,dept").execute()
        students = res.data
    except:
        students = []
    student_scores = []
    for stud in students:
        sid = stud["id"]
        dept = stud["dept"]
        try:
            if dept == "حفظ":
                res = supabase.table(T_HIFZ).select("attendance,surah,sq_p,m_p,sq_m,m_m,cleanliness").eq("student_id", sid).gte("r_date", str(start_date)).lte("r_date", str(end_date)).execute()
                grade_scores = []
                clean_scores = []
                for rec in res.data:
                    att = rec["attendance"]
                    s_nagha = rec.get("surah") in ["ناغہ", "یاد نہیں"]
                    sq_nagha = rec.get("sq_p") in ["ناغہ", "یاد نہیں"]
                    m_nagha = rec.get("m_p") in ["ناغہ", "یاد نہیں"]
                    grade = calculate_grade_with_attendance(att, s_nagha, sq_nagha, m_nagha, rec.get("sq_m") or 0, rec.get("m_m") or 0)
                    grade_map = {"ممتاز": 100, "جید جداً": 85, "جید": 75, "مقبول": 60, "دوبارہ کوشش کریں": 40, "غیر حاضر": 0, "رخصت": 50}
                    grade_scores.append(grade_map.get(grade, 0))
                    if rec.get("cleanliness"):
                        clean_scores.append(cleanliness_to_score(rec["cleanliness"]))
                avg_grade = sum(grade_scores) / len(grade_scores) if grade_scores else 0
                avg_clean = sum(clean_scores) / len(clean_scores) if clean_scores else 0
            else:
                avg_grade = 0
                avg_clean = 0
            student_scores.append({"name": stud["name"], "father": stud["father_name"], "roll": stud["roll_no"], "dept": dept, "avg_grade": avg_grade, "avg_clean": avg_clean})
        except:
            pass
    sorted_grade = sorted(student_scores, key=lambda x: x["avg_grade"], reverse=True)
    sorted_clean = sorted(student_scores, key=lambda x: x["avg_clean"], reverse=True)
    st.subheader("📚 تعلیمی کارکردگی")
    col1, col2, col3 = st.columns(3)
    for i, stud in enumerate(sorted_grade[:3]):
        with [col1, col2, col3][i]:
            medal = ["🥇", "🥈", "🥉"][i]
            color = ["gold", "silver", "bronze"][i]
            st.markdown(f'<div class="best-student-card"><h2 class="{color}">{medal}</h2><h3>{stud["name"]}</h3><p>والد: {stud["father"]}</p><p>اوسط: {stud["avg_grade"]:.1f}%</p></div>', unsafe_allow_html=True)
    st.subheader("🧼 صفائی کارکردگی")
    col1, col2, col3 = st.columns(3)
    for i, stud in enumerate(sorted_clean[:3]):
        with [col1, col2, col3][i]:
            medal = ["🥇", "🥈", "🥉"][i]
            color = ["gold", "silver", "bronze"][i]
            st.markdown(f'<div class="best-student-card"><h2 class="{color}">{medal}</h2><h3>{stud["name"]}</h3><p>صفائی: {(stud["avg_clean"]/3*100):.1f}%</p></div>', unsafe_allow_html=True)

# ==================== 19. بیک اپ ====================
elif selected == "⚙️ بیک اپ & سیٹنگز" and st.session_state.user_type == "admin":
    st.header("بیک اپ - للبنات")
    tables = [T_TEACHERS, T_STUDENTS, T_HIFZ, T_QAIDA, T_GENERAL,
              T_ATTENDANCE, T_EXAMS, T_PARAS, T_TIMETABLE, T_LEAVE, T_MONITORING]
    if st.button("💾 CSV بیک اپ بنائیں"):
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for t in tables:
                try:
                    res = supabase.table(t).select("*").execute()
                    df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
                    zip_file.writestr(f"{t}.csv", df.to_csv(index=False).encode('utf-8-sig'))
                except Exception as e:
                    st.warning(f"{t}: {e}")
        zip_buffer.seek(0)
        st.download_button("📥 زپ ڈاؤن لوڈ", zip_buffer,
                           f"backup_girls_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                           "application/zip")

# ==================== 20. ڈیٹا منتقلی ====================
if selected == "🔄 ڈیٹا منتقلی" and st.session_state.user_type == "admin":
    st.header("🔄 SQLite سے Supabase منتقلی - للبنات")
    st.warning("⚠️ یہ Supabase کا موجودہ ڈیٹا مٹا کر نئے سے بھر دے گا!")
    db_file = st.file_uploader("پرانی .db فائل اپ لوڈ کریں", type=["db"])
    if db_file:
        confirm = st.checkbox("میں سمجھتا/سمجھتی ہوں کہ موجودہ ڈیٹا ختم ہو جائے گا")
        if confirm and st.button("🚀 منتقلی شروع کریں"):
            import sqlite3, os
            tmp_path = "/tmp/migration_girls.db"
            with open(tmp_path, "wb") as f:
                f.write(db_file.getvalue())
            try:
                mig_conn = sqlite3.connect(tmp_path)
                mig_conn.row_factory = sqlite3.Row
                mig_c = mig_conn.cursor()
            except Exception as e:
                st.error(f"❌ فائل نہیں کھلی: {e}")
                st.stop()

            def safe(val):
                if val is None: return None
                if isinstance(val, str) and val.strip() == '': return None
                if isinstance(val, str) and len(val) == 10 and val[2] == '-':
                    try:
                        p = val.split('-')
                        return f"{p[2]}-{p[1]}-{p[0]}"
                    except: pass
                return val

            def do_insert(table, records):
                if not records: return f"⚠️ {table}: خالی\n"
                success = 0
                for i in range(0, len(records), 50):
                    try:
                        supabase.table(table).insert(records[i:i+50]).execute()
                        success += len(records[i:i+50])
                    except:
                        for rec in records[i:i+50]:
                            try:
                                supabase.table(table).insert(rec).execute()
                                success += 1
                            except: pass
                return f"✅ {table}: {success}/{len(records)}\n"

            log_lines = []
            progress = st.progress(0)
            status = st.empty()

            try:
                # Teachers
                status.info("معلمات...")
                try: supabase.table(T_TEACHERS).delete().neq("id", 0).execute()
                except: pass
                rows = mig_c.execute("SELECT * FROM teachers").fetchall()
                recs = []
                for row in rows:
                    row = dict(row)
                    pwd = str(row.get("password") or "jamia123")
                    recs.append({
                        "name": safe(row.get("name")),
                        "password": hashlib.sha256(pwd.encode()).hexdigest() if len(pwd) != 64 else pwd,
                        "dept": safe(row.get("dept")), "phone": safe(row.get("phone")),
                        "address": safe(row.get("address")), "id_card": safe(row.get("id_card")),
                        "joining_date": safe(row.get("joining_date")),
                    })
                log_lines.append(do_insert(T_TEACHERS, recs))
                progress.progress(10)

                # Students (ایک ایک کر کے ID لیں)
                status.info("طالبات...")
                try: supabase.table(T_STUDENTS).delete().neq("id", 0).execute()
                except: pass
                rows = mig_c.execute("SELECT * FROM students").fetchall()
                sqlite_students = {dict(r)["id"]: dict(r) for r in rows}
                sqlite_to_sb = {}
                for idx, (sqlite_id, row) in enumerate(sqlite_students.items()):
                    try:
                        res = supabase.table(T_STUDENTS).insert({
                            "name": safe(row.get("name")), "father_name": safe(row.get("father_name")),
                            "mother_name": safe(row.get("mother_name")), "dob": safe(row.get("dob")),
                            "admission_date": safe(row.get("admission_date")),
                            "exit_date": safe(row.get("exit_date")), "exit_reason": safe(row.get("exit_reason")),
                            "id_card": safe(row.get("id_card")), "phone": safe(row.get("phone")),
                            "address": safe(row.get("address")), "teacher_name": safe(row.get("teacher_name")),
                            "dept": safe(row.get("dept")), "class": safe(row.get("class")),
                            "section": safe(row.get("section")), "roll_no": safe(row.get("roll_no")),
                        }).execute()
                        sqlite_to_sb[sqlite_id] = res.data[0]["id"]
                        status.info(f"طالبات: {idx+1}/{len(sqlite_students)}")
                    except Exception as e:
                        log_lines.append(f"⚠️ طالبہ {row.get('name')} skip: {e}\n")
                log_lines.append(f"✅ {T_STUDENTS}: {len(sqlite_to_sb)}/{len(sqlite_students)}\n")
                progress.progress(25)

                # Hifz Records
                status.info("حفظ ریکارڈ...")
                try: supabase.table(T_HIFZ).delete().neq("id", 0).execute()
                except: pass
                rows = mig_c.execute("SELECT * FROM hifz_records").fetchall()
                recs = []
                for row in rows:
                    row = dict(row)
                    sb_sid = sqlite_to_sb.get(row.get("student_id"))
                    if not sb_sid: continue
                    recs.append({
                        "r_date": safe(row.get("r_date")), "student_id": sb_sid,
                        "t_name": safe(row.get("t_name")), "surah": safe(row.get("surah")),
                        "a_from": safe(row.get("a_from")), "a_to": safe(row.get("a_to")),
                        "sq_p": safe(row.get("sq_p")), "sq_a": int(row.get("sq_a") or 0),
                        "sq_m": int(row.get("sq_m") or 0), "m_p": safe(row.get("m_p")),
                        "m_a": int(row.get("m_a") or 0), "m_m": int(row.get("m_m") or 0),
                        "attendance": safe(row.get("attendance")),
                        "principal_note": safe(row.get("principal_note")),
                        "lines": int(row.get("lines") or 0), "cleanliness": safe(row.get("cleanliness")),
                    })
                log_lines.append(do_insert(T_HIFZ, recs))
                progress.progress(55)

                # Qaida Records
                status.info("قاعدہ ریکارڈ...")
                try: supabase.table(T_QAIDA).delete().neq("id", 0).execute()
                except: pass
                rows = mig_c.execute("SELECT * FROM qaida_records").fetchall()
                recs = []
                for row in rows:
                    row = dict(row)
                    sb_sid = sqlite_to_sb.get(row.get("student_id"))
                    if not sb_sid: continue
                    recs.append({
                        "r_date": safe(row.get("r_date")), "student_id": sb_sid,
                        "t_name": safe(row.get("t_name")), "lesson_no": safe(row.get("lesson_no")),
                        "total_lines": int(row.get("total_lines") or 0), "details": safe(row.get("details")),
                        "attendance": safe(row.get("attendance")), "cleanliness": safe(row.get("cleanliness")),
                    })
                log_lines.append(do_insert(T_QAIDA, recs))
                progress.progress(70)

                # Timetable, Exams, Passed Paras, Leave, Attendance, Monitoring
                for src_table, dst_table, fields in [
                    ("timetable", T_TIMETABLE, lambda r: {"t_name": safe(r.get("t_name")), "day": safe(r.get("day")), "period": safe(r.get("period")), "book": safe(r.get("book")), "room": safe(r.get("room"))}),
                    ("t_attendance", T_ATTENDANCE, lambda r: {"t_name": safe(r.get("t_name")), "a_date": safe(r.get("a_date")), "arrival": safe(r.get("arrival")), "departure": safe(r.get("departure"))}),
                ]:
                    status.info(f"{dst_table}...")
                    try: supabase.table(dst_table).delete().neq("id", 0).execute()
                    except: pass
                    rows = mig_c.execute(f"SELECT * FROM {src_table}").fetchall()
                    recs = [fields(dict(r)) for r in rows]
                    log_lines.append(do_insert(dst_table, recs))

                progress.progress(90)

                # Leave Requests
                status.info("رخصت درخواستیں...")
                try: supabase.table(T_LEAVE).delete().neq("id", 0).execute()
                except: pass
                rows = mig_c.execute("SELECT * FROM leave_requests").fetchall()
                recs = []
                for row in rows:
                    row = dict(row)
                    recs.append({
                        "t_name": safe(row.get("t_name")), "reason": safe(row.get("reason")),
                        "start_date": safe(row.get("start_date")), "back_date": safe(row.get("back_date")),
                        "status": safe(row.get("status")), "request_date": safe(row.get("request_date")),
                        "l_type": safe(row.get("l_type")) or "دیگر", "days": int(row.get("days") or 1),
                        "notification_seen": int(row.get("notification_seen") or 0),
                    })
                log_lines.append(do_insert(T_LEAVE, recs))

                # Staff Monitoring
                status.info("عملہ نگرانی...")
                try: supabase.table(T_MONITORING).delete().neq("id", 0).execute()
                except: pass
                rows = mig_c.execute("SELECT * FROM staff_monitoring").fetchall()
                recs = []
                for row in rows:
                    row = dict(row)
                    recs.append({
                        "staff_name": safe(row.get("staff_name")), "date": safe(row.get("date")),
                        "note_type": safe(row.get("note_type")), "description": safe(row.get("description")),
                        "action_taken": safe(row.get("action_taken")), "status": safe(row.get("status")),
                        "created_by": safe(row.get("created_by")), "created_at": safe(row.get("created_at")),
                    })
                log_lines.append(do_insert(T_MONITORING, recs))
                progress.progress(100)

                mig_conn.close()
                try: os.remove(tmp_path)
                except: pass
                status.success("✅ منتقلی مکمل!")
                st.text_area("نتیجہ:", "".join(log_lines), height=300)

            except Exception as e:
                st.error(f"❌ خرابی: {e}")
                import traceback
                st.code(traceback.format_exc())

# ==================== 21. استاد / معلمہ سیکشن ====================

# روزانہ سبق اندراج
if selected == "📝 روزانہ سبق اندراج" and st.session_state.user_type == "teacher":
    st.header("📝 روزانہ سبق اندراج - للبنات")
    entry_date = st.date_input("تاریخ", date.today())
    dept = st.selectbox("شعبہ", ["حفظ", "قاعدہ", "درسِ نظامی", "عصری تعلیم"])

    if dept == "حفظ":
        try:
            res = supabase.table(T_STUDENTS).select("id,name,father_name").eq("teacher_name", st.session_state.username).eq("dept", "حفظ").execute()
            students = res.data
        except:
            students = []
        if not students:
            st.info("آپ کی کلاس میں کوئی طالبہ نہیں")
        else:
            for stud in students:
                sid = stud["id"]
                s = stud["name"]
                f = stud["father_name"]
                key = f"{sid}_{s}"
                st.markdown(f"### 👤 {s} بنت {f}")
                att = st.radio("حاضری", ["حاضر", "غیر حاضر", "رخصت"], key=f"att_{key}", horizontal=True)
                cleanliness = st.selectbox("صفائی", cleanliness_options, key=f"clean_{key}")
                if att != "حاضر":
                    if st.button(f"محفوظ کریں ({s})", key=f"save_absent_{key}"):
                        chk = supabase.table(T_HIFZ).select("id").eq("r_date", str(entry_date)).eq("student_id", sid).execute()
                        if chk.data:
                            st.error("ریکارڈ پہلے سے موجود ہے")
                        else:
                            supabase.table(T_HIFZ).insert({
                                "r_date": str(entry_date), "student_id": sid,
                                "t_name": st.session_state.username, "surah": "غائب",
                                "lines": 0, "sq_p": "غائب", "sq_a": 0, "sq_m": 0,
                                "m_p": "غائب", "m_a": 0, "m_m": 0,
                                "attendance": att, "cleanliness": cleanliness
                            }).execute()
                            st.success("محفوظ")
                    st.markdown("---")
                    continue
                st.write("**سبق**")
                c1, c2 = st.columns(2)
                sabaq_nagha = c1.checkbox("ناغہ", key=f"sn_{key}")
                sabaq_yad = c2.checkbox("یاد نہیں", key=f"sy_{key}")
                if sabaq_nagha or sabaq_yad:
                    sabaq_text = "ناغہ" if sabaq_nagha else "یاد نہیں"
                    lines = 0
                else:
                    surah = st.selectbox("سورت", surahs_urdu, key=f"surah_{key}")
                    a_from = st.text_input("آیت (سے)", key=f"af_{key}")
                    a_to = st.text_input("آیت (تک)", key=f"at_{key}")
                    sabaq_text = f"{surah}: {a_from}-{a_to}"
                    lines = st.number_input("کل ستر", 0, key=f"lines_{key}")
                st.write("**سبقی**")
                c1, c2 = st.columns(2)
                sq_nagha = c1.checkbox("ناغہ", key=f"sqn_{key}")
                sq_yad = c2.checkbox("یاد نہیں", key=f"sqy_{key}")
                if sq_nagha or sq_yad:
                    sq_text = "ناغہ" if sq_nagha else "یاد نہیں"
                    sq_a = sq_m = 0
                else:
                    if f"sq_rows_{key}" not in st.session_state:
                        st.session_state[f"sq_rows_{key}"] = 1
                    sq_parts = []
                    sq_a = sq_m = 0
                    for i in range(st.session_state[f"sq_rows_{key}"]):
                        cols = st.columns([2, 2, 1, 1])
                        p = cols[0].selectbox("پارہ", paras, key=f"sqp_{key}_{i}")
                        v = cols[1].selectbox("مقدار", ["مکمل", "آدھا", "پون", "پاؤ"], key=f"sqv_{key}_{i}")
                        a = cols[2].number_input("اٹکن", 0, key=f"sqa_{key}_{i}")
                        e = cols[3].number_input("غلطی", 0, key=f"sqe_{key}_{i}")
                        sq_parts.append(f"{p}:{v}")
                        sq_a += a; sq_m += e
                    if st.button("➕ سبقی", key=f"add_sq_{key}"):
                        st.session_state[f"sq_rows_{key}"] += 1
                        st.rerun()
                    sq_text = " | ".join(sq_parts)
                st.write("**منزل**")
                c1, c2 = st.columns(2)
                m_nagha = c1.checkbox("ناغہ", key=f"mn_{key}")
                m_yad = c2.checkbox("یاد نہیں", key=f"my_{key}")
                if m_nagha or m_yad:
                    m_text = "ناغہ" if m_nagha else "یاد نہیں"
                    m_a = m_m = 0
                else:
                    if f"m_rows_{key}" not in st.session_state:
                        st.session_state[f"m_rows_{key}"] = 1
                    m_parts = []
                    m_a = m_m = 0
                    for j in range(st.session_state[f"m_rows_{key}"]):
                        cols = st.columns([2, 2, 1, 1])
                        p = cols[0].selectbox("پارہ", paras, key=f"mp_{key}_{j}")
                        v = cols[1].selectbox("مقدار", ["مکمل", "آدھا", "پون", "پاؤ"], key=f"mv_{key}_{j}")
                        a = cols[2].number_input("اٹکن", 0, key=f"ma_{key}_{j}")
                        e = cols[3].number_input("غلطی", 0, key=f"me_{key}_{j}")
                        m_parts.append(f"{p}:{v}")
                        m_a += a; m_m += e
                    if st.button("➕ منزل", key=f"add_m_{key}"):
                        st.session_state[f"m_rows_{key}"] += 1
                        st.rerun()
                    m_text = " | ".join(m_parts)
                sn_bool = sabaq_nagha or sabaq_yad
                sqn_bool = sq_nagha or sq_yad
                mn_bool = m_nagha or m_yad
                grade = calculate_grade_with_attendance(att, sn_bool, sqn_bool, mn_bool, sq_m, m_m)
                st.info(f"**درجہ:** {grade}")
                if st.button(f"محفوظ کریں ({s})", key=f"save_{key}"):
                    chk = supabase.table(T_HIFZ).select("id").eq("r_date", str(entry_date)).eq("student_id", sid).execute()
                    if chk.data:
                        st.error("ریکارڈ پہلے سے موجود ہے")
                    else:
                        supabase.table(T_HIFZ).insert({
                            "r_date": str(entry_date), "student_id": sid,
                            "t_name": st.session_state.username, "surah": sabaq_text,
                            "lines": int(lines), "sq_p": sq_text, "sq_a": int(sq_a), "sq_m": int(sq_m),
                            "m_p": m_text, "m_a": int(m_a), "m_m": int(m_m),
                            "attendance": att, "cleanliness": cleanliness
                        }).execute()
                        log_audit(st.session_state.username, "Hifz Entry", f"{s} {entry_date}")
                        st.success("محفوظ ہو گیا")
                st.markdown("---")

    elif dept == "قاعدہ":
        try:
            res = supabase.table(T_STUDENTS).select("id,name,father_name").eq("teacher_name", st.session_state.username).eq("dept", "قاعدہ").execute()
            students = res.data
        except:
            students = []
        if not students:
            st.info("کوئی طالبہ نہیں")
        else:
            for stud in students:
                sid = stud["id"]
                s = stud["name"]
                f = stud["father_name"]
                key = f"{sid}_{s}"
                st.markdown(f"### 👤 {s} بنت {f}")
                att = st.radio("حاضری", ["حاضر", "غیر حاضر", "رخصت"], key=f"att_{key}", horizontal=True)
                cleanliness = st.selectbox("صفائی", cleanliness_options, key=f"clean_{key}")
                if att == "حاضر":
                    c1, c2 = st.columns(2)
                    nagha = c1.checkbox("ناغہ", key=f"nagha_{key}")
                    yad = c2.checkbox("یاد نہیں", key=f"yad_{key}")
                    if nagha or yad:
                        lesson_no = "ناغہ" if nagha else "یاد نہیں"
                        total_lines = 0
                        details = ""
                    else:
                        lesson_no = st.text_input("تختی نمبر", key=f"lesson_{key}")
                        total_lines = st.number_input("لائنیں", 0, key=f"lines_{key}")
                        details = st.text_area("تفصیل", key=f"details_{key}")
                    if st.button(f"محفوظ ({s})", key=f"save_{key}"):
                        chk = supabase.table(T_QAIDA).select("id").eq("r_date", str(entry_date)).eq("student_id", sid).execute()
                        if chk.data:
                            st.error("ریکارڈ پہلے سے موجود ہے")
                        else:
                            supabase.table(T_QAIDA).insert({
                                "r_date": str(entry_date), "student_id": sid,
                                "t_name": st.session_state.username, "lesson_no": lesson_no,
                                "total_lines": int(total_lines), "details": details,
                                "attendance": att, "cleanliness": cleanliness
                            }).execute()
                            st.success("محفوظ")
                else:
                    if st.button(f"محفوظ ({s})", key=f"save_{key}"):
                        supabase.table(T_QAIDA).insert({
                            "r_date": str(entry_date), "student_id": sid,
                            "t_name": st.session_state.username, "lesson_no": "غائب",
                            "total_lines": 0, "details": "", "attendance": att, "cleanliness": cleanliness
                        }).execute()
                        st.success("محفوظ")
                st.markdown("---")

# امتحانی درخواست
elif selected == "🎓 امتحانی درخواست" and st.session_state.user_type == "teacher":
    st.subheader("امتحان کے لیے طالبہ نامزد کریں")
    try:
        res = supabase.table(T_STUDENTS).select("id,name,father_name,dept").eq("teacher_name", st.session_state.username).execute()
        students = res.data
    except:
        students = []
    if not students:
        st.warning("کوئی طالبہ نہیں")
    else:
        with st.form("exam_request"):
            s_list = [f"{s['name']} بنت {s['father_name']} ({s['dept']})" for s in students]
            sel = st.selectbox("طالبہ", s_list)
            s_name = sel.split(" بنت ")[0]
            f_name = sel.split(" بنت ")[1].split(" (")[0]
            dept = sel.split(" (")[1].replace(")", "")
            student_id = next((s["id"] for s in students if s["name"] == s_name and s["father_name"] == f_name), None)
            exam_type = st.selectbox("امتحان", ["پارہ ٹیسٹ", "ماہانہ", "سہ ماہی", "سالانہ"])
            start_date = st.date_input("تاریخ ابتدا", date.today())
            end_date = st.date_input("تاریخ اختتام", date.today() + timedelta(days=7))
            total_days = (end_date - start_date).days + 1
            from_para = to_para = 0
            book_name = amount_read = ""
            if exam_type == "پارہ ٹیسٹ":
                c1, c2 = st.columns(2)
                from_para = c1.number_input("پارہ (شروع)", 1, 30, 1)
                to_para = c2.number_input("پارہ (اختتام)", from_para, 30, from_para)
            else:
                c1, c2 = st.columns(2)
                book_name = c1.text_input("کتاب")
                amount_read = c2.text_input("مقدار")
            if st.form_submit_button("بھیجیں"):
                if student_id:
                    supabase.table(T_EXAMS).insert({
                        "student_id": student_id, "dept": dept, "exam_type": exam_type,
                        "from_para": int(from_para), "to_para": int(to_para),
                        "book_name": book_name, "amount_read": amount_read,
                        "start_date": str(start_date), "end_date": str(end_date),
                        "total_days": total_days, "status": "پینڈنگ"
                    }).execute()
                    st.success("درخواست بھیج دی گئی")

# رخصت کی درخواست
elif selected == "📩 رخصت کی درخواست" and st.session_state.user_type == "teacher":
    st.header("📩 رخصت کی درخواست")
    with st.form("leave_form"):
        l_type = st.selectbox("نوعیت", ["بیماری", "ضروری کام", "ہنگامی", "دیگر"])
        start_date = st.date_input("تاریخ آغاز", date.today())
        days = st.number_input("دنوں کی تعداد", 1, 30, 1)
        back_date = start_date + timedelta(days=days - 1)
        st.write(f"واپسی: {back_date}")
        reason = st.text_area("وجہ")
        if st.form_submit_button("جمع کریں"):
            if reason:
                supabase.table(T_LEAVE).insert({
                    "t_name": st.session_state.username, "l_type": l_type,
                    "start_date": str(start_date), "back_date": str(back_date),
                    "days": int(days), "reason": reason,
                    "status": "پینڈنگ", "notification_seen": 0,
                    "request_date": str(date.today())
                }).execute()
                log_audit(st.session_state.username, "Leave Requested", f"{l_type} {days} days")
                st.success("درخواست بھیج دی گئی")
            else:
                st.error("وجہ لکھیں")

# میری حاضری
elif selected == "🕒 میری حاضری" and st.session_state.user_type == "teacher":
    st.header("🕒 میری حاضری")
    today = date.today()
    try:
        res = supabase.table(T_ATTENDANCE).select("arrival,departure").eq("t_name", st.session_state.username).eq("a_date", str(today)).execute()
        rec = res.data[0] if res.data else None
    except:
        rec = None
    if not rec:
        c1, c2 = st.columns(2)
        arr_date = c1.date_input("تاریخ", today)
        arr_time = c2.time_input("آمد کا وقت", datetime.now().time())
        if st.button("آمد درج کریں"):
            supabase.table(T_ATTENDANCE).insert({
                "t_name": st.session_state.username, "a_date": str(arr_date),
                "arrival": arr_time.strftime("%I:%M %p"), "actual_arrival": get_pk_time()
            }).execute()
            st.success("آمد درج ہو گئی")
            st.rerun()
    elif rec and rec.get("departure") is None:
        st.success(f"آمد: {rec['arrival']}")
        dep_time = st.time_input("رخصت", datetime.now().time())
        if st.button("رخصت درج کریں"):
            supabase.table(T_ATTENDANCE).update({
                "departure": dep_time.strftime("%I:%M %p"), "actual_departure": get_pk_time()
            }).eq("t_name", st.session_state.username).eq("a_date", str(today)).execute()
            st.success("رخصت درج ہو گئی")
            st.rerun()
    else:
        st.success(f"آمد: {rec['arrival']} | رخصت: {rec['departure']}")

# میرا ٹائم ٹیبل
elif selected == "📚 میرا ٹائم ٹیبل" and st.session_state.user_type == "teacher":
    st.header("📚 میرا ٹائم ٹیبل")
    try:
        res = supabase.table(T_TIMETABLE).select("day,period,book,room").eq("t_name", st.session_state.username).execute()
        if not res.data:
            st.info("ابھی ٹائم ٹیبل ترتیب نہیں دیا گیا")
        else:
            tt_df = pd.DataFrame(res.data)
            tt_df.columns = ["دن", "وقت", "کتاب", "کمرہ"]
            day_order = {"ہفتہ": 0, "اتوار": 1, "پیر": 2, "منگل": 3, "بدھ": 4, "جمعرات": 5}
            tt_df['day_order'] = tt_df['دن'].map(day_order)
            tt_df = tt_df.sort_values(['day_order', 'وقت'])
            pivot = tt_df.pivot(index='وقت', columns='دن', values='کتاب').fillna("—")
            st.dataframe(pivot, use_container_width=True)
            html_timetable = generate_timetable_html(tt_df)
            st.download_button("📥 HTML ڈاؤن لوڈ", html_timetable,
                               f"Timetable_{st.session_state.username}.html", "text/html")
    except Exception as e:
        st.error(f"خرابی: {e}")

# ==================== لاگ آؤٹ ====================
st.sidebar.divider()
if st.sidebar.button("🚪 لاگ آؤٹ"):
    st.session_state.logged_in = False
    st.rerun()
