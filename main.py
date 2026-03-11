import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import sqlite3
import base64

# ================= 1. ڈیٹا بیس سیٹ اپ =================
DB_NAME = 'jamia_millia_v1.db'
conn = sqlite3.connect(DB_NAME, check_same_thread=False)
c = conn.cursor()

# پاکستان کا وقت حاصل کرنے کا فنکشن
def get_pkt_time():
    return datetime.utcnow() + timedelta(hours=5)

def init_db():
    c.execute('''CREATE TABLE IF NOT EXISTS teachers 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, password TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS students 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, father_name TEXT, teacher_name TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS hifz_records 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, r_date DATE, s_name TEXT, f_name TEXT, t_name TEXT, 
                  surah TEXT, a_from TEXT, a_to TEXT, sq_p TEXT, sq_a INTEGER, sq_m INTEGER, 
                  m_p TEXT, m_a INTEGER, m_m INTEGER, attendance TEXT, principal_note TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS t_attendance 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, t_name TEXT, a_date DATE, arrival TEXT, departure TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS leave_requests 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, t_name TEXT, reason TEXT, start_date DATE, back_date DATE, status TEXT, request_date DATE)''')
    c.execute("""CREATE TABLE IF NOT EXISTS exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            s_name TEXT, f_name TEXT, para_no INTEGER, start_date TEXT, end_date TEXT,
            q1 INTEGER, q2 INTEGER, q3 INTEGER, q4 INTEGER, q5 INTEGER,
            total INTEGER, grade TEXT, status TEXT)""")
    conn.commit()

    # کالمز کا اضافہ (نئے فیچرز کے لیے)
    cols = [
        ("students", "phone", "TEXT"), ("students", "address", "TEXT"), ("students", "id_card", "TEXT"), 
        ("students", "photo", "TEXT"), ("teachers", "phone", "TEXT"), ("teachers", "address", "TEXT"), 
        ("teachers", "id_card", "TEXT"), ("teachers", "photo", "TEXT"), 
        ("leave_requests", "l_type", "TEXT"), ("leave_requests", "days", "INTEGER"), 
        ("leave_requests", "notification_seen", "INTEGER DEFAULT 0"),
        # --- حاضری کو پکڑنے کے لیے نئے کالمز ---
        ("t_attendance", "manual_date", "DATE"), ("t_attendance", "manual_time", "TEXT"),
        ("t_attendance", "system_timestamp", "TEXT"), ("t_attendance", "is_late", "INTEGER DEFAULT 0")
    ]
    for t, col, typ in cols:
        try: c.execute(f"ALTER TABLE {t} ADD COLUMN {col} {typ}")
        except: pass

    c.execute("INSERT OR IGNORE INTO teachers (name, password) VALUES (?,?)", ("admin", "jamia123"))
    conn.commit()

init_db()

@st.cache_data
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8-sig')

