import streamlit as st
import pandas as pd
from datetime import datetime, date
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

    # کالمز کا اضافہ
    cols = [("students", "phone", "TEXT"), ("students", "address", "TEXT"), ("students", "id_card", "TEXT"), 
            ("students", "photo", "TEXT"), ("teachers", "phone", "TEXT"), ("teachers", "address", "TEXT"), 
            ("teachers", "id_card", "TEXT"), ("teachers", "photo", "TEXT")]
    for t, col, typ in cols:
        try: c.execute(f"ALTER TABLE {t} ADD COLUMN {col} {typ}")
        except: pass

    c.execute("INSERT OR IGNORE INTO teachers (name, password) VALUES (?,?)", ("admin", "jamia123"))
    conn.commit()

init_db()

def get_base64(file):
    if file: return base64.b64encode(file.read()).decode()
    return None

# --- 2. اسٹائلنگ ---
st.set_page_config(page_title="جامعہ پورٹل", layout="wide")
st.markdown("<style>body{direction:rtl; text-align:right;} .stButton>button{background:#1e5631; color:white; border-radius:10px; font-weight:bold; width:100%;}</style>", unsafe_allow_html=True)

surahs_urdu = ["الفاتحة", "البقرة", "آل عمران", "النساء", "المائدة", "الأنعام", "الأعراف", "الأنفال", "التوبة", "يونس", "هود", "يوسف", "الرعد", "إبراهيم", "الحجر", "النحل", "الإسراء", "الكهف", "مريم", "طه", "الأنبياء", "الحج", "المؤمنون", "النور", "الفرقان", "الشعراء", "النمل", "القصص", "العنكبوت", "الروم", "لقمان", "السجدة", "الأحزاب", "سبأ", "فاطر", "يس", "الصافات", "ص", "الزمر", "غافر", "فصلت", "الشورى", "الزخرف", "الدخان", "الجاثية", "الأحقاف", "محمد", "الفتح", "الحجرات", "ق", "الذاريات", "الطور", "النجم", "القمر", "الرحمن", "الواقعة", "الحديد", "المجادلة", "الحشر", "الممتحنة", "الصف", "الجمعة", "المنافقون", "التغابن", "الطلاق", "التحریم", "الملک", "القلم", "الحاقة", "المعارج", "نوح", "الجن", "المزمل", "المدثر", "القیامة", "الإنسان", "المرسلات", "النبأ", "النازعات", "عبس", "التکویر", "الإنفطار", "المطففین", "الإنشقاق", "البروج", "الطارق", "الأعلى", "الغاشیة", "الفجر", "البلد", "الشمس", "اللیل", "الضحى", "الشرح", "التین", "العلق", "القدر", "البینة", "الزلزلة", "العادیات", "القارعة", "التکاثر", "العصر", "الهمزة", "الفیل", "قریش", "الماعون", "الکوثر", "الکافرون", "النصر", "المسد", "الإخلاص", "الفلق", "الناس"]
paras = [f"پارہ {i}" for i in range(1, 31)]

if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.header("🕌 لاگ ان")
        u = st.text_input("صارف کا نام"); p = st.text_input("پاسورڈ", type="password")
        if st.button("داخل ہوں"):
            res = c.execute("SELECT * FROM teachers WHERE name=? AND password=?", (u, p)).fetchone()
            if res:
                st.session_state.logged_in, st.session_state.username = True, u
                st.session_state.user_type = "admin" if u == "admin" else "teacher"
                st.rerun()
            else: st.error("غلط معلومات")
