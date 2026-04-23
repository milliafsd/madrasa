"""
جامعہ ملیہ اسلامیہ - SQLite سے Supabase منتقلی
=====================================================
یہ script چلانے کا طریقہ:
1. pip install supabase
2. python migrate.py
"""

import sqlite3
import hashlib
import sys
from datetime import datetime

# ==================== سیٹنگز ====================
SQLITE_FILE = "backup_20260423_052104.db"  # اپنی .db فائل کا نام لکھیں
SUPABASE_URL = "https://hwatymfkrqnllsjhufak.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh3YXR5bWZrcnFubGxzamh1ZmFrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY0ODUzOTEsImV4cCI6MjA5MjA2MTM5MX0.mQbpMrLZqqbSsJMMZdzMT"

try:
    from supabase import create_client
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Supabase سے رابطہ ہو گیا")
except Exception as e:
    print(f"❌ Supabase خرابی: {e}")
    print("pip install supabase چلائیں")
    sys.exit(1)

def hash_password(password):
    if not password:
        return hashlib.sha256("jamia123".encode()).hexdigest()
    # اگر پہلے سے hash ہے (64 حروف hex) تو ویسے ہی رکھیں
    if len(str(password)) == 64:
        try:
            int(str(password), 16)
            return str(password)
        except:
            pass
    return hashlib.sha256(str(password).encode()).hexdigest()

def safe(val):
    """None اور خالی values ٹھیک کریں"""
    if val is None:
        return None
    if isinstance(val, str) and val.strip() == '':
        return None
    return val

def batch_insert(table, records, batch_size=50):
    """بیچز میں insert کریں"""
    total = len(records)
    if total == 0:
        print(f"  ⚠️  {table}: کوئی ریکارڈ نہیں")
        return
    success = 0
    for i in range(0, total, batch_size):
        batch = records[i:i+batch_size]
        try:
            supabase.table(table).insert(batch).execute()
            success += len(batch)
            print(f"  {table}: {success}/{total} ✓", end='\r')
        except Exception as e:
            print(f"\n  ❌ {table} batch {i}: {e}")
            # ایک ایک کر کے try کریں
            for rec in batch:
                try:
                    supabase.table(table).insert(rec).execute()
                    success += 1
                except Exception as e2:
                    print(f"  ❌ ریکارڈ skip: {e2}")
    print(f"\n  ✅ {table}: {success}/{total} منتقل ہوئے")

# ==================== SQLite کھولیں ====================
conn = sqlite3.connect(SQLITE_FILE)
conn.row_factory = sqlite3.Row
c = conn.cursor()
print(f"\n📂 SQLite فائل کھل گئی: {SQLITE_FILE}")

# ==================== 1. TEACHERS ====================
print("\n1️⃣  اساتذہ منتقل کر رہے ہیں...")
try:
    # Supabase میں پہلے سے موجود ناموں کی فہرست
    existing = supabase.table("teachers").select("name").execute()
    existing_names = {r["name"] for r in existing.data}
except:
    existing_names = set()

rows = c.execute("SELECT * FROM teachers").fetchall()
teachers_records = []
for row in rows:
    row = dict(row)
    if row["name"] in existing_names:
        continue
    teachers_records.append({
        "name": safe(row.get("name")),
        "password": hash_password(row.get("password")),
        "dept": safe(row.get("dept")),
        "phone": safe(row.get("phone")),
        "address": safe(row.get("address")),
        "id_card": safe(row.get("id_card")),
        "joining_date": safe(row.get("joining_date")),
    })
if teachers_records:
    batch_insert("teachers", teachers_records)
else:
    print("  ⚠️  تمام اساتذہ پہلے سے موجود ہیں")

# ==================== 2. STUDENTS ====================
print("\n2️⃣  طلباء منتقل کر رہے ہیں...")
# پہلے Supabase خالی کریں (نئے IDs مل سکیں)
try:
    supabase.table("students").delete().neq("id", 0).execute()
    print("  پرانے طلباء ہٹا دیے")
