import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import time
import json
import pytz  
from streamlit_javascript import st_javascript 

# --- CONFIGURATION ---
DB_BASE_URL = "https://office-task-ledger-default-rtdb.asia-southeast1.firebasedatabase.app"
TASKS_URL = f"{DB_BASE_URL}/tasks.json"
USERS_URL = f"{DB_BASE_URL}/users.json"

STAFF_PASSWORD = "1234"
ADMIN_PASSWORD = "1586"
IST = pytz.timezone('Asia/Kolkata') 

# --- PAGE CONFIG ---
st.set_page_config(page_title="Report Correction Ledger Pro", layout="wide")

# --- CUSTOM STYLES (Old Type Bar Colors) ---
st.markdown("""
    <style>
    html, body, [class*="st-"], .stMarkdown p { font-size: 18px !important; } 
    .main { background-color: #000000; }
    .stApp { background-color: #000000; color: #E0E0E0; }
    
    .task-card {
        background-color: #111111;
        border: 1px solid #333333;
        border-radius: 2px;
        padding: 15px;
        margin-bottom: 12px;
        border-left: 10px solid #FF8C00; /* Default Orange for Pending */
    }
    
    .priority-high { border-left-color: #FF0000 !important; }   /* Red */
    .status-completed { border-left-color: #00FF00 !important; } /* Green */
    .status-hold { border-left-color: #FF1493 !important; }      /* Dark Pink */
    
    .task-card strong { font-size: 1.3rem !important; color: #FFFFFF; }
    </style>
""", unsafe_allow_html=True)

# --- PERSISTENCE LOGIC ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

saved_session = st_javascript("localStorage.getItem('office_user');")

if saved_session and saved_session != "null" and not st.session_state.authenticated:
    try:
        user_info = json.loads(saved_session)
        st.session_state.user_data = user_info
        st.session_state.authenticated = True
        st.rerun()
    except:
        pass

device_id = st_javascript("""(async () => {
    return btoa(navigator.userAgent + screen.width + screen.height);
})()""")

# --- HELPERS ---
def get_now_ist(): 
    return datetime.now(IST).strftime("%d/%b/%Y %H:%M:%S")

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

# --- LOGIN ---
if not st.session_state.authenticated:
    st.title("🔐 OFFICE LEDGER LOGIN")
    with st.container():
        name_input = st.text_input("Full Name").upper().strip()
        pwd_input = st.text_input("Password", type="password")
        
        if st.button("LOGIN") and device_id:
            users = fetch_users()
            is_admin = (pwd_input == ADMIN_PASSWORD)
            is_staff = (pwd_input == STAFF_PASSWORD)

            if name_input and (is_admin or is_staff):
                if name_input not in users and not is_admin:
                    st.error("User not authorized. Contact Admin.")
                else:
                    role = "ADMIN" if is_admin else "STAFF"
                    db_user = users.get(name_input, {})
                    reg_device = db_user.get('device')
                    
                    if reg_device and reg_device != device_id and not is_admin:
                        st.error("Locked to another device.")
                    else:
                        if not reg_device:
                            requests.patch(f"{DB_BASE_URL}/users/{name_input}.json", json={"device": device_id, "role": role})
                        
                        user_payload = {"name": name_input, "role": role}
                        st.session_state.user_data = user_payload
                        st.session_state.authenticated = True
                        st_javascript(f"localStorage.setItem('office_user', '{json.dumps(user_payload)}');")
                        st.rerun()
    st.stop()

# --- MAIN APP ---
user = st.session_state.user_data
tasks_dict = fetch_data()

