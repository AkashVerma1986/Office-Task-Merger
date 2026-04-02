import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import time
import pytz 
import io
import os

# --- 1. CONFIGURATION ---
DB_BASE_URL = "https://office-task-ledger-default-rtdb.asia-southeast1.firebasedatabase.app"
TASKS_URL = f"{DB_BASE_URL}/tasks.json"
USERS_URL = f"{DB_BASE_URL}/users.json"
IST = pytz.timezone('Asia/Kolkata') 

st.set_page_config(page_title="RAAS | Report Correction Ledger", layout="wide")

# --- 2. STYLES (+2pt Font & Color Logic) ---
st.markdown("""
    <style>
    /* Global Font Scaling +2pt */
    html, body, [class*="st-"], .stMarkdown p, .stTextInput input, .stSelectbox div { 
        font-size: 20px !important; 
    } 
    .main { background-color: #000000; }
    .stApp { background-color: #000000; color: #E0E0E0; }
    
    /* Branding */
    .logo-container { display: flex; flex-direction: column; align-items: center; justify-content: center; margin-bottom: 30px; }
    .raas-text { font-size: 55px; font-weight: bold; color: #FFFFFF; letter-spacing: 5px; margin-top: -10px; }
    
    /* Master Task Window */
    .master-task-window {
        background-color: #0A0A0A;
        border: 1px solid #222222;
        border-radius: 12px;
        margin-bottom: 12px;
        display: flex;
        flex-direction: column;
        overflow: hidden;
    }
    .task-header { display: flex; width: 100%; }
    .status-bar { width: 18px; flex-shrink: 0; }
    
    /* Status Colors */
    .status-pending { background-color: #C29100; }   /* GOLD */
    .status-completed { background-color: #1B5E20; } /* GREEN */
    .status-hold { background-color: #C71585; }      /* MAGENTA */
    .status-high { background-color: #B71C1C; }      /* RED */
    
    .task-body { padding: 22px; flex-grow: 1; }
    
    .task-footer {
        background-color: #111111;
        padding: 18px 22px;
        border-top: 1px solid #222222;
    }
    .edit-box { 
        background-color: #1A1A1A; 
        border: 1px dashed #444; 
        padding: 15px; 
        border-radius: 8px; 
        margin-bottom: 10px; 
    }
    .completion-text { color: #4CAF50; font-weight: bold; font-size: 18px; }
    </style>
""", unsafe_allow_html=True)

# --- 3. BRANDING LOGO ---
with st.container():
    st.markdown('<div class="logo-container">', unsafe_allow_html=True)
    if os.path.exists("image_0.png"):
        st.image("image_0.png", width=240)
    else:
        st.markdown('<h1 style="font-size: 90px; margin:0;">🍎</h1>', unsafe_allow_html=True)
    st.markdown('<div class="raas-text">RAAS</div></div>', unsafe_allow_html=True)

# --- 4. AUTHENTICATION (ADMIN SLOTS) ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False

def get_now_ist(): return datetime.now(IST).strftime("%d/%b/%Y %H:%M:%S")

if not st.session_state.authenticated:
    st.title("🔐 RAAS AUTHORIZED LOGIN")
    name_in = st.text_input("Name").upper().strip()
    pwd_in = st.text_input("Password", type="password")
    if st.button("LOGIN"):
        users_db = requests.get(USERS_URL).json() or {}
        is_admin = (pwd_in == "1586")
        if name_in and (is_admin or pwd_in == "1234"):
            if name_in not in users_db and not is_admin: 
                st.error("🚫 No Slot. Contact Admin to register your name.")
            else:
                st.session_state.user_data = {"name": name_in, "role": "ADMIN" if is_admin else "STAFF"}
                st.session_state.authenticated = True
                st.rerun()
    st.stop()

# --- 5. DATA & ADMIN PANEL ---
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
            n_name = st.text_input("Rename To").upper()
            if st.button("Rename"):
                for tid, d in tasks_dict.items():
                    if d.get('finance') == t_fin: requests.patch(f"{DB_BASE_URL}/tasks/{tid}.json", json={"finance": n_name})
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

