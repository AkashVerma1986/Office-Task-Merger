import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import time
import pytz  # Point 3: IST Support
from streamlit_javascript import st_javascript # Required for Point 2 & 6

# --- CONFIGURATION (Point 2, 6, 9) ---
DB_BASE_URL = "https://office-task-ledger-default-rtdb.asia-southeast1.firebasedatabase.app"
TASKS_URL = f"{DB_BASE_URL}/tasks.json"
# Point 9: Limit fetch to 100 most recent items
QUERY_URL = f"{TASKS_URL}?orderBy=\"assigned_at\"&limitToLast=100"
SETTINGS_URL = f"{DB_BASE_URL}/settings.json"
USERS_URL = f"{DB_BASE_URL}/users.json"

STAFF_PASSWORD = "1234"
ADMIN_PASSWORD = "1586"
IST = pytz.timezone('Asia/Kolkata') # Point 3

# --- PAGE CONFIG ---
st.set_page_config(page_title="Report Correction Ledger Pro", layout="wide")

# --- CUSTOM STYLES (Point 7: +2pt Font Increase) ---
st.markdown("""
    <style>
    html, body, [class*="st-"] { font-size: 18px !important; } /* Global +2pt increase */
    .main { background-color: #000000; }
    .stApp { background-color: #000000; color: #E0E0E0; }
    .task-card {
        background-color: #0A0A0A;
        border: 1px solid #1A1A1A;
        border-radius: 10px;
        padding: 18px;
        margin-bottom: 12px;
        border-left: 6px solid #C29100;
    }
    .priority-high { border-left-color: #B71C1C !important; }
    .status-completed { border-left-color: #1B5E20 !important; }
    .status-hold { border-left-color: #880E4F !important; }
    .task-card strong { font-size: 1.35rem; } /* Scaled header */
    </style>
""", unsafe_allow_html=True)

# --- POINT 2 & 6: DEVICE FINGERPRINT & PERSISTENCE ---
device_id = st_javascript("""(async () => {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    return btoa(navigator.userAgent + screen.width + screen.height);
})()""")

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'edit_id' not in st.session_state:
    st.session_state.edit_id = None

# --- HELPER FUNCTIONS ---
def get_now(): # Point 3
    return datetime.now(IST).strftime("%d/%b/%Y %H:%M:%S")

def fetch_data(): # Point 9
    try:
        res = requests.get(QUERY_URL, timeout=5)
        return res.json() or {}
    except: return {}

def fetch_users():
    try:
        res = requests.get(USERS_URL, timeout=5)
        return res.json() or {}
    except: return {}

# --- LOGIN SCREEN (Point 1 & 2) ---
if not st.session_state.authenticated:
    st.title("🔐 OFFICE LEDGER LOGIN")
    with st.container():
        name = st.text_input("Full Name").upper()
        desig = st.text_input("Designation").upper()
        pwd = st.text_input("Password", type="password")
        
        if st.button("LOGIN") and device_id:
            users = fetch_users()
            is_admin = (pwd == ADMIN_PASSWORD)
            is_staff = (pwd == STAFF_PASSWORD)

            if name and desig and (is_admin or is_staff):
                role = "ADMIN" if is_admin else "STAFF"
                
                # Point 2: Device Binding Logic
                if name in users:
                    if users[name]['device'] != device_id and not is_admin:
                        st.error("This ID is registered to another device.")
                        st.stop()
                else:
                    # Register new user/device
                    requests.patch(f"{DB_BASE_URL}/users/{name}.json", json={"device": device_id, "role": role})

                st.session_state.user_data = {"name": name, "designation": desig, "role": role}
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Invalid Credentials or Missing Fields")
    st.stop()

# --- MAIN UI ---
user = st.session_state.user_data
tasks_dict = fetch_data()

