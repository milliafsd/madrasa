import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import sqlite3
import base64

# --- 1. ڈیٹا بیس سیٹ اپ ---
DB_NAME = 'jamia_millia_v1.db'
conn = sqlite3.connect(DB_NAME, check_same_thread=False)
c = conn.cursor()

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

    # کالمز کا اضافہ (نئے فیچرز کے لیے)
    cols = [("students", "phone", "TEXT"), ("students", "address", "TEXT"), ("students", "id_card", "TEXT"), 
            ("students", "photo", "TEXT"), ("teachers", "phone", "TEXT"), ("teachers", "address", "TEXT"), 
            ("teachers", "id_card", "TEXT"), ("teachers", "photo", "TEXT"), 
            ("leave_requests", "l_type", "TEXT"), ("leave_requests", "days", "INTEGER"), 
            ("leave_requests", "notification_seen", "INTEGER DEFAULT 0")]
    for t, col, typ in cols:
        try: c.execute(f"ALTER TABLE {t} ADD COLUMN {col} {typ}")
        except: pass

    c.execute("INSERT OR IGNORE INTO teachers (name, password) VALUES (?,?)", ("admin", "jamia123"))
    conn.commit()

init_db()

def get_base64(file):
    if file: return base64.b64encode(file.read()).decode()
    return None

# ڈیٹا ڈاؤن لوڈ کرنے کے لیے فنکشن (اردو ایکسل سپورٹ)
@st.cache_data
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8-sig')

# --- 2. اسٹائلنگ ---
st.set_page_config(page_title="جامعہ ملیہ اسلامیہ پورٹل", layout="wide")
st.markdown("""
<style>
    body {direction: rtl; text-align: right;}
    .stButton>button {background: #1e5631; color: white; border-radius: 8px; font-weight: bold; width: 100%; border: none; padding: 10px;}
    .stButton>button:hover {background: #143e22;}
    .main-header {text-align: center; color: #1e5631; background-color: #f1f8e9; padding: 20px; border-radius: 10px; margin-bottom: 20px; border-bottom: 4px solid #1e5631;}
</style>
""", unsafe_allow_html=True)

surahs_urdu = ["الفاتحة", "البقرة", "آل عمران", "النساء", "المائدة", "الأنعام", "الأعراف", "الأنفال", "التوبة", "يونس", "هود", "يوسف", "الرعد", "إبراهيم", "الحجر", "النحل", "الإسراء", "الكهف", "مريم", "طه", "الأنبياء", "الحج", "المؤمنون", "النور", "الفرقان", "الشعراء", "النمل", "القصص", "العنكبوت", "الروم", "لقمان", "السجدة", "الأحزاب", "سبأ", "فاطر", "يس", "الصافات", "ص", "الزمر", "غافر", "فصلت", "الشورى", "الزخرف", "الدخان", "الجاثية", "الأحقاف", "محمد", "الفتح", "الحجرات", "ق", "الذاريات", "الطور", "النجم", "القمر", "الرحمن", "الواقعة", "الحديد", "المجادلة", "الحشر", "الممتحنة", "الصف", "الجمعة", "المنافقون", "التغابن", "الطلاق", "التحریم", "الملک", "القلم", "الحاقة", "المعارج", "نوح", "الجن", "المزمل", "المدثر", "القیامة", "الإنسان", "المرسلات", "النبأ", "النازعات", "عبس", "التکویر", "الإنفطار", "المطففین", "الإنشقاق", "البروج", "الطارق", "الأعلى", "الغاشیة", "الفجر", "البلد", "الشمس", "اللیل", "الضحى", "الشرح", "التین", "العلق", "القدر", "البینة", "الزلزلة", "العادیات", "القارعة", "التکاثر", "العصر", "الهمزة", "الفیل", "قریش", "الماعون", "الکوثر", "الکافرون", "النصر", "المسد", "الإخلاص", "الفلق", "الناس"]
paras = [f"پارہ {i}" for i in range(1, 31)]

if 'logged_in' not in st.session_state: st.session_state.logged_in = False

# --- مرکزی ہیڈر ---
st.markdown("<div class='main-header'><h1>🕌 جامعہ ملیہ اسلامیہ</h1><p>اسمارٹ تعلیمی و انتظامی پورٹل</p></div>", unsafe_allow_html=True)

