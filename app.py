import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
import json
import plotly.graph_objects as go

# ==========================================
# 1. إعدادات الصفحة العامة (اصلاح واجهة الموبايل)
# ==========================================
st.set_page_config(
    page_title="نظام إدارة محل فيروز",
    page_icon="💎",
    layout="centered", 
    initial_sidebar_state="auto" # تم تغييرها لتفادي مشاكل الفتح التلقائي المشوه على المتصفحات المحمولة
)

# تصميم مخصص CSS مطور لمنع التداخل اللغوي والنصوص العمودية على الموبايل
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap');
    
    /* إعدادات الاتجاه العام لمنع النصوص العمودية */
    html, body, [data-testid="stAppViewContainer"], .main {
        font-family: 'Tajawal', sans-serif;
        direction: rtl !important;
        text-align: right !important;
    }
    
    /* إجبار القائمة الجانبية على البقاء في مكانها بشكل نظيف وبدون تداخل */
    [data-testid="stSidebar"] {
        direction: rtl !important;
        text-align: right !important;
    }
    
    /* إصلاح تداخل العناوين الكبيرة وتعديل حجم الخط ليتناسب مع شاشة الهاتف */
    h1 {
        font-size: 24px !important;
        padding-top: 10px !important;
        padding-bottom: 10px !important;
        word-wrap: break-word !important;
    }
    h2 {
        font-size: 20px !important;
    }
    h3 {
        font-size: 18px !important;
    }

    /* تحسين شكل الأزرار لتكون عريضة ومناسبة للمس */
    .stButton>button {
        width: 100% !important;
        border-radius: 10px !important;
        font-size: 16px !important;
        padding: 10px !important;
        margin-top: 5px !important;
    }
    
    /* تنسيق كروت العرض الحسابية اليومية */
    .main-card {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 15px;
        border-right: 5px solid #1E3A8A; /* إشارة جمالية جانبية بدلاً من التداخل */
    }
    
    .metric-val {
        font-size: 22px;
        font-weight: bold;
        color: #1E3A8A;
        display: block;
        margin-top: 5px;
    }

    /* محاذاة حقول الإدخال */
    .stTextInput input, .stNumberInput input, .stSelectbox select {
        text-align: right !important;
        direction: rtl !important;
    }
    
    /* إخفاء السهم الافتراضي المشوه للنصوص الملتفة */
    [data-testid="stSidebarNav"] ul {
        padding-right: 0px !important;
        list-style-type: none !important;
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
# 5. القائمة الجانبية المحمية من التشويه (Sidebar)
# ==========================================
st.sidebar.markdown("### 💎 قائمة النظام")
page = st.sidebar.radio("انتقل إلى الصفحات:", [
    "📱 لوحة التحكم السريعة",
    "➕ إضافة حركة مالية",
    "👥 إدارة شؤون العمال",
    "📅 إغلاق ومتابعة الأيام",
    "📊 تقارير أين تذهب الأموال",
    "💾 النسخ الاحتياطي والأمان"
])

if st.sidebar.button("تسجيل الخروج"):
    st.session_state['authenticated'] = False
    st.rerun()

# ==========================================
# 6. الواجهات البرمجية للمستخدم (Pages)
# ==========================================

# --- الصفحة 1: لوحة التحكم السريعة ---
if page == "📱 لوحة التحكم السريعة":
    st.title("📱 لوحة التحكم اليومية")
    today_str = str(date.today())
    
    conn = get_db_connection()
    day_info = conn.execute("SELECT * FROM day_status WHERE date = ?", (today_str,)).fetchone()
    day_status = day_info['status'] if day_info else "لم يبدأ بعد"
    
    st.info(f"📅 تاريخ اليوم: {today_str} | حالة اليوم: **{day_status}**")
    
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
    
    # تحويل الكروت إلى هيكل تتابعي عمودي بدلاً من الأعمدة الجانبية لتفادي التداخل على الهواتف الضيقة
    st.markdown(f"<div class='main-card'>💵 إجمالي المبيعات المستلمة للعام الفعلي اليوم:<br><span class='metric-val'>{sales:,.0f} د.ع</span></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='main-card'>🏧 الكاش النظري المتوقع بالصندوق حالياً:<br><span class='metric-val'>{expected_cash:,.0f} د.ع</span></div>", unsafe_allow_html=True)
        
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

    st.markdown("### ⏱️ آخر 5 عمليات مالية مسجلة")
    conn = get_db_connection()
    recent = conn.execute("SELECT type, amount, category, notes, date FROM transactions ORDER BY id DESC LIMIT 5").fetchall()
    conn.close()
    if recent:
        for r in recent:
            st.markdown(f"← **[{r['date']}]** {r['type']} بقيمة `{r['amount']:,.0f}` د.ع _({r['category'] or ''} - {r['notes'] or ''})_")
    else:
        st.caption("لا توجد عمليات مسجلة بعد اليوم.")

# --- الصفحة 2: إضافة حركة مالية سريعة ---
elif page == "➕ إضافة حركة مالية":
    st.title("➕ إدخل حركة مالية سريع")
    
    tx_type = st.selectbox("اختر نوع العملية المالية:", [
        "مبيعات", "مشتريات", "مصروفات", "سحب شخصي", "دين للمحل", "دين على المحل"
    ])
    
    amount = st.number_input("المبلغ (بالدينار العراقي):", min_value=0.0, step=250.0, format="%.0f")
    tx_date = st.date_input("التاريخ:", date.today())
    
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
    st.title("👥 إدارة العمال")
    
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
    st.title("📅 نظام تتبع وإغلاق الأيام")
    
    conn = get_db_connection()
    unclosed_df = pd.read_sql_query("SELECT * FROM day_status WHERE status != 'مغلق' ORDER BY date DESC", conn)
    conn.close()
    
    if unclosed_df.empty:
        st.success("🎉 جميع الأيام السابقة مغلقة ومكتملة مالياً بشكل صحيح.")
    else:
        st.subheader("الأيام غير المكتملة")
        selected_date = st.selectbox("اختر تاريخ اليوم المراد مراجعته وإغلاقه:", unclosed_df['date'].tolist())
        
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
        st.text(f"3. مصروفات تشغيلية: {expenses:,.0f} د.ع")
        st.text(f"4. سحبيات شخصية (تحسين): {owner:,.0f} د.ع")
        st.text(f"5. رواتب وسلف العمال اليوم: {emp_paid:,.0f} د.ع")
        st.markdown(f"**💰 الرصيد النقدي المتوقع وجوده في القاصة: {expected_cash:,.0f} د.ع**")
        
        st.markdown("---")
        actual_cash = st.number_input("💰 أدخل مبلغ الكاش الفعلي الموجود في القاصة الآن (عد يدوي):", min_value=0.0, format="%.0f")
        
        diff = actual_cash - expected_cash
        if diff == 0:
            st.success("✅ الحسابات متطابقة تماماً 100%!")
        elif diff < 0:
            st.error(f"⚠️ يوجد عجز مالي بقيمة: {abs(diff):,.0f} د.ع! (نقص في الكاش)")
        else:
            st.info(f"➕ يوجد زيادة نقدية بقيمة: {diff:,.0f} د.ع!")
            
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
        st.info("لا توجد بيانات كافية لإصدار التقارير حالياً.")
    else:
        t_all['date'] = pd.to_datetime(t_all['date'])
        e_all['date'] = pd.to_datetime(e_all['date'])
        
        if report_type == "يومي بالفترات":
            target_date = st.date_input("اختر اليوم المستهدف للتقرير:", date.today())
            t_filtered = t_all[t_all['date'].dt.date == target_date]
            e_filtered = e_all[e_all['date'].dt.date == target_date]
        elif report_type == "شهري مجمع":
            current_year = date.today().year
            selected_month = st.slider("اختر رقم الشهر المالي:", 1, 12, int(date.today().month))
            t_filtered = t_all[(t_all['date'].dt.month == selected_month) & (t_all['date'].dt.year == current_year)]
            e_filtered = e_all[(e_all['date'].dt.month == selected_month) & (e_all['date'].dt.year == current_year)]
        else:
            selected_year = st.selectbox("اختر السنة المالية:", [2026, 2027, 2025])
            t_filtered = t_all[t_all['date'].dt.year == selected_year]
            e_filtered = e_all[e_all['date'].dt.year == selected_year]
            
        sales = t_filtered[t_filtered['type'] == 'مبيعات']['amount'].sum()
        purchases = t_filtered[t_filtered['type'] == 'مشتريات']['amount'].sum()
        expenses = t_filtered[t_filtered['type'] == 'مصروفات']['amount'].sum()
        owner_draw = t_filtered[t_filtered['type'] == 'سحب شخصي']['amount'].sum()
        
        debts_to_us = t_filtered[t_filtered['type'] == 'دين للمحل']['amount'].sum()
        debts_from_us = t_filtered[t_filtered['type'] == 'دين على المحل']['amount'].sum()
        
        emp_advances = e_filtered[e_filtered['type'] == 'سلفة']['amount'].sum()
        emp_salaries = e_filtered[e_filtered['type'].str.contains('راتب')]['amount'].sum()
        
        net_profit = sales - (purchases + expenses + emp_advances + emp_salaries)
        
        st.markdown("### 📊 النتائج المالية الدقيقة للفترة المحددة")
        
        st.metric("🟢 إجمالي المبيعات", f"{sales:,.0f} د.ع")
        st.metric("🔴 إجمالي المشتريات", f"{purchases:,.0f} د.ع")
        st.metric("💸 مصروفات التشغيل", f"{expenses:,.0f} د.ع")
        st.metric("💼 سحبيات تحسين الشخصية", f"{owner_draw:,.0f} د.ع")
        st.metric("👥 سلف العمال المدفوعة", f"{emp_advances:,.0f} د.ع")
        st.metric("💰 الرواتب المصروفة", f"{emp_salaries:,.0f} د.ع")
            
        st.markdown("---")
        if net_profit >= 0:
            st.success(f"🏆 صافي الربح الحقيقي للمحل: {net_profit:,.0f} د.ع")
        else:
            st.error(f"🚨 صافي خسارة حقيقية: {net_profit:,.0f} د.ع")
            
        st.markdown("### 🍩 المخطط البياني لتوزيع المصاريف")
        labels = ['مشتريات بضاعة', 'مصروفات تشغيلية', 'سحبيات تحسين', 'سلف عمال', 'رواتب عمال']
        values = [purchases, expenses, owner_draw, emp_advances, emp_salaries]
        
        if sum(values) > 0:
            fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.4, textinfo='percent+label')])
            fig.update_layout(showlegend=True, margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("لا توجد مصاريف لعرضها بيانياً.")

# --- الصفحة 6: النسخ الاحتياطي وإعدادات الأمان ---
elif page == "💾 النسخ الاحتياطي والأمان":
    st.title("💾 نظام أمان البيانات والتصدير")
    
    if st.button("📤 توليد وتصدير نسخة احتياطية شاملة"):
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
            label="📥 اضغط هنا الآن لتحميل ملف النسخة الاحتياطية",
            data=json_string,
            file_name=f"fairoz_store_backup_{date.today()}.json",
            mime="application/json"
        )

    st.markdown("---")
    st.subheader("📥 استعادة البيانات من نسخة احتياطية")
    uploaded_file = st.file_uploader("اختر ملف النسخة الاحتياطية (.json):", type=["json"])
    
    if uploaded_file is not None:
        if st.button("⚠️ تأكيد الاستعادة ومسح البيانات القديمة"):
            try:
                backup_data = json.load(uploaded_file)
                conn = get_db_connection()
                
                conn.execute("DELETE FROM transactions")
                conn.execute("DELETE FROM employees")
                conn.execute("DELETE FROM employee_tx")
                conn.execute("DELETE FROM day_status")
                
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
                st.success("🎉 تمت استعادة كامل البيانات بنجاح!")
                st.rerun()
            except Exception as e:
                st.error(f"حدث خطأ أثناء الاستعادة: {e}")