# --- 7. EXPORT WITH DATE SELECTION ---
st.divider()
s1, s2, s3, s4 = st.columns([2, 1.5, 0.5, 1])
search = s1.text_input("🔍 Search Ledger").lower()
export_range = s2.date_input("Select Export Dates", [datetime.now(IST), datetime.now(IST)])
if s3.button("🔄"): st.rerun()
if s4 and tasks_dict:
    df = pd.DataFrame.from_dict(tasks_dict, orient='index')
    df['date_dt'] = pd.to_datetime(df['assigned_at'], format="%d/%b/%Y %H:%M:%S", errors='coerce').dt.date
    if len(export_range) == 2:
        df = df[(df['date_dt'] >= export_range[0]) & (df['date_dt'] <= export_range[1])]
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as wr: df.drop(columns=['date_dt'], errors='ignore').to_excel(wr)
    st.download_button("📥 Export Excel", buf.getvalue(), "RAAS_Report.xlsx", use_container_width=True)

# --- 8. MASTER TASK WINDOW ENTRIES ---
st.subheader("📋 RECENT ENTRIES")
keys = list(tasks_dict.keys())
keys.reverse()

for tid in keys:
    task = tasks_dict[tid]
    t_status, t_prio = task.get('status', 'Pending'), task.get('priority', 'Normal')
    if search and (search not in str(task.get('finance','')).lower() and search not in str(task.get('task','')).lower()): continue

    # Color Logic Application
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
        
        # Edit Logic (Only Admin/Assigner before completion)
        if t_status != "Completed" and (user['role'] == "ADMIN" or task.get('assigner') == user['name']):
            if st.checkbox(f"✏️ Edit Task", key=f"edit_check_{tid}"):
                with st.container():
                    st.markdown('<div class="edit-box">', unsafe_allow_html=True)
                    e_fin = st.text_input("Finance", value=task.get('finance'), key=f"ef_{tid}")
                    e_dtl = st.text_area("Details", value=task.get('task'), key=f"ed_{tid}")
                    e_prio = st.selectbox("Priority", ["Normal", "Medium", "High"], index=["Normal", "Medium", "High"].index(t_prio), key=f"ep_{tid}")
                    if st.button("💾 Save Changes", key=f"esave_{tid}"):
                        requests.patch(f"{DB_BASE_URL}/tasks/{tid}.json", json={"finance": e_fin, "task": e_dtl, "priority": e_prio})
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

        if t_status == "Completed":
            st.markdown(f"""
                <span class="completion-text">✅ COMPLETED [{task.get('work_type', 'N/A')}]</span><br>
                <small>By: {task.get('completed_by')} | At: {task.get('finished_at')}</small><br>
                <small>Note: {task.get('comment', 'No note')}</small>
            """, unsafe_allow_html=True)
            # Delete Logic: Only Admin after completion
            if user['role'] == "ADMIN":
                if st.button("🗑️ Admin Delete", key=f"del_{tid}"):
                    requests.delete(f"{DB_BASE_URL}/tasks/{tid}.json"); st.rerun()
        else:
            # Action Footer
            c_n, c_t, c_h, c_c = st.columns([1.5, 0.8, 0.7, 1])
            note = c_n.text_input("Note", key=f"n_{tid}", label_visibility="collapsed", placeholder="Note...")
            w_type = c_t.selectbox("Type", ["Regular", "Major"], key=f"t_{tid}", label_visibility="collapsed")
            if c_h.button("⏸️ Hold", key=f"h_{tid}", use_container_width=True):
                requests.patch(f"{DB_BASE_URL}/tasks/{tid}.json", json={"status": "Hold", "comment": note}); st.rerun()
            if c_c.button("✅ Completed", key=f"c_{tid}", use_container_width=True):
                requests.patch(f"{DB_BASE_URL}/tasks/{tid}.json", json={"status": "Completed", "comment": note, "work_type": w_type, "completed_by": user['name'], "finished_at": get_now_ist()}); st.rerun()

            # Delete Logic: Assigner/Admin before completion
            if user['role'] == "ADMIN" or task.get('assigner') == user['name']:
                if st.button("🗑️ Delete Task", key=f"del_{tid}"):
                    requests.delete(f"{DB_BASE_URL}/tasks/{tid}.json"); st.rerun()
        st.markdown('</div></div>', unsafe_allow_html=True)
    st.divider()

if st.sidebar.button("🚪 Logout"):
    st.session_state.authenticated = False
    st.rerun()