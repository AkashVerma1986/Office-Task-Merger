import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import time
import json
import pytz  # Point 3: IST Support
from streamlit_javascript import st_javascript # Point 2 & 6
import io

# --- CONFIGURATION ---
DB_BASE_URL = "https://office-task-ledger-default-rtdb.asia-southeast1.firebasedatabase.app"
TASKS_URL = f"{DB_BASE_URL}/tasks.json"
USERS_URL = f"{DB_BASE_URL}/users.json"

STAFF_PASSWORD = "1234"
ADMIN_PASSWORD = "1586"
IST = pytz.timezone('Asia/Kolkata') 

# --- PAGE CONFIG ---
st.set_page_config(page_title="Report Correction Ledger Pro", layout="wide")

# --- CUSTOM STYLES (Updated with Vertical Bar CSS) ---
st.markdown("""
    <style>
    html, body, [class*="st-"], .stMarkdown p { font-size: 18px !important; } 
    .main { background-color: #000000; }
    .stApp { background-color: #000000; color: #E0E0E0; }
    
    /* Task Card Container */
    .task-container {
        display: flex;
        background-color: #0A0A0A;
        border: 1px solid #1A1A1A;
        border-radius: 10px;
        margin-bottom: 15px;
        overflow: hidden;
        min-height: 120px;
    }
    
    /* THE VERTICAL STATUS BAR - Full Height */
    .status-bar {
        width: 12px;
        height: auto;
    }
    
    .status-pending { background-color: #C29100; }
    .status-high { background-color: #B71C1C; }
    .status-completed { background-color: #1B5E20; }
    .status-hold { background-color: #880E4F; }
    
    .task-content {
        padding: 20px;
        flex-grow: 1;
    }
    
    .task-card strong { font-size: 1.4rem !important; color: #3E91D4; }
    </style>
""", unsafe_allow_html=True)

# --- POINT 6: PERSISTENCE (LocalStorage) ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_data' not in st.session_state:
    st.session_state.user_data = None

# JavaScript to get saved session
saved_session = st_javascript("localStorage.getItem('office_user');")

# Auto-login if session exists in browser
if saved_session and not st.session_state.authenticated:
    try:
        user_info = json.loads(saved_session)
        st.session_state.user_data = user_info
        st.session_state.authenticated = True
        st.rerun()
    except:
        pass

# --- POINT 2: FINGERPRINTING ---
device_id = st_javascript("""(async () => {
    return btoa(navigator.userAgent + screen.width + screen.height);
})()""")

# --- HELPER FUNCTIONS ---
def get_now_ist(): 
    return datetime.now(IST).strftime("%d/%b/%Y %H:%M:%S")

def fetch_data(): 
    try:
        res = requests.get(TASKS_URL, timeout=5)
        data = res.json() or {}
        # POINT 9: Limit to last 100 locally
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
    with st.container():
        name_input = st.text_input("Full Name").upper().strip()
        desig_input = st.text_input("Designation").upper().strip()
        pwd_input = st.text_input("Password", type="password")
        
        if st.button("LOGIN") and device_id:
            users = fetch_users()
            is_admin = (pwd_input == ADMIN_PASSWORD)
            is_staff = (pwd_input == STAFF_PASSWORD)

            if name_input and (is_admin or is_staff):
                if name_input not in users and not is_admin:
                    st.error("User not authorized. Please contact Admin to add your name.")
                else:
                    role = "ADMIN" if is_admin else "STAFF"
                    db_user = users.get(name_input, {})
                    reg_device = db_user.get('device')
                    
                    if reg_device and reg_device != device_id and not is_admin:
                        st.error("Access Denied: This ID is locked to another device.")
                    else:
                        if not reg_device:
                            requests.patch(f"{DB_BASE_URL}/users/{name_input}.json", json={"device": device_id, "role": role})
                        
                        user_payload = {"name": name_input, "role": role}
                        st.session_state.user_data = user_payload
                        st.session_state.authenticated = True
                        st_javascript(f"localStorage.setItem('office_user', '{json.dumps(user_payload)}');")
                        st.rerun()
            else:
                st.error("Invalid credentials or missing fields.")
    st.stop()

# --- MAIN UI ---
user = st.session_state.user_data
tasks_dict = fetch_data()