except:
    pass

rows = c.execute("SELECT * FROM students").fetchall()
students_records = []
# SQLite ID → Supabase ID کا نقشہ بنائیں گے بعد میں
sqlite_students = {}
for row in rows:
    row = dict(row)
    sqlite_students[row["id"]] = row  # بعد میں کام آئے گا
    students_records.append({
        "name": safe(row.get("name")),
        "father_name": safe(row.get("father_name")),
        "mother_name": safe(row.get("mother_name")),
        "dob": safe(row.get("dob")),
        "admission_date": safe(row.get("admission_date")),
        "exit_date": safe(row.get("exit_date")),
        "exit_reason": safe(row.get("exit_reason")),
        "id_card": safe(row.get("id_card")),
        "phone": safe(row.get("phone")),
        "address": safe(row.get("address")),
        "teacher_name": safe(row.get("teacher_name")),
        "dept": safe(row.get("dept")),
        "class": safe(row.get("class")),
        "section": safe(row.get("section")),
        "roll_no": safe(row.get("roll_no")),
        "photo": None,  # تصویریں Supabase میں نہیں
    })

batch_insert("students", students_records)

# Supabase سے نئے IDs لیں (name+father_name کے ذریعے)
print("  🔄 نئے IDs حاصل کر رہے ہیں...")
try:
    sb_students = supabase.table("students").select("id, name, father_name").execute()
    # name+father → supabase_id کا نقشہ
    name_to_sbid = {}
    for s in sb_students.data:
        key = f"{s['name']}|{s['father_name']}"
        name_to_sbid[key] = s["id"]
    
    # SQLite ID → Supabase ID
    sqlite_to_sb = {}
    for sqlite_id, stud in sqlite_students.items():
        key = f"{stud['name']}|{stud['father_name']}"
        if key in name_to_sbid:
            sqlite_to_sb[sqlite_id] = name_to_sbid[key]
    
    print(f"  ✅ {len(sqlite_to_sb)} طلباء کا ID نقشہ تیار")
except Exception as e:
    print(f"  ❌ ID نقشہ خرابی: {e}")
    sqlite_to_sb = {}

# ==================== 3. HIFZ RECORDS ====================
print("\n3️⃣  حفظ ریکارڈ منتقل کر رہے ہیں...")
try:
    supabase.table("hifz_records").delete().neq("id", 0).execute()
except:
    pass

rows = c.execute("SELECT * FROM hifz_records").fetchall()
hifz_records = []
skipped = 0
for row in rows:
    row = dict(row)
    sqlite_sid = row.get("student_id")
    sb_sid = sqlite_to_sb.get(sqlite_sid)
    if not sb_sid:
        skipped += 1
        continue
    hifz_records.append({
        "r_date": safe(row.get("r_date")),
        "student_id": sb_sid,
        "t_name": safe(row.get("t_name")),
        "surah": safe(row.get("surah")),
        "a_from": safe(row.get("a_from")),
        "a_to": safe(row.get("a_to")),
        "sq_p": safe(row.get("sq_p")),
        "sq_a": row.get("sq_a") or 0,
        "sq_m": row.get("sq_m") or 0,
        "m_p": safe(row.get("m_p")),
        "m_a": row.get("m_a") or 0,
        "m_m": row.get("m_m") or 0,
        "attendance": safe(row.get("attendance")),
        "principal_note": safe(row.get("principal_note")),
        "lines": row.get("lines") or 0,
        "cleanliness": safe(row.get("cleanliness")),
    })
if skipped:
    print(f"  ⚠️  {skipped} ریکارڈ skip (student_id نہیں ملا)")
batch_insert("hifz_records", hifz_records)

# ==================== 4. QAIDA RECORDS ====================
print("\n4️⃣  قاعدہ ریکارڈ منتقل کر رہے ہیں...")
try:
    supabase.table("qaida_records").delete().neq("id", 0).execute()
