# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import plotly.express as px
import os
import hashlib
import shutil
import zipfile
import io
from supabase import create_client, Client

# ==================== SUPABASE کنکشن ====================
@st.cache_resource
def init_supabase():
    url = st.secrets["connections"]["supabase"]["SUPABASE_URL"]
    key = st.secrets["connections"]["supabase"]["SUPABASE_KEY"]
    return create_client(url, key)

try:
    supabase: Client = init_supabase()
except Exception as e:
    st.error(f"❌ Supabase کنکشن میں خرابی: {e}")
    st.stop()

def hash_password(password):
    """SHA256 ہیش بنائیں - تمام اضافی اسپیس ہٹا کر"""
    return hashlib.sha256(str(password).strip().encode('utf-8')).hexdigest()

# ==================== ہیلپر فنکشنز ====================
def log_audit(user, action, details=""):
    try:
        supabase.table("audit_log").insert({
            "user": user,
            "action": action,
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
    if attendance == "غیر حاضر": return "غیر حاضر"
    if attendance == "رخصت": return "رخصت"
    nagha_count = sum([sabaq_nagha, sq_nagha, m_nagha])
    if nagha_count == 1: return "ناقص (ناغہ)"
    elif nagha_count == 2: return "کمزور (ناغہ)"
    elif nagha_count == 3: return "ناکام (مکمل ناغہ)"
    total_mistakes = sq_mistakes + m_mistakes
    return get_grade_from_mistakes(total_mistakes)

def cleanliness_to_score(clean):
    if clean == "بہترین": return 3
    elif clean == "بہتر": return 2
    elif clean == "ناقص": return 1
    else: return 0

def generate_exam_result_card(exam_row):
    html = f"""
    <!DOCTYPE html><html dir="rtl"><head><meta charset="UTF-8"><title>رزلٹ کارڈ - {exam_row['s_name']}</title>
    <style>@font-face{{font-family:'Jameel Noori Nastaleeq';src:url('https://fonts.cdnfonts.com/css/jameel-noori-nastaleeq');}}body{{font-family:'Jameel Noori Nastaleeq','Noto Nastaliq Urdu',Arial,sans-serif;margin:20px;direction:rtl;text-align:right;}}.card{{border:2px solid #1e5631;border-radius:15px;padding:20px;max-width:600px;margin:auto;}}h2{{text-align:center;color:#1e5631;}}table{{width:100%;border-collapse:collapse;margin:15px 0;}}th,td{{border:1px solid #ddd;padding:8px;text-align:center;}}th{{background-color:#f2f2f2;}}.footer{{margin-top:20px;display:flex;justify-content:space-between;}}</style></head><body><div class="card"><h2>جامعہ ملیہ اسلامیہ فیصل آباد</h2><h3>رزلٹ کارڈ</h3><p><b>نام:</b> {exam_row['s_name']} ولد {exam_row['f_name']}</p><p><b>شناختی نمبر:</b> {exam_row.get('roll_no','')}</p><p><b>امتحان کی قسم:</b> {exam_row['exam_type']}</p>{f"<p><b>پارہ:</b> {exam_row['from_para']} تا {exam_row['to_para']}</p>" if exam_row.get('from_para') else ""}{f"<p><b>کتاب:</b> {exam_row.get('book_name','')}</p>" if exam_row.get('book_name') else ""}{f"<p><b>مقدار خواندگی:</b> {exam_row.get('amount_read','')}</p>" if exam_row.get('amount_read') else ""}<p><b>تاریخ:</b> {exam_row['start_date']} تا {exam_row['end_date']}</p><p><b>کل دن:</b> {exam_row.get('total_days','')}</p><table><tr><th>سوال</th><th>1</th><th>2</th><th>3</th><th>4</th><th>5</th><th>کل</th></tr><tr><td>{exam_row['q1']}</td><td>{exam_row['q2']}</td><td>{exam_row['q3']}</td><td>{exam_row['q4']}</td><td>{exam_row['q5']}</td><td>{exam_row['total']}</td></tr></table><p><b>گریڈ:</b> {exam_row['grade']}</p><div class="footer"><span>دستخط استاذ: _________________</span><span>دستخط مہتمم: _________________</span></div></div><div class="no-print" style="text-align:center;margin-top:20px;"><button onclick="window.print()">🖨️ پرنٹ کریں</button></div></body></html>"""
    return html

def generate_para_report(student_name, father_name, passed_paras_df):
    if passed_paras_df.empty: return "<p>کوئی پاس شدہ پارہ نہیں</p>"
    html_table = passed_paras_df.to_html(index=False, classes='print-table', border=1, justify='center', escape=False)
    html = f"""
    <!DOCTYPE html><html dir="rtl"><head><meta charset="UTF-8"><title>پارہ تعلیمی رپورٹ - {student_name}</title>
    <style>@font-face{{font-family:'Jameel Noori Nastaleeq';src:url('https://fonts.cdnfonts.com/css/jameel-noori-nastaleeq');}}body{{font-family:'Jameel Noori Nastaleeq','Noto Nastaliq Urdu',Arial,sans-serif;margin:20px;direction:rtl;text-align:right;}}h2,h3{{text-align:center;color:#1e5631;}}table{{width:100%;border-collapse:collapse;margin:20px 0;}}th,td{{border:1px solid #ddd;padding:8px;text-align:center;}}th{{background-color:#f2f2f2;}}@media print{{body{{margin:0;}}.no-print{{display:none;}}}}</style></head><body><div class="header"><h2>جامعہ ملیہ اسلامیہ فیصل آباد</h2><h3>پارہ تعلیمی رپورٹ</h3><p><b>طالب علم:</b> {student_name} ولد {father_name}</p></div>{html_table}<div class="signatures" style="display:flex;justify-content:space-between;margin-top:50px;"><span>دستخط استاذ: _______________________</span><span>دستخط مہتمم: _______________________</span></div><div class="no-print" style="text-align:center;margin-top:30px;"><button onclick="window.print()">🖨️ پرنٹ کریں</button></div></body></html>"""
    return html

def generate_html_report(df, title, student_name="", start_date="", end_date="", passed_paras=None):
    html_table = df.to_html(index=False, classes='print-table', border=1, justify='center', escape=False)
    passed_html = ""
    if passed_paras: passed_html = f"<div style='margin-top:20px'><b>پاس شدہ پارے:</b> {', '.join(map(str, passed_paras))}</div>"
    html = f"""
    <!DOCTYPE html><html dir="rtl"><head><meta charset="UTF-8"><title>{title}</title>
    <style>@font-face{{font-family:'Jameel Noori Nastaleeq';src:url('https://fonts.cdnfonts.com/css/jameel-noori-nastaleeq');}}body{{font-family:'Jameel Noori Nastaleeq','Noto Nastaliq Urdu',Arial,sans-serif;margin:20px;direction:rtl;text-align:right;}}h2,h3{{text-align:center;color:#1e5631;}}table{{width:100%;border-collapse:collapse;margin:20px 0;}}th,td{{border:1px solid #ddd;padding:8px;text-align:center;}}th{{background-color:#f2f2f2;}}@media print{{body{{margin:0;}}.no-print{{display:none;}}}}</style></head><body><div class="header"><h2>جامعہ ملیہ اسلامیہ فیصل آباد</h2><h3>{title}</h3>{f"<p><b>طالب علم:</b> {student_name} &nbsp;&nbsp; <b>تاریخ:</b> {start_date} تا {end_date}</p>" if student_name else ""}</div>{html_table}{passed_html}<div class="signatures" style="display:flex;justify-content:space-between;margin-top:50px;"><span>دستخط استاذ: _______________________</span><span>دستخط مہتمم: _______________________</span></div><div class="no-print" style="text-align:center;margin-top:30px;"><button onclick="window.print()">🖨️ پرنٹ کریں</button></div></body></html>"""
    return html

def generate_timetable_html(df_timetable):
    if df_timetable.empty: return "<p>کوئی ٹائم ٹیبل دستیاب نہیں</p>"
    day_order = {"ہفتہ":0,"اتوار":1,"پیر":2,"منگل":3,"بدھ":4,"جمعرات":5}
    df_timetable['day_order'] = df_timetable['دن'].map(day_order)
    df_timetable = df_timetable.sort_values(['day_order','وقت'])
    pivot = df_timetable.pivot(index='وقت', columns='دن', values='کتاب').fillna("—")
    html = f"""
    <!DOCTYPE html><html dir="rtl"><head><meta charset="UTF-8"><title>ٹائم ٹیبل</title>
    <style>@font-face{{font-family:'Jameel Noori Nastaleeq';src:url('https://fonts.cdnfonts.com/css/jameel-noori-nastaleeq');}}body{{font-family:'Jameel Noori Nastaleeq','Noto Nastaliq Urdu',Arial,sans-serif;margin:20px;direction:rtl;text-align:right;}}h2,h3{{text-align:center;color:#1e5631;}}table{{width:100%;border-collapse:collapse;margin:20px 0;}}th,td{{border:1px solid #ddd;padding:8px;text-align:center;}}th{{background-color:#f2f2f2;}}@media print{{body{{margin:0;}}.no-print{{display:none;}}}}</style></head><body><div class="header"><h2>جامعہ ملیہ اسلامیہ فیصل آباد</h2><h3>ٹائم ٹیبل</h3></div>{pivot.to_html(classes='print-table',border=1,justify='center',escape=False)}<div class="signatures" style="display:flex;justify-content:space-between;margin-top:50px;"><span>دستخط استاذ: _______________________</span><span>دستخط مہتمم: _______________________</span></div><div class="no-print" style="text-align:center;margin-top:30px;"><button onclick="window.print()">🖨️ پرنٹ کریں</button></div></body></html>"""
    return html

# ==================== اسٹائلنگ ====================
st.set_page_config(page_title="جامعہ ملیہ اسلامیہ فیصل آباد | سمارٹ ERP", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
    @font-face { font-family: 'Jameel Noori Nastaleeq'; src: url('https://raw.githubusercontent.com/urdufonts/jameel-noori-nastaleeq/master/JameelNooriNastaleeq.ttf') format('truetype'); font-weight: normal; font-style: normal; }
    @import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu&display=swap');
    * { font-family: 'Jameel Noori Nastaleeq', 'Noto Nastaliq Urdu', 'Arial', sans-serif; }
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
    .best-student-card { background: linear-gradient(135deg, #fff9e6, #ffe6b3); border-radius: 20px; padding: 20px; text-align: center; box-shadow: 0 8px 16px rgba(0,0,0,0.1); transition: 0.3s; }
    .best-student-card:hover { transform: translateY(-5px); }
    .gold { color: #d4af37; } .silver { color: #a0a0a0; } .bronze { color: #cd7f32; }
    @media (max-width: 768px) { .stButton > button { padding: 0.4rem 0.8rem; font-size: 0.8rem; } .main-header h1 { font-size: 1.5rem; } }
</style>
""", unsafe_allow_html=True)

# ==================== لاگ ان ====================
f verify_login(username, password):
    try:
        hashed_input = hash_password(password)
        res = supabase.table("teachers").select("*").eq("name", username).execute()
        
        if not res.data:
            st.error(f"❌ صارف '{username}' موجود نہیں")
            return None
            
        stored = res.data[0]['password']
        
        # ڈیبگ معلومات
        st.write("### 🔍 ڈیبگ معلومات")
        st.write(f"**آپ کا پاسورڈ:** `{password}`")
        st.write(f"**اس کی ہیش:** `{hashed_input}`")
        st.write(f"**Supabase میں محفوظ ہیش:** `{stored}`")
        st.write(f"**دونوں برابر؟** `{stored == hashed_input}`")
        
        if stored == hashed_input or stored == password:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.user_type = "admin" if username == "admin" else "teacher"
            return res.data[0]
        else:
            st.error("❌ پاسورڈ میچ نہیں ہوا")
            return None
    except Exception as e:
        st.error(f"خرابی: {e}")
        return None

# لاگ ان اسکرین
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
                    st.session_state.user_type = "admin" if u == "admin" else "teacher"
                    log_audit(u, "Login", f"User type: {st.session_state.user_type}")
                    st.rerun()
                else:
                    st.error("غلط صارف نام یا پاسورڈ")
            st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ==================== مینو ====================
if st.session_state.user_type == "admin":
    menu = ["📊 ایڈمن ڈیش بورڈ", "📊 یومیہ تعلیمی رپورٹ", "🎓 امتحانی نظام", "📜 ماہانہ رزلٹ کارڈ",
            "📘 پارہ تعلیمی رپورٹ", "🕒 اساتذہ حاضری", "🏛️ رخصت کی منظوری",
            "👥 یوزر مینجمنٹ", "📚 ٹائم ٹیبل مینجمنٹ", "🔑 پاسورڈ تبدیل کریں", "📋 عملہ نگرانی و شکایات",
            "📢 نوٹیفیکیشنز", "📈 تجزیہ و رپورٹس", "🏆 ماہانہ بہترین طلباء", "⚙️ بیک اپ & سیٹنگز"]
else:
    menu = ["📝 روزانہ سبق اندراج", "🎓 امتحانی درخواست", "📩 رخصت کی درخواست",
            "🕒 میری حاضری", "📚 میرا ٹائم ٹیبل", "🔑 پاسورڈ تبدیل کریں", "📢 نوٹیفیکیشنز"]

selected = st.sidebar.radio("📌 مینو", menu)

# ==================== ڈیٹا ====================
surahs_urdu = ["الفاتحة","البقرة","آل عمران","النساء","المائدة","الأنعام","الأعراف","الأنفال","التوبة","يونس","هود","يوسف","الرعد","إبراهيم","الحجر","النحل","الإسراء","الكهف","مريم","طه","الأنبياء","الحج","المؤمنون","النور","الفرقان","الشعراء","النمل","القصص","العنكبوت","الروم","لقمان","السجدة","الأحزاب","سبأ","فاطر","يس","الصافات","ص","الزمر","غافر","فصلت","الشورى","الزخرف","الدخان","الجاثية","الأحقاف","محمد","الفتح","الحجرات","ق","الذاريات","الطور","النجم","القمر","الرحمن","الواقعة","الحديد","المجادلة","الحشر","الممتحنة","الصف","الجمعة","المنافقون","التغابن","الطلاق","التحریم","الملک","القلم","الحاقة","المعارج","نوح","الجن","المزمل","المدثر","القیامة","الإنسان","المرسلات","النبأ","النازعات","عبس","التکویر","الإنفطار","المطففین","الإنشقاق","البروج","الطارق","الأعلى","الغاشیة","الفجر","البلد","الشمس","اللیل","الضحى","الشرح","التین","العلق","القدر","البینة","الزلزلة","العادیات","القارعة","التکاثر","العصر","الهمزة","الفیل","قریش","الماعون","الکوثر","الکافرون","النصر","المسد","الإخلاص","الفلق","الناس"]
paras = [f"پارہ {i}" for i in range(1,31)]
cleanliness_options = ["بہترین","بہتر","ناقص"]

# ==================== پاسورڈ فنکشنز ====================
def verify_password(user, plain_password):
    try:
        res = supabase.table("teachers").select("password").eq("name", user).execute()
        if not res.data: return False
        stored = res.data[0]['password']
        return stored == plain_password or stored == hash_password(plain_password)
    except: return False

def change_password(user, old_pass, new_pass):
    if not verify_password(user, old_pass): return False
    try:
        supabase.table("teachers").update({"password": hash_password(new_pass)}).eq("name", user).execute()
        log_audit(user, "Password Changed", "Success")
        return True
    except: return False

def admin_reset_password(teacher_name, new_pass):
    try:
        supabase.table("teachers").update({"password": hash_password(new_pass)}).eq("name", teacher_name).execute()
        log_audit(st.session_state.username, "Admin Reset Password", f"Teacher: {teacher_name}")
    except: pass

# ==================== ایڈمن سیکشنز ====================
# 8.1 ایڈمن ڈیش بورڈ
if selected == "📊 ایڈمن ڈیش بورڈ" and st.session_state.user_type == "admin":
    st.markdown("<div class='main-header'><h1>📊 ایڈمن ڈیش بورڈ</h1></div>", unsafe_allow_html=True)
    res_s = supabase.table("students").select("id", count="exact").execute()
    total_students = res_s.count if res_s.count else 0
    res_t = supabase.table("teachers").select("id", count="exact").neq("name", "admin").execute()
    total_teachers = res_t.count if res_t.count else 0
    col1, col2 = st.columns(2)
    col1.metric("کل طلباء", total_students)
    col2.metric("کل اساتذہ", total_teachers)

# 8.2 یومیہ تعلیمی رپورٹ
elif selected == "📊 یومیہ تعلیمی رپورٹ" and st.session_state.user_type == "admin":
    st.header("📊 یومیہ تعلیمی رپورٹ - صرف دیکھیں")
    with st.sidebar:
        d1 = st.date_input("تاریخ آغاز", date.today().replace(day=1))
        d2 = st.date_input("تاریخ اختتام", date.today())
        teachers_res = supabase.table("teachers").select("name").neq("name", "admin").execute()
        teachers_list = ["تمام"] + [t['name'] for t in teachers_res.data]
        sel_teacher = st.selectbox("استاد / کلاس", teachers_list)
        dept_filter = st.selectbox("شعبہ", ["تمام", "حفظ", "قاعدہ", "درسِ نظامی", "عصری تعلیم"])
    
    combined_df = pd.DataFrame()
    if dept_filter in ["تمام", "حفظ"]:
        query = supabase.table("hifz_records").select("*, students(name, father_name, roll_no)").gte("r_date", str(d1)).lte("r_date", str(d2))
        if sel_teacher != "تمام": query = query.eq("t_name", sel_teacher)
        res = query.execute()
        if res.data:
            df = pd.DataFrame(res.data)
            df['نام'] = df['students'].apply(lambda x: x['name'] if x else '')
            df['والد کا نام'] = df['students'].apply(lambda x: x['father_name'] if x else '')
            df['شناختی نمبر'] = df['students'].apply(lambda x: x.get('roll_no','') if x else '')
            df['شعبہ'] = 'حفظ'
            df = df.rename(columns={'r_date':'تاریخ','t_name':'استاد','surah':'سبق','lines':'کل ستر','sq_p':'سبقی','sq_m':'سبقی (غلطی)','sq_a':'سبقی (اٹکن)','m_p':'منزل','m_m':'منزل (غلطی)','m_a':'منزل (اٹکن)','attendance':'حاضری','cleanliness':'صفائی'})
            combined_df = pd.concat([combined_df, df[['تاریخ','نام','والد کا نام','شناختی نمبر','استاد','شعبہ','سبق','کل ستر','سبقی','سبقی (غلطی)','سبقی (اٹکن)','منزل','منزل (غلطی)','منزل (اٹکن)','حاضری','صفائی']]], ignore_index=True)
    if dept_filter in ["تمام", "قاعدہ"]:
        query = supabase.table("qaida_records").select("*, students(name, father_name, roll_no)").gte("r_date", str(d1)).lte("r_date", str(d2))
        if sel_teacher != "تمام": query = query.eq("t_name", sel_teacher)
        res = query.execute()
        if res.data:
            df = pd.DataFrame(res.data)
            df['نام'] = df['students'].apply(lambda x: x['name'] if x else '')
            df['والد کا نام'] = df['students'].apply(lambda x: x['father_name'] if x else '')
            df['شناختی نمبر'] = df['students'].apply(lambda x: x.get('roll_no','') if x else '')
            df['شعبہ'] = 'قاعدہ'
            df = df.rename(columns={'r_date':'تاریخ','t_name':'استاد','lesson_no':'تختی نمبر','total_lines':'کل لائنیں','details':'تفصیل','attendance':'حاضری','cleanliness':'صفائی'})
            combined_df = pd.concat([combined_df, df[['تاریخ','نام','والد کا نام','شناختی نمبر','استاد','شعبہ','تختی نمبر','کل لائنیں','تفصیل','حاضری','صفائی']]], ignore_index=True)
    if dept_filter in ["تمام", "درسِ نظامی", "عصری تعلیم"]:
        query = supabase.table("general_education").select("*, students(name, father_name, roll_no)").gte("r_date", str(d1)).lte("r_date", str(d2))
        if sel_teacher != "تمام": query = query.eq("t_name", sel_teacher)
        if dept_filter != "تمام": query = query.eq("dept", dept_filter)
        res = query.execute()
        if res.data:
            df = pd.DataFrame(res.data)
            df['نام'] = df['students'].apply(lambda x: x['name'] if x else '')
            df['والد کا نام'] = df['students'].apply(lambda x: x['father_name'] if x else '')
            df['شناختی نمبر'] = df['students'].apply(lambda x: x.get('roll_no','') if x else '')
            df = df.rename(columns={'r_date':'تاریخ','t_name':'استاد','dept':'شعبہ','book_subject':'کتاب/مضمون','today_lesson':'آج کا سبق','homework':'ہوم ورک','performance':'کارکردگی','attendance':'حاضری','cleanliness':'صفائی'})
            combined_df = pd.concat([combined_df, df], ignore_index=True)
    if combined_df.empty: st.warning("کوئی ریکارڈ نہیں ملا")
    else:
        st.success(f"کل {len(combined_df)} ریکارڈ ملے")
        st.dataframe(combined_df, use_container_width=True)
        html_report = generate_html_report(combined_df, "یومیہ تعلیمی رپورٹ", start_date=d1.strftime("%Y-%m-%d"), end_date=d2.strftime("%Y-%m-%d"))
        st.download_button("📥 HTML رپورٹ ڈاؤن لوڈ کریں", html_report, "daily_report.html", "text/html")
        if st.button("🖨️ پرنٹ کریں"): st.components.v1.html(f"<script>var w=window.open();w.document.write(`{html_report}`);w.print();</script>", height=0)

# 8.3 امتحانی نظام
elif selected == "🎓 امتحانی نظام" and st.session_state.user_type == "admin":
    st.header("🎓 امتحانی نظام")
    tab1, tab2 = st.tabs(["پینڈنگ امتحانات", "مکمل شدہ"])
    with tab1:
        res = supabase.table("exams").select("*, students(name, father_name, roll_no)").eq("status", "پینڈنگ").execute()
        pending = res.data
        if not pending: st.info("کوئی پینڈنگ امتحان نہیں")
        else:
            for exam in pending:
                with st.expander(f"{exam['students']['name']} ولد {exam['students']['father_name']} | شناختی نمبر: {exam['students'].get('roll_no','')} | {exam['dept']} | {exam['exam_type']}"):
                    st.write(f"**تاریخ ابتدا:** {exam['start_date']}")
                    st.write(f"**تاریخ اختتام:** {exam['end_date']}")
                    st.write(f"**کل دن:** {exam.get('total_days','-')}")
                    if exam['exam_type'] == "پارہ ٹیسٹ": st.info(f"پارہ نمبر: {exam.get('from_para','')} تا {exam.get('to_para','')}")
                    else: st.info(f"کتاب: {exam.get('book_name','')}"); st.info(f"مقدار خواندگی: {exam.get('amount_read','')}")
                    cols = st.columns(5)
                    q1 = cols[0].number_input("س1",0,20,key=f"q1_{exam['id']}")
                    q2 = cols[1].number_input("س2",0,20,key=f"q2_{exam['id']}")
                    q3 = cols[2].number_input("س3",0,20,key=f"q3_{exam['id']}")
                    q4 = cols[3].number_input("س4",0,20,key=f"q4_{exam['id']}")
                    q5 = cols[4].number_input("س5",0,20,key=f"q5_{exam['id']}")
                    total = q1+q2+q3+q4+q5
                    if total >= 90: g = "ممتاز"
                    elif total >= 80: g = "جید جداً"
                    elif total >= 70: g = "جید"
                    elif total >= 60: g = "مقبول"
                    else: g = "ناکام"
                    st.write(f"کل: {total} | گریڈ: {g}")
                    if st.button("کلیئر کریں", key=f"save_{exam['id']}"):
                        supabase.table("exams").update({"q1":q1,"q2":q2,"q3":q3,"q4":q4,"q5":q5,"total":total,"grade":g,"status":"مکمل","end_date":str(date.today())}).eq("id", exam['id']).execute()
                        if g != "ناکام":
                            if exam['exam_type'] == "پارہ ٹیسٹ" and exam.get('from_para'):
                                for para in range(exam['from_para'], exam['to_para']+1):
                                    supabase.table("passed_paras").insert({"student_id":exam['student_id'],"para_no":para,"passed_date":str(date.today()),"exam_type":exam['exam_type'],"grade":g,"marks":total}).execute()
                            else:
                                supabase.table("passed_paras").insert({"student_id":exam['student_id'],"book_name":exam.get('book_name',''),"passed_date":str(date.today()),"exam_type":exam['exam_type'],"grade":g,"marks":total}).execute()
                        st.success("امتحان کلیئر کر دیا گیا")
                        st.rerun()
    with tab2:
        res = supabase.table("exams").select("*, students(name, father_name, roll_no)").eq("status", "مکمل").order("end_date", desc=True).execute()
        if res.data:
            hist_df = pd.DataFrame(res.data)
            hist_df['نام'] = hist_df['students'].apply(lambda x: x['name'])
            hist_df['والد کا نام'] = hist_df['students'].apply(lambda x: x['father_name'])
            hist_df['شناختی نمبر'] = hist_df['students'].apply(lambda x: x.get('roll_no',''))
            hist_df = hist_df[['نام','والد کا نام','شناختی نمبر','dept','exam_type','from_para','to_para','book_name','amount_read','start_date','end_date','total','grade']]
            st.dataframe(hist_df, use_container_width=True)
            st.download_button("ہسٹری CSV", convert_df_to_csv(hist_df), "exam_history.csv")
        else: st.info("کوئی مکمل شدہ امتحان نہیں")

# 8.4 عملہ نگرانی و شکایات
elif selected == "📋 عملہ نگرانی و شکایات" and st.session_state.user_type == "admin":
    st.header("📋 عملہ نگرانی و شکایات")
    tab1, tab2 = st.tabs(["➕ نیا اندراج", "📜 ریکارڈ دیکھیں"])
    with tab1:
        with st.form("new_monitoring"):
            res = supabase.table("teachers").select("name").neq("name","admin").execute()
            staff_list = [t['name'] for t in res.data]
            if not staff_list: st.warning("کوئی استاد/عملہ موجود نہیں۔")
            else:
                staff_name = st.selectbox("عملہ کا نام", staff_list)
                note_date = st.date_input("تاریخ", date.today())
                note_type = st.selectbox("نوعیت", ["یادداشت","شکایت","تنبیہ","تعریف","کارکردگی جائزہ"])
                description = st.text_area("تفصیل", height=150)
                action_taken = st.text_area("کیا کارروائی کی گئی؟", height=100)
                status = st.selectbox("حالت", ["زیر التواء","حل شدہ","زیر غور"])
                if st.form_submit_button("محفوظ کریں"):
                    supabase.table("staff_monitoring").insert({"staff_name":staff_name,"date":str(note_date),"note_type":note_type,"description":description,"action_taken":action_taken,"status":status,"created_by":st.session_state.username}).execute()
                    log_audit(st.session_state.username, "Staff Monitoring Added", f"{staff_name} - {note_type}")
                    st.success("اندراج محفوظ ہو گیا")
                    st.rerun()
    with tab2:
        st.subheader("فلٹرز")
        res = supabase.table("teachers").select("name").neq("name","admin").execute()
        staff_names = ["تمام"] + [t['name'] for t in res.data]
        filter_staff = st.selectbox("عملہ فلٹر کریں", staff_names)
        filter_type = st.selectbox("نوعیت فلٹر کریں", ["تمام","یادداشت","شکایت","تنبیہ","تعریف","کارکردگی جائزہ"])
        start_date = st.date_input("تاریخ از", date.today() - timedelta(days=30))
        end_date = st.date_input("تاریخ تا", date.today())
        query = supabase.table("staff_monitoring").select("*").gte("date", str(start_date)).lte("date", str(end_date)).order("date", desc=True)
        if filter_staff != "تمام": query = query.eq("staff_name", filter_staff)
        if filter_type != "تمام": query = query.eq("note_type", filter_type)
        res = query.execute()
        if res.data:
            df = pd.DataFrame(res.data)
            st.dataframe(df, use_container_width=True)
            csv = convert_df_to_csv(df)
            st.download_button("📥 CSV ڈاؤن لوڈ کریں", csv, "staff_monitoring.csv", "text/csv")
            html_report = generate_html_report(df, "عملہ نگرانی و شکایات رپورٹ")
            st.download_button("📥 HTML رپورٹ ڈاؤن لوڈ کریں", html_report, "staff_monitoring_report.html", "text/html")
            if st.button("🖨️ پرنٹ کریں"): st.components.v1.html(f"<script>var w=window.open();w.document.write(`{html_report}`);w.print();</script>", height=0)
            with st.expander("⚠️ ریکارڈ حذف کریں"):
                record_id = st.number_input("ریکارڈ ID درج کریں", min_value=1, step=1)
                if st.button("حذف کریں"):
                    supabase.table("staff_monitoring").delete().eq("id", record_id).execute()
                    st.success("ریکارڈ حذف کر دیا گیا")
                    st.rerun()
        else: st.info("کوئی ریکارڈ موجود نہیں")

# 8.5 ماہانہ رزلٹ کارڈ
elif selected == "📜 ماہانہ رزلٹ کارڈ" and st.session_state.user_type == "admin":
    st.header("📜 ماہانہ رزلٹ کارڈ")
    res = supabase.table("students").select("id,name,father_name,roll_no,dept").execute()
    students_list = res.data
    if not students_list: st.warning("کوئی طالب علم نہیں")
    else:
        student_names = [f"{s['name']} ولد {s['father_name']} (شناختی نمبر: {s.get('roll_no','')}) - {s['dept']}" for s in students_list]
        sel = st.selectbox("طالب علم منتخب کریں", student_names)
        parts = sel.split(" ولد ")
        s_name = parts[0]
        rest = parts[1]
        f_name, rest2 = rest.split(" (شناختی نمبر: ")
        roll_no, dept = rest2.split(") - ")
        start = st.date_input("تاریخ آغاز", date.today().replace(day=1))
        end = st.date_input("تاریخ اختتام", date.today())
        student_id = [s['id'] for s in students_list if s['name'] == s_name and s['father_name'] == f_name][0]
        if dept == "حفظ":
            res = supabase.table("hifz_records").select("*").eq("student_id", student_id).gte("r_date", str(start)).lte("r_date", str(end)).order("r_date").execute()
            if res.data:
                df = pd.DataFrame(res.data)
                grades = []
                for _, row in df.iterrows():
                    att = row['attendance']
                    sabaq_nagha = (row['surah'] in ["ناغہ","یاد نہیں"])
                    sq_nagha = (row['sq_p'] in ["ناغہ","یاد نہیں"])
                    m_nagha = (row['m_p'] in ["ناغہ","یاد نہیں"])
                    sq_m = row['sq_m'] if row['sq_m'] else 0
                    m_m = row['m_m'] if row['m_m'] else 0
                    grade = calculate_grade_with_attendance(att, sabaq_nagha, sq_nagha, m_nagha, sq_m, m_m)
                    grades.append(grade)
                df['درجہ'] = grades
                df = df.rename(columns={'r_date':'تاریخ','attendance':'حاضری','surah':'سبق','lines':'کل ستر','sq_p':'سبقی','sq_m':'سبقی (غلطی)','sq_a':'سبقی (اٹکن)','m_p':'منزل','m_m':'منزل (غلطی)','m_a':'منزل (اٹکن)','cleanliness':'صفائی'})
                st.dataframe(df[['تاریخ','حاضری','سبق','سبقی','منزل','صفائی','درجہ']], use_container_width=True)
                html = generate_html_report(df, "ماہانہ رزلٹ کارڈ (حفظ)", student_name=f"{s_name} ولد {f_name}", start_date=start.strftime("%Y-%m-%d"), end_date=end.strftime("%Y-%m-%d"))
                st.download_button("📥 HTML ڈاؤن لوڈ", html, f"{s_name}_result.html", "text/html")
                if st.button("🖨️ پرنٹ کریں"): st.components.v1.html(f"<script>var w=window.open();w.document.write(`{html}`);w.print();</script>", height=0)
        elif dept == "قاعدہ":
            res = supabase.table("qaida_records").select("*").eq("student_id", student_id).gte("r_date", str(start)).lte("r_date", str(end)).order("r_date").execute()
            if res.data:
                df = pd.DataFrame(res.data)
                df = df.rename(columns={'r_date':'تاریخ','lesson_no':'تختی نمبر','total_lines':'کل لائنیں','details':'تفصیل','attendance':'حاضری','cleanliness':'صفائی'})
                st.dataframe(df, use_container_width=True)
                html = generate_html_report(df, "ماہانہ رزلٹ کارڈ (قاعدہ)", student_name=f"{s_name} ولد {f_name}", start_date=start.strftime("%Y-%m-%d"), end_date=end.strftime("%Y-%m-%d"))
                st.download_button("📥 HTML ڈاؤن لوڈ", html, f"{s_name}_qaida_result.html", "text/html")
                if st.button("🖨️ پرنٹ کریں"): st.components.v1.html(f"<script>var w=window.open();w.document.write(`{html}`);w.print();</script>", height=0)
            else: st.warning("کوئی ریکارڈ نہیں")
        else:
            res = supabase.table("general_education").select("*").eq("student_id", student_id).eq("dept", dept).gte("r_date", str(start)).lte("r_date", str(end)).order("r_date").execute()
            if res.data:
                df = pd.DataFrame(res.data)
                df = df.rename(columns={'r_date':'تاریخ','book_subject':'کتاب/مضمون','today_lesson':'آج کا سبق','homework':'ہوم ورک','performance':'کارکردگی','cleanliness':'صفائی'})
                st.dataframe(df, use_container_width=True)
                html = generate_html_report(df, "ماہانہ رزلٹ کارڈ", student_name=f"{s_name} ولد {f_name}", start_date=start.strftime("%Y-%m-%d"), end_date=end.strftime("%Y-%m-%d"))
                st.download_button("📥 HTML ڈاؤن لوڈ", html, f"{s_name}_result.html", "text/html")
                if st.button("🖨️ پرنٹ کریں"): st.components.v1.html(f"<script>var w=window.open();w.document.write(`{html}`);w.print();</script>", height=0)
            else: st.warning("کوئی ریکارڈ نہیں")

# 8.6 پارہ تعلیمی رپورٹ
elif selected == "📘 پارہ تعلیمی رپورٹ" and st.session_state.user_type == "admin":
    st.header("📘 پارہ تعلیمی رپورٹ")
    res = supabase.table("students").select("id,name,father_name").eq("dept","حفظ").execute()
    students_list = res.data
    if not students_list: st.warning("کوئی حفظ کا طالب علم نہیں")
    else:
        student_names = [f"{s['name']} ولد {s['father_name']}" for s in students_list]
        sel = st.selectbox("طالب علم منتخب کریں", student_names)
        s_name, f_name = sel.split(" ولد ")
        student_id = [s['id'] for s in students_list if s['name'] == s_name and s['father_name'] == f_name][0]
        res = supabase.table("passed_paras").select("para_no,passed_date,exam_type,grade,marks").eq("student_id", student_id).not_.is_("para_no","null").order("para_no").execute()
        if res.data:
            passed_df = pd.DataFrame(res.data)
            passed_df = passed_df.rename(columns={'para_no':'پارہ نمبر','passed_date':'تاریخ پاس','exam_type':'امتحان قسم','grade':'گریڈ','marks':'نمبر'})
            st.dataframe(passed_df, use_container_width=True)
            html = generate_para_report(s_name, f_name, passed_df)
            st.download_button("📥 رپورٹ ڈاؤن لوڈ کریں", html, f"Para_Report_{s_name}.html", "text/html")
            if st.button("🖨️ پرنٹ کریں"): st.components.v1.html(f"<script>var w=window.open();w.document.write(`{html}`);w.print();</script>", height=0)
        else: st.info("اس طالب علم کا کوئی پاس شدہ پارہ نہیں")

# 8.7 اساتذہ حاضری
elif selected == "🕒 اساتذہ حاضری" and st.session_state.user_type == "admin":
    st.header("اساتذہ حاضری ریکارڈ")
    res = supabase.table("t_attendance").select("a_date,t_name,arrival,departure").order("a_date", desc=True).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        df = df.rename(columns={'a_date':'تاریخ','t_name':'استاد','arrival':'آمد','departure':'رخصت'})
        st.dataframe(df, use_container_width=True)

# 8.8 رخصت کی منظوری
elif selected == "🏛️ رخصت کی منظوری" and st.session_state.user_type == "admin":
    st.header("رخصت کی منظوری")
    res = supabase.table("leave_requests").select("*").ilike("status", "%پینڈنگ%").execute()
    pending = res.data
    if not pending: st.info("کوئی پینڈنگ درخواست نہیں")
    else:
        for req in pending:
            with st.expander(f"{req['t_name']} | {req['l_type']} | {req['days']} دن"):
                st.write(f"وجہ: {req['reason']}")
                col1, col2 = st.columns(2)
                if col1.button("✅ منظور", key=f"app_{req['id']}"):
                    supabase.table("leave_requests").update({"status":"منظور"}).eq("id", req['id']).execute()
                    st.rerun()
                if col2.button("❌ مسترد", key=f"rej_{req['id']}"):
                    supabase.table("leave_requests").update({"status":"مسترد"}).eq("id", req['id']).execute()
                    st.rerun()

# 8.9 یوزر مینجمنٹ
elif selected == "👥 یوزر مینجمنٹ" and st.session_state.user_type == "admin":
    st.header("👥 یوزر مینجمنٹ")
    tab1, tab2 = st.tabs(["اساتذہ", "طلبہ"])
    with tab1:
        st.subheader("موجودہ اساتذہ")
        res = supabase.table("teachers").select("*").neq("name","admin").execute()
        teachers_df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        if not teachers_df.empty:
            edited_teachers = st.data_editor(teachers_df, num_rows="dynamic", use_container_width=True, key="teachers_edit")
            if st.button("اساتذہ میں تبدیلیاں محفوظ کریں"):
                for _, row in edited_teachers.iterrows():
                    if pd.isna(row['id']) or row['id'] == 0:
                        data = {k: row[k] for k in ['name','dept','phone','address','id_card','joining_date'] if k in row}
                        if 'password' in row and row['password']: data['password'] = hash_password(row['password'])
                        supabase.table("teachers").insert(data).execute()
                    else:
                        data = {k: row[k] for k in ['name','dept','phone','address','id_card','joining_date'] if k in row}
                        if 'password' in row and row['password']: data['password'] = hash_password(row['password'])
                        supabase.table("teachers").update(data).eq("id", row['id']).execute()
                st.success("تبدیلیاں محفوظ ہو گئیں")
                st.rerun()
        else: st.info("کوئی استاد موجود نہیں")
        with st.expander("➕ نیا استاد رجسٹر کریں"):
            with st.form("new_teacher_form"):
                name = st.text_input("استاد کا نام*")
                password = st.text_input("پاسورڈ*", type="password")
                dept = st.selectbox("شعبہ", ["حفظ","قاعدہ","درسِ نظامی","عصری تعلیم"])
                phone = st.text_input("فون نمبر")
                address = st.text_area("پتہ")
                id_card = st.text_input("شناختی کارڈ نمبر")
                joining_date = st.date_input("تاریخ شمولیت", date.today())
                if st.form_submit_button("رجسٹر کریں"):
                    if name and password:
                        supabase.table("teachers").insert({"name":name,"password":hash_password(password),"dept":dept,"phone":phone,"address":address,"id_card":id_card,"joining_date":str(joining_date)}).execute()
                        st.success("استاد کامیابی سے رجسٹر ہو گیا")
                        st.rerun()
                    else: st.error("نام اور پاسورڈ ضروری ہیں")
    with tab2:
        st.subheader("موجودہ طلبہ")
        res = supabase.table("students").select("*").execute()
        students_df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        if not students_df.empty:
            edited_students = st.data_editor(students_df, num_rows="dynamic", use_container_width=True, key="students_edit")
            if st.button("طلبہ میں تبدیلیاں محفوظ کریں"):
                for _, row in edited_students.iterrows():
                    if pd.isna(row['id']) or row['id'] == 0:
                        data = row.drop('id').to_dict()
                        for col in ['dob','admission_date','exit_date']:
                            if col in data and data[col]: data[col] = str(data[col])
                        supabase.table("students").insert(data).execute()
                    else:
                        data = row.drop('id').to_dict()
                        for col in ['dob','admission_date','exit_date']:
                            if col in data and data[col]: data[col] = str(data[col])
                        supabase.table("students").update(data).eq("id", row['id']).execute()
                st.success("تبدیلیاں محفوظ ہو گئیں")
                st.rerun()
        else: st.info("کوئی طالب علم موجود نہیں")
        with st.expander("➕ نیا طالب علم داخل کریں"):
            with st.form("new_student_form"):
                col1, col2 = st.columns(2)
                with col1:
                    name = st.text_input("طالب علم کا نام*")
                    father = st.text_input("والد کا نام*")
                    mother = st.text_input("والدہ کا نام")
                    dob = st.date_input("تاریخ پیدائش", date.today() - timedelta(days=365*10))
                    admission_date = st.date_input("تاریخ داخلہ", date.today())
                    roll_no = st.text_input("شناختی نمبر (اختیاری)")
                with col2:
                    dept = st.selectbox("شعبہ*", ["حفظ","قاعدہ","درسِ نظامی","عصری تعلیم"])
                    class_name = st.text_input("کلاس (عصری تعلیم کے لیے)")
                    section = st.text_input("سیکشن")
                    res_t = supabase.table("teachers").select("name").neq("name","admin").execute()
                    teachers_list = [t['name'] for t in res_t.data]
                    teacher = st.selectbox("استاد*", teachers_list) if teachers_list else st.text_input("استاد کا نام*")
                id_card = st.text_input("B-Form / شناختی کارڈ نمبر")
                phone = st.text_input("فون نمبر")
                address = st.text_area("پتہ")
                exit_date = st.date_input("تاریخ خارج", value=None)
                exit_reason = st.text_area("وجہ خارج")
                if st.form_submit_button("داخلہ کریں"):
                    if name and father and teacher and dept:
                        supabase.table("students").insert({"name":name,"father_name":father,"mother_name":mother,"dob":str(dob) if dob else None,"admission_date":str(admission_date),"exit_date":str(exit_date) if exit_date else None,"exit_reason":exit_reason,"id_card":id_card,"phone":phone,"address":address,"teacher_name":teacher,"dept":dept,"class":class_name,"section":section,"roll_no":roll_no}).execute()
                        st.success("طالب علم کامیابی سے داخل ہو گیا")
                        st.rerun()
                    else: st.error("نام، ولدیت، استاد اور شعبہ ضروری ہیں")

# 8.10 ٹائم ٹیبل مینجمنٹ
elif selected == "📚 ٹائم ٹیبل مینجمنٹ" and st.session_state.user_type == "admin":
    st.header("📚 ٹائم ٹیبل مینجمنٹ")
    res = supabase.table("teachers").select("name").neq("name","admin").execute()
    teachers = [t['name'] for t in res.data]
    if not teachers: st.warning("پہلے اساتذہ رجسٹر کریں")
    else:
        sel_t = st.selectbox("استاد منتخب کریں", teachers)
        res_tt = supabase.table("timetable").select("*").eq("t_name", sel_t).execute()
        tt_df = pd.DataFrame(res_tt.data) if res_tt.data else pd.DataFrame()
        if not tt_df.empty:
            st.subheader("موجودہ ٹائم ٹیبل")
            day_order = {"ہفتہ":0,"اتوار":1,"پیر":2,"منگل":3,"بدھ":4,"جمعرات":5}
            tt_df['day_order'] = tt_df['day'].map(day_order)
            tt_df = tt_df.sort_values(['day_order','period'])
            st.dataframe(tt_df[['day','period','book','room']].rename(columns={'day':'دن','period':'وقت','book':'کتاب','room':'کمرہ'}), use_container_width=True)
        with st.expander("➕ نیا پیریڈ شامل کریں"):
            with st.form("add_period"):
                col1, col2 = st.columns(2)
                day = col1.selectbox("دن", ["ہفتہ","اتوار","پیر","منگل","بدھ","جمعرات"])
                period = col2.text_input("وقت (مثلاً 08:00-09:00)")
                book = st.text_input("کتاب / مضمون")
                room = st.text_input("کمرہ نمبر")
                if st.form_submit_button("شامل کریں"):
                    supabase.table("timetable").insert({"t_name":sel_t,"day":day,"period":period,"book":book,"room":room}).execute()
                    st.success("پیریڈ شامل کر دیا گیا")
                    st.rerun()

# 8.11 پاسورڈ تبدیل کریں
elif selected == "🔑 پاسورڈ تبدیل کریں":
    st.header("🔑 پاسورڈ تبدیل کریں")
    if st.session_state.user_type == "admin":
        res = supabase.table("teachers").select("name").neq("name","admin").execute()
        teachers = [t['name'] for t in res.data]
        if teachers:
            selected_teacher = st.selectbox("استاد منتخب کریں", teachers)
            new_pass = st.text_input("نیا پاسورڈ", type="password")
            confirm_pass = st.text_input("پاسورڈ کی تصدیق کریں", type="password")
            if st.button("پاسورڈ تبدیل کریں"):
                if new_pass and new_pass == confirm_pass:
                    admin_reset_password(selected_teacher, new_pass)
                    st.success(f"{selected_teacher} کا پاسورڈ تبدیل کر دیا گیا")
                else: st.error("پاسورڈ میل نہیں کھاتے")
        else: st.info("کوئی دوسرا استاد موجود نہیں")
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
                else: st.error("پرانا پاسورڈ غلط ہے")
            else: st.error("نیا پاسورڈ اور تصدیق ایک جیسی ہونی چاہیے")

# 8.12 نوٹیفیکیشنز
elif selected == "📢 نوٹیفیکیشنز":
    st.header("نوٹیفیکیشن سینٹر")
    if st.session_state.user_type == "admin":
        with st.form("new_notif"):
            title = st.text_input("عنوان")
            msg = st.text_area("پیغام")
            target = st.selectbox("بھیجیں", ["تمام","اساتذہ","طلبہ"])
            if st.form_submit_button("بھیجیں"):
                supabase.table("notifications").insert({"title":title,"message":msg,"target":target}).execute()
                st.success("نوٹیفکیشن بھیج دیا گیا")
    res = supabase.table("notifications").select("*").order("created_at", desc=True).limit(10).execute()
    if st.session_state.user_type != "admin": res = supabase.table("notifications").select("*").in_("target", ["تمام","اساتذہ"]).order("created_at", desc=True).limit(10).execute()
    for n in res.data: st.info(f"**{n['title']}**\n\n{n['message']}\n\n*{n['created_at']}*")

# 8.13 تجزیہ و رپورٹس
elif selected == "📈 تجزیہ و رپورٹس" and st.session_state.user_type == "admin":
    st.header("تجزیہ")
    res = supabase.table("t_attendance").select("a_date").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        df['a_date'] = pd.to_datetime(df['a_date'])
        fig = px.bar(df, x='a_date', title="اساتذہ کی حاضری")
        st.plotly_chart(fig)

# 8.14 ماہانہ بہترین طلباء
elif selected == "🏆 ماہانہ بہترین طلباء" and st.session_state.user_type == "admin":
    st.markdown("<div class='main-header'><h1>🏆 ماہانہ بہترین طلباء</h1><p>تعلیمی اور صفائی کی بنیاد پر بہترین کارکردگی</p></div>", unsafe_allow_html=True)
    month_year = st.date_input("مہینہ منتخب کریں", date.today().replace(day=1), key="month_picker")
    start_date = month_year.replace(day=1)
    if month_year.month == 12: end_date = month_year.replace(year=month_year.year+1, month=1, day=1) - timedelta(days=1)
    else: end_date = month_year.replace(month=month_year.month+1, day=1) - timedelta(days=1)
    st.markdown(f"### 📅 {start_date.strftime('%B %Y')} کے لیے نتائج")
    res_s = supabase.table("students").select("id,name,father_name,roll_no,dept").execute()
    students = res_s.data
    if not students: st.warning("کوئی طالب علم موجود نہیں")
    else:
        student_scores = []
        for s in students:
            sid = s['id']; dept = s['dept']
            if dept == "حفظ":
                res = supabase.table("hifz_records").select("attendance,surah,sq_p,m_p,sq_m,m_m,cleanliness").eq("student_id", sid).gte("r_date", str(start_date)).lte("r_date", str(end_date)).execute()
                grade_scores = []; clean_scores = []
                for rec in res.data:
                    att = rec['attendance']
                    sabaq_nagha = (rec['surah'] in ["ناغہ","یاد نہیں"])
                    sq_nagha = (rec['sq_p'] in ["ناغہ","یاد نہیں"])
                    m_nagha = (rec['m_p'] in ["ناغہ","یاد نہیں"])
                    sq_m = rec['sq_m'] or 0; m_m = rec['m_m'] or 0
                    grade = calculate_grade_with_attendance(att, sabaq_nagha, sq_nagha, m_nagha, sq_m, m_m)
                    if grade == "ممتاز": grade_scores.append(100)
                    elif grade == "جید جداً": grade_scores.append(85)
                    elif grade == "جید": grade_scores.append(75)
                    elif grade == "مقبول": grade_scores.append(60)
                    elif grade == "دوبارہ کوشش کریں": grade_scores.append(40)
                    elif grade == "ناقص (ناغہ)": grade_scores.append(30)
                    elif grade == "کمزور (ناغہ)": grade_scores.append(20)
                    elif grade == "ناکام (مکمل ناغہ)": grade_scores.append(10)
                    elif grade == "غیر حاضر": grade_scores.append(0)
                    elif grade == "رخصت": grade_scores.append(50)
                    if rec.get('cleanliness'): clean_scores.append(cleanliness_to_score(rec['cleanliness']))
                avg_grade = sum(grade_scores)/len(grade_scores) if grade_scores else 0
                avg_clean = sum(clean_scores)/len(clean_scores) if clean_scores else 0
            elif dept == "قاعدہ":
                res = supabase.table("qaida_records").select("attendance,cleanliness").eq("student_id", sid).gte("r_date", str(start_date)).lte("r_date", str(end_date)).execute()
                grade_scores = []; clean_scores = []
                for rec in res.data:
                    att = rec['attendance']
                    if att == "حاضر": grade_scores.append(85)
                    elif att == "رخصت": grade_scores.append(50)
                    else: grade_scores.append(0)
                    if rec.get('cleanliness'): clean_scores.append(cleanliness_to_score(rec['cleanliness']))
                avg_grade = sum(grade_scores)/len(grade_scores) if grade_scores else 0
                avg_clean = sum(clean_scores)/len(clean_scores) if clean_scores else 0
            else:
                res = supabase.table("general_education").select("attendance,performance,cleanliness").eq("student_id", sid).eq("dept", dept).gte("r_date", str(start_date)).lte("r_date", str(end_date)).execute()
                grade_scores = []; clean_scores = []
                for rec in res.data:
                    att = rec['attendance']; perf = rec.get('performance','')
                    if att == "حاضر":
                        if perf == "بہت بہتر": grade_scores.append(90)
                        elif perf == "بہتر": grade_scores.append(80)
                        elif perf == "مناسب": grade_scores.append(65)
                        elif perf == "کمزور": grade_scores.append(45)
                        else: grade_scores.append(75)
                    elif att == "رخصت": grade_scores.append(50)
                    else: grade_scores.append(0)
                    if rec.get('cleanliness'): clean_scores.append(cleanliness_to_score(rec['cleanliness']))
                avg_grade = sum(grade_scores)/len(grade_scores) if grade_scores else 0
                avg_clean = sum(clean_scores)/len(clean_scores) if clean_scores else 0
            student_scores.append({"name":s['name'],"father":s['father_name'],"roll":s.get('roll_no',''),"dept":dept,"avg_grade":avg_grade,"avg_clean":avg_clean})
        sorted_grade = sorted(student_scores, key=lambda x: x["avg_grade"], reverse=True)
        sorted_clean = sorted(student_scores, key=lambda x: x["avg_clean"], reverse=True)
        st.subheader("📚 تعلیمی کارکردگی کے لحاظ سے بہترین طلباء")
        cols = st.columns(3)
        for i, student in enumerate(sorted_grade[:3]):
            with cols[i]:
                medal = ["🥇","🥈","🥉"][i]; color_class = ["gold","silver","bronze"][i]
                st.markdown(f"""<div class="best-student-card"><h2 class="{color_class}">{medal}</h2><h3>{student['name']}</h3><p>والد: {student['father']}</p><p>شناختی نمبر: {student['roll'] or '-'}</p><p>شعبہ: {student['dept']}</p><p>اوسط نمبر: {student['avg_grade']:.1f}%</p></div>""", unsafe_allow_html=True)
        st.subheader("🧹 صفائی کے لحاظ سے بہترین طلباء")
        cols = st.columns(3)
        for i, student in enumerate(sorted_clean[:3]):
            with cols[i]:
                medal = ["🥇","🥈","🥉"][i]; color_class = ["gold","silver","bronze"][i]
                clean_percent = (student['avg_clean'] / 3) * 100 if student['avg_clean'] else 0
                st.markdown(f"""<div class="best-student-card"><h2 class="{color_class}">{medal}</h2><h3>{student['name']}</h3><p>والد: {student['father']}</p><p>شناختی نمبر: {student['roll'] or '-'}</p><p>شعبہ: {student['dept']}</p><p>صفائی اوسط: {clean_percent:.1f}%</p></div>""", unsafe_allow_html=True)

# 8.15 بیک اپ & سیٹنگز
elif selected == "⚙️ بیک اپ & سیٹنگز" and st.session_state.user_type == "admin":
    st.header("بیک اپ اور سیٹنگز")
    st.subheader("📥 ڈیٹا بیک اپ (CSV)")
    tables = ["teachers","students","hifz_records","qaida_records","general_education","t_attendance","exams","passed_paras","timetable","leave_requests","notifications","audit_log","staff_monitoring"]
    if st.button("💾 تمام ٹیبلز کی CSV بیک اپ (زپ) بنائیں"):
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for t in tables:
                res = supabase.table(t).select("*").execute()
                if res.data:
                    df = pd.DataFrame(res.data)
                    csv_data = df.to_csv(index=False).encode('utf-8-sig')
                    zip_file.writestr(f"{t}.csv", csv_data)
        zip_buffer.seek(0)
        st.download_button(label="📥 CSV بیک اپ زپ ڈاؤن لوڈ کریں", data=zip_buffer, file_name=f"backup_tables_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip", mime="application/zip")
    st.markdown("---")
    with st.expander("آڈٹ لاگ"):
        res = supabase.table("audit_log").select("*").order("timestamp", desc=True).limit(50).execute()
        if res.data: st.dataframe(pd.DataFrame(res.data))

# ==================== استاد سیکشنز ====================
# 9.1 روزانہ سبق اندراج
if selected == "📝 روزانہ سبق اندراج" and st.session_state.user_type == "teacher":
    st.header("📝 روزانہ سبق اندراج")
    entry_date = st.date_input("تاریخ (جس دن کا اندراج کرنا ہے)", date.today())
    dept = st.selectbox("شعبہ منتخب کریں", ["حفظ","قاعدہ","درسِ نظامی","عصری تعلیم"])
    if dept == "حفظ":
        st.subheader("حفظ کا اندراج")
        res = supabase.table("students").select("id,name,father_name").eq("teacher_name", st.session_state.username).eq("dept","حفظ").execute()
        students = res.data
        if not students: st.info("آپ کی کلاس میں کوئی طالب علم نہیں")
        else:
            for s in students:
                sid, s_name, f_name = s['id'], s['name'], s['father_name']
                key = f"{sid}_{s_name}_{f_name}"
                st.markdown(f"### 👤 {s_name} ولد {f_name}")
                att = st.radio("حاضری", ["حاضر","غیر حاضر","رخصت"], key=f"att_{key}", horizontal=True)
                cleanliness = st.selectbox("صفائی کا معیار", cleanliness_options, key=f"clean_{key}")
                if att != "حاضر":
                    grade = calculate_grade_with_attendance(att, False, False, False, 0, 0)
                    st.info(f"**اس طالب علم کا درجہ:** {grade}")
                    if st.button(f"محفوظ کریں ({s_name})", key=f"save_absent_{key}"):
                        supabase.table("hifz_records").insert({"r_date":str(entry_date),"student_id":sid,"t_name":st.session_state.username,"surah":"غائب","lines":0,"sq_p":"غائب","sq_a":0,"sq_m":0,"m_p":"غائب","m_a":0,"m_m":0,"attendance":att,"cleanliness":cleanliness}).execute()
                        st.success("محفوظ ہو گیا")
                    st.markdown("---")
                    continue
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
                    lines = st.number_input("کل ستر", min_value=0, value=0, key=f"lines_{key}")
                st.write("**سبقی**")
                col1, col2 = st.columns(2)
                sq_nagha = col1.checkbox("ناغہ", key=f"sq_nagha_{key}")
                sq_yad_nahi = col2.checkbox("یاد نہیں", key=f"sq_yad_{key}")
                if sq_nagha or sq_yad_nahi:
                    sq_text = "ناغہ" if sq_nagha else "یاد نہیں"
                    sq_parts = [sq_text]; sq_a = 0; sq_m = 0
                else:
                    if f"sq_rows_{key}" not in st.session_state: st.session_state[f"sq_rows_{key}"] = 1
                    sq_parts = []; sq_a = 0; sq_m = 0
                    for i in range(st.session_state[f"sq_rows_{key}"]):
                        cols = st.columns([2,2,1,1])
                        p = cols[0].selectbox("پارہ", paras, key=f"sqp_{key}_{i}")
                        v = cols[1].selectbox("مقدار", ["مکمل","آدھا","پون","پاؤ"], key=f"sqv_{key}_{i}")
                        a = cols[2].number_input("اٹکن", 0, key=f"sqa_{key}_{i}")
                        e = cols[3].number_input("غلطی", 0, key=f"sqe_{key}_{i}")
                        sq_parts.append(f"{p}:{v}"); sq_a += a; sq_m += e
                    if st.button("➕", key=f"add_sq_{key}"): st.session_state[f"sq_rows_{key}"] += 1; st.rerun()
                st.write("**منزل**")
                col1, col2 = st.columns(2)
                m_nagha = col1.checkbox("ناغہ", key=f"m_nagha_{key}")
                m_yad_nahi = col2.checkbox("یاد نہیں", key=f"m_yad_{key}")
                if m_nagha or m_yad_nahi:
                    m_text = "ناغہ" if m_nagha else "یاد نہیں"
                    m_parts = [m_text]; m_a = 0; m_m = 0
                else:
                    if f"m_rows_{key}" not in st.session_state: st.session_state[f"m_rows_{key}"] = 1
                    m_parts = []; m_a = 0; m_m = 0
                    for j in range(st.session_state[f"m_rows_{key}"]):
                        cols = st.columns([2,2,1,1])
                        p = cols[0].selectbox("پارہ", paras, key=f"mp_{key}_{j}")
                        v = cols[1].selectbox("مقدار", ["مکمل","آدھا","پون","پاؤ"], key=f"mv_{key}_{j}")
                        a = cols[2].number_input("اٹکن", 0, key=f"ma_{key}_{j}")
                        e = cols[3].number_input("غلطی", 0, key=f"me_{key}_{j}")
                        m_parts.append(f"{p}:{v}"); m_a += a; m_m += e
                    if st.button("➕", key=f"add_m_{key}"): st.session_state[f"m_rows_{key}"] += 1; st.rerun()
                sabaq_nagha_bool = sabaq_nagha or sabaq_yad_nahi
                sq_nagha_bool = sq_nagha or sq_yad_nahi
                m_nagha_bool = m_nagha or m_yad_nahi
                grade = calculate_grade_with_attendance(att, sabaq_nagha_bool, sq_nagha_bool, m_nagha_bool, sq_m, m_m)
                st.info(f"**درجہ:** {grade}")
                if st.button(f"محفوظ کریں ({s_name})", key=f"save_{key}"):
                    supabase.table("hifz_records").insert({"r_date":str(entry_date),"student_id":sid,"t_name":st.session_state.username,"surah":sabaq_text,"lines":lines,"sq_p":" | ".join(sq_parts),"sq_a":sq_a,"sq_m":sq_m,"m_p":" | ".join(m_parts),"m_a":m_a,"m_m":m_m,"attendance":att,"cleanliness":cleanliness}).execute()
                    log_audit(st.session_state.username, "Hifz Entry", f"{s_name} {entry_date}")
                    st.success("محفوظ ہو گیا")
                st.markdown("---")
    elif dept == "قاعدہ":
        st.subheader("قاعدہ (نورانی قاعدہ / نماز) کا اندراج")
        res = supabase.table("students").select("id,name,father_name").eq("teacher_name", st.session_state.username).eq("dept","قاعدہ").execute()
        students = res.data
        if not students: st.info("آپ کی کلاس میں کوئی طالب علم نہیں")
        else:
            for s in students:
                sid, s_name, f_name = s['id'], s['name'], s['father_name']
                key = f"{sid}_{s_name}_{f_name}"
                st.markdown(f"### 👤 {s_name} ولد {f_name}")
                att = st.radio("حاضری", ["حاضر","غیر حاضر","رخصت"], key=f"att_{key}", horizontal=True)
                cleanliness = st.selectbox("صفائی کا معیار", cleanliness_options, key=f"clean_{key}")
                if att == "حاضر":
                    col1, col2 = st.columns(2)
                    nagha = col1.checkbox("ناغہ", key=f"nagha_{key}")
                    yad_nahi = col2.checkbox("یاد نہیں", key=f"yad_nahi_{key}")
                    if nagha or yad_nahi: lesson_no = "ناغہ" if nagha else "یاد نہیں"; total_lines = 0; details = ""
                    else:
                        lesson_type = st.radio("نوعیت", ["نورانی قاعدہ","نماز (حنفی)"], key=f"lesson_type_{key}", horizontal=True)
                        if lesson_type == "نورانی قاعدہ":
                            lesson_no = st.text_input("تختی نمبر / سبق نمبر", key=f"lesson_{key}")
                            total_lines = st.number_input("کل لائنیں", min_value=0, value=0, key=f"lines_{key}")
                            details = ""
                        else:
                            lesson_no = st.selectbox("سبق منتخب کریں", ["وضو کا طریقہ","غسل کا طریقہ","تیمم کا طریقہ","اذان و اقامت","نماز کا طریقہ (مسنون)","دعائے ثنا","سورہ فاتحہ","سورہ اخلاص","قنوت دعا","تشہد","درود شریف","دعائے ختم نماز"], key=f"lesson_{key}")
                            total_lines = st.number_input("کل لائنیں (اگر کوئی ہوں)", min_value=0, value=0, key=f"lines_{key}")
                            details = st.text_area("تفصیل / نوٹ", key=f"details_{key}")
                    if st.button(f"محفوظ کریں ({s_name})", key=f"save_{key}"):
                        supabase.table("qaida_records").insert({"r_date":str(entry_date),"student_id":sid,"t_name":st.session_state.username,"lesson_no":lesson_no,"total_lines":total_lines,"details":details,"attendance":att,"cleanliness":cleanliness}).execute()
                        log_audit(st.session_state.username, "Qaida Entry", f"{s_name} {entry_date}")
                        st.success("محفوظ ہو گیا")
                else:
                    if st.button(f"غیر حاضر / رخصت محفوظ کریں ({s_name})", key=f"save_absent_{key}"):
                        supabase.table("qaida_records").insert({"r_date":str(entry_date),"student_id":sid,"t_name":st.session_state.username,"lesson_no":"غائب","total_lines":0,"details":"","attendance":att,"cleanliness":cleanliness}).execute()
                        st.success("محفوظ ہو گیا")
                st.markdown("---")
    elif dept == "درسِ نظامی":
        st.subheader("درسِ نظامی سبق ریکارڈ")
        res = supabase.table("students").select("id,name,father_name").eq("teacher_name", st.session_state.username).eq("dept","درسِ نظامی").execute()
        students = res.data
        if not students: st.info("کوئی طالب علم نہیں")
        else:
            with st.form("dars_form"):
                records = []
                for s in students:
                    sid, s_name, f_name = s['id'], s['name'], s['father_name']
                    st.markdown(f"### {s_name} ولد {f_name}")
                    att = st.radio("حاضری", ["حاضر","غیر حاضر","رخصت"], key=f"att_dars_{sid}", horizontal=True)
                    cleanliness = st.selectbox("صفائی کا معیار", cleanliness_options, key=f"clean_dars_{sid}")
                    if att == "حاضر":
                        col1, col2 = st.columns(2)
                        nagha = col1.checkbox("ناغہ", key=f"nagha_dars_{sid}")
                        yad_nahi = col2.checkbox("یاد نہیں", key=f"yad_dars_{sid}")
                        if nagha or yad_nahi: book = "ناغہ" if nagha else "یاد نہیں"; lesson = "ناغہ" if nagha else "یاد نہیں"; perf = "ناغہ" if nagha else "یاد نہیں"
                        else:
                            book = st.text_input("کتاب کا نام", key=f"book_{sid}")
                            lesson = st.text_area("آج کا سبق", key=f"lesson_{sid}")
                            perf = st.select_slider("کارکردگی", ["بہت بہتر","بہتر","مناسب","کمزور"], key=f"perf_{sid}")
                        records.append((str(entry_date), sid, st.session_state.username, "درسِ نظامی", book, lesson, perf, att, cleanliness))
                    else: records.append((str(entry_date), sid, st.session_state.username, "درسِ نظامی", "غائب", "غائب", "غائب", att, cleanliness))
                if st.form_submit_button("محفوظ کریں"):
                    for rec in records:
                        supabase.table("general_education").insert({"r_date":rec[0],"student_id":rec[1],"t_name":rec[2],"dept":rec[3],"book_subject":rec[4],"today_lesson":rec[5],"performance":rec[6],"attendance":rec[7],"cleanliness":rec[8]}).execute()
                    st.success("محفوظ ہو گیا")
    elif dept == "عصری تعلیم":
        st.subheader("عصری تعلیم ڈائری")
        res = supabase.table("students").select("id,name,father_name").eq("teacher_name", st.session_state.username).eq("dept","عصری تعلیم").execute()
        students = res.data
        if not students: st.info("کوئی طالب علم نہیں")
        else:
            with st.form("school_form"):
                records = []
                for s in students:
                    sid, s_name, f_name = s['id'], s['name'], s['father_name']
                    st.markdown(f"### {s_name} ولد {f_name}")
                    att = st.radio("حاضری", ["حاضر","غیر حاضر","رخصت"], key=f"att_school_{sid}", horizontal=True)
                    cleanliness = st.selectbox("صفائی کا معیار", cleanliness_options, key=f"clean_school_{sid}")
                    if att == "حاضر":
                        col1, col2 = st.columns(2)
                        nagha = col1.checkbox("ناغہ", key=f"nagha_school_{sid}")
                        yad_nahi = col2.checkbox("یاد نہیں", key=f"yad_school_{sid}")
                        if nagha or yad_nahi: subject = "ناغہ" if nagha else "یاد نہیں"; topic = "ناغہ" if nagha else "یاد نہیں"; hw = "ناغہ" if nagha else "یاد نہیں"
                        else:
                            subject = st.selectbox("مضمون", ["اردو","انگلش","ریاضی","سائنس","اسلامیات","سماجی علوم"], key=f"sub_{sid}")
                            topic = st.text_input("عنوان", key=f"topic_{sid}")
                            hw = st.text_area("ہوم ورک", key=f"hw_{sid}")
                        records.append((str(entry_date), sid, st.session_state.username, "عصری تعلیم", subject, topic, hw, att, cleanliness))
                    else: records.append((str(entry_date), sid, st.session_state.username, "عصری تعلیم", "غائب", "غائب", "غائب", att, cleanliness))
                if st.form_submit_button("محفوظ کریں"):
                    for rec in records:
                        supabase.table("general_education").insert({"r_date":rec[0],"student_id":rec[1],"t_name":rec[2],"dept":rec[3],"book_subject":rec[4],"today_lesson":rec[5],"homework":rec[6],"attendance":rec[7],"cleanliness":rec[8]}).execute()
                    st.success("محفوظ ہو گیا")

# 9.2 امتحانی درخواست
elif selected == "🎓 امتحانی درخواست" and st.session_state.user_type == "teacher":
    st.subheader("امتحان کے لیے طالب علم نامزد کریں")
    res = supabase.table("students").select("id,name,father_name,dept").eq("teacher_name", st.session_state.username).execute()
    students = res.data
    if not students: st.warning("کوئی طالب علم نہیں")
    else:
        with st.form("exam_request"):
            s_list = [f"{s['name']} ولد {s['father_name']} ({s['dept']})" for s in students]
            sel = st.selectbox("طالب علم", s_list)
            s_name, rest = sel.split(" ولد ")
            f_name, dept = rest.split(" ("); dept = dept.replace(")","")
            student_id = [s['id'] for s in students if s['name'] == s_name and s['father_name'] == f_name][0]
            exam_type = st.selectbox("امتحان کی قسم", ["پارہ ٹیسٹ","ماہانہ","سہ ماہی","سالانہ"])
            start_date = st.date_input("تاریخ ابتدا", date.today())
            end_date = st.date_input("تاریخ اختتام", date.today() + timedelta(days=7))
            total_days = (end_date - start_date).days + 1
            st.write(f"**کل دن:** {total_days}")
            from_para = to_para = 0; book_name = amount_read = ""
            if exam_type == "پارہ ٹیسٹ":
                col1, col2 = st.columns(2)
                from_para = col1.number_input("پارہ نمبر (شروع)", min_value=1, max_value=30, value=1)
                to_para = col2.number_input("پارہ نمبر (اختتام)", min_value=from_para, max_value=30, value=from_para)
            else:
                if dept == "حفظ":
                    col1, col2 = st.columns(2)
                    from_para = col1.number_input("پارہ نمبر (شروع)", min_value=1, max_value=30, value=1)
                    to_para = col2.number_input("پارہ نمبر (اختتام)", min_value=from_para, max_value=30, value=min(from_para+4,30))
                    amount_read = st.text_input("مقدار خواندگی", placeholder="مقدار")
                else:
                    col1, col2 = st.columns(2)
                    book_name = col1.text_input("کتاب کا نام", placeholder="مثلاً: نحو میر, قدوری")
                    amount_read = col2.text_input("مقدار خواندگی", placeholder="مثلاً: باب اول تا باب پنجم")
            if st.form_submit_button("بھیجیں"):
                supabase.table("exams").insert({"student_id":student_id,"dept":dept,"exam_type":exam_type,"from_para":from_para,"to_para":to_para,"book_name":book_name,"amount_read":amount_read,"start_date":str(start_date),"end_date":str(end_date),"total_days":total_days,"status":"پینڈنگ"}).execute()
                st.success("درخواست بھیج دی گئی")

# 9.3 رخصت کی درخواست
elif selected == "📩 رخصت کی درخواست" and st.session_state.user_type == "teacher":
    st.header("📩 رخصت کی درخواست")
    with st.form("leave_request_form"):
        l_type = st.selectbox("رخصت کی نوعیت", ["بیماری","ضروری کام","ہنگامی","دیگر"])
        start_date = st.date_input("تاریخ آغاز", date.today())
        days = st.number_input("دنوں کی تعداد", min_value=1, max_value=30, value=1)
        back_date = start_date + timedelta(days=days-1)
        st.write(f"واپسی کی تاریخ: {back_date}")
        reason = st.text_area("تفصیلی وجہ")
        if st.form_submit_button("درخواست جمع کریں"):
            if reason:
                supabase.table("leave_requests").insert({"t_name":st.session_state.username,"l_type":l_type,"start_date":str(start_date),"days":days,"reason":reason,"status":"پینڈنگ","notification_seen":0,"request_date":str(date.today())}).execute()
                log_audit(st.session_state.username, "Leave Requested", f"{l_type} for {days} days")
                st.success("درخواست بھیج دی گئی۔")
            else: st.error("براہ کرم وجہ تحریر کریں")

# 9.4 میری حاضری
elif selected == "🕒 میری حاضری" and st.session_state.user_type == "teacher":
    st.header("🕒 میری حاضری")
    today = date.today()
    res = supabase.table("t_attendance").select("*").eq("t_name", st.session_state.username).eq("a_date", str(today)).execute()
    rec = res.data[0] if res.data else None
    if not rec:
        col1, col2 = st.columns(2)
        arr_date = col1.date_input("تاریخ", today)
        arr_time = col2.time_input("آمد کا وقت", datetime.now().time())
        if st.button("آمد درج کریں"):
            time_str = arr_time.strftime("%I:%M %p")
            supabase.table("t_attendance").insert({"t_name":st.session_state.username,"a_date":str(arr_date),"arrival":time_str,"actual_arrival":get_pk_time()}).execute()
            st.success("آمد درج ہو گئی")
            st.rerun()
    elif rec and not rec.get('departure'):
        st.success(f"آمد: {rec['arrival']}")
        dep_time = st.time_input("رخصت کا وقت", datetime.now().time())
        if st.button("رخصت درج کریں"):
            time_str = dep_time.strftime("%I:%M %p")
            supabase.table("t_attendance").update({"departure":time_str,"actual_departure":get_pk_time()}).eq("t_name", st.session_state.username).eq("a_date", str(today)).execute()
            st.success("رخصت درج ہو گئی")
            st.rerun()
    else: st.success(f"آمد: {rec['arrival']} | رخصت: {rec['departure']}")

# 9.5 میرا ٹائم ٹیبل
elif selected == "📚 میرا ٹائم ٹیبل" and st.session_state.user_type == "teacher":
    st.header("📚 میرا ٹائم ٹیبل")
    res = supabase.table("timetable").select("*").eq("t_name", st.session_state.username).execute()
    tt_df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
    if tt_df.empty: st.info("ابھی آپ کا ٹائم ٹیبل ترتیب نہیں دیا گیا")
    else:
        day_order = {"ہفتہ":0,"اتوار":1,"پیر":2,"منگل":3,"بدھ":4,"جمعرات":5}
        tt_df['day_order'] = tt_df['day'].map(day_order)
        tt_df = tt_df.sort_values(['day_order','period'])
        pivot = tt_df.pivot(index='period', columns='day', values='book').fillna("—")
        st.dataframe(pivot, use_container_width=True)
        tt_df_renamed = tt_df.rename(columns={'day':'دن','period':'وقت','book':'کتاب','room':'کمرہ'})
        html_timetable = generate_timetable_html(tt_df_renamed)
        st.download_button("📥 HTML ڈاؤن لوڈ کریں", html_timetable, f"Timetable_{st.session_state.username}.html", "text/html")
        if st.button("🖨️ پرنٹ کریں"): st.components.v1.html(f"<script>var w=window.open();w.document.write(`{html_timetable}`);w.print();</script>", height=0)

# ==================== لاگ آؤٹ ====================
st.sidebar.divider()
if st.sidebar.button("🚪 لاگ آؤٹ"):
    st.session_state.logged_in = False
    st.rerun()
