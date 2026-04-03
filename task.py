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

st.set_page_config(page_title="RAAS | Ultimate Ledger 5.0", layout="wide")

# --- 2. THE ULTIMATE CSS (Galloping Bar + 22px Font) ---
st.markdown("""
    <style>
    html, body, [class*="st-"], .stMarkdown p, .stTextInput input, .stSelectbox div { font-size: 22px !important; } 
    .main { background-color: #000000; }
    .stApp { background-color: #000000; color: #E0E0E0; }
    
    .sleek-card {
        display: flex;
        background-color: #0A0A0A;
        border: 1px solid #333333;
        border-radius: 15px;
        margin-bottom: 25px;
        overflow: hidden;
    }
    .galloping-bar { width: 25px; flex-shrink: 0; }
    .card-body { flex-grow: 1; display: flex; flex-direction: column; width: 100%; }
    .card-text { padding: 25px; border-bottom: 1px solid #222222; }
    .card-footer { background-color: #111111; padding: 20px; border-top: 1px solid #222222; }
    
    .edit-zone { background-color: #161616; padding: 20px; border-top: 1px dashed #444; border-bottom: 1px dashed #444; }
    
    .status-pending { background-color: #C29100 !important; }
    .status-completed { background-color: #1B5E20 !important; }
    .status-hold { background-color: #C71585 !important; }
    .status-high { background-color: #B71C1C !important; }
    
    .completion-box { background-color: #0D1B0D; border: 1px solid #1B5E20; padding: 15px; border-radius: 10px; color: #81C784; }
    </style>
""", unsafe_allow_html=True)

# --- 3. AUTH & HARDWARE LOCK ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if "edit_mode" not in st.session_state: st.session_state.edit_mode = False
if "edit_tid" not in st.session_state: st.session_state.edit_tid = None

def get_now_ist(): return datetime.now(IST).strftime("%d/%b/%Y %H:%M:%S")

if not st.session_state.authenticated:
    st.title("🔐 RAAS SECURE ACCESS")
    name_in = st.text_input("Name").upper().strip()
    pwd_in = st.text_input("Password", type="password")
    if st.button("LOGIN"):
        users_db = requests.get(USERS_URL).json() or {}
        is_admin = (pwd_in == "1586")
        if name_in and (is_admin or pwd_in == "1234"):
            if name_in not in users_db and not is_admin:
                st.error("🚫 Access Denied. No Slot.")
            else:
                st.session_state.user_data = {"name": name_in, "role": "ADMIN" if is_admin else "STAFF"}
                st.session_state.authenticated = True
                st.toast(f"Welcome, {name_in}!")
                st.rerun()
    st.stop()

# --- 4. DATA FETCH ---
user = st.session_state.user_data
# This pulls the entire database into the app
tasks_dict = requests.get(TASKS_URL).json() or {}

# GLOBAL LIST GENERATOR: This scans every task and creates the unique list of Finance names
all_fins = sorted(list(set(str(t.get('finance', '')).upper() for t in tasks_dict.values() if t.get('finance'))))

