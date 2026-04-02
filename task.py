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

st.set_page_config(page_title="RAAS | Report Correction Ledger", layout="wide")

# --- 2. THE REINFORCED CSS (+2pt Font & Permanent Side Bar) ---
st.markdown("""
    <style>
    html, body, [class*="st-"], .stMarkdown p, .stTextInput input, .stSelectbox div { 
        font-size: 22px !important; 
    } 
    .main { background-color: #000000; }
    .stApp { background-color: #000000; color: #E0E0E0; }
    
    .logo-container { display: flex; flex-direction: column; align-items: center; justify-content: center; margin-bottom: 30px; }
    .raas-text { font-size: 55px; font-weight: bold; color: #FFFFFF; letter-spacing: 5px; margin-top: -10px; }
    
    .unified-task-card {
        background-color: #0A0A0A;
        border: 1px solid #444444;
        border-radius: 12px;
        margin-bottom: 25px;
        display: flex !important; 
        flex-direction: row !important; 
        overflow: hidden;
    }
    
    .status-bar { 
        width: 35px !important; 
        min-width: 35px !important;
        flex-shrink: 0 !important;
        display: block !important;
    }
    
    .status-pending { background-color: #C29100 !important; } 
    .status-completed { background-color: #1B5E20 !important; } 
    .status-hold { background-color: #C71585 !important; }      
    .status-high { background-color: #B71C1C !important; }      
    
    .task-content-container { flex-grow: 1; display: flex; flex-direction: column; width: 100%; }
    .task-text-padding { padding: 25px; }
    .task-action-footer { background-color: #111111; padding: 22px; border-top: 1px solid #222222; margin-top: auto; }
    .completion-text { color: #4CAF50; font-weight: bold; font-size: 20px; }
    </style>
""", unsafe_allow_html=True)

# --- 3. BRANDING ---
with st.container():
    st.markdown('<div class="logo-container">', unsafe_allow_html=True)
    if os.path.exists("image_0.png"):
        st.image("image_0.png", width=240)
    else:
        st.markdown('<h1 style="font-size: 90px; margin:0;">🍎</h1>', unsafe_allow_html=True)
    st.markdown('<div class="raas-text">RAAS</div></div>', unsafe_allow_html=True)

# --- 4. AUTH & SCROLL STATE ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'scroll_to_top' not in st.session_state: st.session_state.scroll_to_top = False

def get_now_ist(): return datetime.now(IST).strftime("%d/%b/%Y %H:%M:%S")

# --- 5. TOP ANCHOR (Forced Scroll Logic) ---
if st.session_state.scroll_to_top:
    st.markdown('<a href="#top_form" id="click_me"></a>', unsafe_allow_html=True)
    components.html("<script>window.parent.document.getElementById('click_me').click();</script>", height=0)
    st.session_state.scroll_to_top = False

st.markdown("<div id='top_form'></div>", unsafe_allow_html=True)

if not st.session_state.authenticated:
    st.title("🔐 RAAS AUTHORIZED LOGIN")
    name_in = st.text_input("Name").upper().strip()
    pwd_in = st.text_input("Password", type="password")
    if st.button("LOGIN"):
        users_db = requests.get(USERS_URL).json() or {}
        is_admin = (pwd_in == "1586")
        if name_in and (is_admin or pwd_in == "1234"):
            if name_in not in users_db and not is_admin: st.error("🚫 No Slot.")
            else:
                st.session_state.user_data = {"name": name_in, "role": "ADMIN" if is_admin else "STAFF"}
                st.session_state.authenticated = True
                st.rerun()
    st.stop()

# --- 6. DATA FETCH & ADMIN TOOLS ---
user = st.session_state.user_data
tasks_dict = requests.get(TASKS_URL).json() or {}

