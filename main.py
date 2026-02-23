import streamlit as st
import pandas as pd
from datetime import datetime, date
from streamlit_gsheets import GSheetsConnection

# --- 1. پیج سیٹنگز اور برانڈنگ ---
st.set_page_config(page_title="جامعہ پورٹل", layout="wide")

# مینو اور فوٹر چھپانے کے لیے CSS
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            .stApp { direction: rtl; text-align: right; }
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- 2. گوگل شیٹ کنکشن ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_sheet_data(worksheet_name):
    try:
        return conn.read(worksheet=worksheet_name, ttl="0")
    except:
        return pd.DataFrame()

def save_to_sheet(df, worksheet_name):
    conn.update(worksheet=worksheet_name, data=df)
    st.success("ڈیٹا کامیابی سے محفوظ ہو گیا!")

# --- 3. ڈیٹا لسٹیں ---
surahs_urdu = ["الفاتحة", "البقرة", "آل عمران", "النساء", "المائدة", "الأنعام", "الأعراف", "الأنفال", "التوبة", "يونس", "هود", "يوسف", "الرعد", "إبراهيم", "الحجر", "النحل", "الإسراء", "الكهف", "مريم", "طه", "الأنبياء", "الحج", "المؤمنون", "النور", "الفرقان", "الشعراء", "النمل", "القصص", "العنكبوت", "الروم", "لقمان", "السجدة", "الأحزاب", "سبأ", "فاطر", "يس", "الصافات", "ص", "الزمر", "غافر", "فصلت", "الشورى", "الزخرف", "الدخان", "الجاثية", "الأحقاف", "محمد", "الفتح", "الحجرات", "ق", "الذاريات", "الطور", "النجم", "القمر", "الرحمن", "الواقعة", "الحديد", "المجادلة", "الحشر", "الممتحنة", "الصف", "الجمعة", "المنافقون", "التغابن", "الطلاق", "التحريم", "الملك", "القلم", "الحاقة", "المعارج", "نوح", "الجن", "المزمل", "المدثر", "القيامة", "الإنسان", "المرسلات", "النبأ", "النازعات", "عبس", "التكوير", "الإنفطار", "المطففين", "الإنشقاق", "البروج", "الطارق", "الأعلى", "الغاشية", "الفجر", "البلد", "الشمس", "الليل", "الضحى", "الشرح", "التين", "العلق", "القدر", "البينة", "الزلزلة", "العاديات", "القارعة", "التکاثر", "العصر", "الهمزة", "الفيل", "قریش", "الماعون", "الکوثر", "الكافرون", "النصر", "المسد", "الإخلاص", "الفلق", "الناس"]
paras = [f"پارہ {i}" for i in range(1, 31)]

# --- 4. لاگ ان سسٹم ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.header("🕌 لاگ ان")
        u = st.text_input("صارف کا نام")
        p = st.text_input("پاسورڈ", type="password")
        if st.button("داخل ہوں"):
            # اساتذہ کا ڈیٹا شیٹ سے چیک کریں
            teachers_df = load_sheet_data("Teachers")
            if not teachers_df.empty:
                user_match = teachers_df[(teachers_df['name'] == u) & (teachers_df['password'] == p)]
                if not user_match.empty:
                    st.session_state.logged_in, st.session_state.username = True, u
                    st.session_state.user_type = "admin" if u == "admin" else "teacher"
                    st.rerun()
                else: st.error("غلط معلومات")
            else:
                # اگر شیٹ خالی ہے تو ڈیفالٹ ایڈمن
                if u == "admin" and p == "jamia123":
                    st.session_state.logged_in, st.session_state.username = True, u
                    st.session_state.user_type = "admin"
                    st.rerun()
else:
    # مینو
    if st.session_state.user_type == "admin":
        menu = ["📊 تعلیمی رپورٹ", "🕒 اساتذہ کا ریکارڈ", "⚙️ انتظامی کنٹرول"]
    else:
        menu = ["📝 تعلیمی اندراج", "📩 رخصت کی درخواست", "🕒 میری حاضری"]

    m = st.sidebar.radio("مینو", menu)

    # --- استاد: تعلیمی اندراج ---
    if m == "📝 تعلیمی اندراج":
        st.header("📖 تعلیمی اندراج")
        students_df = load_sheet_data("Students")
        if not students_df.empty:
            my_students = students_df[students_df['teacher_name'] == st.session_state.username]
            for index, row in my_students.iterrows():
                s, f = row['name'], row['father_name']
                with st.expander(f"👤 طالب علم: {s} ولد {f}"):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        su = st.selectbox("سورت", surahs_urdu, key=f"su_{s}")
                        att = st.radio("حاضری", ["حاضر", "غیر حاضر"], key=f"at_{s}")
                    with c2:
                        sp = st.selectbox("سبقی پارہ", paras, key=f"sp_{s}")
                        sa = st.number_input("اٹکن", 0, key=f"sa_{s}")
                    with c3:
                        mp = st.selectbox("منزل پارہ", paras, key=f"mp_{s}")
                        mm = st.number_input("غلطی", 0, key=f"mm_{s}")
                    
                    if st.button(f"محفوظ کریں: {s}", key=f"btn_{s}"):
                        new_rec = pd.DataFrame([{
                            "r_date": date.today().strftime("%Y-%m-%d"),
                            "s_name": s, "surah": su, "sq_p": sp, "sq_a": sa, "m_p": mp, "m_m": mm, "attendance": att, "t_name": st.session_state.username
                        }])
                        records_df = load_sheet_data("HifzRecords")
                        updated_df = pd.concat([records_df, new_rec], ignore_index=True)
                        save_to_sheet(updated_df, "HifzRecords")

    # --- ایڈمن: رپورٹ ---
    elif m == "📊 تعلیمی رپورٹ":
        st.header("تعلیمی رپورٹ")
        df = load_sheet_data("HifzRecords")
        st.dataframe(df, use_container_width=True)

    # --- انتظامی کنٹرول ---
    elif m == "⚙️ انتظامی کنٹرول":
        tab1, tab2 = st.tabs(["اساتذہ", "طلباء"])
        with tab1:
            t_df = load_sheet_data("Teachers")
            st.dataframe(t_df)
            un = st.text_input("نام استاد"); up = st.text_input("پاسورڈ")
            if st.button("استاد شامل کریں"):
                new_t = pd.DataFrame([{"name": un, "password": up}])
                updated_t = pd.concat([t_df, new_t], ignore_index=True)
                save_to_sheet(updated_t, "Teachers")

    if st.sidebar.button("🚪 لاگ آؤٹ"):
        st.session_state.logged_in = False; st.rerun()
