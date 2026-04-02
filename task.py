import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import time
import json
import pytz 
from streamlit_javascript import st_javascript 
import io

# --- CONFIGURATION (Maintained as is) ---
DB_BASE_URL = "https://office-task-ledger-default-rtdb.asia-southeast1.firebasedatabase.app"
TASKS_URL = f"{DB_BASE_URL}/tasks.json"
USERS_URL = f"{DB_BASE_URL}/users.json"

STAFF_PASSWORD = "1234"
ADMIN_PASSWORD = "1586"
IST = pytz.timezone('Asia/Kolkata') 

# --- PAGE CONFIG ---
st.set_page_config(page_title="Report Correction Ledger Pro", layout="wide")

# --- CUSTOM STYLES (+2pt Scaling & Full-Height Vertical Bar) ---
st.markdown("""
    <style>
    html, body, [class*="st-"], .stMarkdown p { font-size: 18px !important; } 
    .main { background-color: #000000; }
    .stApp { background-color: #000000; color: #E0E0E0; }
    
    .task-container {
        display: flex;
        background-color: #0A0A0A;
        border: 1px solid #1A1A1A;
        border-radius: 10px;
        margin-bottom: 15px;
        overflow: hidden;
        min-height: 100px;
    }
    
    .status-bar { width: 12px; height: auto; flex-shrink: 0; }
    .status-pending { background-color: #C29100; }
    .status-high { background-color: #B71C1C; }
    .status-completed { background-color: #1B5E20; }
    .status-hold { background-color: #880E4F; }
    
    .task-content { padding: 20px; flex-grow: 1; }
    .task-card strong { font-size: 1.4rem !important; color: #3E91D4; }
    
    /* Completion Box Styling */
    .completion-box {
        background-color: #1B5E2033; 
        border: 1px solid #1B5E20; 
        border-radius: 5px; 
        padding: 10px; 
        margin-left: 20px; 
        margin-bottom: 15px;
    }
    </style>
""", unsafe_allow_html=True)

# --- PERSISTENCE & FINGERPRINTING (Maintained as is) ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'user_data' not in st.session_state: st.session_state.user_data = None

saved_session = st_javascript("localStorage.getItem('office_user');")
if saved_session and not st.session_state.authenticated:
    try:
        user_info = json.loads(saved_session)
        st.session_state.user_data = user_info
        st.session_state.authenticated = True
        st.rerun()
    except: pass

device_id = st_javascript("(async () => { return btoa(navigator.userAgent + screen.width + screen.height); })()")

# --- HELPER FUNCTIONS ---
def get_now_ist(): return datetime.now(IST).strftime("%d/%b/%Y %H:%M:%S")

def fetch_data(): 
    try:
        res = requests.get(TASKS_URL, timeout=5)
        data = res.json() or {}
        if len(data) > 100:
            keys = list(data.keys())[-100:]
            return {k: data[k] for k in keys}
        return data
    except: return {}

def fetch_users():
    try:
        res = requests.get(USERS_URL, timeout=5)
        return res.json() or {}
    except: return {}

# --- LOGIN SCREEN (Maintained as is) ---
if not st.session_state.authenticated:
    st.title("🔐 OFFICE LEDGER LOGIN")
    name_input = st.text_input("Full Name").upper().strip()
    desig_input = st.text_input("Designation").upper().strip()
    pwd_input = st.text_input("Password", type="password")
    
    if st.button("LOGIN") and device_id:
        users = fetch_users()
        is_admin, is_staff = (pwd_input == ADMIN_PASSWORD), (pwd_input == STAFF_PASSWORD)
        if name_input and (is_admin or is_staff):
            if name_input not in users and not is_admin:
                st.error("User not authorized.")
            else:
                role = "ADMIN" if is_admin else "STAFF"
                user_payload = {"name": name_input, "role": role}
                st.session_state.user_data, st.session_state.authenticated = user_payload, True
                st_javascript(f"localStorage.setItem('office_user', '{json.dumps(user_payload)}');")
                st.rerun()
    st.stop()

# --- MAIN UI ---
user = st.session_state.user_data
tasks_dict = fetch_data()

# --- SEARCH & DATE-WISE EXCEL EXPORT ---
st.subheader("🔍 Search & Date-Wise Reports")
search_col, date_col, export_col = st.columns([2, 2, 1])

with search_col:
    search_query = st.text_input("Search Finance/Details", placeholder="Search...").lower()
    prio_filter = st.checkbox("⭐ High Priority Only")