# --- امتحانی رپورٹ کا فنکشن ---
def render_exam_report():
    st.subheader("🎓 امتحانی تعلیمی نظام")
    u_type = st.session_state.user_type

    if u_type == "teacher":
        st.info("📢 **استاد پینل:** یہاں سے آپ طالب علم کا نام امتحان کے لیے بھیج سکتے ہیں۔")
        students = c.execute("SELECT name, father_name FROM students WHERE teacher_name=?", (st.session_state.username,)).fetchall()
        
        if not students:
            st.warning("آپ کی کلاس میں کوئی طالب علم رجسٹرڈ نہیں ہے۔")
        else:
            with st.form("exam_request_form"):
                s_list = [f"{s[0]} ولد {s[1]}" for s in students]
                sel_student = st.selectbox("طالب علم منتخب کریں", s_list)
                para_to_test = st.number_input("پارہ نمبر جس کا امتحان لینا ہے", 1, 30)
                s_date = st.date_input("آغازِ امتحان (تاریخِ درخواست)", get_pkt_time().date())
                
                if st.form_submit_button("امتحان کے لیے نامزد کریں 🚀"):
                    s_name, f_name = sel_student.split(" ولد ")
                    exists = c.execute("SELECT 1 FROM exams WHERE s_name=? AND f_name=? AND para_no=? AND status='پینڈنگ'", (s_name, f_name, para_to_test)).fetchone()
                    
                    if exists:
                        st.error("🛑 اس طالب علم کی اس پارے کے لیے درخواست پہلے سے موجود ہے۔")
                    else:
                        c.execute("INSERT INTO exams (s_name, f_name, para_no, start_date, status) VALUES (?,?,?,?,?)",
                                  (s_name, f_name, para_to_test, str(s_date), "پینڈنگ"))
                        conn.commit()
                        st.success(f"✅ {s_name} (پارہ {para_to_test}) کی درخواست بھیج دی گئی ہے۔")

    elif u_type == "admin":
        tab1, tab2 = st.tabs(["📥 پینڈنگ امتحانات", "📜 مکمل شدہ ریکارڈ"])
        with tab1:
            pending = c.execute("SELECT id, s_name, f_name, para_no, start_date FROM exams WHERE status='پینڈنگ'").fetchall()
            if not pending: st.info("کوئی طالب علم امتحان کے لیے نامزد نہیں ہے۔")
            else:
                for eid, sn, fn, pn, sd in pending:
                    with st.expander(f"📝 {sn} ولد {fn} (پارہ {pn}) - تاریخ: {sd}"):
                        q_cols = st.columns(5)
                        q1 = q_cols[0].number_input("س 1", 0, 20, key=f"q1_{eid}")
                        q2 = q_cols[1].number_input("س 2", 0, 20, key=f"q2_{eid}")
                        q3 = q_cols[2].number_input("س 3", 0, 20, key=f"q3_{eid}")
                        q4 = q_cols[3].number_input("س 4", 0, 20, key=f"q4_{eid}")
                        q5 = q_cols[4].number_input("س 5", 0, 20, key=f"q5_{eid}")
                        total = q1 + q2 + q3 + q4 + q5
                        
                        if total >= 90: g, s_msg = "ممتاز", "کامیاب"
                        elif total >= 80: g, s_msg = "جید جداً", "کامیاب"
                        elif total >= 70: g, s_msg = "جید", "کامیاب"
                        elif total >= 60: g, s_msg = "مقبول", "کامیاب"
                        else: g, s_msg = "دوبارہ کوشش کریں", "ناکام"
                        
                        st.markdown(f"**کل نمبر:** `{total}` | **گریڈ:** `{g}` | **کیفیت:** `{s_msg}`")
                        if st.button("امتحان کلیئر کریں ✅", key=f"save_{eid}"):
                            e_date = str(get_pkt_time().date())
                            c.execute("""UPDATE exams SET q1=?, q2=?, q3=?, q4=?, q5=?, total=?, grade=?, status=?, end_date=? WHERE id=?""", (q1, q2, q3, q4, q5, total, g, s_msg, e_date, eid))
                            conn.commit()
                            st.rerun()

        with tab2:
            history_df = pd.read_sql_query("""SELECT s_name as نام, f_name as ولدیت, para_no as پارہ, start_date as آغاز, end_date as اختتام, total as نمبر, grade as درجہ, status as کیفیت FROM exams WHERE status != 'پینڈنگ' ORDER BY id DESC""", conn)
            if not history_df.empty:
                st.dataframe(history_df, use_container_width=True, hide_index=True)
            else: st.info("ابھی تک کوئی امتحان مکمل نہیں ہوا۔")