except:
    pass

rows = c.execute("SELECT * FROM qaida_records").fetchall()
qaida_records = []
skipped = 0
for row in rows:
    row = dict(row)
    sb_sid = sqlite_to_sb.get(row.get("student_id"))
    if not sb_sid:
        skipped += 1
        continue
    qaida_records.append({
        "r_date": safe(row.get("r_date")),
        "student_id": sb_sid,
        "t_name": safe(row.get("t_name")),
        "lesson_no": safe(row.get("lesson_no")),
        "total_lines": row.get("total_lines") or 0,
        "details": safe(row.get("details")),
        "attendance": safe(row.get("attendance")),
        "principal_note": safe(row.get("principal_note")),
        "cleanliness": safe(row.get("cleanliness")),
    })
if skipped:
    print(f"  ⚠️  {skipped} ریکارڈ skip")
batch_insert("qaida_records", qaida_records)

# ==================== 5. GENERAL EDUCATION ====================
print("\n5️⃣  عمومی تعلیم منتقل کر رہے ہیں...")
try:
    supabase.table("general_education").delete().neq("id", 0).execute()
except:
    pass

rows = c.execute("SELECT * FROM general_education").fetchall()
gen_records = []
for row in rows:
    row = dict(row)
    sb_sid = sqlite_to_sb.get(row.get("student_id"))
    if not sb_sid:
        continue
    gen_records.append({
        "r_date": safe(row.get("r_date")),
        "student_id": sb_sid,
        "t_name": safe(row.get("t_name")),
        "dept": safe(row.get("dept")),
        "book_subject": safe(row.get("book_subject")),
        "today_lesson": safe(row.get("today_lesson")),
        "homework": safe(row.get("homework")),
        "performance": safe(row.get("performance")),
        "attendance": safe(row.get("attendance")),
        "cleanliness": safe(row.get("cleanliness")),
    })
batch_insert("general_education", gen_records)

# ==================== 6. T_ATTENDANCE ====================
print("\n6️⃣  اساتذہ حاضری منتقل کر رہے ہیں...")
try:
    supabase.table("t_attendance").delete().neq("id", 0).execute()
except:
    pass

rows = c.execute("SELECT * FROM t_attendance").fetchall()
att_records = []
for row in rows:
    row = dict(row)
    att_records.append({
        "t_name": safe(row.get("t_name")),
        "a_date": safe(row.get("a_date")),
        "arrival": safe(row.get("arrival")),
        "departure": safe(row.get("departure")),
        "actual_arrival": None,
        "actual_departure": None,
    })
batch_insert("t_attendance", att_records)

# ==================== 7. LEAVE REQUESTS ====================
print("\n7️⃣  رخصت درخواستیں منتقل کر رہے ہیں...")
try:
    supabase.table("leave_requests").delete().neq("id", 0).execute()
except:
    pass

rows = c.execute("SELECT * FROM leave_requests").fetchall()
leave_records = []
for row in rows:
    row = dict(row)
    leave_records.append({
        "t_name": safe(row.get("t_name")),
        "reason": safe(row.get("reason")),
        "start_date": safe(row.get("start_date")),
        "back_date": safe(row.get("back_date")),
        "status": safe(row.get("status")),
        "request_date": safe(row.get("request_date")),
        "l_type": "دیگر",  # پرانے ڈیٹا میں نہیں تھا
        "days": 1,
        "notification_seen": row.get("notification_seen") or 0,
    })
batch_insert("leave_requests", leave_records)

# ==================== 8. EXAMS ====================
print("\n8️⃣  امتحانات منتقل کر رہے ہیں...")
try:
    supabase.table("exams").delete().neq("id", 0).execute()
except:
    pass

