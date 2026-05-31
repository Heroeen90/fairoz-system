import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
import json
import plotly.graph_objects as go

# ==========================================
# 1. إعدادات الصفحة العامة (Mobile-Friendly)
# ==========================================
st.set_page_config(
    page_title="نظام إدارة محل فيروز",
    page_icon="💎",
    layout="centered",  # أفضل للهواتف للحفاظ على تماسك الواجهة
    initial_sidebar_state="collapsed"
)

# تصميم مخصص CSS لجعل الواجهة تبدو كتطبيق هاتف ذكي واحترافي
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap');
    
    * {
        font-family: 'Tajawal', sans-serif;
        direction: rtl;
        text-align: right;
    }
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        font-size: 16px;
        padding: 10px;
        margin-top: 5px;
    }
    .main-card {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 15px;
    }
    .metric-val {
        font-size: 20px;
        font-weight: bold;
        color: #1E3A8A;
    }
    /* تعديل اتجاه القوائم الجانبية وعناصر التحكم */
    div[data-testid="stSidebarNav"] {
        direction: rtl;
    }
    .stTextInput input, .stNumberInput input, .stSelectbox select {
        text-align: right;
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
    
    # جدول العمال
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    )""")
    
    # جدول العمليات المالية المالية الأساسية
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT NOT NULL,         -- مبيعات, مشتريات, مصروفات, سحب شخصي, دين للمحل, دين على المحل
        amount REAL NOT NULL,
        date TEXT NOT NULL,         -- YYYY-MM-DD
        category TEXT,              -- تصنيف فرعي (كهرباء, نقل, زبائن, إلخ)
        notes TEXT
    )""")
    
    # جدول رواتب وسلف العمال
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS employee_tx (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER,
        type TEXT NOT NULL,         -- سلفة, راتب جزئي, راتب كامل
        amount REAL NOT NULL,
        date TEXT NOT NULL,
        notes TEXT,
        FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
    )""")
    
    # جدول حالة الأيام والخزنة
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS day_status (
        date TEXT PRIMARY KEY,       -- YYYY-MM-DD
        status TEXT NOT NULL,        -- مفتوح, غير مكتمل, مغلق
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
    
    # زر دخول عريض مناسب للموبايل
    if st.button("دخول المالك تحسين"):
        if pin_input == "1234":  # الرمز الافتراضي المطلوب
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
    # تحديث تلقائي لحالة اليوم إذا لم يكن مسجلاً
    conn.execute("INSERT OR IGNORE INTO day_status (date, status) VALUES (?, ?)", (str(t_date), 'غير مكتمل'))
    conn.commit()
    conn.close()

def get_all_employees():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM employees").fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ==========================================
# 5. القائمة الجانبية للتنقل (Sidebar)
# ==========================================
st.sidebar.title("💎 قائمة النظام")
page = st.sidebar.radio("انتقل إلى:", [
    "📱 لوحة التحكم السريعة",
    "➕ إضافة حركة مالية",
    "👥 إدارة شؤون العمال",
    "📅 إغلاق ومتابعة الأيام",
    "📊 تقارير أين تذهب الأموال",
    "💾 النسخ الاحتياطي والأمان"
])

# زر تسجيل الخروج
if st.sidebar.button("تسجيل الخروج"):
    st.session_state['authenticated'] = False
    st.rerun()

# ==========================================
# 6. الصفحات والواجهات (Pages)
# ==========================================

# --- الصفحة 1: لوحة التحكم السريعة ---
if page == "📱 لوحة التحكم السريعة":
    st.title("📱 لوحة التحكم اليومية")
    today_str = str(date.today())
    
    # جلب بيانات اليوم الحالية
    conn = get_db_connection()
    day_info = conn.execute("SELECT * FROM day_status WHERE date = ?", (today_str,)).fetchone()
    day_status = day_info['status'] if day_info else "لم يبدأ بعد"
    
    # عرض حالة اليوم الحالية
    st.info(f"📅 تاريخ اليوم: {today_str} | حالة اليوم: **{day_status}**")
    
    # حساب سريع لملخص اليوم الحقيقي الحالي
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
    
    # النقد المتوقع في الخزنة حالياً
    expected_cash = sales - purchases - expenses - owner - emp_paid
    
    # كروت عرض سريعة ممتازة للهاتف
    st.markdown("### 💰 كشف الخزنة السريع اليوم")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"<div class='main-card'>💵 إجمالي المبيعات<br><span class='metric-val'>{sales:,.0f} د.ع</span></div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='main-card'>🏧 الكاش المتوقع بالصندوق<br><span class='metric-val'>{expected_cash:,.0f} د.ع</span></div>", unsafe_allow_html=True)
        
    # تنبيهات هامة للمالك تحسين
    st.markdown("### ⚠️ تنبيهات النظام")
    conn = get_db_connection()
    uncompleted_days = conn.execute("SELECT COUNT(*) FROM day_status WHERE status = 'غير مكتمل'").fetchone()[0]
    debts_to_store = conn.execute("SELECT SUM(amount) FROM transactions WHERE type = 'دين للمحل'").fetchone()[0] or 0
    debts_from_store = conn.execute("SELECT SUM(amount) FROM transactions WHERE type = 'دين على المحل'").fetchone()[0] or 0
    conn.close()
    
    if uncompleted_days > 0:
        st.warning(f"🔔 يوجد عدد ({uncompleted_days}) أيام غير مكتملة الإغلاق المالي. توجه لصفحة إغلاق الأيام.")
    if debts_to_store > 0:
        st.info(f"📈 إجمالي الديون المستحقة للمحل بطرف الزبائن: {debts_to_store:,.0f} د.ع")
    if debts_from_store > 0:
        st.error(f"📉 إجمالي الديون المطلوبة من المحل للمجهزين: {debts_from_store:,.0f} د.ع")

    # آخر 5 عمليات مسجلة بالسيستم مجمعة لسرعة المراجعة
    st.markdown("### ⏱️ آخر 5 عمليات مالية مسجلة")
    conn = get_db_connection()
    recent = conn.execute("SELECT type, amount, category, notes, date FROM transactions ORDER BY id DESC LIMIT 5").fetchall()
    conn.close()
    if recent:
        for r in recent:
            st.text(f"← [{r['date']}] {r['type']} بقيمة {r['amount']:,.0f} د.ع ({r['category'] or ''} - {r['notes'] or ''})")
    else:
        st.caption("لا توجد عمليات مسجلة بعد اليوم.")

# --- الصفحة 2: إضافة حركة مالية سريعة ---
elif page == "➕ إضافة حركة مالية":
    st.title("➕ إدخال حركة مالية سريع")
    
    tx_type = st.selectbox("اختر نوع العملية المالية:", [
        "مبيعات", "مشتريات", "مصروفات", "سحب شخصي", "دين للمحل", "دين على المحل"
    ])
    
    amount = st.number_input("المبلغ (بالدينار العراقي):", min_value=0.0, step=250.0, format="%.0f")
    tx_date = st.date_input("التاريخ:", date.today())
    
    # تكييف التصنيفات بناءً على النوع لمنع التشتت والسرعة (أقل من 5 ثواني)
    category = "عام"
    if tx_type == "مصروفات":
        category = st.selectbox("تصنيف المصروفات:", ["كهرباء", "صيانة ثلاجة/معدات", "نقل وأجور شحن", "أدوات ومستلزمات", "أخرى"])
    elif tx_type == "مشتريات":
        category = st.selectbox("تصنيف المشتريات البضاعة:", ["مواد غذائية", "مشروبات وعصائر", "حلويات وسجائر", "بقوليات", "مواد تنظيف", "أخرى"])
    elif tx_type in ["دين للمحل", "دين على المحل"]:
        category = st.text_input("اسم الشخص الدائن / المدين:")
        
    notes = st.text_input("ملاحظة إضافية توضيحية (اختياري):")
    
    if st.button("💾 حفظ العملية فوراً"):
        if amount <= 0:
            st.error("الرجاء إدخال مبلغ أكبر من صفر!")
        else:
            add_transaction(tx_type, amount, tx_date, category, notes)
            st.success(f"✅ تم تسجيل عملية ({tx_type}) بمبلغ {amount:,.0f} د.ع بنجاح!")

# --- الصفحة 3: إدارة شؤون العمال ---
elif page == "👥 إدارة شؤون العمال":
    st.title("👥 إدارة العمال (الرواتب والسلف الديناميكية)")
    
    tab1, tab2, tab3 = st.tabs(["➕ إضافة عامل جديد", "💰 دفع (سلفة / راتب)", "📊 كشف حساب عامل"])
    
    with tab1:
        new_emp = st.text_input("اسم العامل الثنائي:")
        if st.button("إضافة العامل للنظام"):
            if new_emp.strip() != "":
                try:
                    conn = get_db_connection()
                    conn.execute("INSERT INTO employees (name) VALUES (?)", (new_emp.strip(),))
                    conn.commit()
                    conn.close()
                    st.success(f"تم تسجيل العامل [{new_emp}] في النظام.")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("هذا الاسم مسجل مسبقاً!")
            else:
                st.error("الرجاء كتابة اسم صحيح.")
                
    with tab2:
        emps = get_all_employees()
        if not emps:
            st.info("لا يوجد عمال مضافين حالياً.")
        else:
            emp_options = {e['name']: e['id'] for e in emps}
            selected_emp = st.selectbox("اختر العامل:", list(emp_options.keys()))
            action_type = st.selectbox("نوع الدفعة المالية:", ["سلفة", "راتب جزئي", "راتب كامل"])
            emp_amount = st.number_input("المبلغ المدفوع:", min_value=0.0, step=1000.0, format="%.0f", key="emp_pay")
            emp_date = st.date_input("تاريخ الدفع:", date.today(), key="emp_date")
            emp_notes = st.text_input("ملاحظات:", key="emp_notes")
            
            if st.button("حفظ دفعة العامل"):
                if emp_amount <= 0:
                    st.error("أدخل مبلغاً حقيقياً.")
                else:
                    conn = get_db_connection()
                    conn.execute(
                        "INSERT INTO employee_tx (employee_id, type, amount, date, notes) VALUES (?, ?, ?, ?, ?)",
                        (emp_options[selected_emp], action_type, emp_amount, str(emp_date), emp_notes)
                    )
                    conn.execute("INSERT OR IGNORE INTO day_status (date, status) VALUES (?, ?)", (str(emp_date), 'غير مكتمل'))
                    conn.commit()
                    conn.close()
                    st.success(f"✅ تم تسجيل {action_type} للعامل {selected_emp} بقيمة {emp_amount:,.0f} د.ع")

    with tab3:
        emps = get_all_employees()
        if emps:
            emp_options = {e['name']: e['id'] for e in emps}
            view_emp = st.selectbox("اختر العامل لعرض كشفه:", list(emp_options.keys()), key="view_emp")
            
            conn = get_db_connection()
            tx_rows = conn.execute("""
                SELECT type, amount, date, notes FROM employee_tx 
                WHERE employee_id = ? ORDER BY date DESC
            """, (emp_options[view_emp],)).fetchall()
            conn.close()
            
            # حساب إجماليات العامل
            total_advances = sum(r['amount'] for r in tx_rows if r['type'] == 'سلفة')
            total_salaries = sum(r['amount'] for r in tx_rows if 'راتب' in r['type'])
            
            st.markdown(f"### 📊 ملخص حساب: {view_emp}")
            st.text(f"• إجمالي السلف المسحوبة: {total_advances:,.0f} د.ع")
            st.text(f"• إجمالي الرواتب المستلمة: {total_salaries:,.0f} د.ع")
            st.text(f"• إجمالي ما تم صرفه للعامل: {(total_advances + total_salaries):,.0f} د.ع")
            
            st.markdown("#### سجل الدفعات المفصل:")
            if tx_rows:
                for r in tx_rows:
                    st.caption(f"← التاريخ: {r['date']} | النوع: {r['type']} | المبلغ: {r['amount']:,.0f} د.ع | ملاحظة: {r['notes'] or 'لا يوجد'}")
            else:
                st.caption("لا توجد دفعات مسجلة لهذا العامل.")

# --- الصفحة 4: إغلاق ومتابعة الأيام ---
elif page == "📅 إغلاق ومتابعة الأيام":
    st.title("📅 نظام تتبع وإغلاق الأيام المالية")
    
    conn = get_db_connection()
    unclosed_df = pd.read_sql_query("SELECT * FROM day_status WHERE status != 'مغلق' ORDER BY date DESC", conn)
    conn.close()
    
    if unclosed_df.empty:
        st.success("🎉 ممتااااز يا تحسين! جميع الأيام السابقة مغلقة ومكتملة مالياً بشكل صحيح.")
    else:
        st.subheader("الأيام المفتوحة وغير المكتملة")
        selected_date = st.selectbox("اختر تاريخ اليوم المراد مراجعته وإغلاقه:", unclosed_df['date'].tolist())
        
        # جلب تفاصيل ذلك اليوم محدد
        conn = get_db_connection()
        t_df = pd.read_sql_query("SELECT * FROM transactions WHERE date = ?", conn, params=(selected_date,))
        e_df = pd.read_sql_query(
            "SELECT tx.*, e.name FROM employee_tx tx JOIN employees e ON tx.employee_id = e.id WHERE tx.date = ?", 
            conn, params=(selected_date,)
        )
        conn.close()
        
        sales = t_df[t_df['type'] == 'مبيعات']['amount'].sum()
        purchases = t_df[t_df['type'] == 'مشتريات']['amount'].sum()
        expenses = t_df[t_df['type'] == 'مصروفات']['amount'].sum()
        owner = t_df[t_df['type'] == 'سحب شخصي']['amount'].sum()
        emp_paid = e_df['amount'].sum()
        
        expected_cash = sales - purchases - expenses - owner - emp_paid
        
        st.markdown(f"### 📋 ملخص الحسابات ليوم: {selected_date}")
        st.text(f"1. إجمالي مبيعات اليوم المستلمة: {sales:,.0f} د.ع")
        st.text(f"2. مشتريات بضاعة نقدية من الصندوق: {purchases:,.0f} د.ع")
        st.text(f"3. مصروفات تشغيلية (صيانة، كهرباء..): {expenses:,.0f} د.ع")
        st.text(f"4. سحبيات شخصية (تحسين): {owner:,.0f} د.ع")
        st.text(f"5. رواتب وسلف مدفوعة للعمال اليوم: {emp_paid:,.0f} د.ع")
        st.markdown(f"**💰 الرصيد النقدي (الكاش) المتوقع وجوده في القاصة: {expected_cash:,.0f} د.ع**")
        
        st.markdown("---")
        actual_cash = st.number_input("💰 أدخل مبلغ الكاش الفعلي الموجود في القاصة الآن (عد يدوي):", min_value=0.0, format="%.0f")
        
        diff = actual_cash - expected_cash
        if diff == 0:
            st.success("✅ الحسابات متطابقة تماماً 100%! لا يوجد أي عجز أو زيادة.")
        elif diff < 0:
            st.error(f"⚠️ يوجد عجز مالي في القاصة بقيمة: {abs(diff):,.0f} د.ع! (الفلوس ناقصة)")
        else:
            st.info(f"➕ يوجد زيادة نقدية في القاصة غير مفسرة بقيمة: {diff:,.0f} د.ع!")
            
        if st.button("🔒 إغلاق اليوم نهائياً وحفظ الفروقات"):
            conn = get_db_connection()
            conn.execute(
                "INSERT INTO day_status (date, status, actual_cash) VALUES (?, 'مغلق', ?) ON CONFLICT(date) DO UPDATE SET status='مغلق', actual_cash=?",
                (selected_date, actual_cash, actual_cash)
            )
            conn.commit()
            conn.close()
            st.success(f"تم إغلاق يوم {selected_date} نهائياً بالسيستم.")
            st.rerun()

# --- الصفحة 5: تقارير أين تذهب الأموال الشاملة ---
elif page == "📊 تقارير أين تذهب الأموال":
    st.title("📊 تقرير الإجابة الشامل: أين تذهب أموال محل فيروز؟")
    
    report_type = st.radio("اختر نطاق التقرير التحليلي:", ["يومي بالفترات", "شهري مجمع", "سنوي مجمع"], horizontal=True)
    
    conn = get_db_connection()
    t_all = pd.read_sql_query("SELECT * FROM transactions", conn)
    e_all = pd.read_sql_query("SELECT * FROM employee_tx", conn)
    conn.close()
    
    if t_all.empty and e_all.empty:
        st.info("لا توجد بيانات كافية لإصدار التقارير حالياً. ابدأ بإدخال الحركات.")
    else:
        # تحويل التواريخ لمنطق الباندا للتصفية المتقدمة
        t_all['date'] = pd.to_datetime(t_all['date'])
        e_all['date'] = pd.to_datetime(e_all['date'])
        
        if report_type == "يومي بالفترات":
            target_date = st.date_input("اختر اليوم المستهدف للتقرير:", date.today())
            t_filtered = t_all[t_all['date'].dt.date == target_date]
            e_filtered = e_all[e_all['date'].dt.date == target_date]
        elif report_type == "شهري مجمع":
            current_year = date.today().year
            selected_month = st.slider("اختر رقم الشهر المالي المطلوبة دراسته:", 1, 12, int(date.today().month))
            t_filtered = t_all[(t_all['date'].dt.month == selected_month) & (t_all['date'].dt.year == current_year)]
            e_filtered = e_all[(e_all['date'].dt.month == selected_month) & (e_all['date'].dt.year == current_year)]
        else:
            selected_year = st.selectbox("اختر السنة المالية:", [2026, 2027, 2025])
            t_filtered = t_all[t_all['date'].dt.year == selected_year]
            e_filtered = e_all[e_all['date'].dt.year == selected_year]
            
        # الحسابات المجمعة الدقيقة
        sales = t_filtered[t_filtered['type'] == 'مبيعات']['amount'].sum()
        purchases = t_filtered[t_filtered['type'] == 'مشتريات']['amount'].sum()
        expenses = t_filtered[t_filtered['type'] == 'مصروفات']['amount'].sum()
        owner_draw = t_filtered[t_filtered['type'] == 'سحب شخصي']['amount'].sum()
        
        debts_to_us = t_filtered[t_filtered['type'] == 'دين للمحل']['amount'].sum()
        debts_from_us = t_filtered[t_filtered['type'] == 'دين على المحل']['amount'].sum()
        
        emp_advances = e_filtered[e_filtered['type'] == 'سلفة']['amount'].sum()
        emp_salaries = e_filtered[e_filtered['type'].str.contains('راتب')]['amount'].sum()
        
        # صافي الربح الحقيقي للمحل قبل سحب المالك شخصياً
        # صافي الربح الحقيقي = المبيعات - (المشتريات + المصروفات + إجمالي الرواتب والسلف الممنوحة)
        net_profit = sales - (purchases + expenses + emp_advances + emp_salaries)
        
        # عرض الأرقام المالية الكبيرة بشكل مرتب وتصميم جذاب
        st.markdown("### 📊 النتائج المالية الدقيقة للفترة المحددة")
        
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            st.metric("🟢 إجمالي المبيعات (دفقات المال الداخل)", f"{sales:,.0f} د.ع")
            st.metric("🔴 إجمالي مشتريات بضاعة للمحل", f"{purchases:,.0f} د.ع")
            st.metric("💸 مصروفات التشغيل العامة", f"{expenses:,.0f} د.ع")
            st.metric("💼 سحبيات المالك الشخصية (تحسين)", f"{owner_draw:,.0f} د.ع")
        with col_r2:
            st.metric("👥 إجمالي سلف العمال المدفوعة", f"{emp_advances:,.0f} د.ع")
            st.metric("💰 إجمالي الرواتب المصروفة", f"{emp_salaries:,.0f} د.ع")
            st.metric("📈 ديون جديدة للمحل (على الزبائن)", f"{debts_to_us:,.0f} د.ع")
            st.metric("📉 ديون جديدة على المحل (للموردين)", f"{debts_from_us:,.0f} د.ع")
            
        st.markdown("---")
        if net_profit >= 0:
            st.success(f"🏆 صافي الربح الحقيقي الفعلي للمحل في هذه الفترة: {net_profit:,.0f} د.ع")
        else:
            st.error(f"🚨 صافي خسارة حقيقية للفترة المحددة: {net_profit:,.0f} د.ع (المصاريف تجاوزت الدخل)")
            
        # رسم بياني احترافي دائري يوضح بالملي أين تذهب الأموال (مستثنى المبيعات لأنها دخل)
        st.markdown("### 🍩 المخطط البياني: تشريح وتقسيم المصاريف أين ذهبت؟")
        labels = ['مشتريات بضاعة', 'مصروفات تشغيلية', 'سحبيات تحسين', 'سلف عمال', 'رواتب عمال']
        values = [purchases, expenses, owner_draw, emp_advances, emp_salaries]
        
        if sum(values) > 0:
            fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.4, textinfo='percent+label')])
            fig.update_layout(showlegend=False, margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("لا توجد مصاريف أو حركات خارجة لعرضها في الرسم البياني.")

        # جدول الملاحظات والمطالبات الهامة لكشف الملاحظات المكتوبة باليد
        st.markdown("### 📝 الملاحظات المالية المسجلة خلال هذه الفترة")
        notes_list = t_filtered[t_filtered['notes'].str.strip() != ''][['type', 'amount', 'notes', 'category']]
        if not notes_list.empty:
            for _, row in notes_list.iterrows():
                st.markdown(f"• **[{row['type']} - {row['category']}]** كتب تحسين ملاحظة: *\"{row['notes']}\"* بمبلغ {row['amount']:,.0f} د.ع")
        else:
            st.caption("لم يتم تدوين ملاحظات نصية خاصة خلال هذه المدة.")

# --- الصفحة 6: النسخ الاحتياطي وإعدادات الأمان ---
elif page == "💾 النسخ الاحتياطي والأمان":
    st.title("💾 نظام أمان البيانات والتصدير الاحترافي")
    st.markdown("حفاظاً على بيانات محل فيروز من الضياع أو عند تغيير الهاتف المحمول، يمكنك تصدير أو استعادة كامل النظام بضغطة واحدة كملف نصي موثوق.")
    
    # تصدير البيانات إلى JSON للتحميل على الموبايل مباشرة
    if st.button("📤 توليد وتصدير نسخة احتياطية شاملة للنظام"):
        conn = get_db_connection()
        tx_data = [dict(r) for r in conn.execute("SELECT * FROM transactions").fetchall()]
        emp_data = [dict(r) for r in conn.execute("SELECT * FROM employees").fetchall()]
        emp_tx_data = [dict(r) for r in conn.execute("SELECT * FROM employee_tx").fetchall()]
        day_data = [dict(r) for r in conn.execute("SELECT * FROM day_status").fetchall()]
        conn.close()
        
        backup_dict = {
            "transactions": tx_data,
            "employees": emp_data,
            "employee_tx": emp_tx_data,
            "day_status": day_data
        }
        
        json_string = json.dumps(backup_dict, ensure_ascii=False, indent=4)
        st.download_button(
            label="📥 اضغط هنا الآن لتحميل ملف النسخة الاحتياطية على هاتفك",
            data=json_string,
            file_name=f"fairoz_store_backup_{date.today()}.json",
            mime="application/json"
        )
        st.success("تم تجهيز ملف النسخة الاحتياطية بنجاح.")

    st.markdown("---")
    st.subheader("📥 استعادة البيانات من نسخة احتياطية")
    uploaded_file = st.file_uploader("اختر ملف النسخة الاحتياطية (.json) من ذاكرة الهاتف:", type=["json"])
    
    if uploaded_file is not None:
        if st.button("⚠️ تأكيد مسح البيانات الحالية واستعادة البيانات المرفوعة"):
            try:
                backup_data = json.load(uploaded_file)
                conn = get_db_connection()
                
                # مسح الجداول القديمة تماماً لتفادي تكرار المفاتيح الأساسية
                conn.execute("DELETE FROM transactions")
                conn.execute("DELETE FROM employees")
                conn.execute("DELETE FROM employee_tx")
                conn.execute("DELETE FROM day_status")
                
                # إعادة ملء الجداول من ملف الـ Backup المرفوع
                for r in backup_data.get('employees', []):
                    conn.execute("INSERT INTO employees (id, name) VALUES (?, ?)", (r['id'], r['name']))
                for r in backup_data.get('transactions', []):
                    conn.execute("INSERT INTO transactions (id, type, amount, date, category, notes) VALUES (?, ?, ?, ?, ?, ?)",
                                 (r['id'], r['type'], r['amount'], r['date'], r['category'], r['notes']))
                for r in backup_data.get('employee_tx', []):
                    conn.execute("INSERT INTO employee_tx (id, employee_id, type, amount, date, notes) VALUES (?, ?, ?, ?, ?, ?)",
                                 (r['id'], r['employee_id'], r['type'], r['amount'], r['date'], r['notes']))
                for r in backup_data.get('day_status', []):
                    conn.execute("INSERT INTO day_status (date, status, actual_cash) VALUES (?, ?, ?)",
                                 (r['date'], r['status'], r['actual_cash']))
                    
                conn.commit()
                conn.close()
                st.success("🎉 تمت استعادة كامل بيانات محل فيروز بنجاح وتحديث النظام بالكامل!")
                st.rerun()
            except Exception as e:
                st.error(f"حدث خطأ أثناء قراءة الملف، تأكد من سلامة الملف المرفوع. تفاصيل الخطأ: {e}")
