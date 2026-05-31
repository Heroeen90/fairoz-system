import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
import json
import plotly.graph_objects as go

# ==========================================
# 1. إعدادات الصفحة العامة (التوافق التام مع الموبايل)
# ==========================================
st.set_page_config(
    page_title="نظام إدارة محل فيروز",
    page_icon="💎",
    layout="centered", 
    initial_sidebar_state="collapsed" # إخفاء القائمة الجانبية تماماً لمنع التشوه
)

# تصميم مخصص CSS لإلغاء القائمة الجانبية وجعل التنقل علوي بالكامل
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap');
    
    /* إعدادات الاتجاه العام للشاشة */
    html, body, [data-testid="stAppViewContainer"], .main {
        font-family: 'Tajawal', sans-serif;
        direction: rtl !important;
        text-align: right !important;
    }
    
    /* إخفاء زر القائمة الجانبية الافتراضي تماماً من شاشة الموبايل لمنع تفعيله بالخطأ */
    [data-testid="stSidebarCollapseButton"] {
        display: none !important;
    }
    [data-testid="stSidebar"] {
        display: none !important;
    }
    
    /* تحسين طريقة عرض التبويبات العلوية لتكون كأزرار تصفح كبيرة على الموبايل */
    button[data-baseweb="tab"] {
        font-size: 15px !important;
        font-weight: bold !important;
        padding: 10px 12px !important;
    }

    /* تحسين حجم العناوين لتناسب الموبايل بشكل أنيق */
    h1 {
        font-size: 22px !important;
        color: #1E3A8A !important;
        padding-top: 5px !important;
    }
    h3 {
        font-size: 17px !important;
    }

    /* كروت العرض المالية اليومية ممتدة بالكامل */
    .main-card {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 15px;
        border-right: 5px solid #1E3A8A;
    }
    
    .metric-val {
        font-size: 22px;
        font-weight: bold;
        color: #1E3A8A;
        display: block;
        margin-top: 5px;
    }

    /* أزرار الإدخال والحفظ */
    .stButton>button {
        width: 100% !important;
        border-radius: 10px !important;
        font-size: 16px !important;
        padding: 10px !important;
    }
    
    .stTextInput input, .stNumberInput input, .stSelectbox select {
        text-align: right !important;
        direction: rtl !important;
    }