if user['role'] == "ADMIN":
    with st.sidebar:
        st.header("⚙️ ADMIN PANEL")
        with st.expander("👤 User Slots"):
            nu = st.text_input("New Name").upper().strip()
            if st.button("Add Slot"): 
                requests.patch(f"{DB_BASE_URL}/users/{nu}.json", json={"role":"STAFF"}); st.rerun()
        with st.expander("📝 Manage Finance"):
            f_list = sorted(list(set(t.get('finance', '').upper() for t in tasks_dict.values() if t.get('finance'))))
            t_fin = st.selectbox("Select Finance", ["---"] + f_list)
            n_name = st.text_input("Rename To").upper()
            if st.button("Rename All", use_container_width=True):
                for tid, d in tasks_dict.items():
                    if d.get('finance') == t_fin: requests.patch(f"{DB_BASE_URL}/tasks/{tid}.json", json={"finance": n_name})
                st.rerun()
            if st.button("🗑️ Delete All for this Finance", use_container_width=True):
                for tid, d in tasks_dict.items():
                    if d.get('finance') == t_fin: requests.delete(f"{DB_BASE_URL}/tasks/{tid}.json")
                st.rerun()

# --- 7. LEDGER FORM ---
if "edit_fin" not in st.session_state: st.session_state.edit_fin = "--- SELECT ---"
if "edit_dtl" not in st.session_state: st.session_state.edit_dtl = ""

st.subheader("📝 Report Correction Ledger")
with st.expander("Open Ledger Form", expanded=True):
    c1, c2 = st.columns(2)
    with c1:
        fins = sorted(list(set(t.get('finance', '').upper() for t in tasks_dict.values() if t.get('finance'))))
        try: f_idx = (["--- SELECT ---", "ADD NEW+"] + fins).index(st.session_state.edit_fin)
        except: f_idx = 0
        f_sel = st.selectbox("Finance", ["--- SELECT ---", "ADD NEW+"] + fins, index=f_idx)
        fin = st.text_input("New Finance Name").upper() if f_sel == "ADD NEW+" else f_sel
    with c2:
        cat = st.selectbox("Category", ["---", "1. Rate Correction", "2. Spelling/Address", "3. Digital Sign", "4. Report Upload", "5. Photos/Drafting"])
    prio = st.select_slider("Priority", ["Normal", "Medium", "High"])
    dtl = st.text_area("Task Details", value=st.session_state.edit_dtl)
    if st.button("🚀 ADD TO LEDGER", use_container_width=True):
        if fin != "--- SELECT ---" and cat != "---" and dtl:
            requests.post(TASKS_URL, json={"finance":fin, "task":f"[{cat}] {dtl}", "priority":prio, "assigner":user['name'], "status":"Pending", "assigned_at":get_now_ist()})
            st.session_state.edit_fin, st.session_state.edit_dtl = "--- SELECT ---", ""; st.rerun()

# --- 8. EXPORT & SEARCH ---
st.divider()
s1, s2, s3, s4 = st.columns([2, 1.5, 0.5, 1])
search = s1.text_input("🔍 Search Ledger").lower()
export_range = s2.date_input("Export Dates", [datetime.now(IST), datetime.now(IST)])
if s3.button("🔄"): st.rerun()
if s4 and tasks_dict:
    df = pd.DataFrame.from_dict(tasks_dict, orient='index')
    df['date_dt'] = pd.to_datetime(df['assigned_at'], format="%d/%b/%Y %H:%M:%S", errors='coerce').dt.date
    if len(export_range) == 2: df = df[(df['date_dt'] >= export_range[0]) & (df['date_dt'] <= export_range[1])]
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as wr: df.drop(columns=['date_dt'], errors='ignore').to_excel(wr)
    st.download_button("📥 Export Excel", buf.getvalue(), "RAAS_Report.xlsx", use_container_width=True)

# --- 9. THE UNIFIED MASTER WINDOW ENTRIES ---
st.subheader("📋 RECENT ENTRIES")
keys = list(tasks_dict.keys()); keys.reverse()