else:
    menu = ["📊 یومیہ تعلیمی رپورٹ", "📜 ماہانہ رزلٹ کارڈ", "🕒 اساتذہ کا ریکارڈ", "⚙️ انتظامی کنٹرول"] if st.session_state.user_type == "admin" else ["📝 تعلیمی اندراج", "📩 رخصت کی درخواست", "🕒 میری حاضری"]
    m = st.sidebar.radio("مینو", menu)

    # --- ایڈمن: یومیہ تعلیمی رپورٹ ---
    if m == "📊 یومیہ تعلیمی رپورٹ":
        st.header("📊 یومیہ تعلیمی رپورٹ")
        c1, c2, c3 = st.columns([2, 1, 1])
        s_type = c1.radio("رپورٹ کی قسم:", ["کلاس وائز (استاد)", "طالب علم وائز"], horizontal=True)
        d1, d2 = c2.date_input("کب سے", date.today()), c3.date_input("کب تک", date.today())

        target = st.selectbox("منتخب کریں:", [t[0] for t in c.execute(f"SELECT {'name' if s_type=='کلاس وائز (استاد)' else 'DISTINCT s_name'} FROM {'teachers' if s_type=='کلاس وائز (استاد)' else 'hifz_records'}").fetchall()])
        query = f"SELECT id, r_date, s_name, f_name, surah, sq_m, m_m, principal_note FROM hifz_records WHERE {'t_name' if s_type=='کلاس وائز (استاد)' else 's_name'}='{target}' AND r_date BETWEEN '{d1}' AND '{d2}' ORDER BY r_date DESC"

        df = pd.read_sql_query(query, conn)
        if not df.empty:
            df.columns = ['آئی ڈی', 'تاریخ', 'نام طالب علم', 'ولدیت', 'سبق/سورت', 'سبقی غلطی', 'منزل غلطی', 'مہتمم کی رائے']
            edited = st.data_editor(df, hide_index=True, use_container_width=True)
            if st.button("💾 تبدیلیاں محفوظ کریں"):
                for _, r in edited.iterrows():
                    c.execute("UPDATE hifz_records SET surah=?, sq_m=?, m_m=?, principal_note=? WHERE id=?", (r['سبق/سورت'], r['سبقی غلطی'], r['منزل غلطی'], r['مہتمم کی رائے'], r['آئی ڈی']))
                conn.commit(); st.success("محفوظ!"); st.rerun()
        else: st.warning("ریکارڈ نہیں ملا")

    # --- ایڈمن: ماہانہ رزلٹ کارڈ ---
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
                st.dataframe(res_df, use_container_width=True, hide_index=True)
            else: st.warning("ریکارڈ نہیں ملا")

    # --- ایڈمن: انتظامی کنٹرول (ترمیم و حذف) ---
   
    elif m == "⚙️ انتظامی کنٹرول":
        st.header("⚙️ رجسٹریشن، ترمیم و حذف")
        t1, t2 = st.tabs(["👨‍🏫 اساتذہ", "👨‍🎓 طلباء"])

        with t1:
            with st.form("t_reg"):
                c1, c2 = st.columns(2)
                tn, tp = c1.text_input("نام"), c2.text_input("پاسورڈ")
                tid, tph = c1.text_input("شناختی کارڈ"), c2.text_input("فون")
                tadr, tpic = st.text_area("پتہ"), st.file_uploader("تصویر", type=['jpg','png'])
                if st.form_submit_button("رجسٹر کریں"):
                    c.execute("INSERT INTO teachers (name, password, id_card, phone, address, photo) VALUES (?,?,?,?,?,?)", (tn, tp, tid, tph, tadr, get_base64(tpic)))
                    conn.commit(); st.success("کامیاب")

            st.divider(); st.subheader("ترمیم و حذف")
            t_df = pd.read_sql_query("SELECT id, name as نام, password as پاسورڈ, id_card as کارڈ, phone as فون FROM teachers WHERE name!='admin'", conn)
            t_edt = st.data_editor(t_df, hide_index=True, use_container_width=True)
            if st.button("اساتذہ کا ڈیٹا اپ ڈیٹ کریں"):
                for _, r in t_edt.iterrows():
                    c.execute("UPDATE teachers SET name=?, password=?, id_card=?, phone=? WHERE id=?", (r['نام'], r['پاسورڈ'], r['کارڈ'], r['فون'], r['id']))
                conn.commit(); st.success("اپ ڈیٹ مکمل"); st.rerun()

            del_t = st.number_input("خارج کرنے کے لیے استاد کی آئی ڈی لکھیں", min_value=0, step=1)
            if st.button("❌ استاد خارج کریں"):
                c.execute("DELETE FROM teachers WHERE id=?", (del_t,))
                conn.commit(); st.warning("خارج کر دیا گیا"); st.rerun()

        with t2:
            with st.form("s_reg"):
                c1, c2 = st.columns(2)
                sn, sf = c1.text_input("نام"), c2.text_input("ولدیت")
                sid, stch = c1.text_input("ب فارم"), c2.selectbox("استاد", [t[0] for t in c.execute("SELECT name FROM teachers WHERE name!='admin'").fetchall()])
                sph, sadr = c1.text_input("فون"), st.text_area("پتہ")
                spic = st.file_uploader("تصویر ", type=['jpg','png'])
                if st.form_submit_button("داخلہ کریں"):
                    c.execute("INSERT INTO students (name, father_name, teacher_name, id_card, phone, address, photo) VALUES (?,?,?,?,?,?,?)", (sn, sf, stch, sid, sph, sadr, get_base64(spic)))
                    conn.commit(); st.success("داخلہ مکمل")

            st.divider(); st.subheader("طلباء ترمیم و حذف")
            s_df = pd.read_sql_query("SELECT id, name as نام, father_name as ولدیت, teacher_name as استاد, id_card as ب_فارم FROM students", conn)
            s_edt = st.data_editor(s_df, hide_index=True, use_container_width=True)
            if st.button("طلباء کا ڈیٹا اپ ڈیٹ کریں"):
                for _, r in s_edt.iterrows():
                    c.execute("UPDATE students SET name=?, father_name=?, teacher_name=?, id_card=? WHERE id=?", (r['نام'], r['ولدیت'], r['استاد'], r['ب_فارم'], r['id']))
                conn.commit(); st.success("محفوظ!"); st.rerun()

            del_s = st.number_input("خارج کرنے کے لیے طالب علم کی آئی ڈی لکھیں", min_value=0, step=1)
            if st.button("❌ طالب علم خارج کریں"):
                c.execute("DELETE FROM students WHERE id=?", (del_s,))
                conn.commit(); st.warning("خارج کر دیا گیا"); st.rerun()

    # --- استاد کے مینیو (تعلیمی اندراج، رخصت، حاضری) ---

    if m == "📝 تعلیمی اندراج":
        st.header("🚀 اسمارٹ تعلیمی ڈیش بورڈ")

        tab_entry, tab_ranking, tab_analysis = st.tabs(["📝 جدید اندراج", "🏆 ہفتہ وار ٹاپ 3", "📊 کارکردگی کا موازنہ"])

        with tab_entry:
            # (اندراج کا کوڈ وہی رہے گا، یہاں صرف رینکنگ اور گراف کی تبدیلی دی جا رہی ہے)
            sel_date = st.date_input("تاریخ", date.today())
            students = c.execute("SELECT name, father_name FROM students WHERE teacher_name=?", (st.session_state.username,)).fetchall()

            if not students:
                st.info("آپ کی کلاس میں کوئی طالب علم رجسٹرڈ نہیں ہے۔")
            else:
                for s, f in students:
                    last_rec = c.execute("SELECT surah, sq_p, m_p FROM hifz_records WHERE s_name=? ORDER BY r_date DESC LIMIT 1", (s,)).fetchone()
                    with st.expander(f"👤 {s} ولد {f}"):
                        if last_rec:
                            st.markdown(f"📍 **پچھلا ریکارڈ:** سبق: `{last_rec[0]}` | سبقی: `{last_rec[1]}` | منزل: `{last_rec[2]}`")
                        att = st.radio(f"حاضری {s}", ["حاضر", "غیر حاضر", "رخصت"], key=f"att_{s}", horizontal=True)
                        if att == "حاضر":
                            c1, c2, c3 = st.columns(3)
                            with c1:
                                st.subheader("📖 سبق")
                                n_s = st.checkbox("سبق ناغہ", key=f"ns_{s}")
                                su = st.selectbox("سورت", surahs_urdu, key=f"su_{s}") if not n_s else "ناغہ"
                                af = st.text_input("آیت نمبر", "1", key=f"af_{s}")
                            with c2:
                                st.subheader("🔄 سبقی")
                                n_sq = st.checkbox("سبقی ناغہ", key=f"nsq_{s}")
                                sp = st.selectbox("پارہ", paras, key=f"sp_{s}") if not n_sq else "ناغہ"
                                sa = st.number_input("اٹکن", 0, key=f"sa_{s}")
                                sm = st.number_input("غلطی", 0, key=f"sm_{s}")
                            with c3:
                                st.subheader("🏠 منزل")
                                n_m = st.checkbox("منزل ناغہ", key=f"nm_{s}")
                                mp = st.selectbox("منزل پارہ", paras, key=f"mp_{s}") if not n_m else "ناغہ"
                                ma = st.number_input("اٹکن ", 0, key=f"ma_{s}")
                                mm = st.number_input("غلطی ", 0, key=f"mm_{s}")
                        else:
                            su, af, sp, sa, sm, mp, ma, mm = att, "-", att, 0, 0, att, 0, 0

                        if st.button(f"محفوظ کریں: {s}", key=f"btn_{s}"):
                            c.execute("""INSERT INTO hifz_records (r_date, s_name, f_name, t_name, surah, a_from, sq_p, sq_a, sq_m, m_p, m_a, m_m, attendance, principal_note) 
                                      VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", 
                                      (sel_date, s, f, st.session_state.username, su, af, sp, sa, sm, mp, ma, mm, att, "انتظار رائے"))
                            conn.commit()
                            st.success(f"ریکارڈ محفوظ ہوگیا")
                            st.rerun()

        with tab_ranking:
            st.subheader("🏆 اس ہفتے کے بہترین طلباء")
            # فلٹر: صرف 'حاضر' بچوں کا ڈیٹا لیں اور جن کی کم از کم 1 حاضری ہو
            rank_query = f"""SELECT s_name, 
                            AVG(sq_m + m_m) as avg_errors, 
                            COUNT(CASE WHEN attendance='حاضر' THEN 1 END) as presence
                            FROM hifz_records 
                            WHERE t_name='{st.session_state.username}' 
                            AND r_date >= date('now', '-7 days')
                            AND attendance = 'حاضر'
                            GROUP BY s_name 
                            HAVING presence > 0
                            ORDER BY presence DESC, avg_errors ASC LIMIT 3"""
            ranks = c.execute(rank_query).fetchall()

            if ranks:
                cols = st.columns(3)
                medals, colors = ["🥇 ممتاز", "🥈 جید جدا", "🥉 جید"], ["#FFD700", "#C0C0C0", "#CD7F32"]
                for i, (name, avg_err, pres) in enumerate(ranks):
                    with cols[i]:
                        st.markdown(f"""
                        <div style="background:{colors[i]}; padding:15px; border-radius:10px; text-align:center; color:black; border:3px solid #333;">
                            <h2 style="margin:0;">{medals[i]}</h2>
                            <h3 style="margin:5px 0;">{name}</h3>
                            <p style="margin:0;">حاضری: <b>{pres} دن</b></p>
                            <p style="margin:0;">اوسط غلطی: <b>{avg_err:.1f}</b></p>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.info("ٹاپ پوزیشنز کے لیے فی الحال کوئی 'حاضر' طالب علم موجود نہیں ہے۔")

        with tab_analysis:
            st.subheader("📊 طلباء کی ہفتہ وار کارکردگی")
            # تمام ڈیٹا لانا لیکن گراف میں واضح دکھانا
            query = f"SELECT s_name as طالب_علم, (sq_m + m_m) as غلطیاں, r_date as تاریخ FROM hifz_records WHERE t_name='{st.session_state.username}' AND r_date >= date('now', '-7 days') AND attendance='حاضر'"
            data = pd.read_sql_query(query, conn)

            if not data.empty:
                # گروپ بائی کر کے روزانہ کی غلطیوں کا موازنہ
                chart_df = data.pivot_table(index='تاریخ', columns='طالب_علم', values='غلطیاں', aggfunc='mean').fillna(0)
                st.line_chart(chart_df)
                st.write("💡 **وضاحت:** گراف کی لائن جتنی نیچے ہوگی، طالب علم کی کارکردگی اتنی ہی بہتر ہے۔")
            else:
                st.info("گراف دکھانے کے لیے 'حاضر' بچوں کا ڈیٹا دستیاب نہیں ہے۔")

    # --- اساتذہ کا رخصت اور نوٹیفیکیشن پورٹل ---

    elif m == "🕒 اساتذہ کا ریکارڈ":
        st.header("🕒 اساتذہ کی حاضری و رخصت کا ریکارڈ")
        
        tab_att, tab_leaves = st.tabs(["📅 اساتذہ کی حاضری", "📩 رخصت کا ریکارڈ"])
        
        with tab_att:
            st.subheader("اساتذہ کی روزانہ کی حاضری")
            sel_date = st.date_input("تاریخ منتخب کریں", date.today(), key="admin_att_date")
            
            # حاضری کا ڈیٹا لانا
            att_query = f"""
                SELECT t.name as استاد, a.arrival as آمد, a.departure as رخصت 
                FROM teachers t 
                LEFT JOIN t_attendance a ON t.name = a.t_name AND a.a_date = '{sel_date}'
                WHERE t.name != 'admin'
            """
            att_df = pd.read_sql_query(att_query, conn)
            
            if not att_df.empty:
                # غیر حاضر اساتذہ کو سرخ رنگ میں دکھانا
                st.dataframe(att_df.style.highlight_null(null_color="red"), use_container_width=True)
            else:
                st.info("اس تاریخ کا کوئی ریکارڈ موجود نہیں ہے۔")

        with tab_leaves:
            st.subheader("اساتذہ کی رخصتوں کی تفصیل")
            # تمام رخصتوں کا ڈیٹا لانا (منظور شدہ اور مسترد شدہ سب)
            leaves_df = pd.read_sql_query("""
                SELECT t_name as استاد, l_type as نوعیت, start_date as آغاز, 
                days as دن, status as حالت, reason as وجہ 
                FROM leave_requests 
                ORDER BY start_date DESC
            """, conn)
            
            if not leaves_df.empty:
                st.dataframe(leaves_df, use_container_width=True)
            else:
                st.info("رخصت کا کوئی ریکارڈ موجود نہیں ہے۔")

    elif m == "🕒 میری حاضری":
        st.header("🕒 اسمارٹ حاضری پورٹل")
        
        # وقت کے حساب سے خوش آمدیدی پیغام
        current_hour = datetime.now().hour
        if current_hour < 12: greeting = "صبح بخیر! ☀️"
        elif current_hour < 17: greeting = "سہ پہر بخیر! 🌤️"
        else: greeting = "شام بخیر! ✨"
        
        st.subheader(f"السلام علیکم، {st.session_state.username}! {greeting}")

        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("✅ حاضری لگائیں (Arrival)"):
                now_time = datetime.now().strftime("%I:%M %p")
                c.execute("INSERT OR REPLACE INTO t_attendance (t_name, a_date, arrival) VALUES (?,?,?)", 
                          (st.session_state.username, date.today(), now_time))
                conn.commit()
                st.balloons() # حاضری پر خوشی کا اظہار
                st.success(f"آپ کی حاضری لگ چکی ہے: {now_time}")

        with col2:
            if st.button("🚩 رخصتی ریکارڈ کریں (Departure)"):
                now_time = datetime.now().strftime("%I:%M %p")
                c.execute("UPDATE t_attendance SET departure=? WHERE t_name=? AND a_date=?", 
                          (now_time, st.session_state.username, date.today()))
                conn.commit()
                st.warning(f"آپ کی رخصتی ریکارڈ کر لی گئی ہے: {now_time}")

        # آج کی حاضری کا کارڈ
        st.divider()
        today_rec = c.execute("SELECT arrival, departure FROM t_attendance WHERE t_name=? AND a_date=?", 
                              (st.session_state.username, date.today())).fetchone()
        if today_rec:
            c1, c2 = st.columns(2)
            c1.metric("آمد کا وقت", today_rec[0] if today_rec[0] else "--:--")
            c2.metric("رخصت کا وقت", today_rec[1] if today_rec[1] else "--:--")
            
    if st.sidebar.button("🚪 لاگ آؤٹ"):
        st.session_state.logged_in = False; st.rerun()

# ڈیٹا بیس میں نیا کالم شامل کرنے کے لیے (اگر پہلے سے موجود نہ ہو)
try:
    c.execute("ALTER TABLE leave_requests ADD COLUMN notification_seen INTEGER DEFAULT 0")
    conn.commit()
except:
    # اگر کالم پہلے سے موجود ہے تو یہ حصہ کچھ نہیں کرے گا
    pass

