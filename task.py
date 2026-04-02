import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import time
import json
import pytz 
import io
import os

# --- 1. CONFIGURATION ---
DB_BASE_URL = "https://office-task-ledger-default-rtdb.asia-southeast1.firebasedatabase.app"
TASKS_URL = f"{DB_BASE_URL}/tasks.json"
USERS_URL = f"{DB_BASE_URL}/users.json"
IST = pytz.timezone('Asia/Kolkata') 

st.set_page_config(page_title="RAAS | Report Correction Ledger", layout="wide")

# --- 2. THE MASTER WINDOW & BRANDING STYLES ---
st.markdown("""
    <style>
    html, body, [class*="st-"], .stMarkdown p { font-size: 18px !important; } 
    .main { background-color: #000000; }
    .stApp { background-color: #000000; color: #E0E0E0; }
    
    .logo-container { display: flex; flex-direction: column; align-items: center; justify-content: center; margin-bottom: 30px; }
    .raas-text { font-size: 50px; font-weight: bold; color: #FFFFFF; letter-spacing: 5px; margin-top: -10px; }
    
    .master-task-window {
        background-color: #0A0A0A;
        border: 1px solid #222222;
        border-radius: 12px;
        margin-bottom: 10px;
        display: flex;
        flex-direction: column;
        overflow: hidden;
    }
    .task-header { display: flex; width: 100%; }
    .status-bar { width: 14px; flex-shrink: 0; }
    
    /* STATUS COLORS */
    .status-pending { background-color: #C29100; } 
    .status-completed { background-color: #1B5E20; } 
    .status-hold { background-color: #C71585; } 
    .status-high { background-color: #B71C1C; } 
    
    .task-body { padding: 20px; flex-grow: 1; }
    
    .task-footer {
        background-color: #111111;
        padding: 15px 20px;
        border-top: 1px solid #222222;
    }
    .completion-text { color: #4CAF50; font-weight: bold; font-size: 16px; }
    </style>
""", unsafe_allow_html=True)

# --- 3. BRANDING LOGO (Fixed Reliability) ---
with st.container():
    st.markdown('<div class="logo-container">', unsafe_allow_html=True)
    if os.path.exists("image_0.png"):
        st.image("image_0.png", width=200)
    else:
        # Fallback if file is missing
        st.markdown('<h1 style="font-size: 70px; margin:0;">🍎</h1>', unsafe_allow_html=True)
    st.markdown('<div class="raas-text">RAAS</div></div>', unsafe_allow_html=True)

# --- 4. AUTHENTICATION (ADMIN SLOTS ONLY) ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False

def get_now_ist(): return datetime.now(IST).strftime("%d/%b/%Y %H:%M:%S")

if not st.session_state.authenticated:
    st.title("🔐 RAAS AUTHORIZED LOGIN")
    name_in = st.text_input("Name").upper().strip()
    pwd_in = st.text_input("Password", type="password")
    if st.button("LOGIN"):
        users_db = requests.get(USERS_URL).json() or {}
        is_admin, is_staff = (pwd_in == "1586"), (pwd_in == "1234")
        if name_in and (is_admin or is_staff):
            if name_in not in users_db and not is_admin: 
                st.error("🚫 No Slot. Contact Admin.")
            else:
                st.session_state.user_data = {"name": name_in, "role": "ADMIN" if is_admin else "STAFF"}
                st.session_state.authenticated = True
                st.rerun()
    st.stop()

# --- 5. DATA & ADMIN TOOLS ---
user = st.session_state.user_data
tasks_dict = requests.get(TASKS_URL).json() or {}

if user['role'] == "ADMIN":
    with st.sidebar:
        st.header("⚙️ ADMIN PANEL")
        with st.expander("👤 Create User Slots"):
            nu = st.text_input("New Name").upper().strip()
            if st.button("Add Slot"): 
                requests.patch(f"{DB_BASE_URL}/users/{nu}.json", json={"role":"STAFF"})
                st.success("Slot Created!")
        
        with st.expander("📝 Manage Finance"):
            fins = sorted(list(set(t.get('finance', '').upper() for t in tasks_dict.values() if t.get('finance'))))
            t_fin = st.selectbox("Select", ["---"] + fins)
            n_name = st.text_input("New Name").upper()
            c1, c2 = st.columns(2)
            if c1.button("Rename"):
                for tid, d in tasks_dict.items():
                    if d.get('finance') == t_fin: requests.patch(f"{DB_BASE_URL}/tasks/{tid}.json", json={"finance": n_name})
                st.rerun()
            if c2.button("Delete All", type="primary"):
                for tid, d in tasks_dict.items():
                    if d.get('finance') == t_fin: requests.delete(f"{DB_BASE_URL}/tasks/{tid}.json")
                st.rerun()