with date_col:
    today = datetime.now(IST)
    date_range = st.date_input("Export Date Range", value=(today - pd.Timedelta(days=7), today))

with export_col:
    if tasks_dict:
        df_export = pd.DataFrame.from_dict(tasks_dict, orient='index')
        if 'assigned_at' in df_export.columns:
            df_export['date_dt'] = pd.to_datetime(df_export['assigned_at'], format="%d/%b/%Y %H:%M:%S", errors='coerce').dt.date
            if len(date_range) == 2:
                start_date, end_date = date_range
                df_filtered = df_export[(df_export['date_dt'] >= start_date) & (df_export['date_dt'] <= end_date)]
            else: df_filtered = df_export
        
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_filtered.to_excel(writer, index=True)
        st.download_button(label="📥 Export Excel", data=buffer.getvalue(), file_name="Ledger_Report.xlsx", use_container_width=True)

# --- ORGANIZED TASK FORM WINDOW ---
st.subheader("📝 Add New Task")
with st.expander("Open Task Form", expanded=True):
    c1, c2 = st.columns(2)
    with c1:
        raw_fins = sorted(list(set(t.get('finance', '').upper() for t in tasks_dict.values() if t.get('finance'))))
        fin_name_sel = st.selectbox("Finance Name", options=["--- SELECT FINANCE ---", "ADD NEW+"] + raw_fins)
        fin_name = st.text_input("New Name").upper() if fin_name_sel == "ADD NEW+" else fin_name_sel
    with c2:
        category = st.selectbox("Category", ["--- SELECT CATEGORY ---", "1. Rate Correction", "2. Spelling/Address", "3. Digital Sign", "4. Report Upload", "5. Photos/Drafting"])
    
    priority = st.select_slider("Priority", options=["Normal", "Medium", "High"])
    task_details = st.text_area("Task Details")
    
    if st.button("🚀 ADD TO LEDGER", use_container_width=True):
        if fin_name != "--- SELECT FINANCE ---" and category != "--- SELECT CATEGORY ---" and task_details:
            new_task = {
                "finance": fin_name, "task": f"[{category}] {task_details}",
                "priority": priority, "assigner": user['name'],
                "status": "Pending", "assigned_at": get_now_ist() 
            }
            requests.post(TASKS_URL, json=new_task)
            st.success("Task Added!")
            time.sleep(1)
            st.rerun()

# --- TASK LIST (Vertical Bar & Completion Details) ---
st.subheader("📋 RECENT ENTRIES")
keys = list(tasks_dict.keys())
keys.reverse() 

for tid in keys:
    task = tasks_dict[tid]
    t_status, t_priority = task.get('status', 'Pending'), task.get('priority', 'Normal')
    
    if search_query and (search_query not in str(task.get('finance','')).lower() and search_query not in str(task.get('task','')).lower()): continue
    if prio_filter and t_priority != "High": continue

    status_class = "status-pending"
    if t_status == "Completed": status_class = "status-completed"
    elif t_status == "Hold": status_class = "status-hold"
    elif t_priority == "High": status_class = "status-high"

    st.markdown(f'''
        <div class="task-container">
            <div class="status-bar {status_class}"></div>
            <div class="task-content">
                <strong>{task.get('finance')}</strong> | <small>Assigned: {task.get('assigned_at')}</small><br>
                {task.get('task')}
            </div>
        </div>
    ''', unsafe_allow_html=True)

    if t_status == "Completed":
        st.markdown(f"""<div class="completion-box">
            <span style="color: #4CAF50; font-weight: bold;">✅ COMPLETION RECORD:</span><br>
            <small><b>Done By:</b> {task.get('completed_by', 'N/A')}</small> | 
            <small><b>Finished At:</b> {task.get('finished_at', 'N/A')}</small><br>
            <small><b>Comment:</b> {task.get('comment', 'No comments provided.')}</small>
        </div>""", unsafe_allow_html=True)
    else:
        col_a, col_b, col_c = st.columns([2, 1, 1])
        with col_a: note = st.text_input("Note", key=f"note_{tid}")
        with col_b: t_type = st.selectbox("Type", ["Regular", "Major"], key=f"type_{tid}")
        with col_c:
            if st.button("✅ Done", key=f"done_{tid}", use_container_width=True):
                patch = {"status": "Completed", "comment": note, "task_type": t_type, "completed_by": user['name'], "finished_at": get_now_ist()}
                requests.patch(f"{DB_BASE_URL}/tasks/{tid}.json", json=patch)
                st.rerun()
    st.divider()