# ================= 2. اسٹائلنگ اور دائیں سے بائیں (RTL) =================
st.set_page_config(page_title="جامعہ ملیہ اسلامیہ پورٹل", layout="wide")
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu:wght@400;700&display=swap');
    
    /* پورے پیج پر نستعلیق اور RTL */
    body, p, h1, h2, h3, h4, h5, h6, div, span, label, td, th {
        font-family: 'Noto Nastaliq Urdu', 'Jameel Noori Nastaleeq', serif !important;
        direction: rtl;
        text-align: right;
    }
    
    .stButton>button {background: #1e5631; color: white; border-radius: 8px; font-weight: bold; width: 100%; border: none; padding: 10px;}
    .stButton>button:hover {background: #143e22;}
    .main-header {text-align: center; color: #1e5631; background-color: #f1f8e9; padding: 20px; border-radius: 10px; margin-bottom: 20px; border-bottom: 4px solid #1e5631;}
    
    /* تاریخ کو نمایاں کرنے کے لیے */
    .date-divider {
        background-color: #2e7d32; color: white; text-align: center; padding: 10px; 
        font-size: 20px; border-radius: 8px; margin-top: 30px; margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

surahs_urdu = ["الفاتحة", "البقرة", "آل عمران", "النساء", "المائدة", "الأنعام", "الأعراف", "الأنفال", "التوبة", "يونس", "هود", "يوسف", "الرعد", "إبراهيم", "الحجر", "النحل", "الإسراء", "الكهف", "مريم", "طه", "الأنبياء", "الحج", "المؤمنون", "النور", "الفرقان", "الشعراء", "النمل", "القصص", "العنكبوت", "الروم", "لقمان", "السجدة", "الأحزاب", "سبأ", "فاطر", "يس", "الصافات", "ص", "الزمر", "غافر", "فصلت", "الشورى", "الزخرف", "الدخان", "الجاثية", "الأحقاف", "محمد", "الفتح", "الحجرات", "ق", "الذاريات", "الطور", "النجم", "القمر", "الرحمن", "الواقعة", "الحديد", "المجادلة", "الحشر", "الممتحنة", "الصف", "الجمعة", "المنافقون", "التغابن", "الطلاق", "التحریم", "الملک", "القلم", "الحاقة", "المعارج", "نوح", "الجن", "المزمل", "المدثر", "القیامة", "الإنسان", "المرسلات", "النبأ", "النازعات", "عبس", "التکویر", "الإنفطار", "المطففین", "الإنشقاق", "البروج", "الطارق", "الأعلى", "الغاشیة", "الفجر", "البلد", "الشمس", "اللیل", "الضحى", "الشرح", "التین", "العلق", "القدر", "البینة", "الزلزلة", "العادیات", "القارعة", "التکاثر", "العصر", "الهمزة", "الفیل", "قریش", "الماعون", "الکوثر", "الکافرون", "النصر", "المسد", "الإخلاص", "الفلق", "الناس"]
paras = [f"پارہ {i}" for i in range(1, 31)]

# --- مرکزی ہیڈر ---
st.markdown("<div class='main-header'><h1>🕌 جامعہ ملیہ اسلامیہ</h1><p>اسمارٹ تعلیمی و انتظامی پورٹل</p></div>", unsafe_allow_html=True)

if "logged_in" not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.subheader("🔐 لاگ ان پینل")
        u = st.text_input("صارف کا نام")
        p = st.text_input("پاسورڈ", type="password")
        if st.button("داخل ہوں"):
            res = c.execute("SELECT * FROM teachers WHERE name=? AND password=?", (u, p)).fetchone()
            if res:
                st.session_state.logged_in, st.session_state.username = True, u
                st.session_state.user_type = "admin" if u == "admin" else "teacher"
                st.rerun()
            else: st.error("❌ غلط معلومات، براہ کرم دوبارہ کوشش کریں۔")
else:
    if st.session_state.user_type == "admin":
        menu = ["📊 یومیہ تعلیمی رپورٹ", "🎓 امتحانی تعلیمی رپورٹ", "📜 ماہانہ رزلٹ کارڈ", "🕒 اساتذہ کا ریکارڈ", "🏛️ مہتمم پینل (رخصت)", "⚙️ انتظامی کنٹرول"]
    else:
        menu = ["📝 تعلیمی اندراج", "🎓 امتحانی تعلیمی رپورٹ", "📩 درخواستِ رخصت", "🕒 میری حاضری"]
        
    m = st.sidebar.radio("📌 مینو منتخب کریں", menu)

    # ================= ADMIN SECTION =================
    if m == "📊 یومیہ تعلیمی رپورٹ":
        st.markdown("<h2 style='text-align: center; color: #1e5631;'>📊 ماسٹر تعلیمی رپورٹ و تجزیہ</h2>", unsafe_allow_html=True)

        with st.sidebar:
            st.header("🔍 فلٹرز")
            d1 = st.date_input("آغاز", date.today().replace(day=1))
            d2 = st.date_input("اختتام", get_pkt_time().date())
            t_list = ["تمام"] + [t[0] for t in c.execute("SELECT DISTINCT t_name FROM hifz_records").fetchall()]
            sel_t = st.selectbox("استاد/کلاس", t_list)
            s_list = ["تمام"] + [s[0] for s in c.execute("SELECT DISTINCT s_name FROM hifz_records").fetchall()]
            sel_s = st.selectbox("طالب علم", s_list)

        query = "SELECT r_date, s_name, f_name, t_name, attendance, surah, sq_m, m_m, principal_note FROM hifz_records WHERE r_date BETWEEN ? AND ? ORDER BY r_date DESC"
        params = [d1, d2]
        if sel_t != "تمام": query += " AND t_name = ?"; params.append(sel_t)
        if sel_s != "تمام": query += " AND s_name = ?"; params.append(sel_s)
        
        df = pd.read_sql_query(query, conn, params=params)

        if df.empty:
            st.warning("منتخب کردہ فلٹرز کے مطابق کوئی ریکارڈ نہیں ملا۔")
        else:
            # --- نیا فیچر: ہر روز کا ریکارڈ الگ الگ تاریخ کے ساتھ ---
            grouped = df.groupby('r_date')
            for date_val, group_df in grouped:
                st.markdown(f"<div class='date-divider'>📅 تاریخ: {date_val}</div>", unsafe_allow_html=True)
                # ڈیٹا فریم کو ڈسپلے کریں بغیر index کے
                st.dataframe(group_df.drop(columns=['r_date']), use_container_width=True, hide_index=True)

            st.divider()
            st.subheader("🛠️ ڈیٹا کنٹرول (تبدیلی اور حذف)")
            edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, hide_index=True)

    elif m == "📜 ماہانہ رزلٹ کارڈ":
        st.header("📜 ماہانہ رزلٹ کارڈ")
        s_list = [s[0] for s in c.execute("SELECT DISTINCT name FROM students").fetchall()]
        if s_list:
            sc, d1c, d2c = st.columns([2,1,1])
            sel_s = sc.selectbox("طالب علم", s_list)
            date1, date2 = d1c.date_input("آغاز", date.today().replace(day=1)), d2c.date_input("اختتام", get_pkt_time().date())
            res_df = pd.read_sql_query(f"SELECT r_date as تاریخ, surah as سورت, sq_m as سبقی_غلطی, m_m as منزل_غلطی, principal_note as رائے FROM hifz_records WHERE s_name='{sel_s}' AND r_date BETWEEN '{date1}' AND '{date2}'", conn)

            if not res_df.empty:
                st.line_chart(res_df.set_index('تاریخ')[['سبقی_غلطی', 'منزل_غلطی']])
                avg_err = res_df['سبقی_غلطی'].mean() + res_df['منزل_غلطی'].mean()
                if avg_err <= 0.8: g, col = "🌟 ممتاز", "green"
                elif avg_err <= 2.5: g, col = "✅ جید جدا", "blue"
                elif avg_err <= 5.0: g, col = "🟡 جید", "orange"
                elif avg_err <= 10.0: g, col = "🟠 مقبول", "darkorange"
                else: g, col = "❌ راسب", "red"
                
                st.markdown(f"<div style='background:{col}; padding:20px; border-radius:10px; text-align:center; color:white;'><h2>درجہ: {g}</h2><p>اوسط غلطی: {avg_err:.2f}</p></div>", unsafe_allow_html=True)
            else: st.warning("اس طالب علم کا ریکارڈ نہیں ملا۔")

    elif m == "🏛️ مہتمم پینل (رخصت)":
        st.header("🏛️ مہتمم پینل (رخصت کی منظوری)")
        pending = c.execute("SELECT id, t_name, l_type, reason, start_date, days FROM leave_requests WHERE status LIKE '%پینڈنگ%'").fetchall()
        if not pending: st.info("کوئی نئی درخواست نہیں ہے۔")
        else:
            for l_id, t_n, l_t, reas, s_d, dys in pending:
                with st.expander(f"📌 استاد: {t_n} | دن: {dys} | نوعیت: {l_t}"):
                    st.write(f"**وجہ:** {reas}")
                    c_a, c_r = st.columns(2)
                    if c_a.button("✅ منظور", key=f"app_{l_id}"):
                        c.execute("UPDATE leave_requests SET status='منظور شدہ ✅', notification_seen=0 WHERE id=?", (l_id,))
                        conn.commit(); st.rerun()
                    if c_r.button("❌ مسترد", key=f"rej_{l_id}"):
                        c.execute("UPDATE leave_requests SET status='مسترد شدہ ❌', notification_seen=0 WHERE id=?", (l_id,))
                        conn.commit(); st.rerun()

    elif m == "⚙️ انتظامی کنٹرول":
        st.header("⚙️ رجسٹریشن اور انتظامی کنٹرول")
        t1, t2, t3 = st.tabs(["👨‍🏫 اساتذہ مینجمنٹ", "👨‍🎓 طلباء مینجمنٹ", "🔐 اساتذہ کے پاسورڈز بدلیں"])
        with t1:
            with st.form("t_reg_form"):
                tn = st.text_input("استاد کا نام")
                tp = st.text_input("پاسورڈ")
                if st.form_submit_button("رجسٹر کریں"):
                    if tn and tp:
                        try:
                            c.execute("INSERT INTO teachers (name, password) VALUES (?,?)", (tn, tp))
                            conn.commit(); st.success("کامیاب!")
                        except sqlite3.IntegrityError: st.error("نام پہلے سے موجود ہے!")
        with t2:
            with st.form("s_reg_form"):
                sn, sf = st.columns(2)
                s_name = sn.text_input("طالب علم نام")
                s_father = sf.text_input("ولدیت")
                t_list = [t[0] for t in c.execute("SELECT name FROM teachers WHERE name!='admin'").fetchall()]
                if t_list:
                    s_teacher = st.selectbox("استاد", t_list)
                    if st.form_submit_button("داخل کریں"):
                        if s_name and s_father:
                            c.execute("INSERT INTO students (name, father_name, teacher_name) VALUES (?,?,?)", (s_name, s_father, s_teacher))
                            conn.commit(); st.success("داخلہ کامیاب!")
        
        # --- نیا فیچر: اساتذہ کے نام اور پاسورڈ میں ترمیم ---
        with t3:
            st.subheader("اساتذہ کا ڈیٹا ایڈٹ کریں")
            tech_df = pd.read_sql_query("SELECT id, name, password FROM teachers WHERE name != 'admin'", conn)
            edited_tech = st.data_editor(tech_df, hide_index=True, use_container_width=True)
            if st.button("پاسورڈ اور نام محفوظ کریں"):
                for index, row in edited_tech.iterrows():
                    c.execute("UPDATE teachers SET name=?, password=? WHERE id=?", (row['name'], row['password'], row['id']))
                conn.commit()
                st.success("تبدیلیاں محفوظ ہو گئیں۔")

    # ================= نیا ایڈمن فیچر: حاضری کا تفصیلی چیک =================
    elif m == "🕒 اساتذہ کا ریکارڈ":
        st.header("🕒 اساتذہ کی حاضری اور تجزیہ")
        
        att_df = pd.read_sql_query("""
            SELECT id, t_name as 'استاد', manual_date as 'درج کردہ تاریخ', manual_time as 'درج کردہ وقت', 
            system_timestamp as 'اصل بٹن دبانے کا وقت' 
            FROM t_attendance ORDER BY id DESC
        """, conn)

        if not att_df.empty:
            # گراف اور ٹوٹل
            total_att = len(att_df)
            st.metric("کل حاضری کا ریکارڈ", total_att)
            
            # ایڈیٹ ایبل ٹیبل (ایڈمن ترمیم یا ڈیلیٹ کر سکے گا)
            st.markdown("### مکمل ریکارڈ (تبدیلی کی سہولت کے ساتھ)")
            edited_att = st.data_editor(att_df, num_rows="dynamic", use_container_width=True, hide_index=True)
            if st.button("حاضری کی تبدیلیاں محفوظ کریں"):
                c.execute("DELETE FROM t_attendance")
                # دوبارہ انسرٹ کریں
                for _, row in edited_att.iterrows():
                    c.execute("INSERT INTO t_attendance (id, t_name, manual_date, manual_time, system_timestamp) VALUES (?,?,?,?,?)",
                              (row['id'], row['استاد'], row['درج کردہ تاریخ'], row['درج کردہ وقت'], row['اصل بٹن دبانے کا وقت']))
                conn.commit()
                st.success("اپ ڈیٹ ہو گیا!")
        else:
            st.info("کوئی حاضری موجود نہیں ہے۔")

    # ================= TEACHER SECTION =================
    elif m == "📝 تعلیمی اندراج":
        st.header("🚀 اسمارٹ تعلیمی ڈیش بورڈ")
        sel_date = st.date_input("تاریخ منتخب کریں", get_pkt_time().date())
        
        students = c.execute("SELECT name, father_name FROM students WHERE teacher_name=?", (st.session_state.username,)).fetchall()

        if not students:
            st.info("آپ کی کلاس میں کوئی طالب علم رجسٹرڈ نہیں ہے۔")
        else:
            for s, f in students:
                with st.expander(f"👤 {s} ولد {f}"):
                    att = st.radio(f"حاضری {s}", ["حاضر", "غیر حاضر (ناغہ)", "رخصت"], key=f"att_{s}", horizontal=True)
                    
                    if att == "حاضر":
                        # نیا سبق
                        st.subheader("📖 نیا سبق")
                        s_nagha = st.checkbox("سبق کا ناغہ", key=f"sn_nagha_{s}")
                        if not s_nagha:
                            col_s1, col_s2, col_s3 = st.columns([2, 1, 1])
                            surah_sel = col_s1.selectbox("سورت", surahs_urdu, key=f"surah_{s}")
                            a_from = col_s2.text_input("آیت (سے)", key=f"af_{s}")
                            a_to = col_s3.text_input("آیت (تک)", key=f"at_{s}")
                            sabq_final = f"{surah_sel}: {a_from}-{a_to}"
                        else: sabq_final = "ناغہ"

                        # سبقی
                        st.subheader("🔄 سبقی")
                        sq_total_nagha = st.checkbox("سبقی کا مکمل ناغہ", key=f"sq_tn_{s}")
                        sq_list, f_sq_m, f_sq_a = [], 0, 0
                        if not sq_total_nagha:
                            if f"sq_count_{s}" not in st.session_state: st.session_state[f"sq_count_{s}"] = 1
                            for i in range(st.session_state[f"sq_count_{s}"]):
                                c1, c2, c3, c4, c5 = st.columns([2, 2, 1, 1, 1])
                                p = c1.selectbox(f"پارہ {i+1}", paras, key=f"sqp_{s}_{i}")
                                v = c2.selectbox(f"مقدار {i+1}", ["مکمل", "آدھا", "پون", "پاؤ"], key=f"sqv_{s}_{i}")
                                a = c3.number_input(f"اٹکن {i+1}", 0, key=f"sqa_{s}_{i}")
                                e = c4.number_input(f"غلطی {i+1}", 0, key=f"sqe_{s}_{i}")
                                ind_n = c5.checkbox("ناغہ", key=f"sq_n_{s}_{i}")
                                if ind_n: sq_list.append(f"{p}:ناغہ")
                                else: sq_list.append(f"{p}:{v}(غ:{e},ا:{a})"); f_sq_m += e; f_sq_a += a
                            if st.button(f"➕ مزید سبقی {s}", key=f"btn_sq_{s}"): st.session_state[f"sq_count_{s}"] += 1; st.rerun()
                        else: sq_list = ["ناغہ"]

                        # منزل
                        st.subheader("🏠 منزل")
                        m_total_nagha = st.checkbox("منزل کا مکمل ناغہ", key=f"m_tn_{s}")
                        m_list, f_m_m, f_m_a = [], 0, 0
                        if not m_total_nagha:
                            if f"m_count_{s}" not in st.session_state: st.session_state[f"m_count_{s}"] = 1
                            for j in range(st.session_state[f"m_count_{s}"]):
                                mc1, mc2, mc3, mc4, mc5 = st.columns([2, 2, 1, 1, 1])
                                mp = mc1.selectbox(f"پارہ {j+1}", paras, key=f"mp_{s}_{j}")
                                mv = mc2.selectbox(f"مقدار {j+1}", ["مکمل", "آدھا", "پون", "پاؤ"], key=f"mv_{s}_{j}")
                                ma = mc3.number_input(f"اٹکن {j+1}", 0, key=f"ma_{s}_{j}")
                                me = mc4.number_input(f"غلطی {j+1}", 0, key=f"me_{s}_{j}")
                                m_ind_n = mc5.checkbox("ناغہ", key=f"m_n_{s}_{j}")
                                if m_ind_n: m_list.append(f"{mp}:ناغہ")
                                else: m_list.append(f"{mp}:{mv}(غ:{me},ا:{ma})"); f_m_m += me; f_m_a += ma
                            if st.button(f"➕ مزید منزل {s}", key=f"btn_m_{s}"): st.session_state[f"m_count_{s}"] += 1; st.rerun()
                        else: m_list = ["ناغہ"]

                        # --- ڈیٹا محفوظ کرنا اور ڈبل انٹری روکنا ---
                        if st.button(f"محفوظ کریں: {s}", key=f"save_{s}"):
                            check = c.execute("SELECT 1 FROM hifz_records WHERE r_date = ? AND s_name = ? AND f_name = ?", (sel_date, s, f)).fetchone()
                            if check:
                                st.error(f"🛑 اس تاریخ کا ریکارڈ پہلے سے موجود ہے!")
                            else:
                                c.execute("""INSERT INTO hifz_records 
                                          (r_date, s_name, f_name, t_name, surah, sq_p, sq_a, sq_m, m_p, m_a, m_m, attendance) 
                                          VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", 
                                          (sel_date, s, f, st.session_state.username, sabq_final, 
                                           " | ".join(sq_list), f_sq_a, f_sq_m, " | ".join(m_list), f_m_a, f_m_m, att))
                                conn.commit()
                                st.success(f"✅ {s} کا ریکارڈ محفوظ ہو گیا۔")

                    else:
                        if st.button(f"حاضری لگائیں: {s}", key=f"save_absent_{s}"):
                            check = c.execute("SELECT 1 FROM hifz_records WHERE r_date = ? AND s_name = ? AND f_name = ?", (sel_date, s, f)).fetchone()
                            if check:
                                st.error(f"🛑 اس تاریخ کا ریکارڈ پہلے سے موجود ہے!")
                            else:
                                c.execute("""INSERT INTO hifz_records (r_date, s_name, f_name, t_name, attendance, surah, sq_p, m_p) 
                                          VALUES (?,?,?,?,?,?,?,?)""", (sel_date, s, f, st.session_state.username, att, "ناغہ", "ناغہ", "ناغہ"))
                                conn.commit()
                                st.success(f"✅ {s} کی حاضری ({att}) لگ گئی ہے۔")

    elif m == "📩 درخواستِ رخصت":
        st.header("📩 اسمارٹ رخصت و نوٹیفیکیشن")
        tab_apply, tab_status = st.tabs(["✍️ نئی درخواست", "📜 میری رخصتوں کی تاریخ"])
        with tab_apply:
            with st.form("teacher_leave_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                l_type = col1.selectbox("رخصت کی نوعیت", ["ضروری کام", "بیماری", "ہنگامی رخصت", "دیگر"])
                s_date = col1.date_input("تاریخ آغاز", get_pkt_time().date())
                days = col2.number_input("کتنے دن؟", 1, 15)
                e_date = s_date + timedelta(days=days-1)
                col2.write(f"واپسی کی تاریخ: **{e_date}**")
                reason = st.text_area("تفصیلی وجہ درج کریں")
                if st.form_submit_button("درخواست ارسال کریں 🚀"):
                    if reason:
                        c.execute("""INSERT INTO leave_requests (t_name, l_type, start_date, days, reason, status, notification_seen) 
                                  VALUES (?,?,?,?,?,?,?)""", (st.session_state.username, l_type, s_date, days, reason, "پینڈنگ (زیرِ غور)", 0))
                        conn.commit(); st.info("✅ درخواست مہتمم کو بھیج دی گئی ہے۔")
                    else: st.warning("براہ کرم وجہ ضرور لکھیں۔")
        with tab_status:
            my_leaves = pd.read_sql_query(f"SELECT start_date as تاریخ, l_type as نوعیت, days as دن, status as حالت FROM leave_requests WHERE t_name='{st.session_state.username}' ORDER BY start_date DESC", conn)
            if not my_leaves.empty: st.dataframe(my_leaves, use_container_width=True, hide_index=True)
            else: st.info("کوئی ریکارڈ نہیں ملا۔")

    # ================= نیا فیچر: استاد کی ایڈوانسڈ حاضری =================
    elif m == "🕒 میری حاضری":
        st.header("🕒 اساتذہ کی حاضری")
        st.info("اپنی آمد کا وقت اور تاریخ منتخب کریں، سسٹم آپ کی انٹری کا اصل وقت بھی خفیہ طور پر محفوظ کرے گا۔")
        
        with st.form("teacher_att_form"):
            col_d, col_t = st.columns(2)
            m_date = col_d.date_input("حاضری کی تاریخ", get_pkt_time().date())
            
            # ڈیفالٹ وقت میں سے سیکنڈز ہٹانے کے لیے
            curr_time = get_pkt_time().time()
            m_time = col_t.time_input("آمد کا وقت", curr_time)
            
            if st.form_submit_button("✅ حاضری درج کریں"):
                sys_time_str = get_pkt_time().strftime("%Y-%m-%d %I:%M %p")
                man_time_str = m_time.strftime("%I:%M %p")
                
                # ڈبل انٹری چیک
                exists = c.execute("SELECT 1 FROM t_attendance WHERE t_name=? AND manual_date=?", (st.session_state.username, m_date)).fetchone()
                
                if exists:
                    st.error("🛑 آپ کی اس دن کی حاضری پہلے ہی لگ چکی ہے!")
                else:
                    c.execute("""INSERT INTO t_attendance (t_name, manual_date, manual_time, system_timestamp) 
                                 VALUES (?,?,?,?)""", (st.session_state.username, m_date, man_time_str, sys_time_str))
                    conn.commit()
                    st.success(f"حاضری کامیابی سے درج ہو گئی! (درج وقت: {man_time_str})")

    elif m == "🎓 امتحانی تعلیمی رپورٹ":
        render_exam_report()

    # ================= LOGOUT =================
    st.sidebar.divider()
    if st.sidebar.button("🚪 لاگ آؤٹ کریں"):
        st.session_state.logged_in = False
        st.rerun()
