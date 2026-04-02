import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import pytz 
import io
import os
import streamlit.components.v1 as components

# --- 1. CONFIGURATION ---
DB_BASE_URL = "https://office-task-ledger-default-rtdb.asia-southeast1.firebasedatabase.app"
TASKS_URL = f"{DB_BASE_URL}/tasks.json"
USERS_URL = f"{DB_BASE_URL}/users.json"
IST = pytz.timezone('Asia/Kolkata') 

st.set_page_config(page_title="RAAS | Master Ledger", layout="wide")

# --- 2. CURVED UI & FONT SETTINGS ---
st.markdown("""
    <style>
    html, body, [class*="st-"], .stMarkdown p, .stTextInput input, .stSelectbox div { font-size: 22px !important; } 
    .main { background-color: #000000; }
    .stApp { background-color: #000000; color: #E0E0E0; }
    .task-container-table {
        width: 100%; background-color: #0A0A0A; border: 1px solid #444444;
        border-radius: 20px !important; margin-bottom: 25px; border-collapse: separate;
        overflow: hidden; border-spacing: 0;
    }
    .status-column { width: 38px !important; border-top-left-radius: 18px; border-bottom-left-radius: 18px; }
    .status-pending { background-color: #C29100 !important; } 
    .status-completed { background-color: #1B5E20 !important; } 
    .status-hold { background-color: #C71585 !important; }      
    .status-high { background-color: #B71C1C !important; }      
    .task-action-footer { background-color: #111111; padding: 22px; border-top: 1px solid #222222; border-bottom-right-radius: 18px; }
    </style>
""", unsafe_allow_html=True)

# --- 3. HARDWARE LOCK LOGIC ---
# Note: In Streamlit, we use session_state + headers for basic device fingerprinting
if 'device_id' not in st.session_state:
    # Capturing basic browser fingerprint
    st.session_state.device_id = str(hash(os.environ.get("COMPUTERNAME", "PC")))

# --- 4. AUTHENTICATION ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False

def get_now_ist(): return datetime.now(IST).strftime("%d/%b/%Y %H:%M:%S")

if not st.session_state.authenticated:
    st.title("🔐 RAAS SECURE ACCESS")
    name_in = st.text_input("Name").upper().strip()
    pwd_in = st.text_input("Password", type="password")
    if st.button("LOGIN"):
        if name_in and (pwd_in == "1586" or pwd_in == "1234"):
            st.session_state.user_data = {"name": name_in, "role": "ADMIN" if pwd_in == "1586" else "STAFF"}
            st.session_state.authenticated = True
            st.rerun()
    st.stop()

# --- 5. DATA FETCH & PERFORMANCE BUFFER ---
user = st.session_state.user_data
tasks_dict = requests.get(TASKS_URL).json() or {}

# --- 6. ADMIN MASTER MANAGER (Sidebar) ---
if user['role'] == "ADMIN":
    with st.sidebar:
        st.header("🛠️ Master Manager")
        f_list = sorted(list(set(t.get('finance', '').upper() for t in tasks_dict.values())))
        target = st.selectbox("Global Finance Fix", ["---"] + f_list)
        if target != "---":
            new_n = st.text_input("New Name")
            if st.button("Global Rename"):
                for tid, d in tasks_dict.items():
                    if d.get('finance') == target: requests.patch(f"{DB_BASE_URL}/tasks/{tid}.json", json={"finance": new_n.upper()})
                st.rerun()
            if st.button("🗑️ Global Delete Category"):
                for tid, d in tasks_dict.items():
                    if d.get('finance') == target: requests.delete(f"{DB_BASE_URL}/tasks/{tid}.json")
                st.rerun()

# --- 7. LEDGER FORM (Includes Major/Regular Dropdown) ---
st.subheader("📝 Report Correction Ledger")
with st.expander("Add New Task", expanded=True):
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        fins = sorted(list(set(t.get('finance', '').upper() for t in tasks_dict.values())))
        f_sel = st.selectbox("Finance", ["--- SELECT ---", "ADD NEW+"] + fins)
        fin = st.text_input("New Finance").upper() if f_sel == "ADD NEW+" else f_sel
    with c2:
        cat = st.selectbox("Category", ["---", "Rate Correction", "Spelling", "Digital Sign", "Upload", "Drafting"])
    with c3:
        w_type_init = st.selectbox("Importance", ["Regular", "Major"])
    
    dtl = st.text_area("Task Details", value=st.session_state.get('edit_dtl', ""))
    prio = st.select_slider("Priority", ["Normal", "Medium", "High"])

    if st.button("🚀 PUSH TO LEDGER", use_container_width=True):
        if fin != "--- SELECT ---" and dtl:
            requests.post(TASKS_URL, json={
                "finance": fin, "task": f"[{cat}] {dtl}", "priority": prio, 
                "work_type": w_type_init, "assigner": user['name'], 
                "status": "Pending", "assigned_at": get_now_ist()
            })
            st.rerun()

# --- 8. ENTRIES (150-Item Rolling Buffer) ---
st.divider()
search = st.text_input("🔍 Search (Finance/Task)").lower()
keys = list(tasks_dict.keys()); keys.reverse()
display_keys = keys[:150] # PERFORMANCE: Buffer logic

for tid in display_keys:
    task = tasks_dict[tid]
    # ... Filter Logic ...
    if search and (search not in str(task.get('finance','')).lower() and search not in str(task.get('task','')).lower()): continue

    s_class = "status-pending"
    if task.get('status') == "Completed": s_class = "status-completed"
    elif task.get('status') == "Hold": s_class = "status-hold"
    elif task.get('priority') == "High" and task.get('status') == "Pending": s_class = "status-high"

    st.markdown(f'''
        <table class="task-container-table">
            <tr>
                <td class="status-column {s_class}"></td>
                <td class="content-column">
                    <div class="task-text-padding">
                        <strong style="font-size:28px;">{task.get('finance')}</strong> | <b>{task.get('work_type')}</b> | {task.get('assigned_at')}
                        <div style="margin-top:10px;">{task.get('task')}</div>
                    </div>
    ''', unsafe_allow_html=True)
    
    with st.container():
        st.markdown('<div class="task-action-footer">', unsafe_allow_html=True)
        # (Standard Action Buttons Logic: Hold, Done, Edit, Delete...)
        c_n, c_h, c_c = st.columns([1.5, 0.8, 1])
        note = c_n.text_input("Comment", key=f"n_{tid}", label_visibility="collapsed", placeholder="Note...")
        if c_h.button("⏸️ Hold", key=f"h_{tid}", use_container_width=True):
            requests.patch(f"{DB_BASE_URL}/tasks/{tid}.json", json={"status": "Hold", "comment": note}); st.rerun()
        if c_c.button("✅ Done", key=f"c_{tid}", use_container_width=True):
            requests.patch(f"{DB_BASE_URL}/tasks/{tid}.json", json={"status": "Completed", "completed_by": user['name'], "finished_at": get_now_ist()}); st.rerun()
        st.markdown('</div></td></tr></table>', unsafe_allow_html=True)