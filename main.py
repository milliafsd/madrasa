import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date, datetime

# --- 1. پیج سیٹنگز اور برانڈنگ ---
st.set_page_config(page_title="جامعہ ملیہ اسلامیہ فیصل آباد", layout="wide")

# مینو اور فوٹر چھپانے کے لیے CSS
hide_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stApp { direction: rtl; text-align: right; }
    </style>
"""
st.markdown(hide_style, unsafe_allow_html=True)

# --- 2. گوگل شیٹ سے کنکشن ---
conn = st.connection("gsheets", type=GSheetsConnection)

# ڈیٹا لوڈ کرنے کا فنکشن
def load_data(sheet_name):
    try:
        return conn.read(worksheet=sheet_name, ttl="0")
    except:
        # اگر شیٹ موجود نہ ہو تو خالی فریم بنانا
        return pd.DataFrame()

# --- 3. ٹائٹل اور لوگو ---
st.markdown("<h1 style='text-align: center; color: #1e5631;'>🕌 جامعہ ملیہ اسلامیہ فیصل آباد</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'>آن لائن تعلیمی و مالیاتی پورٹل</p>", unsafe_allow_html=True)
st.divider()

# --- 4. لاگ ان سسٹم ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.subheader("لاگ ان پینل")
        user = st.text_input("صارف کا نام")
        pw = st.text_input("پاسورڈ", type="password")
        if st.button("داخل ہوں"):
            # سادہ لاگ ان (آپ اسے شیٹ سے بھی جوڑ سکتے ہیں)
            if (user == "admin" and pw == "jamia123") or (user == "staff" and pw == "staff123"):
                st.session_state.logged_in = True
                st.session_state.username = user
                st.rerun()
            else:
                st.error("غلط معلومات")
else:
    # --- 5. مین مینو ---
    menu = ["📝 تعلیمی اندراج", "💰 اخراجات", "📊 رپورٹ", "🕒 حاضری اساتذہ"]
    choice = st.sidebar.radio("مینو", menu)

    # --- تعلیمی اندراج کا حصہ ---
    if choice == "📝 تعلیمی اندراج":
        st.header("روزانہ تعلیمی ریکارڈ")
        with st.form("edu_form", clear_on_submit=True):
            s_name = st.text_input("طالب علم کا نام")
            surah = st.text_input("سورت / پارہ")
            lesson_detail = st.text_area("سبق کی تفصیل")
            errors = st.number_input("غلطیاں / اٹکن", min_value=0)
            status = st.selectbox("حاضری", ["حاضر", "غیر حاضر", "رخصت"])
            entry_date = st.date_input("تاریخ", date.today())
            
            if st.form_submit_button("محفوظ کریں"):
                new_data = pd.DataFrame([{
                    "تاریخ": entry_date.strftime("%Y-%m-%d"),
                    "نام": s_name,
                    "سبق": surah,
                    "تفصیل": lesson_detail,
                    "غلطیاں": errors,
                    "حاضری": status,
                    "درج کنندہ": st.session_state.username
                }])
                # گوگل شیٹ میں ڈیٹا بھیجنا
                old_data = load_data("Education")
                updated_df = pd.concat([old_data, new_data], ignore_index=True)
                conn.update(worksheet="Education", data=updated_df)
                st.success("ریکارڈ گوگل شیٹ میں محفوظ ہو گیا!")

    # --- اخراجات کا حصہ ---
    elif choice == "💰 اخراجات":
        st.header("جامعہ کے اخراجات")
        with st.form("exp_form", clear_on_submit=True):
            item = st.text_input("اشیاء کا نام")
            amount = st.number_input("رقم", min_value=0.0)
            buyer = st.text_input("خرچ کرنے والا", value=st.session_state.username)
            exp_date = st.date_input("تاریخ", date.today())
            
            if st.form_submit_button("خرچ محفوظ کریں"):
                exp_entry = pd.DataFrame([{
                    "تاریخ": exp_date.strftime("%Y-%m-%d"),
                    "چیز": item,
                    "رقم": amount,
                    "نام": buyer
                }])
                old_exp = load_data("Expenses")
                updated_exp = pd.concat([old_exp, exp_entry], ignore_index=True)
                conn.update(worksheet="Expenses", data=updated_exp)
                st.success("خرچ محفوظ کر لیا گیا۔")

    # --- رپورٹ کا حصہ ---
    elif choice == "📊 رپورٹ":
        st.header("مکمل ریکارڈ")
        tab1, tab2 = st.tabs(["تعلیمی رپورٹ", "اخراجات رپورٹ"])
        with tab1:
            st.dataframe(load_data("Education"), use_container_width=True)
        with tab2:
            st.dataframe(load_data("Expenses"), use_container_width=True)

    # لاگ آؤٹ
    if st.sidebar.button("🚪 لاگ آؤٹ"):
        st.session_state.logged_in = False
        st.rerun()
