import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import time

# --- CONFIGURATION ---
DB_BASE_URL = "https://office-task-ledger-default-rtdb.asia-southeast1.firebasedatabase.app/tasks"
SETTINGS_URL = "https://office-task-ledger-default-rtdb.asia-southeast1.firebasedatabase.app/settings.json"
DB_URL = f"{DB_BASE_URL}.json"

STAFF_PASSWORD = "1234"
ADMIN_PASSWORD = "1586"

# --- PAGE CONFIG ---
st.set_page_config(page_title="Report Correction Ledger Pro", layout="wide")

# --- CUSTOM STYLES (MIDNIGHT PALETTE) ---
st.markdown("""
    <style>
    .main { background-color: #000000; }
    .stApp { background-color: #000000; color: #E0E0E0; }
    .task-card {
        background-color: #0A0A0A;
        border: 1px solid #1A1A1A;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
        border-left: 5px solid #C29100;
    }
    .priority-high { border-left-color: #B71C1C !important; }
    .status-completed { border-left-color: #1B5E20 !important; }
    .status-hold { border-left-color: #880E4F !important; }
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE INITIALIZATION ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_data' not in st.session_state:
    st.session_state.user_data = {"name": "", "designation": "", "role": ""}

# --- HELPER FUNCTIONS ---
def fetch_data():
    try:
        res = requests.get(DB_URL, timeout=5)
        return res.json() or {}
    except:
        return {}

def fetch_settings():
    try:
        res = requests.get(SETTINGS_URL, timeout=5)
        return res.json() or {"hidden": [], "renamed": {}}
    except:
        return {"hidden": [], "renamed": {}}

def format_date(date_str):
    try:
        dt = datetime.strptime(date_str, "%d/%b/%Y %H:%M:%S")
        return dt.strftime("%d %b %Y, %H:%M")
    except:
        return date_str

# --- LOGIN SCREEN ---
if not st.session_state.authenticated:
    st.title("🔐 OFFICE LEDGER LOGIN")
    with st.container():
        name = st.text_input("Full Name")
        desig = st.text_input("Designation")
        pwd = st.text_input("Password", type="password")
        
        if st.button("LOGIN"):
            if name and desig:
                if pwd == ADMIN_PASSWORD:
                    st.session_state.user_data = {"name": name.upper(), "designation": desig.upper(), "role": "ADMIN"}
                    st.session_state.authenticated = True
                    st.rerun()
                elif pwd == STAFF_PASSWORD:
                    st.session_state.user_data = {"name": name.upper(), "designation": desig.upper(), "role": "STAFF"}
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Invalid Password")
            else:
                st.warning("Please fill all fields")
    st.stop()

# --- MAIN UI ---
user = st.session_state.user_data
tasks_dict = fetch_data()
settings = fetch_settings()
hidden_fins = set(settings.get("hidden", []))
renamed_fins = settings.get("renamed", {})

# --- TOP NAVIGATION BAR ---
col1, col2, col3 = st.columns([2, 3, 2])
with col1:
    st.markdown(f"**👤 {user['name']}** \n*{user['designation']} ({user['role']})*")

with col2:
    search_query = st.text_input("", placeholder="🔍 Search records...")

with col3:
    if st.button("🔄 REFRESH DATA"):
        st.rerun()

# --- INPUT SECTION ---
st.subheader("📝 Add New Task")
with st.expander("Click to Open Input Form", expanded=True):
    c1, c2, c3 = st.columns(3)
    with c1:
        # Finance List from existing data
        raw_fins = sorted(list(set(t.get('finance', '').upper() for t in tasks_dict.values() if t.get('finance'))))
        fin_name = st.selectbox("Finance Name", options=["NEW..."] + raw_fins)
        if fin_name == "NEW...":
            fin_name = st.text_input("Enter New Finance Name").upper()
    with c2:
        category = st.selectbox("Category", ["1. Rate Correction", "2. Spelling/Address", "3. Digital Sign", "4. Report Upload", "5. Photos/Drafting"])
    with c3:
        priority = st.select_slider("Priority", options=["Normal", "Medium", "High"])

    task_details = st.text_area("Task Details")
    
    if st.button("🚀 ADD TO LEDGER", use_container_width=True):
        if fin_name and task_details:
            new_task = {
                "finance": fin_name.upper(),
                "task": f"[{category}] {task_details}",
                "priority": priority,
                "assigner": user['name'],
                "status": "Pending",
                "assigned_at": datetime.now().strftime("%d/%b/%Y %H:%M:%S")
            }
            requests.post(DB_URL, json=new_task)
            st.success("Task Added!")
            time.sleep(1)
            st.rerun()

# --- FILTERS & EXPORT ---
st.divider()
f_col1, f_col2, f_col3, f_col4 = st.columns(4)
with f_col1:
    show_pending_only = st.checkbox("🕒 Show Pending Only")
with f_col2:
    sort_priority = st.checkbox("📌 Sort by Priority")
with f_col3:
    raw_list = sorted(list(set(t.get('finance', '').upper() for t in tasks_dict.values())))
    filter_fin = st.selectbox("Filter Finance", ["--- ALL ---"] + raw_list)
with f_col4:
    # Export to Excel
    if tasks_dict:
        df = pd.DataFrame.from_dict(tasks_dict, orient='index')
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📊 EXPORT TO CSV", data=csv, file_name="ledger_export.csv", mime="text/csv")

# --- TASK LIST ---
st.subheader("📋 RECENT ENTRIES")

# Sorting & Filtering Logic
keys = list(tasks_dict.keys())
if sort_priority:
    priority_map = {"High": 3, "Medium": 2, "Normal": 1}
    keys.sort(key=lambda x: priority_map.get(tasks_dict[x].get('priority', 'Normal'), 0), reverse=True)
else:
    keys.reverse() # Show newest first

for tid in keys:
    task = tasks_dict[tid]
    t_status = task.get('status', 'Pending')
    t_fin = task.get('finance', '').upper()
    t_display_fin = renamed_fins.get(t_fin, t_fin)
    
    # Apply Filters
    if t_display_fin in hidden_fins: continue
    if show_pending_only and t_status != "Pending": continue
    if filter_fin != "--- ALL ---" and t_fin != filter_fin: continue
    if search_query.lower() not in f"{t_display_fin} {task.get('task','')} {task.get('assigner','')}".lower(): continue

    # Styling Class
    border_class = ""
    if t_status == "Completed": border_class = "status-completed"
    elif t_status == "Hold": border_class = "status-hold"
    elif task.get('priority') == "High": border_class = "priority-high"

    with st.container():
        st.markdown(f"""
            <div class="task-card {border_class}">
                <small>{task.get('priority','').upper()} | {task.get('assigned_at','')}</small><br>
                <strong style="color:#3E91D4; font-size: 1.2rem;">{t_display_fin}</strong><br>
                <p>{task.get('task','')}</p>
                <small>Assigned by: {task.get('assigner','')}</small>
            </div>
        """, unsafe_allow_html=True)
        
        # Action Buttons
        if t_status != "Completed":
            c1, c2, c3, c4 = st.columns([2, 1, 1, 0.5])
            with c1:
                note = st.text_input("Completion Note", key=f"note_{tid}")
            with c2:
                if st.button("✅ Done", key=f"comp_{tid}"):
                    if not note: st.error("Note required!"); st.stop()
                    patch = {
                        "status": "Completed", 
                        "comment": note, 
                        "completed_by": user['name'],
                        "finished_at": datetime.now().strftime("%d/%b/%Y %H:%M:%S")
                    }
                    requests.patch(f"{DB_BASE_URL}/{tid}.json", json=patch)
                    st.rerun()
            with c3:
                h_label = "⏸ Hold" if t_status == "Pending" else "▶ Unhold"
                if st.button(h_label, key=f"hold_{tid}"):
                    new_s = "Hold" if t_status == "Pending" else "Pending"
                    requests.patch(f"{DB_BASE_URL}/{tid}.json", json={"status": new_s})
                    st.rerun()
            with c4:
                if user['role'] == "ADMIN" or task.get('assigner') == user['name']:
                    if st.button("🗑", key=f"del_{tid}"):
                        requests.delete(f"{DB_BASE_URL}/{tid}.json")
                        st.rerun()
        else:
            st.markdown(f"✅ *Completed by {task.get('completed_by')} on {task.get('finished_at')} - {task.get('comment','')}*")
        st.divider()

# --- ADMIN SETTINGS ---
if user['role'] == "ADMIN":
    with st.sidebar:
        st.header("Admin Controls")
        if st.toggle("Show Finance Management"):
            target_fin = st.selectbox("Select Finance to Manage", raw_list)
            if st.button("Hide Global"):
                hidden_fins.add(target_fin)
                requests.put(SETTINGS_URL, json={"hidden": list(hidden_fins), "renamed": renamed_fins})
                st.rerun()
            
            new_name = st.text_input("Rename to:")
            if st.button("Rename Global"):
                renamed_fins[target_fin] = new_name.upper()
                requests.put(SETTINGS_URL, json={"hidden": list(hidden_fins), "renamed": renamed_fins})
                st.rerun()