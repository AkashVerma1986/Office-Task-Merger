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

st.set_page_config(page_title="RAAS Ledger Pro", layout="wide")

# --- 2. SLEEK CSS (Galloping Bar + 22px Font) ---
st.markdown("""
    <style>
    html, body, [class*="st-"], .stMarkdown p, .stTextInput input, .stSelectbox div { font-size: 22px !important; } 
    .main { background-color: #000000; }
    .stApp { background-color: #000000; color: #E0E0E0; }
    
    .sleek-card {
        display: flex;
        background-color: #0A0A0A;
        border: 1px solid #333;
        border-radius: 15px;
        margin-bottom: 25px;
        overflow: hidden;
    }
    .galloping-bar { width: 25px; flex-shrink: 0; }
    .card-body { flex-grow: 1; display: flex; flex-direction: column; width: 100%; }
    .card-text { padding: 25px; border-bottom: 1px solid #222; }
    .card-footer { background-color: #111; padding: 20px; }
    
    /* STATUS COLORS */
    .status-pending { background-color: #C29100 !important; }
    .status-completed { background-color: #1B5E20 !important; }
    .status-hold { background-color: #C71585 !important; }
    .status-high { background-color: #B71C1C !important; }
    
    .completion-text { color: #4CAF50; font-weight: bold; font-size: 22px; }
    .edit-box-inline { background-color: #1A1A1A; border: 1px dashed #444; padding: 15px; border-radius: 8px; margin-top: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- 3. BRANDING ---
with st.container():
    if os.path.exists("image_0.png"):
        st.image("image_0.png", width=240)
    st.markdown('<h1 style="color:white; letter-spacing:5px; font-size:55px; text-align:center;">RAAS</h1>', unsafe_allow_html=True)

# --- 4. AUTH & SESSION STATE ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if "edit_mode" not in st.session_state: st.session_state.edit_mode = False
if "edit_tid" not in st.session_state: st.session_state.edit_tid = None
if "edit_fin" not in st.session_state: st.session_state.edit_fin = "--- SELECT ---"
if "edit_dtl" not in st.session_state: st.session_state.edit_dtl = ""

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
                st.error("🚫 No Slot. Contact Admin.")
            else:
                st.session_state.user_data = {"name": name_in, "role": "ADMIN" if is_admin else "STAFF"}
                st.session_state.authenticated = True; st.rerun()
    st.stop()

# --- 5. DATA & ADMIN SLOTS ---
user = st.session_state.user_data
tasks_dict = requests.get(TASKS_URL).json() or {}

if user['role'] == "ADMIN":
    with st.sidebar:
        st.header("⚙️ ADMIN PANEL")
        with st.expander("👤 Create User Slots"):
            nu = st.text_input("New Name").upper().strip()
            if st.button("Add Slot"): 
                requests.patch(f"{DB_BASE_URL}/users/{nu}.json", json={"role":"STAFF"})
                st.success(f"Slot for {nu} Created!")

# --- 6. LEDGER FORM ---
st.subheader("📝 Report Correction Ledger")
with st.expander("Open Ledger Form", expanded=True):
    c1, c2, c3 = st.columns([1.5, 1, 1])
    with c1:
        fins = sorted(list(set(t.get('finance', '').upper() for t in tasks_dict.values() if t.get('finance'))))
        try: f_idx = (["--- SELECT ---", "ADD NEW+"] + fins).index(st.session_state.edit_fin)
        except: f_idx = 0
        f_sel = st.selectbox("Finance", ["--- SELECT ---", "ADD NEW+"] + fins, index=f_idx)
        fin = st.text_input("New Finance Name").upper() if f_sel == "ADD NEW+" else f_sel
    with c2:
        cat = st.selectbox("Category", ["---", "1. Rate Correction", "2. Spelling/Address", "3. Digital Sign", "4. Report Upload", "5. Photos/Drafting"])
    with c3:
        prio = st.select_slider("Priority", ["Normal", "Medium", "High"])
    
    dtl = st.text_area("Task Details", value=st.session_state.edit_dtl)
    
    btn_label = "💾 UPDATE TASK" if st.session_state.edit_mode else "🚀 ADD TO LEDGER"
    if st.button(btn_label, use_container_width=True):
        if fin != "--- SELECT ---" and dtl:
            payload = {"finance": fin, "task": f"[{cat}] {dtl}", "priority": prio, "assigner": user['name'], "status": "Pending", "assigned_at": get_now_ist()}
            if st.session_state.edit_mode:
                requests.patch(f"{DB_BASE_URL}/tasks/{st.session_state.edit_tid}.json", json=payload)
            else:
                requests.post(TASKS_URL, json=payload)
            st.session_state.edit_mode, st.session_state.edit_fin, st.session_state.edit_dtl = False, "--- SELECT ---", ""
            st.rerun()

# --- 7. EXPORT & SEARCH ---
st.divider()
s1, s2, s3, s4 = st.columns([2, 1.5, 0.5, 1])
search = s1.text_input("🔍 Search Ledger").lower()
export_range = s2.date_input("Export Dates", [datetime.now(IST), datetime.now(IST)])
if s3.button("🔄"): st.rerun()
if s4 and tasks_dict:
    df = pd.DataFrame.from_dict(tasks_dict, orient='index')
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as wr: df.to_excel(wr)
    st.download_button("📥 Export Excel", buf.getvalue(), "RAAS_Report.xlsx", use_container_width=True)

# --- 8. THE SLEEK TASK WINDOWS ---
st.subheader("📋 RECENT ENTRIES")
keys = list(tasks_dict.keys()); keys.reverse()

for tid in keys[:150]:
    task = tasks_dict[tid]
    t_status, t_prio = task.get('status', 'Pending'), task.get('priority', 'Normal')
    if search and (search not in str(task.get('finance','')).lower() and search not in str(task.get('task','')).lower()): continue

    s_color = "status-pending"
    if t_status == "Completed": s_color = "status-completed"
    elif t_status == "Hold": s_color = "status-hold"
    elif t_prio == "High" and t_status == "Pending": s_color = "status-high"

    # Priority Badge Logic
    p_badge = f'<span style="padding:4px 12px; border-radius:15px; font-size:14px; background:#333;">{t_prio}</span>'
    if t_prio == "High": p_badge = f'<span style="padding:4px 12px; border-radius:15px; font-size:14px; background:#B71C1C;">HIGH</span>'

    st.markdown(f'''
        <div class="sleek-card">
            <div class="galloping-bar {s_color}"></div>
            <div class="card-body">
                <div class="card-text">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <strong style="font-size:28px;">{task.get('finance')}</strong> {p_badge}
                    </div>
                    <small style="color:#888;">{task.get('assigned_at')}</small><br>
                    <div style="margin-top:10px;">{task.get('task')}</div>
                </div>
    ''', unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="card-footer">', unsafe_allow_html=True)
        if t_status == "Completed":
            st.markdown(f'<span class="completion-text">✅ COMPLETED [{task.get("work_type", "N/A")}]</span><br><small>By: {task.get("completed_by")} | Note: {task.get("comment", "N/A")}</small>', unsafe_allow_html=True)
            if user['role'] == "ADMIN":
                if st.button("🗑️ Admin Delete", key=f"del_{tid}"):
                    requests.delete(f"{DB_BASE_URL}/tasks/{tid}.json"); st.rerun()
        else:
            c_n, c_t, c_h, c_c = st.columns([1.5, 0.8, 0.7, 1])
            note = c_n.text_input("Comment", key=f"n_{tid}", label_visibility="collapsed", placeholder="Note...")
            w_type = c_t.selectbox("Type", ["Regular", "Major"], key=f"t_{tid}", label_visibility="collapsed")
            
            if c_h.button("⏸️ Hold" if t_status != "Hold" else "▶️ Unhold", key=f"h_{tid}", use_container_width=True):
                new_s = "Hold" if t_status != "Hold" else "Pending"
                requests.patch(f"{DB_BASE_URL}/tasks/{tid}.json", json={"status": new_s, "comment": note}); st.rerun()
                
            if c_c.button("✅ Done", key=f"done_{tid}", use_container_width=True):
                requests.patch(f"{DB_BASE_URL}/tasks/{tid}.json", json={"status": "Completed", "completed_by": user['name'], "work_type": w_type, "comment": note, "finished_at": get_now_ist()}); st.rerun()

            # LOGIC: Inline Edit Toggle
            if user['role'] == "ADMIN" or task.get('assigner') == user['name']:
                if st.button("✏️ EDIT", key=f"edit_btn_{tid}", use_container_width=True):
                    st.session_state.edit_mode, st.session_state.edit_tid = True, tid
                    st.session_state.edit_fin = task.get('finance')
                    st.session_state.edit_dtl = task.get('task').split('] ', 1)[-1] if '] ' in task.get('task', '') else task.get('task', '')
                    components.html("<script>window.parent.document.querySelector('section.main').scrollTo(0, 0);</script>", height=0)
                    st.rerun()
                    
                if st.checkbox("🗑️ Delete?", key=f"chk_{tid}"):
                    if st.button("CONFIRM DELETE", key=f"btn_{tid}"):
                        requests.delete(f"{DB_BASE_URL}/tasks/{tid}.json"); st.rerun()
        
        st.markdown('</div></div></div>', unsafe_allow_html=True)
    st.divider()

if st.sidebar.button("🚪 Logout"):
    st.session_state.authenticated = False; st.rerun()