if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.subheader("🔐 لاگ ان پینل")
        u = st.text_input("صارف کا نام (Username)")
        p = st.text_input("پاسورڈ (Password)", type="password")
        if st.button("داخل ہوں"):
            res = c.execute("SELECT * FROM teachers WHERE name=? AND password=?", (u, p)).fetchone()
            if res:
                st.session_state.logged_in, st.session_state.username = True, u
                st.session_state.user_type = "admin" if u == "admin" else "teacher"
                st.rerun()
            else: st.error("❌ غلط معلومات، براہ کرم دوبارہ کوشش کریں۔")
else:
    # مینو کی ترتیب
    if st.session_state.user_type == "admin":
        menu = ["📊 یومیہ تعلیمی رپورٹ", "📜 ماہانہ رزلٹ کارڈ", "🕒 اساتذہ کا ریکارڈ", "🏛️ مہتمم پینل (رخصت)", "⚙️ انتظامی کنٹرول"]
    else:
        menu = ["📝 تعلیمی اندراج", "📩 درخواستِ رخصت", "🕒 میری حاضری"]
        
    m = st.sidebar.radio("📌 مینو منتخب کریں", menu)

    # ================= ADMIN SECTION =================
    if m == "📊 یومیہ تعلیمی رپورٹ":
        st.header("📊 یومیہ تعلیمی رپورٹ")
        c1, c2, c3 = st.columns([2, 1, 1])
        s_type = c1.radio("رپورٹ کی قسم:", ["کلاس وائز (استاد)", "طالب علم وائز"], horizontal=True)
        d1, d2 = c2.date_input("کب سے", date.today()), c3.date_input("کب تک", date.today())

        target_list = [t[0] for t in c.execute(f"SELECT {'name' if s_type=='کلاس وائز (استاد)' else 'DISTINCT s_name'} FROM {'teachers' if s_type=='کلاس وائز (استاد)' else 'hifz_records'}").fetchall()]
        if target_list:
            target = st.selectbox("منتخب کریں:", target_list)
            query = f"SELECT id, r_date, s_name, f_name, surah, sq_m, m_m, principal_note FROM hifz_records WHERE {'t_name' if s_type=='کلاس وائز (استاد)' else 's_name'}='{target}' AND r_date BETWEEN '{d1}' AND '{d2}' ORDER BY r_date DESC"

            df = pd.read_sql_query(query, conn)
            if not df.empty:
                df.columns = ['آئی ڈی', 'تاریخ', 'نام طالب علم', 'ولدیت', 'سبق/سورت', 'سبقی غلطی', 'منزل غلطی', 'مہتمم کی رائے']
                
                # ڈاؤن لوڈ بٹن
                csv = convert_df_to_csv(df)
                st.download_button(label="📥 رپورٹ ایکسل (CSV) میں ڈاؤن لوڈ کریں", data=csv, file_name=f"Daily_Report_{target}.csv", mime='text/csv')
                
                edited = st.data_editor(df, hide_index=True, use_container_width=True)
                if st.button("💾 تبدیلیاں محفوظ کریں"):
                    for _, r in edited.iterrows():
                        c.execute("UPDATE hifz_records SET surah=?, sq_m=?, m_m=?, principal_note=? WHERE id=?", (r['سبق/سورت'], r['سبقی غلطی'], r['منزل غلطی'], r['مہتمم کی رائے'], r['آئی ڈی']))
                    conn.commit(); st.success("تبدیلیاں کامیابی سے محفوظ ہو گئیں!"); st.rerun()
            else: st.warning("اس تاریخ کا کوئی ریکارڈ نہیں ملا۔")
        else: st.info("ڈیٹا دستیاب نہیں ہے۔")

    elif m == "📜 ماہانہ رزلٹ کارڈ":
        st.header("📜 ماہانہ رزلٹ کارڈ")
        s_list = [s[0] for s in c.execute("SELECT DISTINCT name FROM students").fetchall()]
        if s_list:
            sc, d1c, d2c = st.columns([2,1,1])
            sel_s = sc.selectbox("طالب علم", s_list)
            date1, date2 = d1c.date_input("آغاز", date.today().replace(day=1)), d2c.date_input("اختتام", date.today())
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
                
                csv = convert_df_to_csv(res_df)
                st.download_button(label="📥 طالب علم کا رزلٹ کارڈ ڈاؤن لوڈ کریں", data=csv, file_name=f"Result_Card_{sel_s}.csv", mime='text/csv')
                
                st.dataframe(res_df, use_container_width=True, hide_index=True)
            else: st.warning("اس طالب علم کا ریکارڈ نہیں ملا۔")

    elif m == "🏛️ مہتمم پینل (رخصت)":
        st.header("🏛️ مہتمم پینل (رخصت کی منظوری)")
        pending = c.execute("SELECT id, t_name, l_type, reason, start_date, days FROM leave_requests WHERE status LIKE '%پینڈنگ%'").fetchall()
        
        if not pending: 
            st.info("اس وقت رخصت کی کوئی نئی درخواست نہیں ہے۔")
        else:
            for l_id, t_n, l_t, reas, s_d, dys in pending:
                with st.expander(f"📌 استاد: {t_n} | نوعیت: {l_t} | دن: {dys}"):
                    st.write(f"**آغاز کی تاریخ:** {s_d}")
                    st.write(f"**تفصیلی وجہ:** {reas}")
                    c_a, c_r = st.columns(2)
                    if c_a.button(f"✅ منظور کریں", key=f"app_{l_id}"):
                        c.execute("UPDATE leave_requests SET status='منظور شدہ ✅', notification_seen=0 WHERE id=?", (l_id,))
                        conn.commit(); st.success("رخصت منظور کر لی گئی"); st.rerun()
                    if c_r.button(f"❌ مسترد کریں", key=f"rej_{l_id}"):
                        c.execute("UPDATE leave_requests SET status='مسترد شدہ ❌', notification_seen=0 WHERE id=?", (l_id,))
                        conn.commit(); st.warning("رخصت مسترد کر دی گئی"); st.rerun()

    elif m == "⚙️ انتظامی کنٹرول":
        st.header("⚙️ رجسٹریشن اور انتظامی کنٹرول")
        t1, t2 = st.tabs(["👨‍🏫 اساتذہ مینجمنٹ", "👨‍🎓 طلباء مینجمنٹ"])

        with t1:
            with st.form("t_reg_form"):
                tn = st.text_input("استاد کا نام")
                tp = st.text_input("پاسورڈ")
                if st.form_submit_button("اساتذہ رجسٹر کریں"):
                    if tn and tp:
                        try:
                            c.execute("INSERT INTO teachers (name, password) VALUES (?,?)", (tn, tp))
                            conn.commit()
                            st.success("رجسٹریشن مکمل ہو گئی!")
                        except sqlite3.IntegrityError:
                            st.error("یہ نام پہلے سے موجود ہے!")
                    else: st.error("نام اور پاسورڈ لازمی ہیں")
            
            st.divider()
            try:
                t_df = pd.read_sql_query("SELECT id, name as نام, password as پاسورڈ, phone as فون FROM teachers WHERE name!='admin'", conn)
                if not t_df.empty:
                    st.subheader("موجودہ اساتذہ (تبدیلی کریں)")
                    t_edt = st.data_editor(t_df, hide_index=True, use_container_width=True)
                    if st.button("اساتذہ کا ڈیٹا اپ ڈیٹ کریں"):
                        for _, r in t_edt.iterrows():
                            c.execute("UPDATE teachers SET name=?, password=?, phone=? WHERE id=?", (r['نام'], r['پاسورڈ'], r['فون'], r['id']))
                        conn.commit(); st.success("ڈیٹا اپ ڈیٹ ہو گیا!"); st.rerun()
                else: st.info("کوئی استاد موجود نہیں")
            except Exception as e: st.error(f"ایرر: {e}")

        with t2:
            with st.form("s_reg_form"):
                sn, sf = st.columns(2)
                s_name = sn.text_input("طالب علم نام")
                s_father = sf.text_input("ولدیت")
                teachers_list = [t[0] for t in c.execute("SELECT name FROM teachers WHERE name!='admin'").fetchall()]
                if teachers_list:
                    s_teacher = st.selectbox("متعلقہ استاد منتخب کریں", teachers_list)
                    if st.form_submit_button("طالب علم داخل کریں"):
                        if s_name and s_father:
                            c.execute("INSERT INTO students (name, father_name, teacher_name) VALUES (?,?,?)", (s_name, s_father, s_teacher))
                            conn.commit(); st.success("داخلہ مکمل ہو گیا!")
                        else: st.error("تمام معلومات پُر کریں")
                else: st.warning("پہلے استاد رجسٹر کریں!")

            st.divider()
            s_df = pd.read_sql_query("SELECT id, name as نام, father_name as ولدیت, teacher_name as استاد FROM students", conn)
            if not s_df.empty:
                s_edt = st.data_editor(s_df, hide_index=True, use_container_width=True)
                if st.button("طلباء کا ڈیٹا اپ ڈیٹ کریں"):
                    for _, r in s_edt.iterrows():
                        c.execute("UPDATE students SET name=?, father_name=?, teacher_name=? WHERE id=?", (r['نام'], r['ولدیت'], r['استاد'], r['id']))
                    conn.commit(); st.success("ڈیٹا اپ ڈیٹ ہو گیا!"); st.rerun()

    elif m == "🕒 اساتذہ کا ریکارڈ":
        st.header("🕒 اساتذہ کا حاضری ریکارڈ")
        att_df = pd.read_sql_query("SELECT a_date as تاریخ, t_name as استاد, arrival as آمد, departure as رخصت FROM t_attendance ORDER BY a_date DESC", conn)
        if not att_df.empty:
            csv = convert_df_to_csv(att_df)
            st.download_button(label="📥 حاضری رپورٹ ڈاؤن لوڈ کریں", data=csv, file_name="Teachers_Attendance.csv", mime='text/csv')
            st.dataframe(att_df, use_container_width=True, hide_index=True)
        else: st.info("حاضری کا کوئی ریکارڈ موجود نہیں ہے۔")

    # ================= TEACHER SECTION =================
   # --- استاد کا مینیو: تعلیمی اندراج ---
    if m == "📝 تعلیمی اندراج":
        st.header("🚀 اسمارٹ تعلیمی ڈیش بورڈ (جامعہ ملیہ اسلامیہ)")

        tab_entry, tab_ranking = st.tabs(["📝 جدید اندراج", "🏆 ہفتہ وار ٹاپ 3"])

        with tab_entry:
            sel_date = st.date_input("تاریخ منتخب کریں", date.today())
            students = c.execute("SELECT name, father_name FROM students WHERE teacher_name=?", (st.session_state.username,)).fetchall()

            if not students:
                st.info("آپ کی کلاس میں کوئی طالب علم رجسٹرڈ نہیں ہے۔")
            else:
                for s, f in students:
                    with st.expander(f"👤 {s} ولد {f}"):
                        att = st.radio(f"حاضری {s}", ["حاضر", "غیر حاضر", "رخصت"], key=f"att_{s}", horizontal=True)
                        
                        sq_final, m_final = "", ""
                        total_sq_m, total_m_m = 0, 0
                        
                        if att == "حاضر":
                            # --- 🔄 سبقی (Sabqi) ---
                            st.subheader("🔄 سبقی")
                            nagha_sq = st.checkbox("سبقی ناغہ", key=f"nsq_{s}")
                            
                            if not nagha_sq:
                                if f"sq_count_{s}" not in st.session_state: st.session_state[f"sq_count_{s}"] = 1
                                
                                sq_data = []
                                for i in range(st.session_state[f"sq_count_{s}"]):
                                    c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
                                    p_num = c1.selectbox(f"پارہ {i+1}", paras, key=f"sqp_{s}_{i}")
                                    p_vol = c2.selectbox(f"مقدار {i+1}", ["مکمل", "آدھا (1/2)", "پون (3/4)", "پاؤ (1/4)"], key=f"sqv_{s}_{i}")
                                    p_atk = c3.number_input(f"اٹکن {i+1}", 0, key=f"sqa_{s}_{i}")
                                    p_err = c4.number_input(f"غلطی {i+1}", 0, key=f"sqe_{s}_{i}")
                                    sq_data.append(f"{p_num}:{p_vol}(غ:{p_err},ا:{p_atk})")
                                
                                if st.button(f"➕ سبقی میں مزید پارہ شامل کریں", key=f"add_sq_{s}"):
                                    st.session_state[f"sq_count_{s}"] += 1
                                    st.rerun()
                                sq_final = " | ".join(sq_data)
                                total_sq_m = sum([int(x.split('غ:')[1].split(',')[0]) for x in sq_data])
                            else:
                                sq_final = "ناغہ"
                                total_sq_m = 0

                            st.divider()

                            # --- 🏠 منزل (Manzil) ---
                            st.subheader("🏠 منزل")
                            nagha_m = st.checkbox("منزل ناغہ", key=f"nm_{s}")
                            
                            if not nagha_m:
                                if f"m_count_{s}" not in st.session_state: st.session_state[f"m_count_{s}"] = 1
                                
                                m_data = []
                                for j in range(st.session_state[f"m_count_{s}"]):
                                    mc1, mc2, mc3, mc4 = st.columns([2, 2, 1, 1])
                                    mp_num = mc1.selectbox(f"منزل پارہ {j+1}", paras, key=f"mp_{s}_{j}")
                                    mp_vol = mc2.selectbox(f"منزل مقدار {j+1}", ["مکمل", "آدھا (1/2)", "پون (3/4)", "پاؤ (1/4)"], key=f"mv_{s}_{j}")
                                    mp_atk = mc3.number_input(f"منزل اٹکن {j+1}", 0, key=f"ma_{s}_{j}")
                                    mp_err = mc4.number_input(f"منزل غلطی {j+1}", 0, key=f"me_{s}_{j}")
                                    m_data.append(f"{mp_num}:{mp_vol}(غ:{mp_err},ا:{mp_atk})")

                                if st.button(f"➕ منزل میں مزید پارہ شامل کریں", key=f"add_m_{s}"):
                                    st.session_state[f"m_count_{s}"] += 1
                                    st.rerun()
                                m_final = " | ".join(m_data)
                                total_m_m = sum([int(x.split('غ:')[1].split(',')[0]) for x in m_data])
                            else:
                                m_final = "ناغہ"
                                total_m_m = 0
                        else:
                            sq_final, m_final = att, att
                            total_sq_m, total_m_m = 0, 0

                        # --- 💾 محفوظ کرنے کا بٹن ---
                        if st.button(f"محفوظ کریں: {s}", key=f"save_{s}"):
                            try:
                                c.execute("""INSERT INTO hifz_records 
                                          (r_date, s_name, f_name, t_name, sq_p, sq_m, m_p, m_m, attendance) 
                                          VALUES (?,?,?,?,?,?,?,?,?)""", 
                                          (sel_date, s, f, st.session_state.username, sq_final, total_sq_m, m_final, total_m_m, att))
                                conn.commit()
                                st.success(f"ریکارڈ کامیابی سے محفوظ ہو گیا!")
                                # ری سیٹ
                                st.session_state[f"sq_count_{s}"] = 1
                                st.session_state[f"m_count_{s}"] = 1
                            except Exception as e:
                                st.error(f"محفوظ کرنے میں مسئلہ: {e}")

        with tab_ranking:
            st.subheader("🏆 اس ہفتے کے بہترین طلباء")
            rank_query = f"""SELECT s_name, AVG(sq_m + m_m) as avg_errors, COUNT(CASE WHEN attendance='حاضر' THEN 1 END) as presence 
                             FROM hifz_records WHERE t_name='{st.session_state.username}' AND r_date >= date('now', '-7 days') AND attendance = 'حاضر' 
                             GROUP BY s_name HAVING presence > 0 ORDER BY presence DESC, avg_errors ASC LIMIT 3"""
            ranks = c.execute(rank_query).fetchall()

            if ranks:
                cols = st.columns(3)
                medals, colors = ["🥇 ممتاز", "🥈 جید جدا", "🥉 جید"], ["#FFD700", "#C0C0C0", "#CD7F32"]
                for i, (name, avg_err, pres) in enumerate(ranks):
                    with cols[i]:
                        st.markdown(f"""
                        <div style="background:{colors[i]}33; padding:15px; border-radius:10px; text-align:center; border:2px solid {colors[i]};">
                            <h2>{medals[i]}</h2><h3>{name}</h3><p>حاضری: <b>{pres} دن</b> | اوسط غلطی: <b>{avg_err:.1f}</b></p>
                        </div>""", unsafe_allow_html=True)
            else: st.info("فی الحال ڈیٹا دستیاب نہیں ہے۔")

        with tab_analysis:
            st.subheader("📊 طلباء کی ہفتہ وار کارکردگی")
            query = f"SELECT s_name as طالب_علم, (sq_m + m_m) as غلطیاں, r_date as تاریخ FROM hifz_records WHERE t_name='{st.session_state.username}' AND r_date >= date('now', '-7 days') AND attendance='حاضر'"
            data = pd.read_sql_query(query, conn)
            if not data.empty:
                chart_df = data.pivot_table(index='تاریخ', columns='طالب_علم', values='غلطیاں', aggfunc='mean').fillna(0)
                st.line_chart(chart_df)
            else: st.info("گراف دکھانے کے لیے ڈیٹا دستیاب نہیں ہے۔")

    elif m == "📩 درخواستِ رخصت":
        st.header("📩 اسمارٹ رخصت و نوٹیفیکیشن")

        # 🔔 نوٹیفیکیشن چیک کرنا
        notifications = c.execute("""SELECT id, status, start_date FROM leave_requests 
                                     WHERE t_name=? AND status != 'پینڈنگ (زیرِ غور)' 
                                     AND notification_seen = 0""", (st.session_state.username,)).fetchall()

        for n_id, n_status, n_date in notifications:
            if "منظور" in n_status:
                st.balloons()
                st.success(f"🎊 خوشخبری! آپ کی مورخہ {n_date} کی رخصت **منظور** کر لی گئی ہے۔")
            else:
                st.error(f"⚠️ اطلاع: آپ کی مورخہ {n_date} کی رخصت کی درخواست **مسترد** کر دی گئی ہے۔")
            if st.button(f"سمجھ گیا (ہٹائیں)", key=f"n_{n_id}"):
                c.execute("UPDATE leave_requests SET notification_seen = 1 WHERE id=?", (n_id,))
                conn.commit(); st.rerun()

        st.divider()
        tab_apply, tab_status = st.tabs(["✍️ نئی درخواست", "📜 میری رخصتوں کی تاریخ"])

        with tab_apply:
            with st.form("teacher_leave_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                l_type = col1.selectbox("رخصت کی نوعیت", ["ضروری کام", "بیماری", "ہنگامی رخصت", "دیگر"])
                s_date = col1.date_input("تاریخ آغاز", date.today())
                days = col2.number_input("کتنے دن؟", 1, 15)
                e_date = s_date + timedelta(days=days-1)
                col2.write(f"واپسی کی تاریخ: **{e_date}**")

                reason = st.text_area("تفصیلی وجہ درج کریں")

                if st.form_submit_button("درخواست ارسال کریں 🚀"):
                    if reason:
                        c.execute("""INSERT INTO leave_requests (t_name, l_type, start_date, days, reason, status, notification_seen) 
                                  VALUES (?,?,?,?,?,?,?)""", 
                                  (st.session_state.username, l_type, s_date, days, reason, "پینڈنگ (زیرِ غور)", 0))
                        conn.commit(); st.info("✅ درخواست مہتمم کو بھیج دی گئی ہے۔")
                    else: st.warning("براہ کرم وجہ ضرور لکھیں۔")

        with tab_status:
            st.subheader("📊 میری رخصتوں کا ریکارڈ")
            my_leaves = pd.read_sql_query(f"SELECT start_date as تاریخ, l_type as نوعیت, days as دن, status as حالت FROM leave_requests WHERE t_name='{st.session_state.username}' ORDER BY start_date DESC", conn)
            if not my_leaves.empty:
                st.dataframe(my_leaves, use_container_width=True, hide_index=True)
            else: st.info("کوئی ریکارڈ نہیں ملا۔")

    elif m == "🕒 میری حاضری":
        st.header("🕒 آمد و رخصت (حاضری)")
        st.write(f"آج کی تاریخ: **{date.today().strftime('%d-%m-%Y')}**")
        
        c1, c2 = st.columns(2)
        if c1.button("✅ آمد (Check-in)"):
            at = datetime.now().strftime("%I:%M %p")
            c.execute("INSERT OR REPLACE INTO t_attendance (t_name, a_date, arrival) VALUES (?,?,?)", (st.session_state.username, date.today(), at))
            conn.commit(); st.success(f"آمد کا وقت ریکارڈ ہو گیا: {at}")
        
        if c2.button("🚩 رخصت (Check-out)"):
            dt = datetime.now().strftime("%I:%M %p")
            c.execute("UPDATE t_attendance SET departure=? WHERE t_name=? AND a_date=?", (dt, st.session_state.username, date.today()))
            conn.commit(); st.warning(f"رخصتی کا وقت ریکارڈ ہو گیا: {dt}")

    # ================= LOGOUT =================
    st.sidebar.divider()
    if st.sidebar.button("🚪 لاگ آؤٹ کریں"):
        st.session_state.logged_in = False
        st.rerun()