rows = c.execute("SELECT * FROM exams").fetchall()
exam_records = []
skipped = 0
for row in rows:
    row = dict(row)
    sb_sid = sqlite_to_sb.get(row.get("student_id"))
    if not sb_sid:
        skipped += 1
        continue
    exam_records.append({
        "student_id": sb_sid,
        "dept": safe(row.get("dept")),
        "exam_type": safe(row.get("exam_type")),
        "from_para": row.get("from_para") or 0,
        "to_para": row.get("to_para") or 0,
        "book_name": safe(row.get("book_name")),
        "amount_read": safe(row.get("amount_read")),
        "start_date": safe(row.get("start_date")),
        "end_date": safe(row.get("end_date")),
        "total_days": row.get("total_days") or 0,
        "q1": row.get("q1") or 0,
        "q2": row.get("q2") or 0,
        "q3": row.get("q3") or 0,
        "q4": row.get("q4") or 0,
        "q5": row.get("q5") or 0,
        "total": row.get("total") or 0,
        "grade": safe(row.get("grade")),
        "status": safe(row.get("status")),
    })
if skipped:
    print(f"  ⚠️  {skipped} ریکارڈ skip")
batch_insert("exams", exam_records)

# ==================== 9. PASSED PARAS ====================
print("\n9️⃣  پاس شدہ پارے منتقل کر رہے ہیں...")
try:
    supabase.table("passed_paras").delete().neq("id", 0).execute()
except:
    pass

rows = c.execute("SELECT * FROM passed_paras").fetchall()
para_records = []
for row in rows:
    row = dict(row)
    sb_sid = sqlite_to_sb.get(row.get("student_id"))
    if not sb_sid:
        continue
    para_records.append({
        "student_id": sb_sid,
        "para_no": row.get("para_no"),
        "book_name": safe(row.get("book_name")),
        "passed_date": safe(row.get("passed_date")),
        "exam_type": safe(row.get("exam_type")),
        "grade": safe(row.get("grade")),
        "marks": row.get("marks") or 0,
    })
batch_insert("passed_paras", para_records)

# ==================== 10. TIMETABLE ====================
print("\n🔟  ٹائم ٹیبل منتقل کر رہے ہیں...")
try:
    supabase.table("timetable").delete().neq("id", 0).execute()
except:
    pass

rows = c.execute("SELECT * FROM timetable").fetchall()
tt_records = [{"t_name": safe(dict(r).get("t_name")), "day": safe(dict(r).get("day")),
               "period": safe(dict(r).get("period")), "book": safe(dict(r).get("book")),
               "room": safe(dict(r).get("room"))} for r in rows]
batch_insert("timetable", tt_records)

# ==================== 11. STAFF MONITORING ====================
print("\n1️⃣1️⃣  عملہ نگرانی منتقل کر رہے ہیں...")
try:
    supabase.table("staff_monitoring").delete().neq("id", 0).execute()
except:
    pass

rows = c.execute("SELECT * FROM staff_monitoring").fetchall()
sm_records = []
for row in rows:
    row = dict(row)
    sm_records.append({
        "staff_name": safe(row.get("staff_name")),
        "date": safe(row.get("date")),
        "note_type": safe(row.get("note_type")),
        "description": safe(row.get("description")),
        "action_taken": safe(row.get("action_taken")),
        "status": safe(row.get("status")),
        "created_by": safe(row.get("created_by")),
        "created_at": safe(row.get("created_at")),
    })
batch_insert("staff_monitoring", sm_records)

conn.close()

print("\n" + "="*50)
print("✅ منتقلی مکمل!")
print("="*50)
print("\nاب Supabase میں چیک کریں:")
tables = ["teachers","students","hifz_records","qaida_records","t_attendance",
          "leave_requests","exams","passed_paras","timetable","staff_monitoring"]
for t in tables:
    try:
        res = supabase.table(t).select("id", count="exact").execute()
        print(f"  {t}: {res.count} ریکارڈ")
    except Exception as e:
        print(f"  {t}: چیک نہیں ہو سکا - {e}")