# --- SEARCH AND EXCEL SECTION (New Features) ---
st.subheader("🔍 Search & Reports")
search_col, priority_col, export_col = st.columns([3, 1, 1])

with search_col:
    search_query = st.text_input("Search by Finance Name or Details", placeholder="Type to filter...").lower()

with priority_col:
    prio_filter = st.checkbox("⭐ High Priority Only")

with export_col:
    # EXCEL EXPORT LOGIC
    if tasks_dict:
        df_export = pd.DataFrame.from_dict(tasks_dict, orient='index')
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_export.to_excel(writer, index=False, sheet_name='Tasks')
        
        st.download_button(
            label="📥 Export Excel",
            data=buffer.getvalue(),
            file_name=f"Task_Ledger_{datetime.now().strftime('%d_%m_%Y')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# --- INPUT SECTION ---
st.subheader("📝 Add New Task")
with st.expander("Open Task Form", expanded=False):
    c1, c2, c3 = st.columns(3)
    with c1:
        raw_fins = sorted(list(set(t.get('finance', '').upper() for t in tasks_dict.values() if t.get('finance'))))
        fin_name_sel = st.selectbox("Finance Name", options=["--- SELECT FINANCE ---", "ADD NEW+"] + raw_fins)
        fin_name = st.text_input("New Name").upper() if fin_name_sel == "ADD NEW+" else fin_name_sel
    with c2:
        category = st.selectbox("Category", ["--- SELECT CATEGORY ---", "1. Rate Correction", "2. Spelling/Address", "3. Digital Sign", "4. Report Upload", "5. Photos/Drafting"])
    with c3:
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

# --- TASK LIST ---
st.subheader("📋 RECENT ENTRIES")

# FILTERING LOGIC
keys = list(tasks_dict.keys())
keys.reverse() 

for tid in keys:
    task = tasks_dict[tid]
    t_status = task.get('status', 'Pending')
    t_priority = task.get('priority', 'Normal')
    t_finance = str(task.get('finance', '')).lower()
    t_details = str(task.get('task', '')).lower()

    # Apply Search & Priority Filters
    if search_query and (search_query not in t_finance and search_query not in t_details):
        continue
    if prio_filter and t_priority != "High":
        continue

    can_manage = (user['role'] == "ADMIN" or task.get('assigner') == user['name'])
    
    # Determine Vertical Bar Color
    status_class = "status-pending"
    if t_status == "Completed": status_class = "status-completed"
    elif t_status == "Hold": status_class = "status-hold"
    elif t_priority == "High": status_class = "status-high"

    # UI RENDERING WITH VERTICAL BAR
    st.markdown(f'''
        <div class="task-container">
            <div class="status-bar {status_class}"></div>
            <div class="task-content">
                <strong>{task.get('finance')}</strong> | <small>{task.get('assigned_at')}</small><br>
                {task.get('task')}
            </div>
        </div>
    ''', unsafe_allow_html=True)

    # Management Actions (Edit/Delete/Done)
    if t_status != "Completed":
        col_a, col_b, col_c, col_d, col_e = st.columns([2, 1, 1, 0.7, 0.5])
        with col_a: note = st.text_input("Note", key=f"note_{tid}")
        with col_b: t_type = st.selectbox("Type", ["Regular", "Major"], key=f"type_{tid}")
        with col_c:
            if st.button("✅ Done", key=f"done_{tid}"):
                patch = {"status": "Completed", "comment": note, "task_type": t_type, "completed_by": user['name'], "finished_at": get_now_ist()}
                requests.patch(f"{DB_BASE_URL}/tasks/{tid}.json", json=patch)
                st.rerun()
        with col_d:
            if can_manage and st.button("📝 Edit", key=f"ed_{tid}"):
                st.session_state.edit_id = tid
                st.rerun()
        with col_e:
            if can_manage and st.button("🗑", key=f"del_{tid}"):
                requests.delete(f"{DB_BASE_URL}/tasks/{tid}.json")
                st.rerun()
    st.divider()

with st.sidebar:
    st.write(f"User: **{user['name']}**")
    if st.button("🚪 LOGOUT"):
        st_javascript("localStorage.removeItem('office_user');")
        st.session_state.authenticated = False
        st.session_state.user_data = None
        st.rerun()