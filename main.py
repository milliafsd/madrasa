import streamlit as st  # 'i' چھوٹا ہونا چاہیے
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
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, password TEXT, phone TEXT, address TEXT, id_card TEXT, photo TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS students 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, father_name TEXT, teacher_name TEXT, phone TEXT, address TEXT, id_card TEXT, photo TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS hifz_records 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, r_date DATE, s_name TEXT, f_name TEXT, t_name TEXT, 
                  surah TEXT, a_from TEXT, a_to TEXT, sq_p TEXT, sq_a INTEGER, sq_m INTEGER, 
                  m_p TEXT, m_a INTEGER, m_m INTEGER, attendance TEXT, principal_note TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS t_attendance 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, t_name TEXT, a_date DATE, arrival TEXT, departure TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS leave_requests 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, t_name TEXT, l_type TEXT, reason TEXT, start_date DATE, days INTEGER, status TEXT, notification_seen INTEGER DEFAULT 0)''')
    
    # کالمز کا اضافہ (اگر موجود نہ ہوں)
    cols = [("students", "phone", "TEXT"), ("students", "address", "TEXT"), ("students", "id_card", "TEXT"), ("students", "photo", "TEXT")]
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
st.markdown("""
<style>
    body { direction: rtl; text-align: right; }
    .stButton>button { background:#1e5631; color:white; border-radius:10px; font-weight:bold; width:100%; }
    .metric-card { background: #f0f2f6; padding: 15px; border-radius: 10px; text-align: center; border-right: 5px solid #1e5631; }
</style>
""", unsafe_allow_html=True)

surahs_urdu = ["الفاتحة", "البقرة", "آل عمران", "النساء", "المائدة", "الأنعام", "الأعراف", "الأنفال", "التوبة", "يونس", "هود", "يوسف", "الرعد", "إبراهيم", "الحجر", "النحل", "الإسراء", "الكهف", "مريم", "طه", "الأنبياء", "الحج", "المؤمنون", "النور", "الفرقان", "الشعراء", "النمل", "القصص", "العنكبوت", "الروم", "لقمان", "السجدة", "الأحزاب", "سبأ", "فاطر", "يس", "الصافات", "ص", "الزمر", "غافر", "فصلت", "الشورى", "الزخرف", "الدخان", "الجاثية", "الأحقاف", "محمد", "الفتح", "الحجرات", "ق", "الذاريات", "الطور", "النجم", "القمر", "الرحمن", "الواقعة", "الحديد", "المجادلة", "الحشر", "الممتحنة", "الصف", "الجمعة", "المنافقون", "التغابن", "الطلاق", "التحریم", "الملک", "القلم", "الحاقة", "المعارج", "نوح", "الجن", "المزمل", "المدثر", "القیامة", "الإنسان", "المرسلات", "النبأ", "النازعات", "عبس", "التکویر", "الإنفطار", "المطففین", "الإنشقاق", "البروج", "الطارق", "الأعلى", "الغاشیة", "الفجر", "البلد", "الشمس", "اللیل", "الضحى", "الشرح", "التین", "العلق", "القدر", "البینة", "الزلزلة", "العادیات", "القارعة", "التکاثر", "العصر", "الهمزة", "الفیل", "قریش", "الماعون", "الکوثر", "الکافرون", "النصر", "المسد", "الإخلاص", "الفلق", "الناس"]
paras = [f"پارہ {i}" for i in range(1, 31)]

if 'logged_in' not in st.session_state: st.session_state.logged_in = False

# --- لاگ ان سسٹم ---
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
    # --- مینیو سلیکشن ---
    menu = ["📊 یومیہ تعلیمی رپورٹ", "📜 ماہانہ رزلٹ کارڈ", "🕒 اساتذہ کا ریکارڈ", "🏛️ مہتمم پینل", "⚙️ انتظامی کنٹرول"] if st.session_state.user_type == "admin" else ["📝 تعلیمی اندراج", "📩 رخصت کی درخواست", "🕒 میری حاضری"]
    m = st.sidebar.radio("مینو منتخب کریں", menu)

    # --- ایڈمن: یومیہ تعلیمی رپورٹ ---
    if m == "📊 یومیہ تعلیمی رپورٹ":
        st.header("📊 یومیہ تعلیمی رپورٹ")
        c1, c2, c3 = st.columns([2, 1, 1])
        s_type = c1.radio("رپورٹ کی قسم:", ["کلاس وائز (استاد)", "طالب علم وائز"], horizontal=True)
        d1, d2 = c2.date_input("کب سے", date.today()), c3.date_input("کب تک", date.today())
        
        target_list = [t[0] for t in c.execute(f"SELECT {'name' if s_type=='کلاس وائز (استاد)' else 'DISTINCT s_name'} FROM {'teachers' if s_type=='کلاس وائز (استاد)' else 'hifz_records'}").fetchall()]
        target = st.selectbox("منتخب کریں:", target_list)
        
        query = f"SELECT id, r_date, s_name, f_name, surah, sq_m, m_m, principal_note FROM hifz_records WHERE {'t_name' if s_type=='کلاس وائز (استاد)' else 's_name'}='{target}' AND r_date BETWEEN '{d1}' AND '{d2}' ORDER BY r_date DESC"
        df = pd.read_sql_query(query, conn)
        if not df.empty:
            df.columns = ['آئی ڈی', 'تاریخ', 'نام طالب علم', 'ولدیت', 'سبق/سورت', 'سبقی غلطی', 'منزل غلطی', 'مہتمم کی رائے']
            edited = st.data_editor(df, hide_index=True, use_container_width=True)
            if st.button("💾 تبدیلیاں محفوظ کریں"):
                for _, r in edited.iterrows():
                    c.execute("UPDATE hifz_records SET surah=?, sq_m=?, m_m=?, principal_note=? WHERE id=?", (r['سبق/سورت'], r['سبقی غلطی'], r['منزل غلطی'], r['مہتمم کی رائے'], r['آئی ڈی']))
                conn.commit(); st.success("محفوظ!"); st.rerun()

    # --- ایڈمن: اساتذہ کا ریکارڈ (روزانہ حاضری و رخصت ہسٹری) ---
    elif m == "🕒 اساتذہ کا ریکارڈ":
        st.header("🕒 اساتذہ کی حاضری و رخصت کا ریکارڈ")
        tab_att, tab_leaves = st.tabs(["📅 روزانہ حاضری", "📜 رخصت کی ہسٹری"])
        with tab_att:
            sel_date = st.date_input("تاریخ منتخب کریں", date.today())
            att_query = f"SELECT t.name as استاد, a.arrival as آمد, a.departure as رخصت FROM teachers t LEFT JOIN t_attendance a ON t.name = a.t_name AND a.a_date = '{sel_date}' WHERE t.name != 'admin'"
            st.dataframe(pd.read_sql_query(att_query, conn).style.highlight_null(null_color="rgba(255,0,0,0.2)"), use_container_width=True)
        with tab_leaves:
            st.dataframe(pd.read_sql_query("SELECT t_name as استاد, l_type as نوعیت, start_date as تاریخ, days as دن, status as حالت, reason as وجہ FROM leave_requests ORDER BY start_date DESC", conn), use_container_width=True)

    # --- ایڈمن: مہتمم پینل (رخصت کی منظوری) ---
    elif m == "🏛️ مہتمم پینل":
        st.header("🏛️ مہتمم پینل (رخصت کی منظوری)")
        pending = c.execute("SELECT id, t_name, l_type, reason, start_date, days FROM leave_requests WHERE status LIKE '%پینڈنگ%'").fetchall()
        if not pending: st.info("کوئی نئی درخواست نہیں ہے۔")
        for l_id, t_n, l_t, reas, s_d, dys in pending:
            with st.expander(f"📌 {t_n} - {l_t}"):
                st.write(f"**وجہ:** {reas} | **آغاز:** {s_d} | **دن:** {dys}")
                c_a, c_r = st.columns(2)
                if c_a.button(f"منظور کریں {l_id}"):
                    c.execute("UPDATE leave_requests SET status='منظور شدہ ✅', notification_seen=0 WHERE id=?", (l_id,))
                    conn.commit(); st.rerun()
                if c_r.button(f"مسترد کریں {l_id}"):
                    c.execute("UPDATE leave_requests SET status='مسترد شدہ ❌', notification_seen=0 WHERE id=?", (l_id,))
                    conn.commit(); st.rerun()

    # --- استاد: تعلیمی اندراج و رینکنگ ---
    elif m == "📝 تعلیمی اندراج":
        st.header("📝 تعلیمی ڈیش بورڈ")
        t_en, t_rk = st.tabs(["📝 اندراج", "🏆 ہفتہ وار ٹاپ 3"])
        with t_en:
            sel_date = st.date_input("تاریخ", date.today())
            students = c.execute("SELECT name, father_name FROM students WHERE teacher_name=?", (st.session_state.username,)).fetchall()
            for s, f in students:
                with st.expander(f"👤 {s} ولد {f}"):
                    att = st.radio(f"حاضری {s}", ["حاضر", "غیر حاضر", "رخصت"], horizontal=True, key=f"at_{s}")
                    if att == "حاضر":
                        c1, c2, c3 = st.columns(3)
                        su = c1.selectbox("سورت", surahs_urdu, key=f"su_{s}")
                        sm = c2.number_input("سبقی غلطی", 0, key=f"sm_{s}")
                        mm = c3.number_input("منزل غلطی", 0, key=f"mm_{s}")
                        if st.button(f"محفوظ کریں: {s}"):
                            c.execute("INSERT INTO hifz_records (r_date, s_name, f_name, t_name, surah, sq_m, m_m, attendance) VALUES (?,?,?,?,?,?,?,?)", (sel_date, s, f, st.session_state.username, su, sm, mm, att))
                            conn.commit(); st.success("محفوظ!")
        with t_rk:
            st.subheader("🏆 اس ہفتے کے بہترین طلباء")
            ranks = c.execute(f"SELECT s_name, AVG(sq_m + m_m) as err FROM hifz_records WHERE t_name='{st.session_state.username}' AND attendance='حاضر' AND r_date >= date('now', '-7 days') GROUP BY s_name ORDER BY err ASC LIMIT 3").fetchall()
            if ranks:
                cols = st.columns(3)
                medals = ["🥇 ممتاز", "🥈 جید جدا", "🥉 جید"]
                for i, (name, err) in enumerate(ranks):
                    cols[i].markdown(f"<div style='background:#f9f9f9; padding:20px; border-radius:10px; border:2px solid gold; text-align:center;'><h3>{medals[i]}</h3><b>{name}</b><br>اوسط غلطی: {err:.1f}</div>", unsafe_allow_html=True)
            else: st.info("ڈیٹا دستیاب نہیں")

    # --- استاد: اسمارٹ حاضری ---
    elif m == "🕒 میری حاضری":
        st.header("🕒 اسمارٹ حاضری پورٹل")
        hour = datetime.now().hour
        greet = "صبح بخیر! ☀️" if hour < 12 else "سہ پہر بخیر! 🌤️" if hour < 17 else "شام بخیر! ✨"
        st.subheader(f"السلام علیکم، {st.session_state.username}! {greet}")
        col1, col2 = st.columns(2)
        if col1.button("✅ حاضری لگائیں (Arrival)"):
            at = datetime.now().strftime("%I:%M %p")
            c.execute("INSERT OR REPLACE INTO t_attendance (t_name, a_date, arrival) VALUES (?,?,?)", (st.session_state.username, date.today(), at))
            conn.commit(); st.balloons(); st.success(f"حاضری لگ گئی: {at}")
        if col2.button("🚩 رخصتی ریکارڈ کریں (Departure)"):
            dt = datetime.now().strftime("%I:%M %p")
            c.execute("UPDATE t_attendance SET departure=? WHERE t_name=? AND a_date=?", (dt, st.session_state.username, date.today()))
            conn.commit(); st.warning(f"رخصتی ریکارڈ: {dt}")
        
        st.divider()
        rec = c.execute("SELECT arrival, departure FROM t_attendance WHERE t_name=? AND a_date=?", (st.session_state.username, date.today())).fetchone()
        if rec:
            c1, c2 = st.columns(2)
            c1.metric("آمد کا وقت", rec[0] if rec[0] else "--:--")
            c2.metric("رخصت کا وقت", rec[1] if rec[1] else "--:--")

    # --- استاد: رخصت مینجمنٹ ---
    elif m == "📩 رخصت کی درخواست":
        st.header("📩 اسمارٹ رخصت مینجمنٹ")
        t_n, t_h = st.tabs(["✍️ نئی درخواست", "📜 ریکارڈ ہسٹری"])
        with t_n:
            with st.form("l_form"):
                lt = st.selectbox("نوعیت", ["ضروری کام", "بیماری", "ہنگامی", "دیگر"])
                dy = st.number_input("دن", 1, 15)
                sd = st.date_input("آغاز")
                re = st.text_area("وجہ")
                if st.form_submit_button("درخواست بھیجیں 🚀"):
                    c.execute("INSERT INTO leave_requests (t_name, l_type, reason, start_date, days, status) VALUES (?,?,?,?,?,?)", (st.session_state.username, lt, re, sd, dy, "پینڈنگ (زیرِ غور) ⏳"))
                    conn.commit(); st.info("درخواست بھیج دی گئی۔")
        with t_h:
            history = c.execute("SELECT start_date, l_type, days, status FROM leave_requests WHERE t_name=? ORDER BY id DESC", (st.session_state.username,)).fetchall()
            for d, t, dy, s in history:
                clr = "#ffc107" if "پینڈنگ" in s else "#28a745" if "منظور" in s else "#dc3545"
                st.markdown(f"<div style='border-right: 5px solid {clr}; background:{clr}11; padding:10px; margin:5px;'><b>{t} ({dy} دن)</b> - {d} | حالت: <b style='color:{clr}'>{s}</b></div>", unsafe_allow_html=True)

    # --- ایڈمن: انتظامی کنٹرول (ترمیم و حذف) ---
    elif m == "⚙️ انتظامی کنٹرول":
        st.header("⚙️ رجسٹریشن و کنٹرول")
        t_t, t_s = st.tabs(["👨‍🏫 اساتذہ", "👨‍🎓 طلباء"])
        with t_t:
            tn, tp = st.text_input("استاد کا نام"), st.text_input("پاسورڈ")
            if st.button("استاد رجسٹر کریں"):
                c.execute("INSERT INTO teachers (name, password) VALUES (?,?)", (tn, tp))
                conn.commit(); st.success("رجسٹریشن مکمل")
            st.divider()
            t_data = pd.read_sql_query("SELECT id, name, password FROM teachers WHERE name!='admin'", conn)
            st.data_editor(t_data, use_container_width=True)
        with t_s:
            sn, sf = st.text_input("طالب علم نام"), st.text_input("ولدیت")
            stch = st.selectbox("استاد منتخب کریں", [t[0] for t in c.execute("SELECT name FROM teachers WHERE name!='admin'").fetchall()])
            if st.button("طالب علم داخل کریں"):
                c.execute("INSERT INTO students (name, father_name, teacher_name) VALUES (?,?,?)", (sn, sf, stch))
                conn.commit(); st.success("داخلہ مکمل")

    if st.sidebar.button("🚪 لاگ آؤٹ"):
        st.session_state.logged_in = False; st.rerun()
