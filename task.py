import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import time
import pytz  # Point 3: IST Support
from streamlit_javascript import st_javascript # Point 2 & 6: Persistence/Fingerprint

# --- CONFIGURATION (Point 2, 6, 9) ---
DB_BASE_URL = "https://office-task-ledger-default-rtdb.asia-southeast1.firebasedatabase.app"
TASKS_URL = f"{DB_BASE_URL}/tasks.json"
# Point 9: Fetch only 100 most recent items for speed
QUERY_URL = f"{TASKS_URL}?orderBy=\"assigned_at\"&limitToLast=100"
USERS_URL = f"{DB_BASE_URL}/users.json"

STAFF_PASSWORD = "1234"
ADMIN_PASSWORD = "1586"
IST = pytz.timezone('Asia/Kolkata') # Point 3: Indian Time

# --- PAGE CONFIG ---
st.set_page_config(page_title="Report Correction Ledger Pro", layout="wide")

# --- CUSTOM STYLES (Point 7: +2pt Font Scaling) ---
st.markdown("""
    <style>
    /* Global font increase by 2pt */
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
    
    /* Point 7: Scaling headers */
    .task-card strong { font-size: 1.4rem !important; color: #3E91D4; }
    </style>
""", unsafe_allow_html=True)

# --- POINT 2 & 6: PERSISTENCE & FINGERPRINTING ---
# Gets a unique browser hash to bind user to device
device_id = st_javascript("""(async () => {
    return btoa(navigator.userAgent + screen.width + screen.height);
})()""")

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'edit_id' not in st.session_state:
    st.session_state.edit_id = None

# --- HELPER FUNCTIONS ---
def get_now_ist(): # Point 3
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
                
                # Point 2: Binding logic - PC/Mobile registration on first login
                if name in users:
                    if users[name]['device'] != device_id and not is_admin:
                        st.error("Access Denied: This ID is already registered on another device.")
                        st.stop()
                else:
                    # Register this device fingerprint to the username
                    requests.patch(f"{DB_BASE_URL}/users/{name}.json", json={"device": device_id, "role": role})

                st.session_state.user_data = {"name": name, "designation": desig, "role": role}
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Invalid Password or empty fields")
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
        # Point 8: Select is default to prevent mistakes
        fin_name_sel = st.selectbox("Finance Name", options=["--- SELECT FINANCE ---", "ADD NEW+"] + raw_fins)
        fin_name = ""
        if fin_name_sel == "ADD NEW+":
            fin_name = st.text_input("Enter New Finance Name").upper()
        else:
            fin_name = fin_name_sel
            
    with c2:
        # Point 8: Placeholder added for category
        cat_list = ["--- SELECT CATEGORY ---", "1. Rate Correction", "2. Spelling/Address", "3. Digital Sign", "4. Report Upload", "5. Photos/Drafting"]
        category = st.selectbox("Category", cat_list)
    with c3:
        priority = st.select_slider("Priority", options=["Normal", "Medium", "High"])

    task_details = st.text_area("Task Details")
    
    if st.button("🚀 ADD TO LEDGER", use_container_width=True):
        if fin_name != "--- SELECT FINANCE ---" and category != "--- SELECT CATEGORY ---" and task_details:
            new_task = {
                "finance": fin_name,
                "task": f"[{category}] {task_details}",
                "priority": priority,
                "assigner": user['name'],
                "status": "Pending",
                "assigned_at": get_now_ist() # Point 3
            }
            requests.post(TASKS_URL, json=new_task)
            st.success("Task Added Successfully!")
            time.sleep(1)
            st.rerun()
        else:
            st.warning("Please ensure Finance and Category are selected.")

# --- TASK LIST ---
st.subheader("📋 RECENT ENTRIES (Displaying Last 100)") # Point 9

keys = list(tasks_dict.keys())
keys.reverse() # Newest on top

for tid in keys:
    task = tasks_dict[tid]
    t_status = task.get('status', 'Pending')
    
    # Point 1 & 5: Check if user has power to edit/delete
    can_manage = (user['role'] == "ADMIN" or task.get('assigner') == user['name'])
    
    with st.container():
        border_class = "priority-high" if task.get('priority') == "High" else ""
        if t_status == "Completed": border_class = "status-completed"
        elif t_status == "Hold": border_class = "status-hold"

        st.markdown(f'<div class="task-card {border_class}">', unsafe_allow_html=True)
        st.markdown(f"**{task.get('finance')}** | <small>{task.get('assigned_at')}</small>", unsafe_allow_html=True)
        
        # Point 5: Inline Editing
        if st.session_state.edit_id == tid:
            edited_val = st.text_area("Edit Task Details", value=task.get('task'), key=f"edit_input_{tid}")
            if st.button("💾 Save Changes", key=f"save_btn_{tid}"):
                requests.patch(f"{DB_BASE_URL}/tasks/{tid}.json", json={"task": edited_val})
                st.session_state.edit_id = None
                st.rerun()
        else:
            st.write(task.get('task'))
            st.markdown(f"<small>Assigned by: {task.get('assigner')}</small>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Action row for non-completed tasks
        if t_status != "Completed":
            col_a, col_b, col_c, col_d, col_e = st.columns([2, 1, 1, 0.7, 0.5])
            with col_a:
                comp_note = st.text_input("Completion Note", key=f"note_{tid}")
            with col_b:
                # Point 4: Classification dropdown
                task_type = st.selectbox("Task Type", ["Regular", "Major"], key=f"type_{tid}")
            with col_c:
                if st.button("✅ Done", key=f"done_{tid}"):
                    if not comp_note: st.error("Note required"); st.stop()
                    finish_patch = {
                        "status": "Completed", "comment": comp_note, "task_type": task_type,
                        "completed_by": user['name'], "finished_at": get_now_ist()
                    }
                    requests.patch(f"{DB_BASE_URL}/tasks/{tid}.json", json=finish_patch)
                    st.rerun()
            with col_d:
                # Point 5: Edit Trigger
                if can_manage and st.button("📝 Edit", key=f"edit_btn_{tid}"):
                    st.session_state.edit_id = tid
                    st.rerun()
            with col_e:
                # Point 1: Delete Power
                if can_manage:
                    if st.button("🗑", key=f"del_btn_{tid}"):
                        requests.delete(f"{DB_BASE_URL}/tasks/{tid}.json")
                        st.rerun()
        else:
            st.markdown(f"✅ *Completed as **{task.get('task_type','Regular')}** by {task.get('completed_by')} on {task.get('finished_at')}*")
        st.divider()

# --- PERSISTENCE & LOGOUT ---
with st.sidebar:
    st.header("👤 User Profile")
    st.write(f"Name: **{user['name']}**")
    st.write(f"Role: **{user['role']}**")
    if st.button("🚪 LOGOUT"):
        st.session_state.authenticated = False
        st.rerun()
    st.divider()
    st.info("Swipe/Pull down to refresh data.")