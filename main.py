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
    c.execute("""CREATE TABLE IF NOT EXISTS exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            s_name TEXT, 
            f_name TEXT, 
            para_no INTEGER, 
            start_date TEXT, 
            end_date TEXT,
            q1 INTEGER, q2 INTEGER, q3 INTEGER, q4 INTEGER, q5 INTEGER,
            total INTEGER, 
            grade TEXT,
            status TEXT)""")
conn.commit()

    # کالمز کا اضافہ (نئے فیچرز کے لیے)
cols = [
            ("students", "phone", "TEXT"), ("students", "address", "TEXT"), ("students", "id_card", "TEXT"), 
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

# --- مرکزی ہیڈر ---
st.markdown("<div class='main-header'><h1>🕌 جامعہ ملیہ اسلامیہ</h1><p>اسمارٹ تعلیمی و انتظامی پورٹل</p></div>", unsafe_allow_html=True)

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

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
        menu = ["📝 تعلیمی اندراج", "🎓 امتحانی تعلیمی رپورٹ", "درخواستِ رخصت", "🕒 میری حاضری"]
        
    m = st.sidebar.radio("📌 مینو منتخب کریں", menu)

    # ================= ADMIN SECTION =================
    if m == "📊 یومیہ تعلیمی رپورٹ":
        st.markdown("<h2 style='text-align: center; color: #1e5631;'>📊 ماسٹر تعلیمی رپورٹ و تجزیہ</h2>", unsafe_allow_html=True)

        # --- فلٹرز (Filters) ---
        with st.sidebar:
            st.header("🔍 فلٹرز")
            d1 = st.date_input("آغاز", date.today().replace(day=1))
            d2 = st.date_input("اختتام", date.today())
            
            t_list = ["تمام"] + [t[0] for t in c.execute("SELECT DISTINCT t_name FROM hifz_records").fetchall()]
            sel_t = st.selectbox("استاد/کلاس", t_list)
            
            s_list = ["تمام"] + [s[0] for s in c.execute("SELECT DISTINCT s_name FROM hifz_records").fetchall()]
            sel_s = st.selectbox("طالب علم", s_list)

        # --- ڈیٹا کیوری (SQL Query) ---
        query = "SELECT * FROM hifz_records WHERE r_date BETWEEN ? AND ?"
        params = [d1, d2]
        if sel_t != "تمام":
            query += " AND t_name = ?"; params.append(sel_t)
        if sel_s != "تمام":
            query += " AND s_name = ?"; params.append(sel_s)
        
        df = pd.read_sql_query(query, conn, params=params)

        if df.empty:
            st.warning("منتخب کردہ فلٹرز کے مطابق کوئی ریکارڈ نہیں ملا۔")
        else:
            # --- 📈 تجزیاتی میٹرکس ---
            st.subheader("💡 خلاصہ (Summary)")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("کل ریکارڈ", len(df))
            m2.metric("حاضر طلباء", len(df[df['attendance'] == 'حاضر']))
            m3.metric("اوسط سبقی غلطی", round(df['sq_m'].mean(), 1))
            m4.metric("اوسط منزل غلطی", round(df['m_m'].mean(), 1))

            # --- 📝 لائیو ڈیٹا ایڈیٹر (Update/Delete) ---
            st.subheader("🛠️ ڈیٹا کنٹرول (تبدیلی اور حذف)")
            st.info("ٹیبل میں کلک کر کے تبدیلی کریں، اور ڈیلیٹ کرنے کے لیے لائن سلیکٹ کر کے Delete دبائیں۔")
            
            # ڈیٹا ایڈیٹر کا جادو
            edited_df = st.data_editor(
                df, 
                num_rows="dynamic", 
                use_container_width=True, 
                key="master_editor",
                hide_index=True
            )

            # --- 💾 تبدیلیوں کو محفوظ کرنے کا لاجک ---
            if st.button("💾 تمام تبدیلیاں مستقل محفوظ کریں"):
                try:
                    # 1. پہلے پرانا ریکارڈ ڈیلیٹ کریں (فلٹر شدہ رینج کا)
                    c.execute(f"DELETE FROM hifz_records WHERE r_date BETWEEN '{d1}' AND '{d2}'" + 
                              (f" AND t_name='{sel_t}'" if sel_t != "تمام" else "") + 
                              (f" AND s_name='{sel_s}'" if sel_s != "تمام" else ""))
                    
                    # 2. ایڈیٹ شدہ ڈیٹا کو دوبارہ انسرٹ کریں
                    edited_df.to_sql('hifz_records', conn, if_exists='append', index=False)
                    st.success("✅ ڈیٹا کامیابی سے اپ ڈیٹ اور محفوظ کر دیا گیا ہے!")
                    st.rerun()
                except Exception as e:
                    st.error(f"ایرر: {e}")

            # --- 🖨️ پرنٹنگ سیکشن ---
            st.divider()
            st.subheader("🖨️ پرنٹ ایبل رپورٹ")
            
            m_name = st.text_input("مدرسہ کا نام لکھیں", "جامعہ ملیہ اسلامیہ")
            
            if st.button("📄 پرنٹ کے لیے رپورٹ تیار کریں"):
                # HTML فارمیٹ برائے پرنٹ
                html_code = f"""
                <div dir="rtl" style="font-family: 'Arial'; padding: 30px; border: 5px double #1e5631; border-radius: 15px; background-color: white;">
                    <div style="text-align: center;">
                        <h1 style="color: #1e5631; margin-bottom: 5px;">{m_name}</h1>
                        <p style="font-size: 18px; margin-top: 0;">تعلیمی و ترقیاتی رپورٹ ریکارڈ</p>
                        <hr style="border: 1px solid #1e5631;">
                    </div>
                    
                    <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
                        <tr style="background-color: #f2f2f2; border: 1px solid #ddd;">
                            <th style="padding: 10px; border: 1px solid #ddd;">تاریخ</th>
                            <th style="padding: 10px; border: 1px solid #ddd;">نام طالب علم</th>
                            <th style="padding: 10px; border: 1px solid #ddd;">سورت/آیات</th>
                            <th style="padding: 10px; border: 1px solid #ddd;">سبقی (غلطی)</th>
                            <th style="padding: 10px; border: 1px solid #ddd;">منزل (غلطی)</th>
                            <th style="padding: 10px; border: 1px solid #ddd;">حاضری</th>
                        </tr>
                """
                for _, row in df.iterrows():
                    html_code += f"""
                        <tr style="border: 1px solid #ddd; text-align: center;">
                            <td style="padding: 8px; border: 1px solid #ddd;">{row['r_date']}</td>
                            <td style="padding: 8px; border: 1px solid #ddd;">{row['s_name']}</td>
                            <td style="padding: 8px; border: 1px solid #ddd;">{row['surah']} ({row['a_from']}-{row['a_to']})</td>
                            <td style="padding: 8px; border: 1px solid #ddd;">{row['sq_m']}</td>
                            <td style="padding: 8px; border: 1px solid #ddd;">{row['m_m']}</td>
                            <td style="padding: 8px; border: 1px solid #ddd;">{row['attendance']}</td>
                        </tr>
                    """
                    html_code += """
                    </table>
                    
                    <div style="margin-top: 60px; display: flex; justify-content: space-between;">
                        <div style="text-align: center; width: 30%;">
                            <hr style="border: 0.5px solid black; width: 80%;">
                            <p>دستخط استاد</p>
                        </div>
                        <div style="text-align: center; width: 30%;">
                            <div style="border: 2px solid #ddd; height: 80px; width: 80px; margin: 0 auto; border-radius: 50%;"></div>
                            <p>مہر ادارہ</p>
                        </div>
                        <div style="text-align: center; width: 30%;">
                            <hr style="border: 0.5px solid black; width: 80%;">
                            <p>دستخط مہتمم / صدر مدرس</p>
                        </div>
                    </div>
                </div>
                """
                st.markdown(html_code, unsafe_allow_html=True)
                st.write("💡 پرنٹ کرنے کے لیے کی بورڈ سے **Ctrl + P** دبائیں اور اسے PDF کے طور پر محفوظ کریں۔")

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
                        conn.commit()
                        st.success("رخصت منظور کر لی گئی")
                        st.rerun()
                    if c_r.button(f"❌ مسترد کریں", key=f"rej_{l_id}"):
                        c.execute("UPDATE leave_requests SET status='مسترد شدہ ❌', notification_seen=0 WHERE id=?", (l_id,))
                        conn.commit()
                        st.warning("رخصت مسترد کر دی گئی")
                        st.rerun()

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
                        conn.commit()
                        st.success("ڈیٹا اپ ڈیٹ ہو گیا!")
                        st.rerun()
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
                            conn.commit()
                            st.success("داخلہ مکمل ہو گیا!")
                        else: st.error("تمام معلومات پُر کریں")
                else: st.warning("پہلے استاد رجسٹر کریں!")

            st.divider()
            s_df = pd.read_sql_query("SELECT id, name as نام, father_name as ولدیت, teacher_name as استاد FROM students", conn)
            if not s_df.empty:
                s_edt = st.data_editor(s_df, hide_index=True, use_container_width=True)
                if st.button("طلباء کا ڈیٹا اپ ڈیٹ کریں"):
                    for _, r in s_edt.iterrows():
                        c.execute("UPDATE students SET name=?, father_name=?, teacher_name=? WHERE id=?", (r['نام'], r['ولدیت'], r['استاد'], r['id']))
                    conn.commit()
                    st.success("ڈیٹا اپ ڈیٹ ہو گیا!")
                    st.rerun()

    elif m == "🕒 اساتذہ کا ریکارڈ":
        st.header("🕒 اساتذہ کا حاضری ریکارڈ")
        att_df = pd.read_sql_query("SELECT a_date as تاریخ, t_name as استاد, arrival as آمد, departure as رخصت FROM t_attendance ORDER BY a_date DESC", conn)
        if not att_df.empty:
            csv = convert_df_to_csv(att_df)
            st.download_button(label="📥 حاضری رپورٹ ڈاؤن لوڈ کریں", data=csv, file_name="Teachers_Attendance.csv", mime='text/csv')
            st.dataframe(att_df, use_container_width=True, hide_index=True)
        else: st.info("حاضری کا کوئی ریکارڈ موجود نہیں ہے۔")

    # ================= TEACHER SECTION =================
    elif m == "📝 تعلیمی اندراج":
        st.header("🚀 اسمارٹ تعلیمی ڈیش بورڈ")
        sel_date = st.date_input("تاریخ منتخب کریں", date.today())
        
        # ڈیٹا بیس سے طلباء کی لسٹ لینا
        students = c.execute("SELECT name, father_name FROM students WHERE teacher_name=?", (st.session_state.username,)).fetchall()

        if not students:
            st.info("آپ کی کلاس میں کوئی طالب علم رجسٹرڈ نہیں ہے۔")
        else:
                                   # طلباء کی فہرست پر لوپ
            for s, f in students:
                with st.expander(f"👤 {s} ولد {f}"):
                    att = st.radio(f"حاضری {s}", ["حاضر", "غیر حاضر", "رخصت"], key=f"att_{s}", horizontal=True)
                    
                    if att == "حاضر":
                        # سبق، سبقی اور منزل کا ڈیٹا جمع کرنا
                        st.subheader("📖 نیا سبق")
                        surah_sel = st.selectbox("موجودہ سبق (سورت)", surahs_urdu, key=f"surah_{s}")
                        c_a1, c_a2 = st.columns(2)
                        ayah_from = c_a1.text_input("آیت (سے)", key=f"af_{s}")
                        ayah_to = c_a2.text_input("آیت (تک)", key=f"at_{s}")

                        st.subheader("🔄 سبقی")
                        if f"sq_count_{s}" not in st.session_state: st.session_state[f"sq_count_{s}"] = 1
                        for i in range(st.session_state[f"sq_count_{s}"]):
                            c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
                            c1.selectbox(f"پارہ {i+1}", paras, key=f"sqp_{s}_{i}")
                            c2.selectbox(f"مقدار {i+1}", ["مکمل", "آدھا", "پون", "پاؤ"], key=f"sqv_{s}_{i}")
                            c3.number_input(f"اٹکن {i+1}", 0, key=f"sqa_{s}_{i}")
                            c4.number_input(f"غلطی {i+1}", 0, key=f"sqe_{s}_{i}")
                        
                        if st.button(f"➕ مزید سبقی", key=f"btn_sq_{s}"):
                            st.session_state[f"sq_count_{s}"] += 1
                            st.rerun()

                        st.subheader("🏠 منزل")
                        if f"m_count_{s}" not in st.session_state: st.session_state[f"m_count_{s}"] = 1
                        for j in range(st.session_state[f"m_count_{s}"]):
                            mc1, mc2, mc3, mc4 = st.columns([2, 2, 1, 1])
                            mc1.selectbox(f"منزل پ {j+1}", paras, key=f"mp_{s}_{j}")
                            mc2.selectbox(f"مقدار {j+1}", ["مکمل", "آدھا", "پون", "پاؤ"], key=f"mv_{s}_{j}")
                            mc3.number_input(f"اٹکن {j+1}", 0, key=f"ma_{s}_{j}")
                            mc4.number_input(f"غلطی {j+1}", 0, key=f"me_{s}_{j}")
                        
                        if st.button(f"➕ مزید منزل", key=f"btn_m_{s}"):
                            st.session_state[f"m_count_{s}"] += 1
                            st.rerun()

                        # --- ڈیٹا محفوظ کرنے کا عمل ---
                        if st.button(f"محفوظ کریں: {s}", key=f"save_{s}"):
                            # 1. پہلے چیک کریں کہ کیا آج کا ریکارڈ پہلے سے موجود ہے؟
                            check = c.execute("SELECT 1 FROM hifz_records WHERE r_date = ? AND s_name = ? AND f_name = ?", (sel_date, s, f)).fetchone()
                            
                            if check:
                                st.error(f"🛑 ریکارڈ پہلے سے موجود ہے! {s} کا {sel_date} کا اندراج ہو چکا ہے۔")
                            else:
                                # ڈیٹا کو ترتیب دینا
                                sq_list, f_sq_m, f_sq_a = [], 0, 0
                                for i in range(st.session_state[f"sq_count_{s}"]):
                                    p, v, a, e = st.session_state[f"sqp_{s}_{i}"], st.session_state[f"sqv_{s}_{i}"], st.session_state[f"sqa_{s}_{i}"], st.session_state[f"sqe_{s}_{i}"]
                                    sq_list.append(f"{p}:{v}(غ:{e},ا:{a})"); f_sq_m += e; f_sq_a += a
                                
                                m_list, f_m_m, f_m_a = [], 0, 0
                                for j in range(st.session_state[f"m_count_{s}"]):
                                    mp, mv, ma, me = st.session_state[f"mp_{s}_{j}"], st.session_state[f"mv_{s}_{j}"], st.session_state[f"ma_{s}_{j}"], st.session_state[f"me_{s}_{j}"]
                                    m_list.append(f"{mp}:{mv}(غ:{me},ا:{ma})"); f_m_m += me; f_m_a += ma

                                # ڈیٹا بیس میں ڈالنا
                                c.execute("""INSERT INTO hifz_records 
                                          (r_date, s_name, f_name, t_name, surah, a_from, a_to, sq_p, sq_a, sq_m, m_p, m_a, m_m, attendance) 
                                          VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", 
                                          (sel_date, s, f, st.session_state.username, surah_sel, ayah_from, ayah_to, 
                                           " | ".join(sq_list), f_sq_a, f_sq_m, " | ".join(m_list), f_m_a, f_m_m, att))
                                conn.commit()
                                st.success(f"✅ الحمدللہ! {s} کا ریکارڈ محفوظ ہو گیا۔")

                    # غیر حاضر یا رخصت کی صورت میں
                    else:
                        if st.button(f"محفوظ کریں: {s}", key=f"save_absent_{s}"):
                            # یہاں بھی چیکنگ کریں
                            check = c.execute("SELECT 1 FROM hifz_records WHERE r_date = ? AND s_name = ? AND f_name = ?", (sel_date, s, f)).fetchone()
                            if check:
                                st.error(f"🛑 ریکارڈ پہلے سے موجود ہے!")
                            else:
                                c.execute("""INSERT INTO hifz_records (r_date, s_name, f_name, t_name, attendance, surah, sq_p, m_p) 
                                          VALUES (?,?,?,?,?,?,?,?)""", (sel_date, s, f, st.session_state.username, att, att, att, att))
                                conn.commit()
                                st.success(f"✅ {s} کی حاضری ({att}) لگ گئی ہے۔")
    

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
                conn.commit()
                st.rerun()

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
                        conn.commit()
                        st.info("✅ درخواست مہتمم کو بھیج دی گئی ہے۔")
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
            # چیک کریں کہ آج کی حاضری پہلے تو نہیں لگی ہوئی
            record_exists = c.execute("SELECT id FROM t_attendance WHERE t_name=? AND a_date=?", (st.session_state.username, date.today())).fetchone()
            if not record_exists:
                c.execute("INSERT INTO t_attendance (t_name, a_date, arrival) VALUES (?,?,?)", (st.session_state.username, date.today(), at))
                conn.commit()
                st.success(f"آمد کا وقت ریکارڈ ہو گیا: {at}")
            else:
                st.info("آج کے دن آپ کی آمد پہلے ہی ریکارڈ ہو چکی ہے!")
        
        if c2.button("🚩 رخصت (Check-out)"):
            dt = datetime.now().strftime("%I:%M %p")
            c.execute("UPDATE t_attendance SET departure=? WHERE t_name=? AND a_date=?", (dt, st.session_state.username, date.today()))
            conn.commit()
            st.warning(f"رخصتی کا وقت ریکارڈ ہو گیا: {dt}")

  elif m == "🎓 امتحانی تعلیمی رپورٹ":
    st.header("🎓 امتحانی تعلیمی رپورٹ (حفظِ قرآن)")
    
    tab1, tab2 = st.tabs(["📝 نیا امتحان", "📜 رزلٹ کارڈز"])
    
    with tab1:
        st.subheader("طالب علم کا انتخاب کریں")
        # طلباء کی فہرست سے نام نکالیں
        student_list = [f"{row[0]} ولد {row[1]}" for row in students]
        selected_s = st.selectbox("طالب علم", student_list)
        s_name, f_name = selected_s.split(" ولد ")
        
        col1, col2, col3 = st.columns(3)
        para = col1.number_input("پارہ نمبر", 1, 30)
        s_date = col2.date_input("آغازِ پارہ")
        e_date = col3.date_input("اختتامِ پارہ")
        
        st.divider()
        st.markdown("### 🖋️ ممتحن (مہتمم صاحب) کے لیے")
        
        # 5 سوالات کے نمبر
        c1, c2, c3, c4, c5 = st.columns(5)
        q1 = c1.number_input("سوال 1", 0, 20, key="q1")
        q2 = c2.number_input("سوال 2", 0, 20, key="q2")
        q3 = c3.number_input("سوال 3", 0, 20, key="q3")
        q4 = c4.number_input("سوال 4", 0, 20, key="q4")
        q5 = c5.number_input("سوال 5", 0, 20, key="q5")
        
        total = q1 + q2 + q3 + q4 + q5
        
        # گریڈ کی لاجک
        grade = ""
        status = "کامیاب"
        if total >= 90: grade = "ممتاز"
        elif total >= 80: grade = "جید جداً"
        elif total >= 70: grade = "جید"
        elif total >= 60: grade = "مقبول"
        else: 
            grade = "دوبارہ کوشش کریں"
            status = "ناکام"

        st.metric("کل نمبر", f"{total} / 100", f"گریڈ: {grade}")

        if st.button("امتحانی رزلٹ محفوظ کریں"):
            c.execute("""INSERT INTO exams (s_name, f_name, para_no, start_date, end_date, q1, q2, q3, q4, q5, total, grade, status) 
                         VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""", 
                      (s_name, f_name, para, str(s_date), str(e_date), q1, q2, q3, q4, q5, total, grade, status))
            conn.commit()
            if status == "کامیاب":
                st.success(f"مبارک ہو! {s_name} نے پارہ نمبر {para} پاس کر لیا ہے۔")
            else:
                st.warning("نتیجہ محفوظ کر لیا گیا ہے۔ طالب علم کو دوبارہ تیاری کی ہدایت کریں۔")

    with tab2:
        # یہاں رزلٹ کارڈ پرنٹ کرنے کا آپشن ہوگا
        results = c.execute("SELECT * FROM exams ORDER BY id DESC").fetchall()
        for res in results:
            with st.expander(f"پارہ {res[3]} - {res[1]} ({res[12]})"):
                # رزلٹ کارڈ کا ڈیزائن (HTML)
                card_html = f"""
                <div style="border: 5px double #1e5631; padding: 20px; text-align: center; direction: rtl; background-color: #f9fff9;">
                    <h2 style="color: #1e5631; margin-bottom: 0;">جامعہ ملیہ اسلامیہ</h2>
                    <p style="margin-top: 0;">امتحانی تعلیمی رپورٹ (حفظِ قرآن)</p>
                    <hr>
                    <table style="width: 100%; text-align: right; border: none;">
                        <tr><td><b>نام:</b> {res[1]}</td><td><b>ولدیت:</b> {res[2]}</td></tr>
                        <tr><td><b>پارہ نمبر:</b> {res[3]}</td><td><b>کیفیت:</b> {res[12]}</td></tr>
                        <tr><td><b>تاریخ آغاز:</b> {res[4]}</td><td><b>تاریخ اختتام:</b> {res[5]}</td></tr>
                    </table>
                    <div style="margin: 20px 0; font-size: 24px; font-weight: bold; color: #1e5631;">
                        حاصل کردہ نمبر: {res[11]} / 100
                    </div>
                    <div style="display: flex; justify-content: space-around; margin-top: 30px;">
                        <div><hr style="width: 100px;">دستخط استاد</div>
                        <div><hr style="width: 100px;">دستخط مہتمم</div>
                    </div>
                </div>
                """
                st.markdown(card_html, unsafe_allow_html=True)
                st.button(f"پرنٹ رزلٹ کارڈ {res[0]}", on_click=None) # پرنٹ کی لاجک یہاں آئے گی


    # ================= LOGOUT =================
    st.sidebar.divider()
    if st.sidebar.button("🚪 لاگ آؤٹ کریں"):
        st.session_state.logged_in = False
        st.rerun() 























