# --- 5. ADMIN SIDEBAR (Master Control: User & Finance Lists) ---
if user['role'] == "ADMIN":
    with st.sidebar:
        st.header("⚙️ MASTER CONTROL")
        
        # --- 1. USER MANAGEMENT ---
        with st.expander("👤 User Slot Management", expanded=False):
            users_db = requests.get(USERS_URL).json() or {}
            all_users = sorted([u for u in users_db.keys() if u != "ADMIN"])
            
            st.subheader("Manage Existing Users")
            target_user = st.selectbox("Select User to Remove", ["---"] + all_users)
            if target_user != "---":
                if st.button(f"🗑️ Delete {target_user}", use_container_width=True):
                    requests.delete(f"{DB_BASE_URL}/users/{target_user}.json")
                    st.toast(f"User {target_user} Removed")
                    st.rerun()
            
            st.divider()
            st.subheader("Add New User")
            nu = st.text_input("New Staff Name").upper().strip()
            if st.button("✅ Authorize New Name", use_container_width=True):
                if nu:
                    requests.patch(f"{DB_BASE_URL}/users/{nu}.json", json={"role":"STAFF"})
                    st.toast(f"Slot Created for {nu}")
                    st.rerun()

        # --- 2. FINANCE CATEGORY MASTER (Global Updates) ---
        with st.expander("🛠️ Finance Category Master", expanded=False):
            st.subheader("Existing Categories")
            target_f = st.selectbox("Select Category to Edit", ["---"] + all_fins)
            
            if target_f != "---":
                # Rename Section: This updates the name in every task in the DB
                st.markdown(f"**Action: Rename {target_f}**")
                rename_f = st.text_input(f"New Name for {target_f}").upper()
                if st.button(f"Update Name to {rename_f}", use_container_width=True):
                    for tid, d in tasks_dict.items():
                        if d.get('finance') == target_f: 
                            requests.patch(f"{DB_BASE_URL}/tasks/{tid}.json", json={"finance": rename_f})
                    st.toast("✅ Global Rename Complete!")
                    st.rerun() # Forces the app to rebuild 'all_fins'

                st.divider()
                # Delete Section: This wipes the category from the DB
                st.markdown(f"**Action: Wipe {target_f}**")
                if st.checkbox(f"Confirm Delete all {target_f}?"):
                    if st.button(f"🔥 WIPE ALL {target_f} RECORDS", use_container_width=True):
                        to_delete = [tid for tid, d in tasks_dict.items() if d.get('finance') == target_f]
                        for tid in to_delete:
                            requests.delete(f"{DB_BASE_URL}/tasks/{tid}.json")
                        st.toast(f"Category {target_f} Deleted!")
                        st.rerun()

# --- 6. TOP FORM (Add New / Jump-to-Edit) ---
st.subheader("📝 Report Correction Ledger")
with st.expander("Ledger Entry Form", expanded=True):
    c1, c2, c3 = st.columns([1.5, 1, 1])
    f_sel = c1.selectbox("Finance", ["--- SELECT ---", "ADD NEW+"] + all_fins)
    fin_active = st.text_input("New Finance Name").upper() if f_sel == "ADD NEW+" else f_sel
    cat = c2.selectbox("Category", ["---", "Rate Correction", "Spelling", "Digital Sign", "Upload", "Drafting"])
    prio = c3.select_slider("Priority", ["Normal", "Medium", "High"])
    dtl_main = st.text_area("Task Details", value=st.session_state.get('edit_dtl_top', ""))
    
    if st.button("🚀 PUSH TO LEDGER", use_container_width=True):
        if fin_active != "--- SELECT ---" and dtl_main:
            requests.post(TASKS_URL, json={"finance": fin_active, "task": f"[{cat}] {dtl_main}", "priority": prio, "assigner": user['name'], "status": "Pending", "assigned_at": get_now_ist()})
            st.session_state.edit_dtl_top = ""
            st.toast("Task Pushed to Database!")
            st.rerun()

# --- 7. SEARCH & EXCEL EXPORT ---
st.divider()
s1, s2, s3 = st.columns([2, 1, 1])
search = s1.text_input("🔍 Search (Finance, Task, or Staff)").lower()
if s2.button("🔄 Refresh Data"): st.rerun()
if s3.button("📥 Export to Excel", use_container_width=True):
    df = pd.DataFrame.from_dict(tasks_dict, orient='index')
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as wr: df.to_excel(wr)
    st.download_button("Download RAAS_Report.xlsx", buf.getvalue(), "RAAS_Report.xlsx")

# --- 8. THE UNIFIED TASK CARDS (150-Item Buffer) ---
keys = list(tasks_dict.keys()); keys.reverse()

