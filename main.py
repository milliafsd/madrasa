"""
جامعہ ملیہ اسلامیہ فیصل آباد — Smart ERP v5.0
Fixed: Icons, Errors, Student Grid, Admin Controls
"""

# ─────────────────────────────────────────
# STEP 1: PAGE CONFIG (must be first)
# ─────────────────────────────────────────
import streamlit as st
st.set_page_config(
    page_title="جامعہ ملیہ ERP",
    page_icon="🕌",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ─────────────────────────────────────────
# STEP 2: IMPORTS
# ─────────────────────────────────────────
import sqlite3
import hashlib
import os
import io
import zipfile
import shutil
import pandas as pd
from datetime import datetime, date, timedelta

# ─────────────────────────────────────────
# STEP 3: DATABASE
# ─────────────────────────────────────────
DB = "jamia_data.db"


def get_conn():
    conn = sqlite3.connect(DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def execute(sql, params=()):
    """Run write query, return lastrowid"""
    with get_conn() as c:
        cur = c.execute(sql, params)
        c.commit()
        return cur.lastrowid


def query(sql, params=(), one=False):
    """Run read query, return list of dicts"""
    try:
        with get_conn() as c:
            rows = [dict(r) for r in c.execute(sql, params).fetchall()]
        if one:
            return rows[0] if rows else None
        return rows
    except Exception as e:
        return None if one else []


def scalar(sql, params=()):
    """Return single value"""
    try:
        with get_conn() as c:
            r = c.execute(sql, params).fetchone()
        return r[0] if r else 0
    except:
        return 0


def table_has_col(table, col):
    rows = query(f"PRAGMA table_info({table})")
    return any(r.get("name") == col for r in rows)


def safe_add_col(table, col, typ):
    if not table_has_col(table, col):
        try:
            execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
        except:
            pass


def init_db():
    """Create all tables"""
    execute("""
    CREATE TABLE IF NOT EXISTS users (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        username     TEXT UNIQUE NOT NULL,
        password     TEXT NOT NULL,
        role         TEXT DEFAULT 'teacher',
        dept         TEXT DEFAULT '',
        phone        TEXT DEFAULT '',
        id_card      TEXT DEFAULT '',
        joining_date TEXT DEFAULT '',
        is_active    INTEGER DEFAULT 1,
        created_at   TEXT DEFAULT (datetime('now','localtime'))
    )""")

    execute("""
    CREATE TABLE IF NOT EXISTS students (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        name           TEXT NOT NULL,
        father_name    TEXT NOT NULL,
        mother_name    TEXT DEFAULT '',
        roll_no        TEXT DEFAULT '',
        dob            TEXT DEFAULT '',
        admission_date TEXT DEFAULT '',
        phone          TEXT DEFAULT '',
        address        TEXT DEFAULT '',
        teacher        TEXT DEFAULT '',
        dept           TEXT DEFAULT '',
        class_name     TEXT DEFAULT '',
        section        TEXT DEFAULT '',
        is_active      INTEGER DEFAULT 1,
        created_at     TEXT DEFAULT (datetime('now','localtime'))
    )""")

    execute("""
    CREATE TABLE IF NOT EXISTS hifz_records (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        rec_date       TEXT NOT NULL,
        student_id     INTEGER NOT NULL,
        teacher        TEXT NOT NULL,
        attendance     TEXT DEFAULT 'حاضر',
        sabaq          TEXT DEFAULT '',
        sabaq_lines    INTEGER DEFAULT 0,
        sabaq_nagha    INTEGER DEFAULT 0,
        sq_text        TEXT DEFAULT '',
        sq_nagha       INTEGER DEFAULT 0,
        sq_atkan       INTEGER DEFAULT 0,
        sq_mistakes    INTEGER DEFAULT 0,
        manzil_text    TEXT DEFAULT '',
        manzil_nagha   INTEGER DEFAULT 0,
        manzil_atkan   INTEGER DEFAULT 0,
        manzil_mistakes INTEGER DEFAULT 0,
        cleanliness    TEXT DEFAULT '',
        grade          TEXT DEFAULT '',
        note           TEXT DEFAULT '',
        created_at     TEXT DEFAULT (datetime('now','localtime'))
    )""")

    execute("""
    CREATE TABLE IF NOT EXISTS qaida_records (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        rec_date    TEXT NOT NULL,
        student_id  INTEGER NOT NULL,
        teacher     TEXT NOT NULL,
        attendance  TEXT DEFAULT 'حاضر',
        lesson_no   TEXT DEFAULT '',
        total_lines INTEGER DEFAULT 0,
        details     TEXT DEFAULT '',
        cleanliness TEXT DEFAULT '',
        note        TEXT DEFAULT '',
        created_at  TEXT DEFAULT (datetime('now','localtime'))
    )""")

    execute("""
    CREATE TABLE IF NOT EXISTS general_records (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        rec_date    TEXT NOT NULL,
        student_id  INTEGER NOT NULL,
        teacher     TEXT NOT NULL,
        dept        TEXT DEFAULT '',
        attendance  TEXT DEFAULT 'حاضر',
        subject     TEXT DEFAULT '',
        lesson      TEXT DEFAULT '',
        homework    TEXT DEFAULT '',
        performance TEXT DEFAULT '',
        cleanliness TEXT DEFAULT '',
        note        TEXT DEFAULT '',
        created_at  TEXT DEFAULT (datetime('now','localtime'))
    )""")

    execute("""
    CREATE TABLE IF NOT EXISTS teacher_attendance (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        username   TEXT NOT NULL,
        att_date   TEXT NOT NULL,
        arrival    TEXT DEFAULT '',
        departure  TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now','localtime')),
        UNIQUE(username, att_date)
    )""")

    execute("""
    CREATE TABLE IF NOT EXISTS leave_requests (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        username   TEXT NOT NULL,
        leave_type TEXT DEFAULT '',
        start_date TEXT DEFAULT '',
        days       INTEGER DEFAULT 1,
        reason     TEXT DEFAULT '',
        status     TEXT DEFAULT 'پینڈنگ',
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )""")

    execute("""
    CREATE TABLE IF NOT EXISTS exams (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id  INTEGER NOT NULL,
        teacher     TEXT DEFAULT '',
        dept        TEXT DEFAULT '',
        exam_type   TEXT DEFAULT '',
        from_para   INTEGER DEFAULT 0,
        to_para     INTEGER DEFAULT 0,
        book_name   TEXT DEFAULT '',
        amount_read TEXT DEFAULT '',
        start_date  TEXT DEFAULT '',
        end_date    TEXT DEFAULT '',
        total_days  INTEGER DEFAULT 0,
        q1 INTEGER DEFAULT 0, q2 INTEGER DEFAULT 0,
        q3 INTEGER DEFAULT 0, q4 INTEGER DEFAULT 0, q5 INTEGER DEFAULT 0,
        total       INTEGER DEFAULT 0,
        grade       TEXT DEFAULT '',
        status      TEXT DEFAULT 'پینڈنگ',
        created_at  TEXT DEFAULT (datetime('now','localtime'))
    )""")

    execute("""
    CREATE TABLE IF NOT EXISTS passed_paras (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id  INTEGER NOT NULL,
        para_no     INTEGER DEFAULT 0,
        book_name   TEXT DEFAULT '',
        passed_date TEXT DEFAULT '',
        exam_type   TEXT DEFAULT '',
        grade       TEXT DEFAULT '',
        marks       INTEGER DEFAULT 0
    )""")

    execute("""
    CREATE TABLE IF NOT EXISTS timetable (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        teacher  TEXT NOT NULL,
        day_name TEXT DEFAULT '',
        period   TEXT DEFAULT '',
        subject  TEXT DEFAULT '',
        room     TEXT DEFAULT ''
    )""")

    execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        title      TEXT NOT NULL,
        message    TEXT DEFAULT '',
        target     TEXT DEFAULT 'تمام',
        created_by TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )""")

    execute("""
    CREATE TABLE IF NOT EXISTS staff_notes (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        staff        TEXT NOT NULL,
        note_date    TEXT DEFAULT '',
        note_type    TEXT DEFAULT '',
        description  TEXT DEFAULT '',
        action_taken TEXT DEFAULT '',
        status       TEXT DEFAULT 'زیر التواء',
        created_by   TEXT DEFAULT '',
        created_at   TEXT DEFAULT (datetime('now','localtime'))
    )""")

    execute("""
    CREATE TABLE IF NOT EXISTS audit_log (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        username   TEXT DEFAULT '',
        action     TEXT DEFAULT '',
        details    TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )""")

    # Default admin
    if not query("SELECT id FROM users WHERE username='admin'", one=True):
        execute(
            "INSERT INTO users(username,password,role,dept) VALUES(?,?,?,?)",
            ("admin", make_hash("jamia123"), "admin", "انتظامیہ")
        )


# ─────────────────────────────────────────
# STEP 4: SECURITY
# ─────────────────────────────────────────
def make_hash(pw):
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()


def verify_password(plain, stored):
    if not plain or not stored:
        return False
    # New hash format
    if make_hash(plain) == stored:
        return True
    # Old format (no utf-8 explicit)
    if hashlib.sha256(plain.encode()).hexdigest() == stored:
        return True
    # Plain text legacy
    if plain == stored:
        return True
    return False


def log_action(user, action, detail=""):
    try:
        execute(
            "INSERT INTO audit_log(username,action,details) VALUES(?,?,?)",
            (user, action, str(detail)[:300])
        )
    except:
        pass


# ─────────────────────────────────────────
# STEP 5: GRADE LOGIC
# ─────────────────────────────────────────
def hifz_grade(att, sn, sqn, mn, sqm, mm):
    if att == "غیر حاضر":
        return "غیر حاضر"
    if att == "رخصت":
        return "رخصت"
    nagha = int(bool(sn)) + int(bool(sqn)) + int(bool(mn))
    if nagha == 1:
        return "ناقص"
    if nagha == 2:
        return "کمزور"
    if nagha >= 3:
        return "ناکام"
    total = int(sqm) + int(mm)
    if total <= 2:
        return "ممتاز"
    if total <= 5:
        return "جید جداً"
    if total <= 8:
        return "جید"
    if total <= 12:
        return "مقبول"
    return "ناکام"


def exam_grade(total):
    if total >= 90: return "ممتاز"
    if total >= 80: return "جید جداً"
    if total >= 70: return "جید"
    if total >= 60: return "مقبول"
    return "ناکام"


# ─────────────────────────────────────────
# STEP 6: REPORT GENERATOR
# ─────────────────────────────────────────
def make_html_report(df, title, subtitle=""):
    table_html = df.to_html(index=False, border=0, classes="rt", escape=False)
    return f"""<!DOCTYPE html>
<html dir="rtl" lang="ur">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu:wght@400;700&display=swap');
* {{ font-family: 'Noto Nastaliq Urdu', serif; direction: rtl; }}
body {{ background: #f5f9f7; margin: 0; padding: 20px; }}
.wrap {{ background: #fff; border-radius: 12px; padding: 24px;
        max-width: 960px; margin: auto;
        box-shadow: 0 4px 20px rgba(0,77,50,.10); }}
h2 {{ text-align: center; color: #0a5c3c;
     border-bottom: 3px solid #c9982a; padding-bottom: 12px; }}
.sub {{ text-align: center; color: #555; margin-top: 4px; font-size: .9rem; }}
table.rt {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
table.rt th {{ background: #0a5c3c; color: #fff;
               padding: 9px 12px; text-align: center; font-size: 14px; }}
table.rt td {{ padding: 7px 12px; border-bottom: 1px solid #e8f0ec;
               text-align: center; font-size: 13px; }}
table.rt tr:nth-child(even) td {{ background: #f0f8f4; }}
.sig {{ display: flex; justify-content: space-between;
        margin-top: 48px; padding-top: 16px;
        border-top: 1px solid #ddd; }}
.pb {{ text-align: center; margin-top: 24px; }}
.pb button {{ padding: 10px 32px; background: #0a5c3c; color: #fff;
              border: none; border-radius: 8px; cursor: pointer;
              font-size: 15px; font-family: inherit; }}
@media print {{ .pb {{ display: none; }} }}
</style>
</head>
<body>
<div class="wrap">
  <h2>🕌 جامعہ ملیہ اسلامیہ فیصل آباد</h2>
  <p class="sub"><b>{title}</b>{" | " + subtitle if subtitle else ""}</p>
  {table_html}
  <div class="sig">
    <span>دستخط استاذ: ___________________</span>
    <span>دستخط مہتمم: ___________________</span>
  </div>
</div>
<div class="pb">
  <button onclick="window.print()">🖨️ پرنٹ کریں</button>
</div>
</body>
</html>"""


def df_csv(df):
    return df.to_csv(index=False).encode("utf-8-sig")


# ─────────────────────────────────────────
# STEP 7: CONSTANTS
# ─────────────────────────────────────────
SURAHS = [
    "الفاتحة", "البقرة", "آل عمران", "النساء", "المائدة",
    "الأنعام", "الأعراف", "الأنفال", "التوبة", "يونس",
    "هود", "يوسف", "الرعد", "إبراهيم", "الحجر", "النحل",
    "الإسراء", "الكهف", "مريم", "طه", "الأنبياء", "الحج",
    "المؤمنون", "النور", "الفرقان", "الشعراء", "النمل", "القصص",
    "العنكبوت", "الروم", "لقمان", "السجدة", "الأحزاب", "سبأ",
    "فاطر", "يس", "الصافات", "ص", "الزمر", "غافر",
    "فصلت", "الشورى", "الزخرف", "الدخان", "الجاثية", "الأحقاف",
    "محمد", "الفتح", "الحجرات", "ق", "الذاريات", "الطور",
    "النجم", "القمر", "الرحمن", "الواقعة", "الحديد", "المجادلة",
    "الحشر", "الممتحنة", "الصف", "الجمعة", "المنافقون", "التغابن",
    "الطلاق", "التحریم", "الملک", "القلم", "الحاقة", "المعارج",
    "نوح", "الجن", "المزمل", "المدثر", "القیامة", "الإنسان",
    "المرسلات", "النبأ", "النازعات", "عبس", "التکویر", "الإنفطار",
    "المطففین", "الإنشقاق", "البروج", "الطارق", "الأعلى", "الغاشیة",
    "الفجر", "البلد", "الشمس", "اللیل", "الضحى", "الشرح",
    "التین", "العلق", "القدر", "البینة", "الزلزلة", "العادیات",
    "القارعة", "التکاثر", "العصر", "الهمزة", "الفیل", "قریش",
    "الماعون", "الکوثر", "الکافرون", "النصر", "المسد", "الإخلاص",
    "الفلق", "الناس",
]
PARAS   = [f"پارہ {i}" for i in range(1, 31)]
DAYS_UR = ["پیر", "منگل", "بدھ", "جمعرات", "جمعہ", "ہفتہ", "اتوار"]
CLEAN   = ["بہترین", "بہتر", "ناقص"]
DEPTS   = ["حفظ", "قاعدہ", "درسِ نظامی", "عصری تعلیم"]
MIQDAR  = ["مکمل", "آدھا", "پون", "پاؤ"]
ATT     = ["حاضر", "غیر حاضر", "رخصت"]


# ─────────────────────────────────────────
# STEP 8: INIT DB
# ─────────────────────────────────────────
init_db()

# ─────────────────────────────────────────
# STEP 9: SESSION STATE
# ─────────────────────────────────────────
defaults = {
    "logged_in": False,
    "username": "",
    "role": "",
    "page": "home",
    "sel_stu": None,
    "entry_dept": "حفظ",
    "entry_date": str(date.today()),
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


def goto(p):
    st.session_state.page = p
    st.session_state.sel_stu = None
    st.rerun()


IS_ADMIN = st.session_state.role == "admin"

# ─────────────────────────────────────────
# STEP 10: CSS
# ─────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu:wght@400;500;700&display=swap');

:root {
  --green:  #0a5c3c;
  --green2: #0d7a52;
  --green3: #10966a;
  --pale:   #e8f5ee;
  --gold:   #c9982a;
  --gold2:  #f5c842;
  --white:  #ffffff;
  --bg:     #f2f7f4;
  --text:   #1a2e25;
  --gray:   #5a6e64;
  --border: #d4e6da;
  --rad:    14px;
  --rads:   10px;
  --sh:     0 2px 12px rgba(10,92,60,.09);
  --sh2:    0 6px 28px rgba(10,92,60,.16);
}

/* Base */
* { font-family: 'Noto Nastaliq Urdu', Georgia, serif !important;
    direction: rtl !important; box-sizing: border-box; }
html, body, [class*="css"] { direction: rtl; text-align: right; }
.stApp { background: var(--bg); }
#MainMenu, footer, header { visibility: hidden !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }
section[data-testid="stSidebar"] { display: none !important; }

/* ─ TOP BAR ─ */
.topbar {
  background: linear-gradient(135deg, var(--green) 0%, var(--green2) 100%);
  padding: 10px 16px;
  display: flex; align-items: center; justify-content: space-between;
  box-shadow: 0 2px 12px rgba(0,0,0,.22);
  position: sticky; top: 0; z-index: 100;
}
.tb-left { display: flex; align-items: center; gap: 10px; }
.tb-icon { font-size: 2rem; }
.tb-name { color: #fff; font-size: 1rem; font-weight: 700; }
.tb-sub  { color: var(--gold2); font-size: .70rem; }
.tb-user { background: rgba(255,255,255,.15);
  border: 1px solid rgba(255,255,255,.25);
  border-radius: 24px; padding: 4px 14px;
  color: #fff; font-size: .78rem; }

/* ─ MAIN WRAP ─ */
.mw { max-width: 1060px; margin: 0 auto; padding: 14px 14px 90px; }

/* ─ SQUARE NAV BUTTONS ─ */
/* We use Streamlit columns + buttons styled via CSS */
.stButton > button {
  background: var(--white) !important;
  color: var(--text) !important;
  border: 2px solid var(--border) !important;
  border-radius: var(--rad) !important;
  padding: 10px 6px 8px !important;
  font-size: .75rem !important;
  font-weight: 700 !important;
  line-height: 1.4 !important;
  box-shadow: var(--sh) !important;
  transition: all .18s ease !important;
  min-height: 72px !important;
  width: 100% !important;
}
.stButton > button:hover {
  border-color: var(--green2) !important;
  transform: translateY(-2px) scale(1.02) !important;
  box-shadow: var(--sh2) !important;
  background: var(--pale) !important;
  color: var(--green) !important;
}

/* ─ ACTION BUTTONS (forms etc) ─ */
.act-btn > button {
  background: linear-gradient(135deg, var(--green), var(--green2)) !important;
  color: #fff !important;
  border: none !important;
  border-radius: var(--rads) !important;
  min-height: 40px !important;
  font-size: .85rem !important;
  font-weight: 700 !important;
}
.act-btn > button:hover {
  background: linear-gradient(135deg, #082e1e, var(--green)) !important;
  transform: translateY(-1px) !important;
}

/* ─ PAGE CARD ─ */
.pc {
  background: var(--white);
  border-radius: var(--rad);
  padding: 18px;
  box-shadow: var(--sh);
  margin-bottom: 12px;
  border: 1px solid rgba(10,92,60,.06);
}

/* ─ SECTION HEADER ─ */
.sh {
  background: linear-gradient(135deg, var(--green), var(--green2));
  border-radius: var(--rad);
  padding: 13px 18px;
  margin-bottom: 14px;
  display: flex; align-items: center; gap: 10px;
}
.sh-ico { font-size: 1.4rem; }
.sh-title { color: #fff; font-size: 1rem; font-weight: 700; }
.sh-sub { color: rgba(255,255,255,.75); font-size: .72rem; margin-top: 1px; }

/* ─ METRICS ─ */
.mets {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px; margin-bottom: 14px;
}
@media(max-width:600px) { .mets { grid-template-columns: repeat(2,1fr); } }
.mc {
  background: var(--white);
  border-radius: var(--rad);
  padding: 14px 10px;
  text-align: center;
  box-shadow: var(--sh);
  position: relative; overflow: hidden;
}
.mc::after {
  content: ''; position: absolute;
  bottom: 0; left: 0; right: 0; height: 3px;
  background: linear-gradient(90deg, var(--green), var(--gold));
}
.mc-ico { font-size: 1.6rem; display: block; margin-bottom: 3px; }
.mc-val { font-size: 1.9rem; font-weight: 800; color: var(--green); line-height: 1; }
.mc-lbl { font-size: .72rem; color: var(--gray); margin-top: 2px; }

/* ─ STUDENT ICON CARDS ─ */
.stu-ico-card {
  background: var(--white);
  border: 2px solid var(--border);
  border-radius: var(--rad);
  padding: 12px 8px 10px;
  text-align: center;
  cursor: pointer;
  box-shadow: var(--sh);
  transition: all .2s ease;
  position: relative;
}
.stu-ico-card.done {
  background: #e8f8ef;
  border-color: #22c55e;
}
.stu-ico-card.sel {
  background: linear-gradient(145deg, var(--green), var(--green2));
  border-color: var(--green);
  box-shadow: var(--sh2);
}
.stu-avatar {
  width: 48px; height: 48px;
  border-radius: 12px;
  display: flex; align-items: center;
  justify-content: center;
  margin: 0 auto 7px;
  font-size: 1.4rem;
  background: linear-gradient(145deg, var(--green), var(--green3));
  box-shadow: 0 3px 8px rgba(10,92,60,.22);
}
.stu-ico-card.done .stu-avatar { background: linear-gradient(145deg,#16a34a,#15803d); }
.stu-ico-card.sel .stu-avatar  { background: rgba(255,255,255,.25); }
.stu-nm { font-size: .8rem; font-weight: 700; color: var(--text); line-height: 1.3; }
.stu-fn { font-size: .68rem; color: var(--gray); }
.stu-ico-card.sel .stu-nm,
.stu-ico-card.sel .stu-fn { color: #fff; }
.done-tag {
  position: absolute; top: 4px; left: 4px;
  background: #16a34a; color: #fff;
  border-radius: 6px; font-size: .58rem;
  padding: 1px 5px; font-weight: 700;
}

/* ─ GRADE CHIPS ─ */
.chip {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 20px;
  font-size: .75rem; font-weight: 700;
}
.cn { background: #d1fae5; color: #065f46; }
.cp { background: #ede9fe; color: #4c1d95; }
.cb { background: #dbeafe; color: #1e40af; }
.cy { background: #fef3c7; color: #92400e; }
.co { background: #ffedd5; color: #9a3412; }
.cr { background: #fee2e2; color: #991b1b; }
.cg { background: #f3f4f6; color: #374151; }

/* ─ STATUS CHIPS ─ */
.sp { background: #fef3c7; color: #92400e;
      border-radius: 16px; padding: 2px 10px; font-size: .72rem; font-weight: 700; }
.so { background: #d1fae5; color: #065f46;
      border-radius: 16px; padding: 2px 10px; font-size: .72rem; font-weight: 700; }
.sr { background: #fee2e2; color: #991b1b;
      border-radius: 16px; padding: 2px 10px; font-size: .72rem; font-weight: 700; }

/* ─ LEAVE CARD ─ */
.lv-card {
  background: var(--white);
  border-right: 4px solid var(--gold);
  border-radius: var(--rad);
  padding: 12px 16px; margin-bottom: 8px;
  box-shadow: var(--sh);
}

/* ─ NOTIF ─ */
.nf-card {
  background: linear-gradient(135deg,#f0f9ff,#e0f2fe);
  border-right: 4px solid #0369a1;
  border-radius: var(--rads);
  padding: 10px 14px; margin-bottom: 8px;
}
.nf-card h5 { color: #0369a1 !important; margin: 0 0 3px !important; font-size: .88rem !important; }
.nf-card p  { color: var(--text); margin: 0; font-size: .80rem; }
.nf-card sm { color: var(--gray); font-size: .68rem; }

/* ─ PROGRESS ─ */
.prog-wrap { background: #e5e7eb; border-radius: 10px; overflow: hidden; height: 15px; }
.prog-bar  { height: 100%;
  background: linear-gradient(90deg, var(--green), var(--gold));
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center; }
.prog-txt  { color: #fff; font-size: .65rem; font-weight: 700; }

/* ─ TROPHY ─ */
.trophy {
  background: linear-gradient(145deg,#fffdf0,#fdf3d0);
  border: 2px solid rgba(201,152,42,.22);
  border-radius: 18px; padding: 18px 12px;
  text-align: center; position: relative;
  box-shadow: 0 5px 24px rgba(201,152,42,.12);
  transition: transform .25s; overflow: hidden;
}
.trophy::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 4px;
  background: linear-gradient(90deg,var(--gold),var(--gold2),var(--gold));
}
.trophy:hover { transform: translateY(-5px); }
.trophy-medal { font-size: 2.4rem; display: block; margin-bottom: 5px; }
.trophy-name  { font-size: .94rem; font-weight: 700; color: var(--text); margin: 4px 0 2px; }
.trophy-sub   { font-size: .72rem; color: var(--gray); }
.trophy-score {
  display: inline-block;
  background: linear-gradient(135deg,var(--green),var(--green2));
  color: #fff; border-radius: 20px;
  padding: 3px 14px; font-size: .78rem; font-weight: 700;
  margin-top: 7px;
}

/* ─ INPUTS ─ */
.stTextInput > div > div > input,
.stTextArea textarea,
.stNumberInput > div > div > input,
.stDateInput > div > div > input,
.stTimeInput > div > div > input {
  border-radius: var(--rads) !important;
  border: 1.5px solid var(--border) !important;
  direction: rtl !important;
  font-size: .85rem !important;
}

/* ─ TABS ─ */
.stTabs [data-baseweb="tab-list"] {
  background: var(--pale) !important;
  border-radius: var(--rad) !important;
  padding: 4px !important; gap: 4px !important;
}
.stTabs [data-baseweb="tab"] {
  border-radius: var(--rads) !important;
  border: none !important;
  color: var(--gray) !important;
  font-weight: 700 !important;
  font-size: .80rem !important;
}
.stTabs [aria-selected="true"] {
  background: linear-gradient(135deg, var(--green), var(--green2)) !important;
  color: #fff !important;
  box-shadow: 0 2px 8px rgba(10,92,60,.25) !important;
}

/* ─ ALERTS ─ */
.stSuccess > div { background: #f0fdf4 !important; border-color: #86efac !important; border-radius: var(--rads) !important; }
.stError   > div { background: #fff1f2 !important; border-color: #fca5a5 !important; border-radius: var(--rads) !important; }
.stWarning > div { background: #fffbeb !important; border-color: #fcd34d !important; border-radius: var(--rads) !important; }
.stInfo    > div { background: #f0f9ff !important; border-color: #93c5fd !important; border-radius: var(--rads) !important; }

/* ─ DATAFRAME ─ */
.stDataFrame { border-radius: var(--rads) !important; overflow: hidden !important; box-shadow: var(--sh) !important; }

/* ─ EXPANDER ─ */
.streamlit-expanderHeader {
  background: linear-gradient(135deg,#f0f8f4,#e4f2eb) !important;
  border-radius: var(--rads) !important;
  border: 1px solid rgba(10,92,60,.12) !important;
}

/* ─ DIVIDER ─ */
hr { border: none; border-top: 1px solid var(--border); margin: 14px 0; }

/* ─ BOTTOM PAD ─ */
.bottom-pad { height: 80px; }

/* ─ LOGIN BOX ─ */
.login-box {
  background: #fff; border-radius: 20px;
  padding: 30px 24px; max-width: 400px;
  margin: 0 auto;
  box-shadow: 0 20px 60px rgba(0,0,0,.20);
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────
# STEP 11: UI HELPERS
# ─────────────────────────────────────────
def section(icon, title, sub=""):
    s = f'<div class="sh"><span class="sh-ico">{icon}</span><div>'
    s += f'<div class="sh-title">{title}</div>'
    if sub:
        s += f'<div class="sh-sub">{sub}</div>'
    s += '</div></div>'
    st.markdown(s, unsafe_allow_html=True)


def chip(grade):
    cls = {
        "ممتاز": "cn", "جید جداً": "cp", "جید": "cb",
        "مقبول": "cy", "ناقص": "co", "کمزور": "co",
        "ناکام": "cr", "غیر حاضر": "cg", "رخصت": "cg",
    }.get(grade, "cg")
    return f"<span class='chip {cls}'>{grade}</span>"


def metric_row(items):
    """items = list of (icon, value, label)"""
    cols = "".join(
        f'<div class="mc"><span class="mc-ico">{ico}</span>'
        f'<div class="mc-val">{val}</div>'
        f'<div class="mc-lbl">{lbl}</div></div>'
        for ico, val, lbl in items
    )
    st.markdown(f'<div class="mets">{cols}</div>', unsafe_allow_html=True)


def progress_bar(value, total, label=""):
    pct = min(int((value / (total or 1)) * 100), 100)
    st.markdown(
        f'<div style="font-size:.80rem;font-weight:700;color:#0a5c3c;margin-bottom:4px">'
        f'{label}: {value}/{total}</div>'
        f'<div class="prog-wrap"><div class="prog-bar" style="width:{pct}%">'
        f'<span class="prog-txt">{pct}%</span></div></div>'
        f'<div style="font-size:.68rem;color:#6b7280;margin-top:3px">'
        f'{total - value} باقی</div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────
# STEP 12: LOGIN
# ─────────────────────────────────────────
if not st.session_state.logged_in:
    st.markdown("<br>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown("""
        <div class="login-box">
          <div style="text-align:center;margin-bottom:18px">
            <span style="font-size:3.5rem">🕌</span>
            <h2 style="color:#0a5c3c;margin:6px 0 2px;font-size:1.2rem">
              جامعہ ملیہ اسلامیہ</h2>
            <p style="color:#c9982a;margin:0;font-size:.80rem">
              فیصل آباد — Smart ERP v5.0</p>
          </div>
        </div>""", unsafe_allow_html=True)

        with st.form("login_form"):
            u = st.text_input("👤 صارف نام")
            p = st.text_input("🔑 پاسورڈ", type="password")
            btn = st.form_submit_button("▶  لاگ ان کریں", use_container_width=True)

        if btn:
            if u.strip() and p:
                user = query(
                    "SELECT * FROM users WHERE username=? AND is_active=1",
                    (u.strip(),), one=True
                )
                if user and verify_password(p, user["password"]):
                    st.session_state.logged_in = True
                    st.session_state.username  = u.strip()
                    st.session_state.role      = user["role"]
                    st.session_state.page      = "home"
                    IS_ADMIN = user["role"] == "admin"
                    log_action(u.strip(), "Login")
                    st.rerun()
                else:
                    st.error("❌ غلط نام یا پاسورڈ")
            else:
                st.warning("نام اور پاسورڈ ضروری ہیں")

        st.caption("🔒 ڈیفالٹ: admin / jamia123")
    st.stop()

# ─────────────────────────────────────────
# STEP 13: TOP BAR (logged in)
# ─────────────────────────────────────────
IS_ADMIN = st.session_state.role == "admin"

st.markdown(
    f'<div class="topbar">'
    f'<div class="tb-left">'
    f'<span class="tb-icon">🕌</span>'
    f'<div><div class="tb-name">جامعہ ملیہ اسلامیہ فیصل آباد</div>'
    f'<div class="tb-sub">Smart ERP v5.0</div></div>'
    f'</div>'
    f'<div class="tb-user">'
    f'{"🛡️ ایڈمن" if IS_ADMIN else "👩‍🏫 استاد"} — {st.session_state.username}'
    f'</div></div>',
    unsafe_allow_html=True,
)

st.markdown('<div class="mw">', unsafe_allow_html=True)

# ─────────────────────────────────────────
# STEP 14: NAVIGATION
# ─────────────────────────────────────────
if IS_ADMIN:
    NAV = [
        ("home",    "📊", "ڈیش بورڈ"),
        ("daily",   "📋", "یومیہ رپورٹ"),
        ("exams",   "🎓", "امتحانات"),
        ("result",  "📜", "رزلٹ"),
        ("para",    "📖", "پارہ رپورٹ"),
        ("t_att_a", "🕒", "حاضری"),
        ("leaves",  "🏛️", "رخصت"),
        ("users",   "👥", "یوزرز"),
        ("timetab", "📚", "ٹائم ٹیبل"),
        ("monitor", "🔍", "نگرانی"),
        ("notifs",  "📢", "اعلانات"),
        ("best",    "🏆", "بہترین"),
        ("pw",      "🔑", "پاسورڈ"),
        ("backup",  "⚙️", "بیک اپ"),
    ]
else:
    NAV = [
        ("home",   "🏠", "مرکزی"),
        ("entry",  "📝", "سبق"),
        ("t_exam", "🎓", "امتحان"),
        ("t_lv",   "📩", "رخصت"),
        ("t_att",  "🕒", "حاضری"),
        ("t_tt",   "📚", "ٹائم ٹیبل"),
        ("notifs", "📢", "اعلانات"),
        ("pw",     "🔑", "پاسورڈ"),
    ]

PER_ROW = 7 if IS_ADMIN else 4
pg = st.session_state.page

rows_nav = [NAV[i:i+PER_ROW] for i in range(0, len(NAV), PER_ROW)]
for row in rows_nav:
    cols = st.columns(len(row))
    for col, (pid, ico, lbl) in zip(cols, row):
        with col:
            label = f"{ico}\n{lbl}"
            if st.button(label, key=f"nb_{pid}", use_container_width=True):
                st.session_state.page   = pid
                st.session_state.sel_stu = None
                st.rerun()

# Logout
_, lout_col = st.columns([6, 1])
with lout_col:
    if st.button("🚪 آؤٹ", use_container_width=True):
        log_action(st.session_state.username, "Logout")
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

st.markdown("<hr>", unsafe_allow_html=True)
pg = st.session_state.page   # refresh after nav

# ═══════════════════════════════════════════════════════
#  PAGES
# ═══════════════════════════════════════════════════════

# ───────────────────────────────
# ADMIN DASHBOARD
# ───────────────────────────────
if pg == "home" and IS_ADMIN:
    section("📊", "ایڈمن ڈیش بورڈ", "جامعہ کا مکمل جائزہ")

    ts = scalar("SELECT COUNT(*) FROM students WHERE is_active=1")
    tt = scalar("SELECT COUNT(*) FROM users WHERE role='teacher' AND is_active=1")
    ta = scalar("SELECT COUNT(*) FROM teacher_attendance WHERE att_date=?", (str(date.today()),))
    hr = (scalar("SELECT COUNT(*) FROM hifz_records") +
          scalar("SELECT COUNT(*) FROM qaida_records") +
          scalar("SELECT COUNT(*) FROM general_records"))
    pl = scalar("SELECT COUNT(*) FROM leave_requests WHERE status='پینڈنگ'")
    pe = scalar("SELECT COUNT(*) FROM exams WHERE status='پینڈنگ'")

    metric_row([
        ("👨‍🎓", ts, "کل طلباء"),
        ("👩‍🏫", tt, "اساتذہ"),
        ("✅",   ta, "آج حاضر"),
        ("📋",   hr, "کل ریکارڈ"),
    ])

    if pl: st.warning(f"⏳ {pl} رخصت درخواستیں پینڈنگ")
    if pe: st.info(f"🎓 {pe} امتحان پینڈنگ")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("<div class='pc'>", unsafe_allow_html=True)
        st.markdown("**📅 آج کی اساتذہ حاضری**")
        rows = query(
            "SELECT username AS استاد, arrival AS آمد, departure AS رخصت "
            "FROM teacher_attendance WHERE att_date=?",
            (str(date.today()),)
        )
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.caption("ابھی کوئی حاضری درج نہیں")
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown("<div class='pc'>", unsafe_allow_html=True)
        st.markdown("**📊 شعبہ وار طلباء**")
        dd = query(
            "SELECT dept, COUNT(*) AS cnt FROM students WHERE is_active=1 GROUP BY dept"
        )
        for d in dd:
            pct = min(int((d["cnt"] / (ts or 1)) * 100), 100)
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;'
                f'font-size:.80rem;margin-bottom:2px">'
                f'<b>{d["dept"]}</b><span style="color:#0a5c3c">{d["cnt"]}</span></div>'
                f'<div class="prog-wrap"><div class="prog-bar" style="width:{pct}%">'
                f'<span class="prog-txt">{pct}%</span></div></div>',
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

# ───────────────────────────────
# DAILY REPORT
# ───────────────────────────────
elif pg == "daily" and IS_ADMIN:
    section("📋", "یومیہ تعلیمی رپورٹ")

    c1, c2, c3, c4 = st.columns(4)
    d1 = c1.date_input("از", date.today().replace(day=1))
    d2 = c2.date_input("تا", date.today())
    ds = c3.selectbox("شعبہ", ["تمام"] + DEPTS)
    tlist = ["تمام"] + [r["username"] for r in query(
        "SELECT username FROM users WHERE role='teacher' AND is_active=1")]
    ts2 = c4.selectbox("استاد", tlist)

    combined = []
    tf = "" if ts2 == "تمام" else f" AND h.teacher='{ts2}'"
    tf2 = "" if ts2 == "تمام" else f" AND q.teacher='{ts2}'"
    tf3 = "" if ts2 == "تمام" else f" AND g.teacher='{ts2}'"
    df3 = "" if ds == "تمام" else f" AND g.dept='{ds}'"

    if ds in ("تمام", "حفظ"):
        rows = query(
            f"SELECT h.id, h.rec_date AS تاریخ, s.name AS نام, s.father_name AS والد, "
            f"s.roll_no AS رول, h.teacher AS استاد, 'حفظ' AS شعبہ, "
            f"h.sabaq AS سبق, h.sabaq_lines AS ستر, "
            f"h.sq_text AS سبقی, h.sq_mistakes AS 'سبقی غلطی', "
            f"h.manzil_text AS منزل, h.manzil_mistakes AS 'منزل غلطی', "
            f"h.attendance AS حاضری, h.cleanliness AS صفائی, h.grade AS درجہ "
            f"FROM hifz_records h JOIN students s ON h.student_id=s.id "
            f"WHERE h.rec_date BETWEEN ? AND ?{tf} ORDER BY h.rec_date DESC",
            (str(d1), str(d2))
        )
        combined.extend(rows or [])

    if ds in ("تمام", "قاعدہ"):
        rows = query(
            f"SELECT q.id, q.rec_date AS تاریخ, s.name AS نام, s.father_name AS والد, "
            f"s.roll_no AS رول, q.teacher AS استاد, 'قاعدہ' AS شعبہ, "
            f"q.lesson_no AS سبق, q.total_lines AS لائنیں, "
            f"'' AS سبقی, 0 AS 'سبقی غلطی', '' AS منزل, 0 AS 'منزل غلطی', "
            f"q.attendance AS حاضری, q.cleanliness AS صفائی, '' AS درجہ "
            f"FROM qaida_records q JOIN students s ON q.student_id=s.id "
            f"WHERE q.rec_date BETWEEN ? AND ?{tf2} ORDER BY q.rec_date DESC",
            (str(d1), str(d2))
        )
        combined.extend(rows or [])

    if ds in ("تمام", "درسِ نظامی", "عصری تعلیم"):
        rows = query(
            f"SELECT g.id, g.rec_date AS تاریخ, s.name AS نام, s.father_name AS والد, "
            f"s.roll_no AS رول, g.teacher AS استاد, g.dept AS شعبہ, "
            f"g.subject AS سبق, 0 AS ستر, '' AS سبقی, 0 AS 'سبقی غلطی', "
            f"'' AS منزل, 0 AS 'منزل غلطی', "
            f"g.attendance AS حاضری, g.cleanliness AS صفائی, g.performance AS درجہ "
            f"FROM general_records g JOIN students s ON g.student_id=s.id "
            f"WHERE g.rec_date BETWEEN ? AND ?{df3}{tf3} ORDER BY g.rec_date DESC",
            (str(d1), str(d2))
        )
        combined.extend(rows or [])

    if combined:
        df = pd.DataFrame(combined)
        st.success(f"✅ کل {len(df)} ریکارڈ")
        st.dataframe(df, use_container_width=True, hide_index=True)
        if IS_ADMIN:
            with st.expander("🗑️ ریکارڈ حذف کریں"):
                with st.form("del_rec_form"):
                    rc1, rc2 = st.columns(2)
                    del_tbl = rc1.selectbox(
                        "ٹیبل",
                        ["hifz_records", "qaida_records", "general_records"],
                    )
                    del_id = rc2.number_input("ریکارڈ ID", min_value=1, step=1)
                    if st.form_submit_button("🗑️ حذف کریں"):
                        execute(f"DELETE FROM {del_tbl} WHERE id=?", (int(del_id),))
                        st.success("✅ حذف!")
                        st.rerun()
        c1, c2 = st.columns(2)
        c1.download_button("📥 CSV", df_csv(df), "daily.csv", "text/csv")
        c2.download_button(
            "📥 HTML رپورٹ",
            make_html_report(df, "یومیہ تعلیمی رپورٹ", f"{d1} تا {d2}"),
            "daily.html", "text/html",
        )
    else:
        st.info("اس مدت میں کوئی ریکارڈ نہیں")

# ───────────────────────────────
# EXAMS
# ───────────────────────────────
elif pg == "exams" and IS_ADMIN:
    section("🎓", "امتحانی نظام")
    tab1, tab2 = st.tabs(["⏳ پینڈنگ", "✅ مکمل"])

    with tab1:
        pend = query(
            "SELECT e.*, s.name, s.father_name, s.roll_no "
            "FROM exams e JOIN students s ON e.student_id=s.id "
            "WHERE e.status='پینڈنگ' ORDER BY e.created_at DESC"
        )
        if not pend:
            st.success("✅ کوئی پینڈنگ امتحان نہیں")
        for ex in (pend or []):
            with st.expander(
                f"👤 {ex.get('name','')} ولد {ex.get('father_name','')} "
                f"| {ex.get('dept','')} | {ex.get('exam_type','')}"
            ):
                c1, c2, c3 = st.columns(3)
                c1.info(f"📅 شروع: {ex.get('start_date','—')}")
                c2.info(f"📅 ختم: {ex.get('end_date','—')}")
                c3.info(f"🗓️ دن: {ex.get('total_days','—')}")
                if ex.get("from_para"):
                    st.info(f"📖 پارہ {ex['from_para']} تا {ex['to_para']}")
                if ex.get("book_name"):
                    st.info(f"📚 {ex['book_name']} | {ex.get('amount_read','')}")

                qcols = st.columns(5)
                qs = [
                    qcols[i].number_input(f"س{i+1}", 0, 20, 0, key=f"q{i}_{ex['id']}")
                    for i in range(5)
                ]
                total = sum(qs)
                g = exam_grade(total)
                st.markdown(
                    f"**کل:** {total}/100 &nbsp; {chip(g)}",
                    unsafe_allow_html=True,
                )
                bc1, bc2 = st.columns(2)
                if bc1.button("✅ نتیجہ محفوظ", key=f"ex_save_{ex['id']}"):
                    execute(
                        "UPDATE exams SET q1=?,q2=?,q3=?,q4=?,q5=?,total=?,"
                        "grade=?,status='مکمل',end_date=? WHERE id=?",
                        (*qs, total, g, str(date.today()), ex["id"]),
                    )
                    if g != "ناکام":
                        sid = ex["student_id"]
                        fp = ex.get("from_para", 0) or 0
                        tp = ex.get("to_para", 0) or 0
                        if fp > 0:
                            for para in range(int(fp), int(tp) + 1):
                                if not query(
                                    "SELECT id FROM passed_paras WHERE student_id=? AND para_no=?",
                                    (sid, para), one=True,
                                ):
                                    execute(
                                        "INSERT INTO passed_paras"
                                        "(student_id,para_no,passed_date,exam_type,grade,marks)"
                                        "VALUES(?,?,?,?,?,?)",
                                        (sid, para, str(date.today()),
                                         ex.get("exam_type",""), g, total),
                                    )
                        bk = ex.get("book_name", "")
                        if bk:
                            if not query(
                                "SELECT id FROM passed_paras WHERE student_id=? AND book_name=?",
                                (sid, bk), one=True,
                            ):
                                execute(
                                    "INSERT INTO passed_paras"
                                    "(student_id,book_name,passed_date,exam_type,grade,marks)"
                                    "VALUES(?,?,?,?,?,?)",
                                    (sid, bk, str(date.today()),
                                     ex.get("exam_type",""), g, total),
                                )
                    log_action(st.session_state.username, "Exam Cleared", ex["id"])
                    st.success("✅ محفوظ!")
                    st.rerun()
                if bc2.button("🗑️ حذف", key=f"ex_del_{ex['id']}"):
                    execute("DELETE FROM exams WHERE id=?", (ex["id"],))
                    st.rerun()

    with tab2:
        done = query(
            "SELECT e.id, s.name AS نام, s.father_name AS والد, "
            "e.dept AS شعبہ, e.exam_type AS امتحان, "
            "e.total AS نمبر, e.grade AS گریڈ, e.end_date AS تاریخ "
            "FROM exams e JOIN students s ON e.student_id=s.id "
            "WHERE e.status='مکمل' ORDER BY e.end_date DESC"
        )
        if done:
            df = pd.DataFrame(done)
            st.dataframe(df, use_container_width=True, hide_index=True)
            with st.expander("🗑️ حذف کریں"):
                with st.form("del_exam_f"):
                    di = st.number_input("ID", min_value=1, step=1)
                    if st.form_submit_button("🗑️ حذف"):
                        execute("DELETE FROM exams WHERE id=?", (int(di),))
                        st.success("✅")
                        st.rerun()
            st.download_button("📥 CSV", df_csv(df), "exams.csv")
        else:
            st.info("کوئی مکمل امتحان نہیں")

# ───────────────────────────────
# RESULT CARD
# ───────────────────────────────
elif pg == "result" and IS_ADMIN:
    section("📜", "ماہانہ رزلٹ کارڈ")
    studs = query(
        "SELECT id,name,father_name,roll_no,dept FROM students "
        "WHERE is_active=1 ORDER BY name"
    )
    if not studs:
        st.warning("کوئی طالب علم نہیں")
    else:
        names = [f"{s['name']} ولد {s['father_name']} ({s['dept']})" for s in studs]
        c1, c2, c3 = st.columns([3, 1, 1])
        idx = c1.selectbox("طالب علم", range(len(names)), format_func=lambda i: names[i])
        s = studs[idx]
        d1 = c2.date_input("از", date.today().replace(day=1))
        d2 = c3.date_input("تا", date.today())

        if s["dept"] == "حفظ":
            rows = query(
                "SELECT rec_date AS تاریخ, attendance AS حاضری, "
                "sabaq AS سبق, sabaq_lines AS ستر, "
                "sq_text AS سبقی, sq_mistakes AS 'سبقی غلطی', "
                "manzil_text AS منزل, manzil_mistakes AS 'منزل غلطی', "
                "cleanliness AS صفائی, grade AS درجہ "
                "FROM hifz_records WHERE student_id=? AND rec_date BETWEEN ? AND ? "
                "ORDER BY rec_date",
                (s["id"], str(d1), str(d2))
            )
        elif s["dept"] == "قاعدہ":
            rows = query(
                "SELECT rec_date AS تاریخ, attendance AS حاضری, "
                "lesson_no AS سبق, total_lines AS لائنیں, "
                "cleanliness AS صفائی, note AS نوٹ "
                "FROM qaida_records WHERE student_id=? AND rec_date BETWEEN ? AND ? "
                "ORDER BY rec_date",
                (s["id"], str(d1), str(d2))
            )
        else:
            rows = query(
                "SELECT rec_date AS تاریخ, attendance AS حاضری, "
                "subject AS مضمون, lesson AS سبق, "
                "performance AS کارکردگی, cleanliness AS صفائی "
                "FROM general_records WHERE student_id=? AND dept=? "
                "AND rec_date BETWEEN ? AND ? ORDER BY rec_date",
                (s["id"], s["dept"], str(d1), str(d2))
            )

        if rows:
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
            sub = f"{s['name']} ولد {s['father_name']} | {d1} تا {d2}"
            c1, c2 = st.columns(2)
            c1.download_button(
                "📥 HTML رپورٹ",
                make_html_report(df, "ماہانہ رزلٹ کارڈ", sub),
                f"result_{s['name']}.html", "text/html",
            )
            c2.download_button("📥 CSV", df_csv(df), f"result_{s['name']}.csv")
        else:
            st.info("اس مدت میں کوئی ریکارڈ نہیں")

# ───────────────────────────────
# PARA REPORT
# ───────────────────────────────
elif pg == "para" and IS_ADMIN:
    section("📖", "پارہ تعلیمی رپورٹ")
    studs = query(
        "SELECT id,name,father_name FROM students "
        "WHERE dept='حفظ' AND is_active=1 ORDER BY name"
    )
    if not studs:
        st.warning("کوئی حفظ کا طالب علم نہیں")
    else:
        names = [f"{s['name']} ولد {s['father_name']}" for s in studs]
        idx = st.selectbox("طالب علم", range(len(names)), format_func=lambda i: names[i])
        s = studs[idx]
        passed = query(
            "SELECT id, para_no AS 'پارہ نمبر', passed_date AS 'تاریخ', "
            "exam_type AS امتحان, grade AS گریڈ, marks AS نمبر "
            "FROM passed_paras WHERE student_id=? AND para_no>0 ORDER BY para_no",
            (s["id"],)
        )
        cnt = len(passed or [])
        progress_bar(cnt, 30, "قرآن مجید کی پیشرفت (پارے)")
        if passed:
            df = pd.DataFrame(passed)
            st.dataframe(df, use_container_width=True, hide_index=True)
            with st.expander("🗑️ پارہ حذف کریں"):
                with st.form("del_para_f"):
                    di = st.number_input("ID", min_value=1, step=1)
                    if st.form_submit_button("🗑️ حذف"):
                        execute("DELETE FROM passed_paras WHERE id=?", (int(di),))
                        st.success("✅")
                        st.rerun()
            st.download_button(
                "📥 رپورٹ",
                make_html_report(df, "پارہ تعلیمی رپورٹ",
                                 f"{s['name']} ولد {s['father_name']}"),
                f"para_{s['name']}.html", "text/html",
            )
        else:
            st.info("کوئی پاس شدہ پارہ نہیں")

# ───────────────────────────────
# TEACHER ATTENDANCE ADMIN
# ───────────────────────────────
elif pg == "t_att_a" and IS_ADMIN:
    section("🕒", "اساتذہ حاضری")
    tab1, tab2 = st.tabs(["📋 ریکارڈ دیکھیں", "✏️ درج / ترمیم"])

    with tab1:
        c1, c2, c3 = st.columns(3)
        fd1 = c1.date_input("از", date.today().replace(day=1))
        fd2 = c2.date_input("تا", date.today())
        tlist = ["تمام"] + [r["username"] for r in query(
            "SELECT username FROM users WHERE role='teacher' AND is_active=1")]
        ft = c3.selectbox("استاد", tlist)
        tf = "" if ft == "تمام" else f" AND username='{ft}'"
        rows = query(
            f"SELECT id, username AS استاد, att_date AS تاریخ, "
            f"arrival AS آمد, departure AS رخصت "
            f"FROM teacher_attendance WHERE att_date BETWEEN ? AND ?{tf} "
            f"ORDER BY att_date DESC",
            (str(fd1), str(fd2))
        )
        if rows:
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
            with st.expander("🗑️ حذف"):
                with st.form("del_att_f"):
                    di = st.number_input("ID", min_value=1, step=1)
                    if st.form_submit_button("🗑️ حذف"):
                        execute("DELETE FROM teacher_attendance WHERE id=?", (int(di),))
                        st.success("✅")
                        st.rerun()
            st.download_button("📥 CSV", df_csv(df), "att.csv")
        else:
            st.info("کوئی ریکارڈ نہیں")

    with tab2:
        with st.form("admin_att_f"):
            c1, c2, c3, c4 = st.columns(4)
            tl2 = [r["username"] for r in query(
                "SELECT username FROM users WHERE role='teacher' AND is_active=1")]
            at = c1.selectbox("استاد", tl2) if tl2 else c1.text_input("استاد")
            ad = c2.date_input("تاریخ", date.today())
            arr = c3.text_input("آمد", "09:00 AM")
            dep = c4.text_input("رخصت", "03:00 PM")
            if st.form_submit_button("💾 محفوظ کریں"):
                ex = query(
                    "SELECT id FROM teacher_attendance WHERE username=? AND att_date=?",
                    (at, str(ad)), one=True,
                )
                if ex:
                    execute(
                        "UPDATE teacher_attendance SET arrival=?,departure=? "
                        "WHERE username=? AND att_date=?",
                        (arr, dep, at, str(ad)),
                    )
                else:
                    try:
                        execute(
                            "INSERT INTO teacher_attendance(username,att_date,arrival,departure) "
                            "VALUES(?,?,?,?)",
                            (at, str(ad), arr, dep),
                        )
                    except:
                        pass
                st.success("✅ محفوظ!")
                st.rerun()

# ───────────────────────────────
# LEAVES ADMIN
# ───────────────────────────────
elif pg == "leaves" and IS_ADMIN:
    section("🏛️", "رخصت کی منظوری")
    tab1, tab2 = st.tabs(["⏳ پینڈنگ", "📜 تمام"])

    with tab1:
        pend = query(
            "SELECT * FROM leave_requests WHERE status='پینڈنگ' "
            "ORDER BY created_at DESC"
        )
        if not pend:
            st.success("✅ کوئی پینڈنگ درخواست نہیں")
        for lv in (pend or []):
            st.markdown(
                f'<div class="lv-card">'
                f'<div style="display:flex;justify-content:space-between">'
                f'<b>👤 {lv["username"]}</b>&nbsp;'
                f'<span class="sp">{lv["leave_type"]}</span>'
                f'<span style="font-size:.75rem;color:#5a6e64">'
                f'📅 {lv["start_date"]} | {lv["days"]} دن</span></div>'
                f'<p style="font-size:.78rem;color:#374151;margin:5px 0 0">'
                f'وجہ: {lv["reason"][:120]}</p></div>',
                unsafe_allow_html=True,
            )
            c1, c2, c3 = st.columns(3)
            if c1.button("✅ منظور", key=f"ap_{lv['id']}", use_container_width=True):
                execute("UPDATE leave_requests SET status='منظور' WHERE id=?", (lv["id"],))
                st.rerun()
            if c2.button("❌ مسترد", key=f"rj_{lv['id']}", use_container_width=True):
                execute("UPDATE leave_requests SET status='مسترد' WHERE id=?", (lv["id"],))
                st.rerun()
            if c3.button("🗑️ حذف", key=f"dl_{lv['id']}", use_container_width=True):
                execute("DELETE FROM leave_requests WHERE id=?", (lv["id"],))
                st.rerun()

    with tab2:
        all_lv = query(
            "SELECT id, username AS استاد, leave_type AS نوعیت, "
            "start_date AS تاریخ, days AS دن, status AS حالت "
            "FROM leave_requests ORDER BY created_at DESC"
        )
        if all_lv:
            df = pd.DataFrame(all_lv)
            st.dataframe(df, use_container_width=True, hide_index=True)
            with st.expander("🗑️ حذف"):
                with st.form("del_lv_f"):
                    di = st.number_input("ID", min_value=1, step=1)
                    if st.form_submit_button("🗑️ حذف"):
                        execute("DELETE FROM leave_requests WHERE id=?", (int(di),))
                        st.success("✅")
                        st.rerun()
            st.download_button("📥 CSV", df_csv(df), "leaves.csv")

# ───────────────────────────────
# USER MANAGEMENT
# ───────────────────────────────
elif pg == "users" and IS_ADMIN:
    section("👥", "یوزر مینجمنٹ")
    tab1, tab2 = st.tabs(["👩‍🏫 اساتذہ", "👨‍🎓 طلبہ"])

    with tab1:
        rows = query(
            "SELECT id, username AS نام, dept AS شعبہ, phone AS فون, "
            "id_card AS شناختی, joining_date AS شمولیت, is_active AS فعال "
            "FROM users WHERE role='teacher' ORDER BY username"
        )
        if rows:
            df = pd.DataFrame(rows)
            edited = st.data_editor(
                df, use_container_width=True,
                num_rows="dynamic", key="te", hide_index=True,
            )
            if st.button("💾 اساتذہ کی تبدیلیاں محفوظ کریں"):
                for _, row in edited.iterrows():
                    if pd.notna(row.get("id")):
                        execute(
                            "UPDATE users SET dept=?,phone=?,id_card=?,"
                            "joining_date=?,is_active=? WHERE id=?",
                            (str(row.get("شعبہ", "")),
                             str(row.get("فون", "")),
                             str(row.get("شناختی", "")),
                             str(row.get("شمولیت", "")),
                             int(row.get("فعال", 1)),
                             int(row["id"])),
                        )
                st.success("✅ محفوظ!")
                st.rerun()

        with st.expander("➕ نیا استاد رجسٹر کریں"):
            with st.form("add_t_f"):
                c1, c2 = st.columns(2)
                tn  = c1.text_input("نام*")
                tp  = c2.text_input("پاسورڈ*", type="password")
                td  = c1.selectbox("شعبہ", DEPTS)
                tph = c2.text_input("فون")
                tic = c1.text_input("شناختی کارڈ")
                tjd = c2.date_input("شمولیت", date.today())
                if st.form_submit_button("✅ رجسٹر کریں"):
                    if tn.strip() and tp:
                        try:
                            execute(
                                "INSERT INTO users(username,password,role,dept,phone,"
                                "id_card,joining_date) VALUES(?,?,?,?,?,?,?)",
                                (tn.strip(), make_hash(tp), "teacher",
                                 td, tph, tic, str(tjd)),
                            )
                            log_action(st.session_state.username, "Teacher Added", tn)
                            st.success(f"✅ {tn} رجسٹر!")
                            st.rerun()
                        except Exception as e:
                            st.error("یہ نام پہلے سے موجود ہے")
                    else:
                        st.error("نام اور پاسورڈ ضروری ہیں")

        with st.expander("🗑️ استاد حذف کریں"):
            with st.form("del_t_f"):
                di = st.number_input("استاد ID", min_value=1, step=1)
                if st.form_submit_button("🗑️ حذف کریں"):
                    execute(
                        "DELETE FROM users WHERE id=? AND role='teacher'",
                        (int(di),),
                    )
                    st.success("✅ حذف!")
                    st.rerun()

    with tab2:
        rows = query(
            "SELECT id, name AS نام, father_name AS والد, roll_no AS رول, "
            "dept AS شعبہ, teacher AS استاد, phone AS فون, is_active AS فعال "
            "FROM students ORDER BY name"
        )
        if rows:
            df = pd.DataFrame(rows)
            edited = st.data_editor(
                df, use_container_width=True,
                num_rows="dynamic", key="se", hide_index=True,
            )
            if st.button("💾 طلبہ کی تبدیلیاں محفوظ کریں"):
                for _, row in edited.iterrows():
                    if pd.notna(row.get("id")):
                        execute(
                            "UPDATE students SET name=?,father_name=?,roll_no=?,"
                            "dept=?,teacher=?,phone=?,is_active=? WHERE id=?",
                            (str(row.get("نام", "")),
                             str(row.get("والد", "")),
                             str(row.get("رول", "")),
                             str(row.get("شعبہ", "")),
                             str(row.get("استاد", "")),
                             str(row.get("فون", "")),
                             int(row.get("فعال", 1)),
                             int(row["id"])),
                        )
                st.success("✅ محفوظ!")
                st.rerun()

        with st.expander("➕ نیا طالب علم داخل کریں"):
            with st.form("add_s_f"):
                c1, c2 = st.columns(2)
                sn   = c1.text_input("نام*")
                sf   = c2.text_input("والد کا نام*")
                sm   = c1.text_input("والدہ کا نام")
                sr   = c2.text_input("رول نمبر")
                sd   = c1.date_input("تاریخ پیدائش", date.today() - timedelta(days=3650))
                sa   = c2.date_input("تاریخ داخلہ", date.today())
                sdept = c1.selectbox("شعبہ*", DEPTS)
                tl   = [r["username"] for r in query(
                    "SELECT username FROM users WHERE role='teacher' AND is_active=1")]
                st_ = c2.selectbox("استاد*", tl) if tl else c2.text_input("استاد*")
                scl  = c1.text_input("کلاس")
                ssec = c2.text_input("سیکشن")
                sph  = c1.text_input("فون")
                sadr = st.text_area("پتہ")
                if st.form_submit_button("✅ داخلہ کریں"):
                    if sn.strip() and sf.strip():
                        execute(
                            "INSERT INTO students(name,father_name,mother_name,roll_no,"
                            "dob,admission_date,phone,address,teacher,dept,"
                            "class_name,section) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                            (sn.strip(), sf.strip(), sm, sr,
                             str(sd), str(sa), sph, sadr, st_, sdept, scl, ssec),
                        )
                        log_action(st.session_state.username, "Student Added", sn)
                        st.success(f"✅ {sn} داخل!")
                        st.rerun()
                    else:
                        st.error("نام اور والد کا نام ضروری ہیں")

        with st.expander("🗑️ طالب علم حذف کریں"):
            with st.form("del_s_f"):
                di = st.number_input("طالب علم ID", min_value=1, step=1)
                if st.form_submit_button("🗑️ حذف کریں"):
                    execute("DELETE FROM students WHERE id=?", (int(di),))
                    st.success("✅ حذف!")
                    st.rerun()

# ───────────────────────────────
# TIMETABLE
# ───────────────────────────────
elif pg == "timetab" and IS_ADMIN:
    section("📚", "ٹائم ٹیبل")
    tl = [r["username"] for r in query(
        "SELECT username FROM users WHERE role='teacher' AND is_active=1")]
    if not tl:
        st.warning("پہلے اساتذہ رجسٹر کریں")
    else:
        st_ = st.selectbox("استاد منتخب کریں", tl)
        tt = query(
            "SELECT id, day_name AS دن, period AS وقت, "
            "subject AS مضمون, room AS کمرہ "
            "FROM timetable WHERE teacher=? ORDER BY day_name,period",
            (st_,)
        )
        if tt:
            df = pd.DataFrame(tt)
            edited = st.data_editor(
                df, use_container_width=True, num_rows="dynamic",
                key="tte", hide_index=True,
            )
            c1, c2 = st.columns(2)
            if c1.button("💾 محفوظ کریں"):
                for _, row in edited.iterrows():
                    if pd.notna(row.get("id")):
                        execute(
                            "UPDATE timetable SET day_name=?,period=?,subject=?,room=? WHERE id=?",
                            (str(row.get("دن", "")), str(row.get("وقت", "")),
                             str(row.get("مضمون", "")), str(row.get("کمرہ", "")),
                             int(row["id"])),
                        )
                    elif pd.isna(row.get("id")) or not row.get("id"):
                        if str(row.get("دن", "")).strip():
                            execute(
                                "INSERT INTO timetable(teacher,day_name,period,subject,room) "
                                "VALUES(?,?,?,?,?)",
                                (st_, str(row.get("دن", "")), str(row.get("وقت", "")),
                                 str(row.get("مضمون", "")), str(row.get("کمرہ", ""))),
                            )
                st.success("✅ محفوظ!")
                st.rerun()
            if c2.button("🗑️ مکمل حذف کریں"):
                execute("DELETE FROM timetable WHERE teacher=?", (st_,))
                st.rerun()
        else:
            st.info("کوئی ٹائم ٹیبل نہیں")

        with st.expander("➕ نیا پیریڈ شامل کریں"):
            with st.form("add_per_f"):
                c1, c2, c3, c4 = st.columns(4)
                dn  = c1.selectbox("دن", DAYS_UR)
                per = c2.text_input("وقت", "08:00-09:00")
                sub = c3.text_input("مضمون")
                rm  = c4.text_input("کمرہ")
                if st.form_submit_button("➕ شامل کریں"):
                    execute(
                        "INSERT INTO timetable(teacher,day_name,period,subject,room) "
                        "VALUES(?,?,?,?,?)",
                        (st_, dn, per, sub, rm),
                    )
                    st.success("✅ شامل!")
                    st.rerun()

# ───────────────────────────────
# STAFF MONITORING
# ───────────────────────────────
elif pg == "monitor" and IS_ADMIN:
    section("🔍", "عملہ نگرانی")
    tab1, tab2 = st.tabs(["➕ نیا اندراج", "📜 ریکارڈ"])

    with tab1:
        tl = [r["username"] for r in query(
            "SELECT username FROM users WHERE role='teacher' AND is_active=1")]
        with st.form("mon_f"):
            c1, c2 = st.columns(2)
            stf = c1.selectbox("عملہ", tl) if tl else c1.text_input("عملہ")
            nd  = c2.date_input("تاریخ", date.today())
            nt  = c1.selectbox("نوعیت", ["یادداشت","شکایت","تنبیہ","تعریف","جائزہ"])
            ns  = c2.selectbox("حالت", ["زیر التواء","حل شدہ","زیر غور"])
            desc = st.text_area("تفصیل*", max_chars=1000)
            act  = st.text_area("کارروائی", max_chars=500)
            if st.form_submit_button("✅ محفوظ کریں"):
                if desc.strip():
                    execute(
                        "INSERT INTO staff_notes(staff,note_date,note_type,description,"
                        "action_taken,status,created_by) VALUES(?,?,?,?,?,?,?)",
                        (stf, str(nd), nt, desc, act, ns, st.session_state.username),
                    )
                    st.success("✅ محفوظ!")
                    st.rerun()
                else:
                    st.error("تفصیل ضروری ہے")

    with tab2:
        notes = query(
            "SELECT id, staff AS عملہ, note_date AS تاریخ, note_type AS نوعیت, "
            "description AS تفصیل, status AS حالت "
            "FROM staff_notes ORDER BY note_date DESC"
        )
        if notes:
            df = pd.DataFrame(notes)
            edited = st.data_editor(
                df, use_container_width=True, num_rows="dynamic",
                key="notes_e", hide_index=True,
            )
            if st.button("💾 تبدیلیاں محفوظ کریں"):
                for _, row in edited.iterrows():
                    if pd.notna(row.get("id")):
                        execute(
                            "UPDATE staff_notes SET status=? WHERE id=?",
                            (str(row.get("حالت", "")), int(row["id"])),
                        )
                st.success("✅")
                st.rerun()
            with st.expander("🗑️ حذف"):
                with st.form("del_note_f"):
                    di = st.number_input("ID", min_value=1, step=1)
                    if st.form_submit_button("🗑️ حذف"):
                        execute("DELETE FROM staff_notes WHERE id=?", (int(di),))
                        st.success("✅")
                        st.rerun()
            st.download_button("📥 CSV", df_csv(df), "notes.csv")
        else:
            st.info("کوئی ریکارڈ نہیں")

# ───────────────────────────────
# NOTIFICATIONS
# ───────────────────────────────
elif pg == "notifs":
    section("📢", "اعلانات")
    if IS_ADMIN:
        with st.expander("➕ نیا اعلان بھیجیں"):
            with st.form("nf_f"):
                t_ = st.text_input("عنوان*")
                m_ = st.text_area("پیغام*")
                tg = st.selectbox("وصول کنندہ", ["تمام","اساتذہ","طلبہ"])
                if st.form_submit_button("📤 بھیجیں"):
                    if t_.strip() and m_.strip():
                        execute(
                            "INSERT INTO notifications(title,message,target,created_by) "
                            "VALUES(?,?,?,?)",
                            (t_, m_, tg, st.session_state.username),
                        )
                        st.success("✅ بھیج دیا!")
                        st.rerun()
                    else:
                        st.error("عنوان اور پیغام ضروری ہیں")
        with st.expander("🗑️ اعلان حذف کریں"):
            with st.form("del_nf_f"):
                di = st.number_input("ID", min_value=1, step=1)
                if st.form_submit_button("🗑️ حذف"):
                    execute("DELETE FROM notifications WHERE id=?", (int(di),))
                    st.success("✅")
                    st.rerun()

    notifs = query(
        "SELECT id, title, message, target, created_by, created_at "
        "FROM notifications ORDER BY created_at DESC LIMIT 30"
    )
    if notifs:
        for n in notifs:
            st.markdown(
                f'<div class="nf-card">'
                f'<h5>🔔 {n["title"]}'
                f'<small style="font-weight:400"> ({n["target"]}) ID:{n["id"]}</small></h5>'
                f'<p>{n["message"]}</p>'
                f'<sm>از: {n["created_by"]} | {str(n["created_at"])[:16]}</sm>'
                f'</div>',
                unsafe_allow_html=True,
            )
    else:
        st.info("کوئی اعلان نہیں")

# ───────────────────────────────
# BEST STUDENTS
# ───────────────────────────────
elif pg == "best" and IS_ADMIN:
    section("🏆", "ماہانہ بہترین طلباء")
    c1, c2 = st.columns(2)
    mnth = c1.date_input("مہینہ", date.today().replace(day=1))
    df_f = c2.selectbox("شعبہ", ["تمام"] + DEPTS)
    d1 = mnth.replace(day=1)
    if mnth.month == 12:
        d2 = mnth.replace(year=mnth.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        d2 = mnth.replace(month=mnth.month + 1, day=1) - timedelta(days=1)

    dw = "" if df_f == "تمام" else f" AND dept='{df_f}'"
    studs = query(
        f"SELECT id,name,father_name,dept FROM students WHERE is_active=1{dw}"
    )
    scores = []
    for s in (studs or []):
        gs, cs = [], []
        if s["dept"] == "حفظ":
            recs = query(
                "SELECT attendance,sabaq_nagha,sq_nagha,manzil_nagha,"
                "sq_mistakes,manzil_mistakes,cleanliness "
                "FROM hifz_records WHERE student_id=? AND rec_date BETWEEN ? AND ?",
                (s["id"], str(d1), str(d2))
            )
            for r in (recs or []):
                g = hifz_grade(r["attendance"], r["sabaq_nagha"], r["sq_nagha"],
                               r["manzil_nagha"], r["sq_mistakes"], r["manzil_mistakes"])
                gm = {"ممتاز":100,"جید جداً":85,"جید":75,"مقبول":60,
                      "ناقص":40,"کمزور":25,"ناکام":10,"غیر حاضر":0,"رخصت":50}
                gs.append(gm.get(g, 0))
                if r.get("cleanliness"):
                    cs.append({"بہترین":3,"بہتر":2,"ناقص":1}.get(r["cleanliness"], 0))
        else:
            recs = query(
                "SELECT attendance,performance,cleanliness "
                "FROM general_records WHERE student_id=? AND rec_date BETWEEN ? AND ?",
                (s["id"], str(d1), str(d2))
            )
            for r in (recs or []):
                pm = {"بہت بہتر":90,"بہتر":80,"مناسب":65,"کمزور":45}
                att = r["attendance"]
                gs.append(
                    pm.get(r.get("performance",""), 70) if att == "حاضر"
                    else (50 if att == "رخصت" else 0)
                )
                if r.get("cleanliness"):
                    cs.append({"بہترین":3,"بہتر":2,"ناقص":1}.get(r["cleanliness"], 0))
        if gs:
            scores.append({
                "name": s["name"], "father": s["father_name"],
                "dept": s["dept"],
                "ga": round(sum(gs) / len(gs), 1),
                "ca": round(sum(cs) / len(cs), 2) if cs else 0,
                "days": len(gs),
            })

    if not scores:
        st.warning("اس مدت میں کوئی ریکارڈ نہیں")
    else:
        by_grade = sorted(scores, key=lambda x: x["ga"], reverse=True)
        by_clean = sorted(scores, key=lambda x: x["ca"], reverse=True)
        medals = ["🥇", "🥈", "🥉"]

        st.subheader("📚 تعلیمی کارکردگی")
        cols = st.columns(3)
        for col, st_, medal in zip(cols, by_grade[:3], medals):
            with col:
                st.markdown(
                    f'<div class="trophy">'
                    f'<span class="trophy-medal">{medal}</span>'
                    f'<div class="trophy-name">{st_["name"]}</div>'
                    f'<div class="trophy-sub">والد: {st_["father"]}</div>'
                    f'<div class="trophy-sub">🏫 {st_["dept"]} | {st_["days"]} دن</div>'
                    f'<div class="trophy-score">{st_["ga"]}%</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        st.markdown("<hr>", unsafe_allow_html=True)
        st.subheader("🧹 صفائی")
        cols2 = st.columns(3)
        for col, st_, medal in zip(cols2, by_clean[:3], medals):
            with col:
                cp = round((st_["ca"] / 3) * 100, 1)
                st.markdown(
                    f'<div class="trophy">'
                    f'<span class="trophy-medal">{medal}</span>'
                    f'<div class="trophy-name">{st_["name"]}</div>'
                    f'<div class="trophy-sub">والد: {st_["father"]}</div>'
                    f'<div class="trophy-sub">🏫 {st_["dept"]}</div>'
                    f'<div class="trophy-score">🧹 {cp}%</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        with st.expander("📊 تمام طلباء"):
            df_a = pd.DataFrame(scores)
            df_a.columns = ["نام","والد","شعبہ","تعلیمی %","صفائی","دن"]
            st.dataframe(
                df_a.sort_values("تعلیمی %", ascending=False),
                use_container_width=True, hide_index=True,
            )
            st.download_button("📥 CSV", df_csv(df_a), "best.csv")

# ───────────────────────────────
# PASSWORD
# ───────────────────────────────
elif pg == "pw":
    section("🔑", "پاسورڈ تبدیل کریں")
    _, col, _ = st.columns([1, 2, 1])
    with col:
        if IS_ADMIN:
            st.markdown("**استاد کا پاسورڈ ری سیٹ کریں**")
            tl = [r["username"] for r in query(
                "SELECT username FROM users WHERE role='teacher'")]
            with st.form("adm_pw_f"):
                sel = st.selectbox("استاد", tl) if tl else st.text_input("استاد")
                np1 = st.text_input("نیا پاسورڈ*", type="password")
                np2 = st.text_input("تصدیق*", type="password")
                if st.form_submit_button("✅ ری سیٹ کریں"):
                    if np1 and np1 == np2 and len(np1) >= 6:
                        execute(
                            "UPDATE users SET password=? WHERE username=?",
                            (make_hash(np1), sel),
                        )
                        log_action(st.session_state.username, "PW Reset", sel)
                        st.success(f"✅ {sel} کا پاسورڈ تبدیل!")
                    elif len(np1) < 6:
                        st.error("کم از کم 6 حروف")
                    else:
                        st.error("پاسورڈ میل نہیں کھاتے")
            st.markdown("<hr>", unsafe_allow_html=True)

        st.markdown("**اپنا پاسورڈ تبدیل کریں**")
        with st.form("my_pw_f"):
            op  = st.text_input("پرانا پاسورڈ*", type="password")
            np1 = st.text_input("نیا پاسورڈ*", type="password")
            np2 = st.text_input("تصدیق*", type="password")
            if st.form_submit_button("✅ تبدیل کریں"):
                u = query(
                    "SELECT password FROM users WHERE username=?",
                    (st.session_state.username,), one=True,
                )
                if u and verify_password(op, u["password"]):
                    if np1 == np2 and len(np1) >= 6:
                        execute(
                            "UPDATE users SET password=? WHERE username=?",
                            (make_hash(np1), st.session_state.username),
                        )
                        log_action(st.session_state.username, "PW Changed")
                        st.success("✅ تبدیل! دوبارہ لاگ ان کریں")
                        for k in list(st.session_state.keys()):
                            del st.session_state[k]
                        st.rerun()
                    elif len(np1) < 6:
                        st.error("کم از کم 6 حروف")
                    else:
                        st.error("پاسورڈ میل نہیں")
                else:
                    st.error("❌ پرانا پاسورڈ غلط ہے")

# ───────────────────────────────
# BACKUP
# ───────────────────────────────
elif pg == "backup" and IS_ADMIN:
    section("⚙️", "بیک اپ & سیٹنگز")
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("<div class='pc'>", unsafe_allow_html=True)
        st.markdown("**📥 ڈیٹا بیس بیک اپ**")
        if os.path.exists(DB):
            with open(DB, "rb") as f:
                st.download_button(
                    "💾 مکمل ڈیٹا بیس (.db)", f,
                    f"jamia_bkp_{datetime.now().strftime('%Y%m%d_%H%M')}.db",
                    "application/x-sqlite3", use_container_width=True,
                )
        if st.button("📦 CSV زپ بنائیں", use_container_width=True):
            tables = [
                "users","students","hifz_records","qaida_records","general_records",
                "teacher_attendance","leave_requests","exams","passed_paras",
                "timetable","notifications","staff_notes","audit_log",
            ]
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w") as zf:
                for t in tables:
                    try:
                        rows = query(f"SELECT * FROM {t}")
                        if rows:
                            zf.writestr(
                                f"{t}.csv",
                                pd.DataFrame(rows).to_csv(index=False).encode("utf-8-sig"),
                            )
                    except:
                        pass
            buf.seek(0)
            st.download_button(
                "📥 CSV زپ ڈاؤن لوڈ", buf,
                f"csv_{datetime.now().strftime('%Y%m%d')}.zip",
                "application/zip", use_container_width=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown("<div class='pc'>", unsafe_allow_html=True)
        st.markdown("**🔄 ڈیٹا بیس ری سٹور**")
        st.warning("⚠️ پہلے بیک اپ لیں!")
        upf = st.file_uploader(".db فائل اپ لوڈ کریں", type=["db"])
        if upf:
            if (st.checkbox("میں سمجھتا/سمجھتی ہوں کہ موجودہ ڈیٹا بدل جائے گا")
                    and st.button("🔄 ری سٹور کریں")):
                if os.path.exists(DB):
                    shutil.copy(DB, DB + ".bak")
                with open(DB, "wb") as f:
                    f.write(upf.getbuffer())
                st.success("✅ ری سٹور مکمل!")
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='pc'>", unsafe_allow_html=True)
    st.markdown("**📋 آڈٹ لاگ (آخری 50)**")
    logs = query(
        "SELECT username AS صارف, action AS عمل, details AS تفصیل, "
        "created_at AS وقت FROM audit_log ORDER BY created_at DESC LIMIT 50"
    )
    if logs:
        st.dataframe(pd.DataFrame(logs), use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════
#  TEACHER PAGES
# ═══════════════════════════════════════════════════════

# ───────────────────────────────
# TEACHER HOME
# ───────────────────────────────
elif pg == "home" and not IS_ADMIN:
    section("🏠", f"خوش آمدید، {st.session_state.username}!")
    ms = scalar(
        "SELECT COUNT(*) FROM students WHERE teacher=? AND is_active=1",
        (st.session_state.username,)
    )
    mr = scalar(
        "SELECT COUNT(*) FROM hifz_records WHERE teacher=?",
        (st.session_state.username,)
    )
    td = scalar(
        "SELECT COUNT(*) FROM hifz_records WHERE teacher=? AND rec_date=?",
        (st.session_state.username, str(date.today())),
    )
    ml = scalar(
        "SELECT COUNT(*) FROM leave_requests WHERE username=? AND status='پینڈنگ'",
        (st.session_state.username,)
    )
    metric_row([
        ("👨‍🎓", ms, "میرے طلباء"),
        ("📋",   mr, "کل ریکارڈ"),
        ("✅",   td, "آج اندراج"),
        ("📩",   ml, "رخصت پینڈنگ"),
    ])
    notifs = query(
        "SELECT title, message FROM notifications "
        "WHERE target IN ('تمام','اساتذہ') ORDER BY created_at DESC LIMIT 5"
    )
    if notifs:
        st.markdown("**🔔 تازہ اعلانات**")
        for n in notifs:
            st.markdown(
                f'<div class="nf-card">'
                f'<h5>{n["title"]}</h5>'
                f'<p>{n["message"][:120]}</p>'
                f'</div>',
                unsafe_allow_html=True,
            )

# ───────────────────────────────
# TEACHER DAILY ENTRY  ← ICON GRID
# ───────────────────────────────
elif pg == "entry" and not IS_ADMIN:
    section("📝", "روزانہ سبق اندراج", "طالب علم کا بٹن دبائیں")

    c1, c2 = st.columns(2)
    entry_date = c1.date_input("تاریخ", date.today())
    dept = c2.selectbox(
        "شعبہ", DEPTS,
        index=DEPTS.index(st.session_state.entry_dept)
        if st.session_state.entry_dept in DEPTS else 0,
    )
    st.session_state.entry_dept = dept

    my_studs = query(
        "SELECT id,name,father_name FROM students "
        "WHERE teacher=? AND dept=? AND is_active=1 ORDER BY name",
        (st.session_state.username, dept),
    )
    if not my_studs:
        st.info(f"آپ کی {dept} کلاس میں کوئی طالب علم نہیں")
        st.stop()

    # Find which students have today's record
    done_ids = set()
    for s in my_studs:
        if dept == "حفظ":
            r = query(
                "SELECT id FROM hifz_records WHERE student_id=? AND rec_date=?",
                (s["id"], str(entry_date)), one=True,
            )
        elif dept == "قاعدہ":
            r = query(
                "SELECT id FROM qaida_records WHERE student_id=? AND rec_date=?",
                (s["id"], str(entry_date)), one=True,
            )
        else:
            r = query(
                "SELECT id FROM general_records WHERE student_id=? AND dept=? AND rec_date=?",
                (s["id"], dept, str(entry_date)), one=True,
            )
        if r:
            done_ids.add(s["id"])

    # ── Render student icon grid ──
    COLS_PER_ROW = 4
    st.markdown(
        f"**{len(my_studs)} طلباء | {entry_date} | "
        f"✅ {len(done_ids)} مکمل | 📝 {len(my_studs)-len(done_ids)} باقی**"
    )
    chunks = [my_studs[i:i+COLS_PER_ROW] for i in range(0, len(my_studs), COLS_PER_ROW)]
    sel = st.session_state.sel_stu

    for chunk in chunks:
        row_cols = st.columns(COLS_PER_ROW)
        for col, s in zip(row_cols, chunk):
            is_done = s["id"] in done_ids
            is_sel  = sel == s["id"]
            nm = s["name"][:7]
            fn = s["father_name"][:6]
            icon = "✅" if is_done else ("✏️" if is_sel else "👤")
            lbl = f"{icon}\n{nm}\n{fn}"
            with col:
                if st.button(lbl, key=f"stu_{s['id']}", use_container_width=True):
                    if not is_done:
                        st.session_state.sel_stu = s["id"]
                        st.rerun()

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Entry form for selected student ──
    if sel and sel not in done_ids:
        s_data = next((s for s in my_studs if s["id"] == sel), None)
        if not s_data:
            st.session_state.sel_stu = None
            st.rerun()

        section("✏️", f"{s_data['name']} ولد {s_data['father_name']}", f"{dept} | {entry_date}")

        k = str(s_data["id"])
        att = st.radio("حاضری", ATT, key=f"att_{k}", horizontal=True)
        cln = st.selectbox("صفائی", CLEAN, key=f"cln_{k}")

        s_nagha = sq_nagha = m_nagha = 0
        sabaq_txt = sq_txt = m_txt = ""
        s_lines = sq_atk = sq_mis = m_atk = m_mis = 0

        # ── HIFZ FORM ──
        if dept == "حفظ" and att == "حاضر":
            st.markdown("**📖 سبق**")
            sc1, sc2 = st.columns(2)
            sn = sc1.checkbox("سبق ناغہ", key=f"sn_{k}")
            sy = sc2.checkbox("سبق یاد نہیں", key=f"sy_{k}")
            if sn or sy:
                s_nagha = 1
                sabaq_txt = "ناغہ" if sn else "یاد نہیں"
            else:
                rc1, rc2, rc3 = st.columns(3)
                sur = rc1.selectbox("سورت", SURAHS, key=f"sr_{k}")
                af  = rc2.text_input("آیت سے", key=f"af_{k}")
                at_ = rc3.text_input("آیت تک", key=f"at_{k}")
                s_lines = st.number_input("ستر (لائنیں)", 0, 50, 0, key=f"sl_{k}")
                sabaq_txt = f"{sur}:{af}-{at_}"

            st.markdown("**📚 سبقی**")
            sc1, sc2 = st.columns(2)
            sqn_ = sc1.checkbox("سبقی ناغہ", key=f"sqn_{k}")
            sqy  = sc2.checkbox("سبقی یاد نہیں", key=f"sqy_{k}")
            if sqn_ or sqy:
                sq_nagha = 1
                sq_txt = "ناغہ" if sqn_ else "یاد نہیں"
            else:
                rc1, rc2, rc3, rc4 = st.columns(4)
                sqp = rc1.selectbox("پارہ", PARAS, key=f"sqp_{k}")
                sqm = rc2.selectbox("مقدار", MIQDAR, key=f"sqm_{k}")
                sq_atk = rc3.number_input("اٹکن", 0, key=f"sqat_{k}")
                sq_mis = rc4.number_input("غلطی", 0, key=f"sqms_{k}")
                sq_txt = f"{sqp}:{sqm}"

            st.markdown("**🌙 منزل**")
            sc1, sc2 = st.columns(2)
            mn_ = sc1.checkbox("منزل ناغہ", key=f"mn_{k}")
            my_ = sc2.checkbox("منزل یاد نہیں", key=f"my_{k}")
            if mn_ or my_:
                m_nagha = 1
                m_txt = "ناغہ" if mn_ else "یاد نہیں"
            else:
                rc1, rc2, rc3, rc4 = st.columns(4)
                mp_   = rc1.selectbox("پارہ", PARAS, key=f"mp_{k}")
                mm__  = rc2.selectbox("مقدار", MIQDAR, key=f"mm_{k}")
                m_atk = rc3.number_input("اٹکن", 0, key=f"mat_{k}")
                m_mis = rc4.number_input("غلطی", 0, key=f"mms_{k}")
                m_txt = f"{mp_}:{mm__}"

            grade = hifz_grade(att, s_nagha, sq_nagha, m_nagha, sq_mis, m_mis)
            st.markdown(f"**درجہ:** {chip(grade)}", unsafe_allow_html=True)

        elif dept == "حفظ":
            grade = "غیر حاضر" if att == "غیر حاضر" else "رخصت"

        # ── QAIDA FORM ──
        elif dept == "قاعدہ" and att == "حاضر":
            lesson_no_v = st.text_input("تختی/سبق نمبر", key=f"ln_{k}")
            lines_v     = st.number_input("لائنیں", 0, key=f"lns_{k}")
            details_v   = st.text_area("تفصیل", key=f"det_{k}")

        # ── GENERAL FORM ──
        elif dept in ("درسِ نظامی", "عصری تعلیم") and att == "حاضر":
            sub_v = st.text_input("مضمون/کتاب", key=f"sub_{k}")
            les_v = st.text_area("سبق", key=f"les_{k}")
            hw_v  = st.text_input("ہوم ورک", key=f"hw_{k}")
            prf_v = st.select_slider(
                "کارکردگی",
                ["بہت بہتر","بہتر","مناسب","کمزور"],
                key=f"prf_{k}",
            )

        note_v = st.text_input("نوٹ (اختیاری)", key=f"nt_{k}")

        bc1, bc2 = st.columns(2)
        if bc1.button(f"💾 {s_data['name']} محفوظ کریں", use_container_width=True):
            try:
                if dept == "حفظ":
                    gr = hifz_grade(att, s_nagha, sq_nagha, m_nagha, sq_mis, m_mis)
                    execute(
                        "INSERT INTO hifz_records("
                        "rec_date,student_id,teacher,attendance,"
                        "sabaq,sabaq_lines,sabaq_nagha,"
                        "sq_text,sq_nagha,sq_atkan,sq_mistakes,"
                        "manzil_text,manzil_nagha,manzil_atkan,manzil_mistakes,"
                        "cleanliness,grade,note) "
                        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (str(entry_date), s_data["id"], st.session_state.username, att,
                         sabaq_txt, s_lines, s_nagha,
                         sq_txt, sq_nagha, sq_atk, sq_mis,
                         m_txt, m_nagha, m_atk, m_mis,
                         cln, gr, note_v),
                    )
                elif dept == "قاعدہ":
                    ln_v = st.session_state.get(f"ln_{k}", "")
                    lns  = st.session_state.get(f"lns_{k}", 0)
                    det  = st.session_state.get(f"det_{k}", "")
                    if att != "حاضر":
                        ln_v = ""; lns = 0; det = ""
                    execute(
                        "INSERT INTO qaida_records("
                        "rec_date,student_id,teacher,attendance,"
                        "lesson_no,total_lines,details,cleanliness,note) "
                        "VALUES(?,?,?,?,?,?,?,?,?)",
                        (str(entry_date), s_data["id"], st.session_state.username, att,
                         ln_v, lns, det, cln, note_v),
                    )
                else:
                    sv  = st.session_state.get(f"sub_{k}", "") if att == "حاضر" else ""
                    lv  = st.session_state.get(f"les_{k}", "") if att == "حاضر" else ""
                    hv  = st.session_state.get(f"hw_{k}",  "") if att == "حاضر" else ""
                    pv  = st.session_state.get(f"prf_{k}", "") if att == "حاضر" else ""
                    execute(
                        "INSERT INTO general_records("
                        "rec_date,student_id,teacher,dept,attendance,"
                        "subject,lesson,homework,performance,cleanliness,note) "
                        "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                        (str(entry_date), s_data["id"], st.session_state.username, dept,
                         att, sv, lv, hv, pv, cln, note_v),
                    )
                log_action(st.session_state.username, "Entry", f"{s_data['name']} {entry_date}")
                st.success(f"✅ {s_data['name']} محفوظ!")
                st.session_state.sel_stu = None
                st.rerun()
            except Exception as e:
                st.error(f"خرابی: {e}")

        if bc2.button("← واپس", use_container_width=True):
            st.session_state.sel_stu = None
            st.rerun()

    elif sel in done_ids:
        st.success("✅ اس طالب علم کا آج کا ریکارڈ پہلے سے محفوظ ہے")
        if st.button("← واپس"):
            st.session_state.sel_stu = None
            st.rerun()

# ───────────────────────────────
# TEACHER EXAM REQUEST
# ───────────────────────────────
elif pg == "t_exam" and not IS_ADMIN:
    section("🎓", "امتحانی درخواست")
    ms = query(
        "SELECT id,name,father_name,dept FROM students "
        "WHERE teacher=? AND is_active=1",
        (st.session_state.username,)
    )
    if not ms:
        st.warning("آپ کی کلاس میں کوئی طالب علم نہیں")
    else:
        with st.form("ex_req_f"):
            names = [f"{s['name']} ولد {s['father_name']} ({s['dept']})" for s in ms]
            idx = st.selectbox("طالب علم", range(len(names)), format_func=lambda i: names[i])
            s = ms[idx]
            et = st.selectbox("امتحان", ["پارہ ٹیسٹ","ماہانہ","سہ ماہی","سالانہ"])
            c1, c2 = st.columns(2)
            sd = c1.date_input("شروع", date.today())
            ed = c2.date_input("ختم", date.today() + timedelta(days=7))
            td_ = (ed - sd).days + 1
            st.caption(f"کل دن: {td_}")
            fp = tp = 0
            bk = amt = ""
            if et == "پارہ ٹیسٹ" or s["dept"] == "حفظ":
                c1, c2 = st.columns(2)
                fp = c1.number_input("پارہ (شروع)", 1, 30, 1)
                tp = c2.number_input("پارہ (ختم)", int(fp), 30, int(fp))
            if s["dept"] != "حفظ":
                bk = st.text_input("کتاب")
            amt = st.text_input("مقدار خواندگی")
            if st.form_submit_button("📤 درخواست بھیجیں"):
                execute(
                    "INSERT INTO exams(student_id,teacher,dept,exam_type,"
                    "from_para,to_para,book_name,amount_read,"
                    "start_date,end_date,total_days) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (s["id"], st.session_state.username, s["dept"], et,
                     fp, tp, bk, amt, str(sd), str(ed), td_),
                )
                st.success("✅ درخواست بھیج دی گئی")

# ───────────────────────────────
# TEACHER LEAVE
# ───────────────────────────────
elif pg == "t_lv" and not IS_ADMIN:
    section("📩", "رخصت کی درخواست")
    ml = query(
        "SELECT leave_type AS نوعیت, start_date AS تاریخ, "
        "days AS دن, status AS حالت "
        "FROM leave_requests WHERE username=? ORDER BY created_at DESC LIMIT 10",
        (st.session_state.username,)
    )
    if ml:
        st.markdown("**حالیہ درخواستیں**")
        for lv in ml:
            sc_ = ("so" if lv["حالت"] == "منظور"
                   else "sr" if lv["حالت"] == "مسترد" else "sp")
            st.markdown(
                f'<div class="lv-card">'
                f'<span class="{sc_}">{lv["حالت"]}</span>&nbsp;'
                f'<b>{lv["نوعیت"]}</b> | {lv["تاریخ"]} | {lv["دن"]} دن'
                f'</div>',
                unsafe_allow_html=True,
            )
        st.markdown("<hr>", unsafe_allow_html=True)

    with st.form("lv_f"):
        c1, c2 = st.columns(2)
        lt   = c1.selectbox("نوعیت", ["بیماری","ضروری کام","ہنگامی","دیگر"])
        sd   = c2.date_input("تاریخ شروع", date.today())
        days = c1.number_input("دنوں کی تعداد", 1, 30, 1)
        c2.caption(f"واپسی: {sd + timedelta(days=int(days) - 1)}")
        rsn = st.text_area("وجہ*", max_chars=500)
        if st.form_submit_button("📤 درخواست بھیجیں"):
            if rsn.strip():
                execute(
                    "INSERT INTO leave_requests(username,leave_type,start_date,days,reason) "
                    "VALUES(?,?,?,?,?)",
                    (st.session_state.username, lt, str(sd), days, rsn),
                )
                st.success("✅ درخواست بھیج دی گئی!")
                st.rerun()
            else:
                st.error("وجہ ضروری ہے")

# ───────────────────────────────
# TEACHER ATTENDANCE
# ───────────────────────────────
elif pg == "t_att" and not IS_ADMIN:
    section("🕒", "میری حاضری")
    today = date.today()
    rec = query(
        "SELECT * FROM teacher_attendance WHERE username=? AND att_date=?",
        (st.session_state.username, str(today)), one=True,
    )
    st.markdown(
        f'<div class="pc" style="text-align:center;font-size:.95rem;'
        f'font-weight:700;color:#0a5c3c">📅 {today}</div>',
        unsafe_allow_html=True,
    )
    if not rec:
        arr = st.time_input("آمد کا وقت", datetime.now().time())
        if st.button("✅ آمد درج کریں", use_container_width=True):
            try:
                execute(
                    "INSERT INTO teacher_attendance(username,att_date,arrival) "
                    "VALUES(?,?,?)",
                    (st.session_state.username, str(today), arr.strftime("%I:%M %p")),
                )
                st.success("✅ آمد درج!")
                st.rerun()
            except:
                st.warning("پہلے سے درج ہے")
    elif not rec.get("departure"):
        st.success(f"✅ آمد: {rec['arrival']}")
        dep = st.time_input("رخصت کا وقت", datetime.now().time())
        if st.button("✅ رخصت درج کریں", use_container_width=True):
            execute(
                "UPDATE teacher_attendance SET departure=? WHERE username=? AND att_date=?",
                (dep.strftime("%I:%M %p"), st.session_state.username, str(today)),
            )
            st.success("✅ رخصت درج!")
            st.rerun()
    else:
        c1, c2 = st.columns(2)
        c1.metric("🟢 آمد", rec["arrival"])
        c2.metric("🔴 رخصت", rec["departure"])

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("**ماہانہ ریکارڈ**")
    monthly = query(
        "SELECT att_date AS تاریخ, arrival AS آمد, departure AS رخصت "
        "FROM teacher_attendance WHERE username=? AND att_date>=? "
        "ORDER BY att_date DESC",
        (st.session_state.username, str(date.today().replace(day=1))),
    )
    if monthly:
        st.dataframe(pd.DataFrame(monthly), use_container_width=True, hide_index=True)
    else:
        st.caption("اس ماہ کوئی ریکارڈ نہیں")

# ───────────────────────────────
# TEACHER TIMETABLE
# ───────────────────────────────
elif pg == "t_tt" and not IS_ADMIN:
    section("📚", "میرا ٹائم ٹیبل")
    tt = query(
        "SELECT day_name AS دن, period AS وقت, subject AS مضمون, room AS کمرہ "
        "FROM timetable WHERE teacher=? ORDER BY day_name,period",
        (st.session_state.username,)
    )
    if tt:
        df = pd.DataFrame(tt)
        try:
            pivot = df.pivot(index="وقت", columns="دن", values="مضمون").fillna("—")
            st.dataframe(pivot, use_container_width=True)
        except:
            st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button(
            "📥 ٹائم ٹیبل ڈاؤن لوڈ",
            make_html_report(df, "ٹائم ٹیبل", st.session_state.username),
            "timetable.html", "text/html",
        )
    else:
        st.info("ابھی آپ کا ٹائم ٹیبل ترتیب نہیں دیا گیا")

# ─────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────
st.markdown(
    '<div class="bottom-pad"></div>'
    '<div style="text-align:center;padding:12px 0;color:#9ca3af;font-size:.68rem;'
    'border-top:1px solid #d4e6da;margin-top:20px">'
    '🕌 جامعہ ملیہ اسلامیہ فیصل آباد — Smart ERP v5.0 | تمام حقوق محفوظ'
    '</div>',
    unsafe_allow_html=True,
)
st.markdown('</div>', unsafe_allow_html=True)