# --- INPUT SECTION (Point 8: Optimized Defaults) ---
st.subheader("📝 Add New Task")
with st.expander("Click to Open Input Form", expanded=True):
    c1, c2, c3 = st.columns(3)
    with c1:
        raw_fins = sorted(list(set(t.get('finance', '').upper() for t in tasks_dict.values() if t.get('finance'))))
        # Point 8: Default to "Select" to prevent accidental entry
        fin_name_sel = st.selectbox("Finance Name", options=["--- SELECT ---", "ADD NEW+"] + raw_fins)
        fin_name = ""
        if fin_name_sel == "ADD NEW+":
            fin_name = st.text_input("Enter New Finance Name").upper()
        else:
            fin_name = fin_name_sel
            
    with c2:
        # Point 8: Placeholder added
        cat_options = ["--- SELECT CATEGORY ---", "1. Rate Correction", "2. Spelling/Address", "3. Digital Sign", "4. Report Upload", "5. Photos/Drafting"]
        category = st.selectbox("Category", cat_options)
    with c3:
        priority = st.select_slider("Priority", options=["Normal", "Medium", "High"])

    task_details = st.text_area("Task Details")
    
    if st.button("🚀 ADD TO LEDGER", use_container_width=True):
        if fin_name != "--- SELECT ---" and category != "--- SELECT CATEGORY ---" and task_details:
            new_task = {
                "finance": fin_name,
                "task": f"[{category}] {task_details}",
                "priority": priority,
                "assigner": user['name'],
                "status": "Pending",
                "assigned_at": get_now() # Point 3
            }
            requests.post(TASKS_URL, json=new_task)
            st.success("Task Added!")
            time.sleep(1)
            st.rerun()
        else:
            st.warning("Please select Finance, Category and enter Details.")

# --- TASK LIST ---
st.subheader("📋 RECENT ENTRIES (Last 100)") # Point 9

keys = list(tasks_dict.keys())
keys.reverse() 

for tid in keys:
    task = tasks_dict[tid]
    t_status = task.get('status', 'Pending')
    
    # Point 5: Edit Logic (Assigner or Admin only)
    is_editor = (user['role'] == "ADMIN" or task.get('assigner') == user['name'])
    
    with st.container():
        border_class = "priority-high" if task.get('priority') == "High" else ""
        if t_status == "Completed": border_class = "status-completed"
        elif t_status == "Hold": border_class = "status-hold"

        st.markdown(f'<div class="task-card {border_class}">', unsafe_allow_html=True)
        st.write(f"**{task.get('finance')}** | {task.get('assigned_at')}")
        
        # Point 5: Show Edit Area or Text
        if st.session_state.edit_id == tid:
            new_text = st.text_area("Edit Task", value=task.get('task'), key=f"input_{tid}")
            if st.button("💾 Save", key=f"save_{tid}"):
                requests.patch(f"{DB_BASE_URL}/tasks/{tid}.json", json={"task": new_text})
                st.session_state.edit_id = None
                st.rerun()
        else:
            st.write(task.get('task'))
            st.write(f"Assigner: {task.get('assigner')}")
        st.markdown('</div>', unsafe_allow_html=True)

        if t_status != "Completed":
            c1, c2, c3, c4, c5 = st.columns([2, 1.2, 0.8, 0.8, 0.5])
            with c1:
                note = st.text_input("Note", key=f"note_{tid}")
            with c2:
                # Point 4: Regular/Major Dropdown
                t_type = st.selectbox("Type", ["Regular", "Major"], key=f"type_{tid}")
            with c3:
                if st.button("✅ Done", key=f"comp_{tid}"):
                    if not note: st.error("Add note!"); st.stop()
                    patch = {
                        "status": "Completed", "comment": note, "task_type": t_type,
                        "completed_by": user['name'], "finished_at": get_now()
                    }
                    requests.patch(f"{DB_BASE_URL}/tasks/{tid}.json", json=patch)
                    st.rerun()
            with c4:
                # Point 5: Edit Toggle
                if is_editor and st.button("📝 Edit", key=f"ed_{tid}"):
                    st.session_state.edit_id = tid
                    st.rerun()
            with c5:
                # Point 1: Admin Power to Delete
                if is_editor:
                    if st.button("🗑", key=f"del_{tid}"):
                        requests.delete(f"{DB_BASE_URL}/tasks/{tid}.json")
                        st.rerun()
        st.divider()

# --- SIDEBAR & LOGOUT (Point 6) ---
with st.sidebar:
    st.write(f"Logged in as: **{user['name']}**")
    if st.button("🚪 LOGOUT"):
        st.session_state.authenticated = False
        st.rerun()
    st.divider()
    st.info("Tip: Pull down to refresh on mobile.") # Point 6