# --- ENTRY FORM ---
st.subheader("📝 Add New Task")
with st.expander("Entry Form", expanded=True):
    c1, c2, c3 = st.columns(3)
    with c1:
        raw_fins = sorted(list(set(t.get('finance', '').upper() for t in tasks_dict.values() if t.get('finance'))))
        fin_sel = st.selectbox("Finance", options=["--- SELECT ---", "ADD NEW+"] + raw_fins)
        fin_name = st.text_input("New Name").upper() if fin_sel == "ADD NEW+" else fin_sel
    with c2:
        cat = st.selectbox("Category", ["--- SELECT ---", "1. Rate Correction", "2. Spelling/Address", "3. Digital Sign", "4. Report Upload", "5. Photos/Drafting"])
    with c3:
        prio = st.select_slider("Priority", options=["Normal", "Medium", "High"])

    details = st.text_area("Task Details")
    
    if st.button("🚀 ADD TASK", use_container_width=True):
        if fin_name != "--- SELECT ---" and cat != "--- SELECT ---" and details:
            new_task = {
                "finance": fin_name, "task": f"[{cat}] {details}",
                "priority": prio, "assigner": user['name'],
                "status": "Pending", "assigned_at": get_now_ist() 
            }
            requests.post(TASKS_URL, json=new_task)
            st.success("Added!")
            time.sleep(1)
            st.rerun()

# --- SEARCH BAR ---
st.divider()
search_query = st.text_input("🔍 Search Ledger (Finance Name or Details)", "").upper()

# --- LEDGER LIST ---
st.subheader("📋 RECENT ENTRIES")
keys = list(tasks_dict.keys())
keys.reverse() 

for tid in keys:
    task = tasks_dict[tid]
    t_finance = task.get('finance', '').upper()
    t_details = task.get('task', '').upper()
    
    # Search Filter
    if search_query and search_query not in t_finance and search_query not in t_details:
        continue

    t_status = task.get('status', 'Pending')
    can_manage = (user['role'] == "ADMIN" or task.get('assigner') == user['name'])
    
    with st.container():
        # Old Type Border Logic
        b_class = ""
        if t_status == "Completed": b_class = "status-completed"
        elif t_status == "Hold": b_class = "status-hold"
        elif task.get('priority') == "High": b_class = "priority-high"

        st.markdown(f'<div class="task-card {b_class}">', unsafe_allow_html=True)
        st.markdown(f"**{task.get('finance')}** | <small>{task.get('assigned_at')}</small>", unsafe_allow_html=True)
        
        if st.session_state.get('edit_id') == tid:
            val = st.text_area("Edit", value=task.get('task'), key=f"ed_in_{tid}")
            if st.button("💾 Save", key=f"sv_{tid}"):
                requests.patch(f"{DB_BASE_URL}/tasks/{tid}.json", json={"task": val})
                st.session_state.edit_id = None
                st.rerun()
        else:
            st.write(task.get('task'))
        st.markdown('</div>', unsafe_allow_html=True)

        if t_status not in ["Completed"]:
            col_a, col_b, col_c, col_d, col_e, col_f = st.columns([1.5, 0.8, 0.6, 0.6, 0.5, 0.4])
            with col_a: note = st.text_input("Note", key=f"n_{tid}", placeholder="Add comment...")
            with col_b: t_type = st.selectbox("Type", ["Regular", "Major"], key=f"t_{tid}")
            with col_c:
                if st.button("✅ Done", key=f"dn_{tid}"):
                    requests.patch(f"{DB_BASE_URL}/tasks/{tid}.json", json={"status": "Completed", "comment": note, "task_type": t_type, "completed_by": user['name'], "finished_at": get_now_ist()})
                    st.rerun()
            with col_d:
                if st.button("⏸ Hold", key=f"hd_{tid}"):
                    requests.patch(f"{DB_BASE_URL}/tasks/{tid}.json", json={"status": "Hold", "comment": note, "hold_at": get_now_ist()})
                    st.rerun()
            with col_e:
                if can_manage and st.button("📝 Edit", key=f"e_{tid}"):
                    st.session_state.edit_id = tid
                    st.rerun()
            with col_f:
                if can_manage and st.button("🗑", key=f"d_{tid}"):
                    requests.delete(f"{DB_BASE_URL}/tasks/{tid}.json")
                    st.rerun()
        else:
            st.markdown(f"✅ *Done by {task.get('completed_by')} on {task.get('finished_at')}*")
        st.divider()

with st.sidebar:
    st.write(f"Logged as: **{user['name']}**")
    if st.button("🚪 LOGOUT"):
        st_javascript("localStorage.removeItem('office_user');")
        st.session_state.authenticated = False
        st.rerun()