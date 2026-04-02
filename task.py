import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import time
import json
import pytz  # Point 3: IST Support
from streamlit_javascript import st_javascript # Point 2 & 6

# --- CONFIGURATION ---
DB_BASE_URL = "https://office-task-ledger-default-rtdb.asia-southeast1.firebasedatabase.app"
TASKS_URL = f"{DB_BASE_URL}/tasks.json"
USERS_URL = f"{DB_BASE_URL}/users.json"

STAFF_PASSWORD = "1234"
ADMIN_PASSWORD = "1586"
IST = pytz.timezone('Asia/Kolkata') 

# --- PAGE CONFIG ---
st.set_page_config(page_title="Report Correction Ledger Pro", layout="wide")

# --- CUSTOM STYLES (Point 7: +2pt Font Scaling) ---
st.markdown("""
    <style>
    html, body, [class*="st-"], .stMarkdown p { font-size: 18px !important; } 
    .main { background-color: #000000; }
    .stApp { background-color: #000000; color: #E0E0E0; }
    .task-card {
        background-color: #0A0A0A;
        border: 1px solid #1A1A1A;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 15px;
        border-left: 7px solid #C29100;
    }
    .priority-high { border-left-color: #B71C1C !important; }
    .status-completed { border-left-color: #1B5E20 !important; }
    .status-hold { border-left-color: #880E4F !important; }
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

# --- LOGIN SCREEN (Point 1, 2, 10) ---
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
                # Point 10: Check if User is Pre-Approved in Firebase
                if name_input not in users and not is_admin:
                    st.error("User not authorized. Please contact Admin to add your name.")
                else:
                    role = "ADMIN" if is_admin else "STAFF"
                    
                    # Point 2: Device ID Binding
                    db_user = users.get(name_input, {})
                    reg_device = db_user.get('device')
                    
                    if reg_device and reg_device != device_id and not is_admin:
                        st.error("Access Denied: This ID is locked to another device.")
                    else:
                        # Success - Register device if new
                        if not reg_device:
                            requests.patch(f"{DB_BASE_URL}/users/{name_input}.json", json={"device": device_id, "role": role})
                        
                        # Set Session State
                        user_payload = {"name": name_input, "role": role}
                        st.session_state.user_data = user_payload
                        st.session_state.authenticated = True
                        
                        # Point 6: Save to Browser Storage
                        st_javascript(f"localStorage.setItem('office_user', '{json.dumps(user_payload)}');")
                        st.rerun()
            else:
                st.error("Invalid credentials or missing fields.")
    st.stop()

# --- MAIN UI ---
user = st.session_state.user_data
tasks_dict = fetch_data()

# --- INPUT SECTION (Point 8) ---
st.subheader("📝 Add New Task")
with st.expander("Open Task Form", expanded=True):
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

# --- TASK LIST (Point 9) ---
st.subheader("📋 RECENT ENTRIES (Last 100)")
keys = list(tasks_dict.keys())
keys.reverse() 

for tid in keys:
    task = tasks_dict[tid]
    t_status = task.get('status', 'Pending')
    can_manage = (user['role'] == "ADMIN" or task.get('assigner') == user['name'])
    
    with st.container():
        border_class = "priority-high" if task.get('priority') == "High" else ""
        if t_status == "Completed": border_class = "status-completed"
        elif t_status == "Hold": border_class = "status-hold"

        st.markdown(f'<div class="task-card {border_class}">', unsafe_allow_html=True)
        st.markdown(f"**{task.get('finance')}** | <small>{task.get('assigned_at')}</small>", unsafe_allow_html=True)
        
        if st.session_state.get('edit_id') == tid:
            edited_val = st.text_area("Edit", value=task.get('task'), key=f"edit_{tid}")
            if st.button("💾 Save", key=f"save_{tid}"):
                requests.patch(f"{DB_BASE_URL}/tasks/{tid}.json", json={"task": edited_val})
                st.session_state.edit_id = None
                st.rerun()
        else:
            st.write(task.get('task'))
        st.markdown('</div>', unsafe_allow_html=True)

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
        # Clear Session and Browser Storage
        st_javascript("localStorage.removeItem('office_user');")
        st.session_state.authenticated = False
        st.session_state.user_data = None
        st.rerun()