</style>
""", unsafe_allow_html=True)

DB_NAME = "fairoz.db"

# ==========================================
# 2. إدارة قاعدة البيانات (Database Layer)
# ==========================================
def get_db_connection():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    )""")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT NOT NULL,         
        amount REAL NOT NULL,
        date TEXT NOT NULL,         
        category TEXT,              
        notes TEXT
    )""")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS employee_tx (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER,
        type TEXT NOT NULL,         
        amount REAL NOT NULL,
        date TEXT NOT NULL,
        notes TEXT,
        FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
    )""")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS day_status (
        date TEXT PRIMARY KEY,       
        status TEXT NOT NULL,        
        actual_cash REAL DEFAULT 0
    )""")
    
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 3. نظام الحماية البسيط (PIN Auth)
# ==========================================
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if not st.session_state['authenticated']:
    st.title("💎 نظام إدارة محل فيروز")
    st.subheader("تسجيل الدخول الذكي")
    pin_input = st.text_input("أدخل رمز الدخول (PIN):", type="password", max_chars=4)
    
    if st.button("دخول المالك تحسين"):
        if pin_input == "1234":  
            st.session_state['authenticated'] = True
            st.rerun()
        else:
            st.error("رمز الـ PIN غير صحيح! حاول مرة أخرى.")
    st.stop()

# ==========================================
# 4. منطق المساعدات والحسابات (Helpers)
# ==========================================
def add_transaction(t_type, amount, t_date, category, notes):
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO transactions (type, amount, date, category, notes) VALUES (?, ?, ?, ?, ?)",
        (t_type, amount, str(t_date), category, notes)
    )
    conn.execute("INSERT OR IGNORE INTO day_status (date, status) VALUES (?, ?)", (str(t_date), 'غير مكتمل'))
    conn.commit()
    conn.close()

def get_all_employees():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM employees").fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ==========================================
# 5. نظام التنقل العلوي الآمن بديل القائمة الجانبية المشوهة
# ==========================================
st.title("💎 إدارة محل فيروز")

# استخدام التبويبات العلوية بدلاً من السايدبار
tab_dashboard, tab_add, tab_workers, tab_days, tab_reports, tab_backup = st.tabs([
    "📱 الرئيسية", 
    "➕ إضافة حركة", 
    "👥 العمال", 
    "📅 الأيام", 
    "📊 التقارير", 
    "💾 الأمان"
])

# --- تبويب 1: لوحة التحكم السريعة ---
with tab_dashboard:
    today_str = str(date.today())
    
    conn = get_db_connection()
    day_info = conn.execute("SELECT * FROM day_status WHERE date = ?", (today_str,)).fetchone()
    day_status = day_info['status'] if day_info else "لم يبدأ بعد"
    
    st.info(f"📅 اليوم: {today_str} | الحالة: **{day_status}**")
    
    t_df = pd.read_sql_query("SELECT * FROM transactions WHERE date = ?", conn, params=(today_str,))
    e_df = pd.read_sql_query(
        "SELECT tx.*, e.name FROM employee_tx tx JOIN employees e ON tx.employee_id = e.id WHERE tx.date = ?", 
        conn, params=(today_str,)
    )
    conn.close()
    
    sales = t_df[t_df['type'] == 'مبيعات']['amount'].sum()
    purchases = t_df[t_df['type'] == 'مشتريات']['amount'].sum()
    expenses = t_df[t_df['type'] == 'مصروفات']['amount'].sum()
    owner = t_df[t_df['type'] == 'سحب شخصي']['amount'].sum()
    emp_paid = e_df['amount'].sum()
    
    expected_cash = sales - purchases - expenses - owner - emp_paid
    
    st.markdown("### 💰 كشف الخزنة السريع اليوم")
    st.markdown(f"<div class='main-card'>💵 إجمالي مبيعات اليوم:<br><span class='metric-val'>{sales:,.0f} د.ع</span></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='main-card'>🏧 الكاش المتوقع بالصندوق حالياً:<br><span class='metric-val'>{expected_cash:,.0f} د.ع</span></div>", unsafe_allow_html=True)
        
    st.markdown("### ⚠️ تنبيهات النظام")
    conn = get_db_connection()
    uncompleted_days = conn.execute("SELECT COUNT(*) FROM day_status WHERE status = 'غير مكتمل'").fetchone()[0]
    debts_to_store = conn.execute("SELECT SUM(amount) FROM transactions WHERE type = 'دين للمحل'").fetchone()[0] or 0
    debts_from_store = conn.execute("SELECT SUM(amount) FROM transactions WHERE type = 'دين على المحل'").fetchone()[0] or 0
    conn.close()
    
    if uncompleted_days > 0:
        st.warning(f"🔔 عدد ({uncompleted_days}) أيام غير مكتملة الإغلاق. انتقل لتبويب [📅 الأيام].")
    if debts_to_store > 0:
        st.info(f"📈 ديون للمحل بطرف الزبائن: {debts_to_store:,.0f} د.ع")
    if debts_from_store > 0:
        st.error(f"📉 ديون مطلوبة من المحل للموردين: {debts_from_store:,.0f} د.ع")

    st.markdown("### ⏱️ آخر 5 عمليات مالية مسجلة")
    conn = get_db_connection()
    recent = conn.execute("SELECT type, amount, category, notes, date FROM transactions ORDER BY id DESC LIMIT 5").fetchall()
    conn.close()
    if recent:
        for r in recent:
            st.markdown(f"← **[{r['date']}]** {r['type']} بقيمة `{r['amount']:,.0f}` د.ع _({r['category'] or ''})_")

# --- تبويب 2: إضافة حركة مالية سريعة ---
with tab_add:
    st.subheader("➕ إدخال حركة مالية سريعة")
    tx_type = st.selectbox("نوع العملية:", ["مبيعات", "مشتريات", "مصروفات", "سحب شخصي", "دين للمحل", "دين على المحل"])
    amount = st.number_input("المبلغ (بالدينار العراقي):", min_value=0.0, step=250.0, format="%.0f")
    tx_date = st.date_input("التاريخ:", date.today(), key="add_tx_date")
    
    category = "عام"
    if tx_type == "مصروفات":
        category = st.selectbox("تصنيف المصروف:", ["كهرباء", "صيانة ثلاجة/معدات", "نقل وأجور شحن", "أدوات ومستلزمات", "أخرى"])
    elif tx_type == "مشتريات":
        category = st.selectbox("تصنيف المشتريات:", ["مواد غذائية", "مشروبات وعصائر", "حلويات وسجائر", "بقوليات", "مواد تنظيف", "أخرى"])
    elif tx_type in ["دين للمحل", "دين على المحل"]:
        category = st.text_input("اسم الشخص (الدائن/المدين):")
        
    notes = st.text_input("ملاحظة توضيحية:")
    
    if st.button("💾 حفظ العملية فوراً"):
        if amount <= 0:
            st.error("أدخل مبلغ أكبر من صفر!")
        else:
            add_transaction(tx_type, amount, tx_date, category, notes)
            st.success(f"✅ تم حفظ العملية بنجاح!")

# --- تبويب 3: إدارة شؤون العمال ---
with tab_workers:
    st.subheader("👥 شؤون العمال والرواتب")
    w_action = st.radio("اختر الإجراء:", ["إضافة عامل", "تسجيل سلفة/راتب", "كشف حساب عامل"], horizontal=True)
    
    if w_action == "إضافة عامل":
        new_emp = st.text_input("اسم العامل الجديد:")
        if st.button("إضافة العامل"):
            if new_emp.strip():
                try:
                    conn = get_db_connection()
                    conn.execute("INSERT INTO employees (name) VALUES (?)", (new_emp.strip(),))
                    conn.commit()
                    conn.close()
                    st.success("تمت الإضافة!")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("الاسم مسجل سابقاً.")
            
    elif w_action == "تسجيل سلفة/راتب":
        emps = get_all_employees()
        if not emps:
            st.info("لا يوجد عمال.")
        else:
            emp_options = {e['name']: e['id'] for e in emps}
            selected_emp = st.selectbox("اختر العامل:", list(emp_options.keys()))
            action_type = st.selectbox("النوع:", ["سلفة", "راتب جزئي", "راتب كامل"])
            emp_amount = st.number_input("المبلغ المدفوع:", min_value=0.0, format="%.0f")
            emp_date = st.date_input("التاريخ:", date.today(), key="emp_tx_date")
            emp_notes = st.text_input("ملاحظة:")
            
            if st.button("حفظ الدفعة"):
                if emp_amount > 0:
                    conn = get_db_connection()
                    conn.execute("INSERT INTO employee_tx (employee_id, type, amount, date, notes) VALUES (?, ?, ?, ?, ?)",
                                 (emp_options[selected_emp], action_type, emp_amount, str(emp_date), emp_notes))
                    conn.execute("INSERT OR IGNORE INTO day_status (date, status) VALUES (?, ?)", (str(emp_date), 'غير مكتمل'))
                    conn.commit()
                    conn.close()
                    st.success("✅ تم الحفظ")
                else:
                    st.error("أدخل مبلغ صحيح")

    elif w_action == "كشف حساب عامل":
        emps = get_all_employees()
        if emps:
            emp_options = {e['name']: e['id'] for e in emps}
            view_emp = st.selectbox("اختر العامل:", list(emp_options.keys()), key="view_emp_tab")
            conn = get_db_connection()
            tx_rows = conn.execute("SELECT type, amount, date, notes FROM employee_tx WHERE employee_id = ? ORDER BY date DESC", (emp_options[view_emp],)).fetchall()
            conn.close()
            
            total_advances = sum(r['amount'] for r in tx_rows if r['type'] == 'سلفة')
            total_salaries = sum(r['amount'] for r in tx_rows if 'راتب' in r['type'])
            
            st.markdown(f"• إجمالي السلف: {total_advances:,.0f} د.ع")
            st.markdown(f"• إجمالي الرواتب: {total_salaries:,.0f} د.ع")
            st.markdown("#### السجل المفصل:")
            for r in tx_rows:
                st.caption(f"← {r['date']} | {r['type']} | {r['amount']:,.0f} د.ع")

# --- تبويب 4: إغلاق ومتابعة الأيام ---
with tab_days:
    st.subheader("📅 مراجعة وإغلاق الأيام المالية")
    conn = get_db_connection()
    unclosed_df = pd.read_sql_query("SELECT * FROM day_status WHERE status != 'مغلق' ORDER BY date DESC", conn)
    conn.close()
    
    if unclosed_df.empty:
        st.success("🎉 جميع الأيام السابقة مغلقة ومكتملة!")
    else:
        selected_date = st.selectbox("اختر اليوم لإغلاقه مالياً:", unclosed_df['date'].tolist())
        conn = get_db_connection()
        t_df = pd.read_sql_query("SELECT * FROM transactions WHERE date = ?", conn, params=(selected_date,))
        e_df = pd.read_sql_query("SELECT tx.* FROM employee_tx tx WHERE tx.date = ?", conn, params=(selected_date,))
        conn.close()
        
        sales = t_df[t_df['type'] == 'مبيعات']['amount'].sum()
        purchases = t_df[t_df['type'] == 'مشتريات']['amount'].sum()
        expenses = t_df[t_df['type'] == 'مصروفات']['amount'].sum()
        owner = t_df[t_df['type'] == 'سحب شخصي']['amount'].sum()
        emp_paid = e_df['amount'].sum()
        expected_cash = sales - purchases - expenses - owner - emp_paid
        
        st.markdown(f"**💰 الكاش المتوقع في القاصة: {expected_cash:,.0f} د.ع**")
        actual_cash = st.number_input("💵 أدخل الكاش الفعلي الموجود باليد (عد يدوي):", min_value=0.0, format="%.0f")
        
        diff = actual_cash - expected_cash
        if diff == 0: st.success(" الحسابات متطابقة!")
        elif diff < 0: st.error(f"⚠️ عجز بمقدار: {abs(diff):,.0f} د.ع")
        else: st.info(f"➕ زيادة بمقدار: {diff:,.0f} د.ع")
            
        if st.button("🔒 إغلاق اليوم نهائياً"):
            conn = get_db_connection()
            conn.execute("INSERT INTO day_status (date, status, actual_cash) VALUES (?, 'مغلق', ?) ON CONFLICT(date) DO UPDATE SET status='مغلق', actual_cash=?", (selected_date, actual_cash, actual_cash))
            conn.commit()
            conn.close()
            st.success("تم الإغلاق!")
            st.rerun()

# --- تبويب 5: تقارير أين تذهب الأموال ---
with tab_reports:
    st.subheader("📊 أين تذهب أموال محل فيروز؟")
    report_type = st.radio("نطاق التقرير:", ["يومي", "شهري", "سنوي"], horizontal=True)
    
    conn = get_db_connection()
    t_all = pd.read_sql_query("SELECT * FROM transactions", conn)
    e_all = pd.read_sql_query("SELECT * FROM employee_tx", conn)
    conn.close()
    
    if not t_all.empty or not e_all.empty:
        t_all['date'] = pd.to_datetime(t_all['date'])
        e_all['date'] = pd.to_datetime(e_all['date'])
        
        if report_type == "يومي":
            t_f = t_all[t_all['date'].dt.date == st.date_input("اختر اليوم:", date.today(), key="rep_date")]
            e_f = e_all[e_all['date'].dt.date == date.today()]
        elif report_type == "شهري":
            m = st.slider("الشهر الحالي:", 1, 12, int(date.today().month))
            t_f = t_all[(t_all['date'].dt.month == m) & (t_all['date'].dt.year == 2026)]
            e_f = e_all[(e_all['date'].dt.month == m) & (e_all['date'].dt.year == 2026)]
        else:
            t_f = t_all[t_all['date'].dt.year == 2026]
            e_f = e_all[e_all['date'].dt.year == 2026]
            
        sales = t_f[t_f['type'] == 'مبيعات']['amount'].sum()
        purchases = t_f[t_f['type'] == 'مشتريات']['amount'].sum()
        expenses = t_f[t_f['type'] == 'مصروفات']['amount'].sum()
        owner_draw = t_f[t_f['type'] == 'سحب شخصي']['amount'].sum()
        emp_advances = e_f[e_f['type'] == 'سلفة']['amount'].sum()
        emp_salaries = e_f[e_f['type'].str.contains('راتب', na=False)]['amount'].sum()
        
        net_profit = sales - (purchases + expenses + emp_advances + emp_salaries)
        
        st.metric("🟢 إجمالي المبيعات (الدخل)", f"{sales:,.0f} د.ع")
        st.metric("🔴 المشتريات والمصاريف الكلية", f"{(purchases + expenses + emp_advances + emp_salaries):,.0f} د.ع")
        st.markdown(f"### 🏆 صافي الربح الحقيقي الحركي: **{net_profit:,.0f} د.ع**")
        
        # الرسم البياني
        labels = ['مشتريات بضاعة', 'مصروفات تشغيلية', 'سحبيات تحسين', 'سلف عمال', 'رواتب عمال']
        values = [purchases, expenses, owner_draw, emp_advances, emp_salaries]
        if sum(values) > 0:
            fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.4)])
            fig.update_layout(margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)

# --- تبويب 6: النسخ الاحتياطي والأمان ---
with tab_backup:
    st.subheader("💾 النسخ الاحتياطي للبيانات")
    if st.button("📤 تصدير نسخة احتياطية فورية"):
        conn = get_db_connection()
        backup_dict = {
            "transactions": [dict(r) for r in conn.execute("SELECT * FROM transactions").fetchall()],
            "employees": [dict(r) for r in conn.execute("SELECT * FROM employees").fetchall()],
            "employee_tx": [dict(r) for r in conn.execute("SELECT * FROM employee_tx").fetchall()],
            "day_status": [dict(r) for r in conn.execute("SELECT * FROM day_status").fetchall()]
        }
        conn.close()
        st.download_button(
            label="📥 اضغط هنا للتحميل والحفظ على الهاتف",
            data=json.dumps(backup_dict, ensure_ascii=False, indent=4),
            file_name=f"fairoz_backup_{date.today()}.json",
            mime="application/json"
        )
        
    st.markdown("---")
    uploaded_file = st.file_uploader("استعادة البيانات من ملف (.json):", type=["json"])
    if uploaded_file is not None and st.button("⚠️ تأكيد مسح البيانات القديمة والاستعادة"):
        try:
            backup_data = json.load(uploaded_file)
            conn = get_db_connection()
            conn.execute("DELETE FROM transactions"); conn.execute("DELETE FROM employees")
            conn.execute("DELETE FROM employee_tx"); conn.execute("DELETE FROM day_status")
            
            for r in backup_data.get('employees', []): conn.execute("INSERT INTO employees (id, name) VALUES (?, ?)", (r['id'], r['name']))
            for r in backup_data.get('transactions', []): conn.execute("INSERT INTO transactions (id, type, amount, date, category, notes) VALUES (?, ?, ?, ?, ?, ?)", (r['id'], r['type'], r['amount'], r['date'], r['category'], r['notes']))
            for r in backup_data.get('employee_tx', []): conn.execute("INSERT INTO employee_tx (id, employee_id, type, amount, date, notes) VALUES (?, ?, ?, ?, ?, ?)", (r['id'], r['employee_id'], r['type'], r['amount'], r['date'], r['notes']))
            for r in backup_data.get('day_status', []): conn.execute("INSERT INTO day_status (date, status, actual_cash) VALUES (?, ?, ?)", (r['date'], r['status'], r['actual_cash']))
            conn.commit(); conn.close()
            st.success("🎉 تمت استعادة كافة الحسابات بنجاح!")
            st.rerun()
        except Exception as e:
            st.error(f"الملف غير صحيح: {e}")
            
    if st.button("🚪 تسجيل الخروج"):
        st.session_state['authenticated'] = False
        st.rerun()