# --- 6. LEDGER FORM ---
st.subheader("📝 Report Correction Ledger")
with st.expander("Open Ledger Form", expanded=True):
    c1, c2 = st.columns(2)
    with c1:
        fins = sorted(list(set(t.get('finance', '').upper() for t in tasks_dict.values() if t.get('finance'))))
        f_sel = st.selectbox("Finance", ["--- SELECT ---", "ADD NEW+"] + fins)
        fin = st.text_input("New Finance Name").upper() if f_sel == "ADD NEW+" else f_sel
    with c2:
        cat = st.selectbox("Category", ["---", "1. Rate Correction", "2. Spelling/Address", "3. Digital Sign", "4. Report Upload", "5. Photos/Drafting"])
    
    prio = st.select_slider("Priority", ["Normal", "Medium", "High"])
    dtl = st.text_area("Task Details")
    if st.button("🚀 ADD TO LEDGER", use_container_width=True):
        if fin != "--- SELECT ---" and cat != "---" and dtl:
            requests.post(TASKS_URL, json={"finance":fin, "task":f"[{cat}] {dtl}", "priority":prio, "assigner":user['name'], "status":"Pending", "assigned_at":get_now_ist()})
            st.rerun()

# --- 7. SEARCH & EXPORT ---
st.divider()
s1, s2, s3, s4 = st.columns([2, 1.5, 0.5, 1])
with s1: search = st.text_input("🔍 Search Ledger").lower()
with s2: dr = st.date_input("Excel Range", [datetime.now(IST), datetime.now(IST)])
with s3: 
    if st.button("🔄"): st.rerun()
with s4:
    if tasks_dict:
        df = pd.DataFrame.from_dict(tasks_dict, orient='index')
        df['date_dt'] = pd.to_datetime(df['assigned_at'], format="%d/%b/%Y %H:%M:%S", errors='coerce').dt.date
        if len(dr) == 2: df = df[(df['date_dt'] >= dr[0]) & (df['date_dt'] <= dr[1])]
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='openpyxl') as wr: df.drop(columns=['date_dt']).to_excel(wr)
        st.download_button("📥 Excel", buf.getvalue(), "RAAS_Report.xlsx", use_container_width=True)

# --- 8. INTEGRATED TASK WINDOWS ---
st.subheader("📋 RECENT ENTRIES")
keys = list(tasks_dict.keys())
keys.reverse()

for tid in keys:
    task = tasks_dict[tid]
    t_status, t_prio = task.get('status', 'Pending'), task.get('priority', 'Normal')
    if search and (search not in str(task.get('finance','')).lower() and search not in str(task.get('task','')).lower()): continue

    s_class = "status-pending"
    if t_status == "Completed": s_class = "status-completed"
    elif t_status == "Hold": s_class = "status-hold"
    elif t_prio == "High" and t_status == "Pending": s_class = "status-high"

    st.markdown(f'''
        <div class="master-task-window">
            <div class="task-header">
                <div class="status-bar {s_class}"></div>
                <div class="task-body">
                    <strong>{task.get('finance')}</strong> | <small>{task.get('assigned_at')}</small><br>
                    {task.get('task')}
                </div>
            </div>
    ''', unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="task-footer">', unsafe_allow_html=True)
        if t_status == "Completed":
            st.markdown(f"""
                <span class="completion-text">✅ RECORD:</span> 
                <small>By: {task.get('completed_by')} | At: {task.get('finished_at')}</small><br>
                <small>Note: {task.get('comment', 'No note')}</small>
            """, unsafe_allow_html=True)
        else:
            c_n, c_h, c_c = st.columns([2, 1, 1])
            note = c_n.text_input("Note", key=f"n_{tid}", label_visibility="collapsed", placeholder="Note...")
            if c_h.button("⏸️ Hold", key=f"h_{tid}", use_container_width=True):
                requests.patch(f"{DB_BASE_URL}/tasks/{tid}.json", json={"status": "Hold", "comment": note})
                st.rerun()
            if c_c.button("✅ Completed", key=f"c_{tid}", use_container_width=True):
                requests.patch(f"{DB_BASE_URL}/tasks/{tid}.json", json={"status": "Completed", "comment": note, "completed_by": user['name'], "finished_at": get_now_ist()})
                st.rerun()
        st.markdown('</div></div>', unsafe_allow_html=True)
    st.divider()

if st.sidebar.button("Logout"):
    st.session_state.authenticated = False
    st.rerun()