for tid in keys:
    task = tasks_dict[tid]
    t_status, t_prio = task.get('status', 'Pending'), task.get('priority', 'Normal')
    if search and (search not in str(task.get('finance','')).lower() and search not in str(task.get('task','')).lower()): continue

    s_class = "status-pending"
    if t_status == "Completed": s_class = "status-completed"
    elif t_status == "Hold": s_class = "status-hold"
    elif t_prio == "High" and t_status == "Pending": s_class = "status-high"

    st.markdown(f'<div class="unified-task-card"><div class="status-bar {s_class}"></div><div class="task-content-container">', unsafe_allow_html=True)
    
    with st.container():
        st.markdown(f'''<div class="task-text-padding"><strong style="font-size: 26px;">{task.get('finance')}</strong> | <small>{task.get('assigned_at')}</small><br>{task.get('task')}</div>''', unsafe_allow_html=True)
        st.markdown('<div class="task-action-footer">', unsafe_allow_html=True)
        
        if t_status == "Completed":
            # LOGIC: Visual Indicator for Major tasks
            work_label = f"<b>{task.get('work_type')}</b>" if task.get('work_type') == "Major" else task.get('work_type')
            st.markdown(f"""<span class="completion-text">✅ COMPLETED [{work_label}]</span><br>
                <small>By: {task.get('completed_by')} | At: {task.get('finished_at')}</small><br>
                <small>Note: {task.get('comment', 'No note')}</small>""", unsafe_allow_html=True)
            if user['role'] == "ADMIN":
                if st.checkbox(f"🗑️ Delete Task?", key=f"conf_admin_{tid}"):
                    if st.button(f"❗ DELETE PERMANENTLY", key=f"del_admin_{tid}", use_container_width=True):
                        requests.delete(f"{DB_BASE_URL}/tasks/{tid}.json"); st.rerun()
        else:
            c_n, c_t, c_h, c_c = st.columns([1.5, 0.8, 0.7, 1])
            note = c_n.text_input("Comment", key=f"n_{tid}", label_visibility="collapsed", placeholder="Note...")
            w_type = c_t.selectbox("Type", ["Regular", "Major"], key=f"t_{tid}", label_visibility="collapsed")
            
            # LOGIC: Persistent comments when toggling Hold/Unhold
            if t_status == "Hold":
                if c_h.button("▶️ Unhold", key=f"h_{tid}", use_container_width=True):
                    requests.patch(f"{DB_BASE_URL}/tasks/{tid}.json", json={"status": "Pending", "comment": note}); st.rerun()
            else:
                if c_h.button("⏸️ Hold", key=f"h_{tid}", use_container_width=True):
                    requests.patch(f"{DB_BASE_URL}/tasks/{tid}.json", json={"status": "Hold", "comment": note}); st.rerun()

            if c_c.button("✅ Completed", key=f"c_{tid}", use_container_width=True):
                requests.patch(f"{DB_BASE_URL}/tasks/{tid}.json", json={"status": "Completed", "comment": note, "work_type": w_type, "completed_by": user['name'], "finished_at": get_now_ist()}); st.rerun()

            if user['role'] == "ADMIN" or task.get('assigner') == user['name']:
                e_col, d_col = st.columns([1, 1])
                if e_col.button("✏️ EDIT", key=f"edit_{tid}", use_container_width=True):
                    st.session_state.edit_fin = task.get('finance', '--- SELECT ---')
                    st.session_state.edit_dtl = task.get('task', '').split('] ', 1)[-1] if '] ' in task.get('task', '') else task.get('task', '')
                    st.session_state.scroll_to_top = True; st.rerun()
                if d_col.checkbox(f"🗑️ Delete?", key=f"conf_staff_{tid}"):
                    if st.button(f"❗ CONFIRM DELETE", key=f"del_staff_{tid}", use_container_width=True):
                        requests.delete(f"{DB_BASE_URL}/tasks/{tid}.json"); st.rerun()
        st.markdown('</div></div></div>', unsafe_allow_html=True)
    st.divider()

if st.sidebar.button("Logout"):
    st.session_state.authenticated = False; st.rerun()