for tid in keys[:150]:
    task = tasks_dict[tid]
    if search and (search not in str(task.get('finance','')).lower() and search not in str(task.get('task','')).lower()): continue

    t_status, t_prio = task.get('status', 'Pending'), task.get('priority', 'Normal')
    s_color = "status-pending"
    if t_status == "Completed": s_color = "status-completed"
    elif t_status == "Hold": s_color = "status-hold"
    elif t_prio == "High" and t_status == "Pending": s_color = "status-high"

    st.markdown(f'''
        <div class="sleek-card">
            <div class="galloping-bar {s_color}"></div>
            <div class="card-body">
                <div class="card-text">
                    <strong style="font-size:28px;">{task.get('finance')}</strong> | <small>{task.get('assigned_at')}</small><br>
                    <div style="margin-top:10px;">{task.get('task')}</div>
                </div>
    ''', unsafe_allow_html=True)

    with st.container():
        # --- INLINE EDIT SUITE (The Integrated Feature) ---
        if t_status != "Completed" and (user['role'] == "ADMIN" or task.get('assigner') == user['name']):
            if st.checkbox(f"✏️ Modify Task", key=f"mod_{tid}"):
                st.markdown('<div class="edit-zone">', unsafe_allow_html=True)
                ec1, ec2 = st.columns(2)
                e_fin = ec1.text_input("Update Finance", value=task.get('finance'), key=f"ef_{tid}")
                e_prio = ec2.selectbox("Update Priority", ["Normal", "Medium", "High"], index=["Normal", "Medium", "High"].index(t_prio), key=f"ep_{tid}")
                e_dtl = st.text_area("Update Details", value=task.get('task'), key=f"ed_{tid}")
                if st.button("💾 SAVE CHANGES", key=f"sv_{tid}", use_container_width=True):
                    requests.patch(f"{DB_BASE_URL}/tasks/{tid}.json", json={"finance": e_fin, "task": e_dtl, "priority": e_prio})
                    st.toast("Changes Saved Successfully!")
                    st.rerun()
                if st.button("⬆️ SEND TO TOP FORM", key=f"top_{tid}", use_container_width=True):
                    st.session_state.edit_dtl_top = task.get('task')
                    components.html("<script>window.parent.document.querySelector('section.main').scrollTo(0, 0);</script>", height=0)
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="card-footer">', unsafe_allow_html=True)
        if t_status == "Completed":
            st.markdown(f'''
                <div class="completion-box">
                    👤 <b>{task.get("completed_by")}</b> closed this <b>{task.get("work_type")}</b> task at {task.get("finished_at")}<br>
                    📝 <i>Note: {task.get("comment", "N/A")}</i>
                </div>
            ''', unsafe_allow_html=True)
            if user['role'] == "ADMIN":
                if st.button("🗑️ Admin Delete Record", key=f"adm_del_{tid}"):
                    requests.delete(f"{DB_BASE_URL}/tasks/{tid}.json"); st.rerun()
        else:
            c_note, c_type, c_hold, c_done = st.columns([1.5, 0.8, 0.7, 1])
            note = c_note.text_input("Comment", key=f"n_{tid}", label_visibility="collapsed", placeholder="Closing note...")
            w_type = c_type.selectbox("Type", ["Regular", "Major"], key=f"t_{tid}", label_visibility="collapsed")
            
            if c_hold.button("⏸️ Hold" if t_status != "Hold" else "▶️ Play", key=f"h_{tid}", use_container_width=True):
                new_s = "Hold" if t_status != "Hold" else "Pending"
                requests.patch(f"{DB_BASE_URL}/tasks/{tid}.json", json={"status": new_s, "comment": note})
                st.toast(f"Status changed to {new_s}")
                st.rerun()
                
            if c_done.button("✅ Mark Done", key=f"d_{tid}", use_container_width=True):
                requests.patch(f"{DB_BASE_URL}/tasks/{tid}.json", json={"status": "Completed", "completed_by": user['name'], "work_type": w_type, "comment": note, "finished_at": get_now_ist()})
                st.toast("Task Completed!")
                st.rerun()
                
            if user['role'] == "ADMIN" or task.get('assigner') == user['name']:
                if st.checkbox("🗑️", key=f"del_chk_{tid}"):
                    if st.button("CONFIRM DELETE", key=f"del_btn_{tid}", use_container_width=True):
                        requests.delete(f"{DB_BASE_URL}/tasks/{tid}.json"); st.rerun()

        st.markdown('</div></div></div>', unsafe_allow_html=True)
    st.divider()

if st.sidebar.button("🚪 LOGOUT"):
    st.session_state.authenticated = False; st.rerun()