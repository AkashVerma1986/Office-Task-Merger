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
CATEGORIES_URL = f"{DB_BASE_URL}/categories.json"
FINANCE_MASTER_URL = f"{DB_BASE_URL}/finance_list.json"
IST = pytz.timezone('Asia/Kolkata') 

st.set_page_config(page_title="RAAS | Ultimate Ledger 5.0", layout="wide")

# --- 2. THE ULTIMATE CSS (Galloping Bar + 22px Font) ---
st.markdown("""
    <style>
    html, body, [class*="st-"], .stMarkdown p, .stTextInput input, .stSelectbox div { font-size: 24px !important; } 
    .main { background-color: #000000; }
    .stApp { background-color: #000000; color: #E0E0E0; }
    
    .sleek-card {
        display: flex;
        background-color: #0A0A0A;
        border: 1px solid #333333;
        border-radius: 15px;
        margin-bottom: 12px;
        overflow: hidden;
    }
    .galloping-bar { width: 7px; flex-shrink: 5; }
    .card-body { flex-grow: 1; display: flex; flex-direction: column; width: 100%; }
    .card-text { padding: 12px; border-bottom: 1px solid #222222; }
    .card-footer { background-color: #111111; padding: 7px; border-top: 1px solid #222222; }
    
    .edit-zone { background-color: #161616; padding: 7px; border-top: 1px dashed #444; border-bottom: 1px dashed #444; }
    
    .status-pending { background-color: #C29100 !important; }
    .status-completed { background-color: #1B5E20 !important; }
    .status-hold { background-color: #C71585 !important; }
    .status-high { background-color: #B71C1C !important; }
    /* Fix for dropdown visibility */
    div[data-baseweb="select"] > div, 
    div[aria-selected="true"], 
    li[role="option"] { 
        color: #FFFFFF !important; 
        background-color: #1A1A1A !important; 
    }

    .completion-box { background-color: #0D1B0D; border: 1px solid #1B5E20; padding: 10px; border-radius: 5px; color: #81C784; }
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
tasks_dict = requests.get(TASKS_URL, verify=False).json() or {}

# NEW: Fetch the Master Finance List directly
FINANCE_MASTER_URL = f"{DB_BASE_URL}/finance_list.json"
master_fin_data = requests.get(FINANCE_MASTER_URL, verify=False).json() or {}
CATEGORIES_URL = f"{DB_BASE_URL}/categories.json"
master_cat_data = requests.get(CATEGORIES_URL, verify=False).json() or {}
all_cats = sorted([c for c in master_cat_data.keys()])
# Convert the dictionary keys into a sorted list
all_fins = sorted([f.upper() for f in master_fin_data.keys()])
# --- 4. DATA FETCH (INSERT HERE) ---
CATEGORIES_URL = f"{DB_BASE_URL}/categories.json"
master_cat_data = requests.get(CATEGORIES_URL, verify=False).json() or {}
all_cats = sorted([c for c in master_cat_data.keys()]) # Removed .upper() to save as typed

# --- 5. ADMIN SIDEBAR (Master Control: All Features) ---
if user['role'] == "ADMIN":
    with st.sidebar:
        st.header("⚙️ MASTER CONTROL")
        
        # --- FEATURE 1: USER SLOT MANAGEMENT ---
        with st.expander("👤 User Slot Management", expanded=False):
            users_db = requests.get(USERS_URL).json() or {}
            all_users = sorted([u for u in users_db.keys() if u != "ADMIN"])
            st.markdown("### Manage Existing")
            target_user = st.selectbox("Select User to Remove", ["---"] + all_users, key="admin_user_sel")
            if target_user != "---":
                if st.button(f"🗑️ Delete {target_user}", use_container_width=True):
                    requests.delete(f"{DB_BASE_URL}/users/{target_user}.json")
                    st.rerun()
            st.divider()
            st.markdown("### Add New User")
            nu = st.text_input("New Staff Name").upper().strip()
            if st.button("✅ Authorize New Name", use_container_width=True):
                if nu:
                    requests.patch(f"{DB_BASE_URL}/users/{nu}.json", json={"role":"STAFF"})
                    st.rerun()

        # --- FEATURE 2: FINANCE MASTER LIST (Dropdown Control) ---
        with st.expander("🛠️ Finance Master List", expanded=False):
            st.markdown("### Add to Dropdown")
            new_f_name = st.text_input("Add New Category").upper().strip()
            if st.button("➕ Add to Master", use_container_width=True):
                if new_f_name:
                    requests.patch(FINANCE_MASTER_URL, json={new_f_name: True})
                    st.rerun()

            st.divider()
            st.markdown("### Edit/Delete Existing")
            target_f = st.selectbox("Select Category", ["---"] + all_fins, key="admin_fin_sel")
            if target_f != "---":
                rename_f = st.text_input(f"Rename '{target_f}' to:").upper().strip()
                if st.button(f"Update Globally", use_container_width=True):
                    # Update Master List
                    requests.patch(FINANCE_MASTER_URL, json={rename_f: True})
                    requests.delete(f"{DB_BASE_URL}/finance_list/{target_f}.json")
                    # Update all tasks in DB
                    for tid, d in tasks_dict.items():
                        if d.get('finance') == target_f:
                            requests.patch(f"{DB_BASE_URL}/tasks/{tid}.json", json={"finance": rename_f})
                    st.rerun()

                if st.checkbox(f"Remove '{target_f}' from List?"):
                    if st.button(f"🗑️ DELETE FROM DROPDOWN", use_container_width=True):
                        requests.delete(f"{DB_BASE_URL}/finance_list/{target_f}.json")
                        st.rerun()

         # --- FEATURE 3: CATEGORY MASTER LIST (INSERT HERE) ---
        with st.expander("📝 Category Master List", expanded=False):
            st.markdown("### Add Category")
            new_c_name = st.text_input("New Category Name", key="add_cat_input").strip()
            if st.button("➕ Add Category", key="btn_add_cat", use_container_width=True):
                if new_c_name:
                    requests.patch(CATEGORIES_URL, json={new_c_name: True})
                    st.rerun()

            st.divider()
            st.markdown("### Edit/Delete Existing")
            target_c = st.selectbox("Select Category", ["---"] + all_cats, key="admin_cat_sel")
            if target_c != "---":
                rename_c = st.text_input(f"Rename '{target_c}' to:", key="ren_cat_input").strip()
                if st.button(f"Update Category Globally", key="btn_upd_cat", use_container_width=True):
                    requests.patch(CATEGORIES_URL, json={rename_c: True})
                    requests.delete(f"{DB_BASE_URL}/categories/{target_c}.json")
                    # Update existing tasks
                    for tid, d in tasks_dict.items():
                        if f"[{target_c}]" in d.get('task', ''):
                            new_text = d.get('task').replace(f"[{target_c}]", f"[{rename_c}]")
                            requests.patch(f"{DB_BASE_URL}/tasks/{tid}.json", json={"task": new_text})
                    st.rerun()

                if st.checkbox(f"Remove '{target_c}' from List?", key="del_cat_chk"):
                    if st.button(f"🗑️ DELETE CATEGORY", key="btn_final_del_cat", use_container_width=True):
                        requests.delete(f"{DB_BASE_URL}/categories/{target_c}.json")
                        st.rerun()

# --- 6. TOP FORM (Add New / Jump-to-Edit) ---
st.subheader("📝 Report Correction Ledger")
with st.expander("Ledger Entry Form", expanded=True):
    # Added a 4th column for LAN No.
    c1, c2, c_lan, c3 = st.columns([1.5, 1, 1, 1])
    
    f_sel = c1.selectbox("Finance", ["--- SELECT ---", "ADD NEW+"] + all_fins, key="main_finance_picker")
    fin_active = st.text_input("New Finance Name").upper() if f_sel == "ADD NEW+" else f_sel
    
    cat = c2.selectbox("Category", ["---"] + all_cats, key="main_cat_picker")
    
    # NEW: LAN No. Input (Mandatory)
    lan_no = c_lan.text_input("LAN No.", placeholder="Required").strip()
    
    prio = c3.select_slider("Priority", ["Normal", "Medium", "High"])
    dtl_main = st.text_area("Task Details", value=st.session_state.get('edit_dtl_top', ""))
    
    if st.button(" SUBMIT", use_container_width=True):
        # Logic Check: Ensure Finance, LAN No, and Details are present
        if fin_active != "--- SELECT ---" and lan_no and dtl_main:
            # Save the record including the new 'lan' field
            payload = {
                "finance": fin_active, 
                "lan": lan_no,
                "task": f"[{cat}] {dtl_main}", 
                "priority": prio, 
                "assigner": user['name'], 
                "status": "Pending", 
                "assigned_at": get_now_ist()
            }
            requests.post(TASKS_URL, json=payload)
            
            # Update Master Finance List
            requests.patch(FINANCE_MASTER_URL, json={fin_active: True})
            
            st.session_state.edit_dtl_top = ""
            if "main_finance_picker" in st.session_state: st.session_state.main_finance_picker = "--- SELECT ---"
            if "main_cat_picker" in st.session_state: st.session_state.main_cat_picker = "---"
            st.toast(f"Pushed Task for LAN: {lan_no}!")
            st.rerun()
        elif not lan_no:
            st.error("🛑 LAN No. is mandatory! Please enter it before pushing.")
        else:
            st.warning("⚠️ Please fill in Finance and Task Details.")

# --- 7. SEARCH, DATE FILTER & EXCEL EXPORT ---
st.divider()
c_date, c_search = st.columns([1, 1])
with c_date:
    date_range = st.date_input("📅 Filter by Date Range", value=[], help="Select Start and End date")

# Convert dictionary to DataFrame for filtering
df_all = pd.DataFrame.from_dict(tasks_dict, orient='index')

if not df_all.empty:
    # Convert 'assigned_at' strings to actual datetime objects for filtering
    df_all['date_dt'] = pd.to_datetime(df_all['assigned_at'], format="%d/%b/%Y %H:%M:%S", errors='coerce')
    
    # Apply Date Filter if two dates are selected
    if len(date_range) == 2:
        start_date, end_date = date_range
        df_all = df_all[(df_all['date_dt'].dt.date >= start_date) & (df_all['date_dt'].dt.date <= end_date)]

s1, s2, s3 = st.columns([2, 1, 1])
search = s1.text_input("🔍 Search (Finance, Task, or Staff)", key="search_bar").lower()

# Apply Search Filter
filtered_df = df_all.copy()
if search:
    filtered_df = filtered_df[
        (filtered_df['finance'].str.contains(search, case=False, na=False)) | 
        (filtered_df['task'].str.contains(search, case=False, na=False)) |
	(filtered_df['lan'].astype(str).str.contains(search, case=False, na=False)) # Added LAN search
    ]

if s2.button("🔄 Refresh Data"): 
    st.rerun()

# Fixed Export Logic using Download Button
with s3:
    if not filtered_df.empty:
        buf = io.BytesIO()
        export_output = filtered_df.drop(columns=['date_dt'], errors='ignore')
        with pd.ExcelWriter(buf, engine='openpyxl') as wr:
            export_output.to_excel(wr, index=True)
        
        st.download_button(
            label="📥 Download Excel",
            data=buf.getvalue(),
            file_name=f"RAAS_Export_{datetime.now().strftime('%d_%b')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    else:
        st.button("📥 No Data", disabled=True, use_container_width=True)

# --- 8. THE UNIFIED TASK CARDS ---
keys = list(filtered_df.index)
keys.reverse()

# --- 8. THE UNIFIED TASK CARDS ---
keys = list(filtered_df.index)
keys.reverse()

# --- 8. THE UNIFIED TASK CARDS ---
keys = list(filtered_df.index)
keys.reverse()

for tid in keys[:150]:
    task = tasks_dict[tid]
    # Search logic
    if search and (search not in str(task.get('finance','')).lower() and search not in str(task.get('task','')).lower()): 
        continue

    # 1. COLOR LOGIC
    t_status, t_prio = task.get('status', 'Pending'), task.get('priority', 'Normal')
    s_color = "status-pending"
    if t_status == "Completed": s_color = "status-completed"
    elif t_status == "Hold": s_color = "status-hold"
    elif t_prio == "High" and t_status == "Pending": s_color = "status-high"

    # 2. CARD HEADER (Displays Finance & LAN)
    st.markdown(f'''
        <div class="sleek-card">
            <div class="galloping-bar {s_color}"></div>
            <div class="card-body">
                <div class="card-text">
                    <strong style="font-size:28px;">{task.get('finance')}</strong> | 
                    <span style="color:#FFD700;">LAN: {task.get('lan', 'N/A')}</span> | 
                    <small>{task.get('assigned_at')}</small><br>
                    <div style="margin-top:10px;">{task.get('task')}</div>
                </div>
    ''', unsafe_allow_html=True)

    with st.container():
        # --- INLINE EDIT SUITE ---
        if t_status != "Completed" and (user['role'] == "ADMIN" or task.get('assigner') == user['name']):
            if st.checkbox(f"✏️ Modify Task", key=f"mod_{tid}"):
                st.markdown('<div class="edit-zone">', unsafe_allow_html=True)
                ec1, ec_l, ec2 = st.columns([1, 1, 1])
                
                # Fetch current finance index
                current_val = task.get('finance', "")
                try:
                    f_idx = all_fins.index(current_val)
                except (ValueError, IndexError):
                    f_idx = 0

                e_fin = ec1.selectbox("Update Finance", all_fins, index=f_idx, key=f"ef_{tid}")
                e_lan = ec_l.text_input("Update LAN No.", value=task.get('lan', ""), key=f"elan_{tid}")
                e_prio = ec2.selectbox("Update Priority", ["Normal", "Medium", "High"], index=["Normal", "Medium", "High"].index(t_prio), key=f"ep_{tid}")
                e_dtl = st.text_area("Update Details", value=task.get('task'), key=f"ed_{tid}")
                
                if st.button("💾 SAVE CHANGES", key=f"sv_{tid}", use_container_width=True):
                    requests.patch(f"{DB_BASE_URL}/tasks/{tid}.json", json={
                        "finance": e_fin, "lan": e_lan, "task": e_dtl, "priority": e_prio
                    })
                    st.session_state.edit_dtl_top = ""
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        # --- COMPLETION & ACTION CONTROLS ---
        if t_status == "Completed":
            st.markdown(f'''
                <div class="completion-box">
                    👤 <b>{task.get("completed_by")}</b> closed this <b>{task.get("work_type")}</b> task at {task.get("finished_at")}<br>
                    📝 <i>Note: {task.get("comment", "N/A")}</i>
                </div>
            ''', unsafe_allow_html=True)
        else:
            c_note, c_type, c_hold, c_done = st.columns([1.5, 0.8, 0.7, 1])
            note = c_note.text_input("Comment", key=f"n_{tid}", label_visibility="collapsed", placeholder="Closing note...")
            w_type = c_type.selectbox("Type", ["Regular", "Major"], key=f"t_{tid}", label_visibility="collapsed")
            
            # Hold Toggle
            if c_hold.button("⏸️ Hold" if t_status != "Hold" else "▶️ Unhold", key=f"h_{tid}", use_container_width=True):
                new_s = "Hold" if t_status != "Hold" else "Pending"
                requests.patch(f"{DB_BASE_URL}/tasks/{tid}.json", json={"status": new_s, "comment": note})
                st.rerun()
                
            # Complete Action
            if c_done.button("✅ Complete", key=f"d_{tid}", use_container_width=True):
                requests.patch(f"{DB_BASE_URL}/tasks/{tid}.json", json={
                    "status": "Completed", "completed_by": user['name'], 
                    "work_type": w_type, "comment": note, "finished_at": get_now_ist()
                })
                st.rerun()
                
            # Admin Delete Option
            if user['role'] == "ADMIN" or task.get('assigner') == user['name']:
                if st.checkbox("🗑️", key=f"del_chk_{tid}"):
                    if st.button("CONFIRM DELETE", key=f"del_btn_{tid}", use_container_width=True):
                        requests.delete(f"{DB_BASE_URL}/tasks/{tid}.json")
                        st.rerun()

        # Close the card-body and sleek-card divs
        st.markdown('</div></div></div>', unsafe_allow_html=True)
    st.divider()

if st.sidebar.button("🚪 LOGOUT"):
    st.session_state.authenticated = False; st.rerun()