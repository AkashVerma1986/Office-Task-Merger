import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import pytz 
import io
import os
import time
import streamlit.components.v1 as components

# --- 1. CONFIGURATION ---
DB_BASE_URL = "https://office-task-ledger-default-rtdb.asia-southeast1.firebasedatabase.app"
TASKS_URL = f"{DB_BASE_URL}/tasks.json"
USERS_URL = f"{DB_BASE_URL}/users.json"
CATEGORIES_URL = f"{DB_BASE_URL}/categories.json"
FINANCE_MASTER_URL = f"{DB_BASE_URL}/finance_list.json"
IST = pytz.timezone('Asia/Kolkata') 

st.set_page_config(page_title="RAAS | Ultimate Ledger 5.0", layout="wide")

# --- 2. THE ULTIMATE CSS (White Theme & Tight Spacing Layout) ---
st.markdown("""
    <style>
    /* Global Font, Clean Background, and Tight Layout */
    html, body, [class*="st-"], .stMarkdown p, .stTextInput input, .stSelectbox div { 
        font-size: 22px !important; 
    } 
    
    .stApp { color: #1A1A1A; }

    /* Force Streamlit to drop general empty vertical whitespace */
    .stAppViewMain .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 1.5rem !important;
        gap: 0.5rem !important; 
    }
    
    /* PROFESSIONAL LIGHT BUTTONS */
    .stButton > button {
        background-color: #F0F2F6 !important; 
        color: #1A1A1A !important;
        border: 1px solid #DDE1E7 !important;
        border-radius: 8px !important;
        padding: 10px 20px !important;
        font-weight: 600 !important;
        width: 100%;
        text-transform: uppercase;
    }

    .stButton > button:hover {
        background-color: #E0E4EB !important;
        border-color: #B0B7C3 !important;
        color: #000000 !important;
    }

    /* Updated Card CSS Layout Gaps */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        margin-bottom: 8px !important; 
    }
    
    /* TARGETS THE NATIVE STREAMLIT BORDER CONTAINER WITH AN INTERNAL SECONDARY BOUNDARY */
    div[data-testid="stVerticalBlockBorderWrapper"].border-pending { 
        border: 2px solid #FFC107 !important; 
        border-left: 10px solid #FFC107 !important; 
        box-shadow: inset 0 0 0 4px #FFFFFF, inset 0 0 0 6px #FFC107 !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"].border-completed { 
        border: 2px solid #28A745 !important; 
        border-left: 10px solid #28A745 !important; 
        box-shadow: inset 0 0 0 4px #FFFFFF, inset 0 0 0 6px #28A745 !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"].border-hold { 
        border: 2px solid #E83E8C !important; 
        border-left: 10px solid #E83E8C !important; 
        box-shadow: inset 0 0 0 4px #FFFFFF, inset 0 0 0 6px #E83E8C !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"].border-high { 
        border: 2px solid #DC3545 !important; 
        border-left: 10px solid #DC3545 !important; 
        box-shadow: inset 0 0 0 4px #FFFFFF, inset 0 0 0 6px #DC3545 !important;
    }

    /* Tightens padding inside the cards and squishes row gaps */
    div[data-testid="stVerticalBlockBorderWrapper"] > div {
        padding: 4px 12px !important;   
        gap: 0.3rem !important;          
    }
    
    /* Strip layout margins on element containers to stop the expanded look */
    div[data-testid="element-container"] {
        margin-bottom: 0px !important;
    }
    
    /* Makes dividers thinner with less whitespace */
    hr {
        margin: 0.4rem 0 !important;
    }

    .gallocation-bar { width: 8px; flex-shrink: 0; }
    .card-body { 
        flex-grow: 1; 
        display: block; 
        width: 100%; 
        padding-bottom: 10px;
    }
    .card-text { padding: 15px; border-bottom: 1px solid #F0F0F0; color: #1A1A1A; }
    .card-footer { background-color: #F8F9FA; padding: 7px; border-top: 1px solid #F0F0F0; }
    
    /* Status Colors */
    .status-pending { background-color: #FFC107 !important; }
    .status-completed { background-color: #28A745 !important; }
    .status-hold { background-color: #E83E8C !important; }
    .status-high { background-color: #DC3545 !important; }

    /* Completion Box */
    .completion-box { 
        background-color: #E9F7EF; 
        border: 1px solid #28A745; 
        padding: 10px; 
        border-radius: 5px; 
        color: #155724; 
        margin: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. AUTH & DEVICE LOCK ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if "edit_mode" not in st.session_state: st.session_state.edit_mode = False
if "edit_tid" not in st.session_state: st.session_state.edit_tid = None
if "my_tasks_only" not in st.session_state: 
    st.session_state.my_tasks_only = False

def get_now_ist(): 
    return datetime.now(IST).strftime("%d/%b/%Y %H:%M:%S")

def get_device_id():
    try:
        return st.context.headers.get("User-Agent", "unknown_device")
    except:
        return "default_device"

if not st.session_state.authenticated:
    st.title("🔐 RAAS SECURE ACCESS")
    name_in = st.text_input("Name").upper().strip()
    pwd_in = st.text_input("Password", type="password")
    
    if st.button("LOGIN"):
        users_db = requests.get(USERS_URL).json() or {}
        is_admin = (pwd_in == "1586")
        dev_id = get_device_id()

        if name_in and (is_admin or pwd_in == "1234"):
            user_entry = users_db.get(name_in, {})
            
            approved = user_entry.get("approved_devices", [])
            pending = user_entry.get("pending_devices", [])
            
            if not isinstance(approved, list): approved = []
            if not isinstance(pending, list): pending = []

            if is_admin:
                st.session_state.user_data = {"name": name_in, "role": "ADMIN"}
                st.session_state.authenticated = True
                st.rerun()
            elif name_in in users_db:
                if dev_id in approved:
                    st.session_state.user_data = {"name": name_in, "role": "STAFF"}
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    if dev_id not in pending:
                        pending.append(dev_id)
                        requests.patch(f"{DB_BASE_URL}/users/{name_in}.json", json={"pending_devices": pending})
                    st.error("🚫 Device not approved. Contact Admin to authorize this device.")
            else:
                st.error("🚫 Access Denied. No Slot.")
    st.stop()

# --- 4. DATA FETCH ---
user = st.session_state.user_data
tasks_dict = requests.get(TASKS_URL, verify=False).json() or {}

master_fin_data = requests.get(FINANCE_MASTER_URL, verify=False).json() or {}
master_cat_data = requests.get(CATEGORIES_URL, verify=False).json() or {}
all_cats = sorted([c for c in master_cat_data.keys()])

df_all = pd.DataFrame.from_dict(tasks_dict, orient='index')

@st.dialog("Edit Task Details", width="large")
def edit_task_dialog(tid, task):
    ec1, ec_cat, ec_l, ec2 = st.columns([2, 2, 2, 2])
    
    current_f = task.get('finance', "")
    f_idx = all_fins.index(current_f) if current_f in all_fins else 0
    e_fin = ec1.selectbox("Update Finance", all_fins, index=f_idx, key=f"ef_dlg_{tid}")
    
    full_task_text = task.get('task', "")
    current_c = "---"
    clean_task_text = full_task_text
    
    if "]" in full_task_text and full_task_text.startswith("["):
        try:
            current_c = full_task_text.split("]")[0].replace("[", "").strip()
            clean_task_text = full_task_text.split("]", 1)[1].strip()
        except:
            pass
    
    all_cats_with_default = ["---"] + all_cats
    c_idx = all_cats_with_default.index(current_c) if current_c in all_cats_with_default else 0
    e_cat = ec_cat.selectbox("Update Category", all_cats_with_default, index=c_idx, key=f"ec_dlg_{tid}")
    
    e_lan = ec_l.text_input("Update LAN No.", value=task.get('lan', ""), key=f"elan_dlg_{tid}")
    e_prio = ec2.selectbox("Update Priority", ["Normal", "Medium", "High"], 
                          index=["Normal", "Medium", "High"].index(task.get('priority', 'Normal')), key=f"ep_dlg_{tid}")
    
    e_dtl = st.text_area("Update Details", value=clean_task_text, key=f"ed_dlg_{tid}", height=200)
    
    if st.button("💾 SAVE CHANGES", key=f"sv_dlg_{tid}", use_container_width=True):
        final_task_string = f"[{e_cat}] {e_dtl}" if e_cat != "---" else e_dtl
        
        requests.patch(f"{DB_BASE_URL}/tasks/{tid}.json", json={
            "finance": e_fin, 
            "lan": e_lan, 
            "task": final_task_string, 
            "priority": e_prio
        })
        
        msg_placeholder = st.empty()
        msg_placeholder.success("✅ Modification Done!")
        time.sleep(3)
        msg_placeholder.empty()
        st.rerun()

all_fins = sorted([f.upper() for f in master_fin_data.keys()])

# --- 5. ADMIN SIDEBAR ---
if user['role'] == "ADMIN":
    with st.sidebar:
        st.header("⚙️ Control Panel")

        if user['role'] == "ADMIN":
            with st.sidebar:
        
                # --- NEW CODE: HIGH-VISIBILITY TASK STATUS COLOR PANEL ---
                st.markdown("### 📊 Task Ledger Summary")
        
                # Calculate task counts from live data safely
                if not df_all.empty:
                    tot_p = len(df_all[df_all['status'] == "Pending"])
                    tot_h = len(df_all[df_all['status'] == "Hold"])
                    tot_c = len(df_all[df_all['status'] == "Completed"])
                else:
                    tot_p, tot_h, tot_c = 0, 0, 0

                # Injecting custom color bars matching your theme
                st.markdown(f"""
                    <div style="background-color: #FFFFFF; padding: 12px; border-radius: 8px; border: 1px solid #E0E4EB; display: flex; flex-direction: column; gap: 8px;">
                    <div style="display: flex; align-items: center; justify-content: space-between; border-left: 6px solid #FFC107; padding-left: 10px; height: 35px;">
                        <span style="font-weight: 600; font-size: 16px; color: #1A1A1A;">⏳ PENDING TASKS</span>
                        <span style="background-color: #FFC107; color: #000000; font-weight: bold; padding: 2px 10px; border-radius: 20px; font-size: 16px;">{tot_p}</span>
                    </div>
                    <div style="display: flex; align-items: center; justify-content: space-between; border-left: 6px solid #E83E8C; padding-left: 10px; height: 35px;">
                        <span style="font-weight: 600; font-size: 16px; color: #1A1A1A;">⏸️ ON HOLD</span>
                        <span style="background-color: #E83E8C; color: #FFFFFF; font-weight: bold; padding: 2px 10px; border-radius: 20px; font-size: 16px;">{tot_h}</span>
                    </div>
                    <div style="display: flex; align-items: center; justify-content: space-between; border-left: 6px solid #28A745; padding-left: 10px; height: 35px;">
                        <span style="font-weight: 600; font-size: 16px; color: #1A1A1A;">✅ COMPLETED</span>
                        <span style="background-color: #28A745; color: #FFFFFF; font-weight: bold; padding: 2px 10px; border-radius: 20px; font-size: 16px;">{tot_c}</span>
                    </div>
                </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        # --- END OF NEW STATUS COLOR PANEL ---

        # (The rest of your expanders like Device Approval Requests, etc., continue below here...)
        
        with st.expander("📱 Device Approval Requests", expanded=False):
            current_db = requests.get(USERS_URL).json() or {}
            request_found = False
            for u_name, u_data in current_db.items():
                p_list = u_data.get("pending_devices", [])
                a_list = u_data.get("approved_devices", [])
                
                if p_list and isinstance(p_list, list):
                    request_found = True
                    st.write(f"**User:** {u_name}")
                    st.caption(f"Approved: {len(a_list)}/2")
                    
                    for d_id in p_list:
                        # Created a 2-column layout for Approve and Reject actions
                        btn_col1, btn_col2 = st.columns(2)
                        
                        with btn_col1:
                            if st.button(f"✅ Approve", key=f"app_{u_name}_{d_id}", use_container_width=True):
                                if len(a_list) < 2:
                                    a_list.append(d_id)
                                    p_list.remove(d_id)
                                    requests.patch(f"{DB_BASE_URL}/users/{u_name}.json", 
                                                   json={"approved_devices": a_list, "pending_devices": p_list})
                                    st.success(f"Device Linked!")
                                    st.rerun()
                                else:
                                    st.error("User already has 2 devices!")
                                    
                        with btn_col2:
                            if st.button(f"❌ Reject", key=f"rej_{u_name}_{d_id}", use_container_width=True):
                                p_list.remove(d_id)
                                requests.patch(f"{DB_BASE_URL}/users/{u_name}.json", 
                                               json={"pending_devices": p_list})
                                st.warning(f"Request Rejected!")
                                time.sleep(1)
                                st.rerun()
            if not request_found:
                st.info("No pending requests.")
        
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
                    requests.patch(FINANCE_MASTER_URL, json={rename_f: True})
                    requests.delete(f"{DB_BASE_URL}/finance_list/{target_f}.json")
                    for tid, d in tasks_dict.items():
                        if d.get('finance') == target_f:
                            requests.patch(f"{DB_BASE_URL}/tasks/{tid}.json", json={"finance": rename_f})
                    st.rerun()

                if st.checkbox(f"Remove '{target_f}' from List?"):
                    if st.button(f"🗑️ DELETE FROM DROPDOWN", use_container_width=True):
                        requests.delete(f"{DB_BASE_URL}/finance_list/{target_f}.json")
                        st.rerun()

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
    c1, c2, c_lan, c3 = st.columns([1.5, 1, 1, 1])
    
    f_sel = c1.selectbox("Finance", ["--- SELECT ---"] + all_fins, key="main_finance_picker")
    fin_active = f_sel
    
    cat = c2.selectbox("Category", ["---"] + all_cats, key="main_cat_picker")
    lan_no = c_lan.text_input("LAN No.", placeholder="Required").strip()
    prio = c3.select_slider("Priority", ["Normal", "Medium", "High"])
    dtl_main = st.text_area("Task Details", value=st.session_state.get('edit_dtl_top', ""))
    
    # Ensure there are no leading code-block spaces in the label string
    if st.button("SUBMIT", use_container_width=True, type="primary"):
        if fin_active != "--- SELECT ---" and lan_no and dtl_main:
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
            requests.patch(FINANCE_MASTER_URL, json={fin_active: True})
            
            st.session_state.edit_dtl_top = ""
            
            for key in ["main_finance_picker", "main_cat_picker"]:
                if key in st.session_state:
                    del st.session_state[key]
            
            # --- NOTIFICATION ON SUBMIT ---
            st.success(f"🎉 Success! Task for LAN {lan_no} has been added to the ledger.")
            st.toast(f"📢 New Task Added by {user['name']}!", icon="✅")
            
            time.sleep(1.5) 
            st.rerun()
        elif not lan_no:
            st.error("🛑 LAN No. is mandatory! Please enter it before pushing.")
        else:
            st.warning("⚠️ Please fill in Finance and Task Details.")

# --- 7. SEARCH, DATE FILTER, SORTING & EXCEL EXPORT ---
st.divider()

view_filter = st.selectbox(
    "📂 View Filter", 
    ["All Tasks", "Pending", "Hold", "Completed", "Today's", "Yesterday"], 
    key="view_filter_main"
) 

# Dynamic Toggle Button for My Tasks Filter Rule
btn_label = "Show All Tasks" if st.session_state.my_tasks_only else " My Tasks"
if st.button(btn_label, key="my_tasks_toggle"):
    st.session_state.my_tasks_only = not st.session_state.my_tasks_only
    st.rerun()

if st.session_state.my_tasks_only:
    st.info(f"Viewing tasks by: {user['name']}")

c_date, c_search = st.columns([1, 1])
with c_date:
    date_range = st.date_input("📅 Filter by Date Range", value=[], help="Select Start and End date")


if not df_all.empty:
    df_all['date_dt'] = pd.to_datetime(df_all['assigned_at'], format="%d/%b/%Y %H:%M:%S", errors='coerce')
    filtered_df = df_all.copy()
    
    # Active Filtering Rule for Creator
    if st.session_state.my_tasks_only:
        filtered_df = filtered_df[filtered_df['assigner'] == user['name']]
    
    today_dt = datetime.now(IST).date()
    if view_filter == "Pending":
        filtered_df = filtered_df[filtered_df['status'] == "Pending"]
    elif view_filter == "Hold":
        filtered_df = filtered_df[filtered_df['status'] == "Hold"]
    elif view_filter == "Completed":
        filtered_df = filtered_df[filtered_df['status'] == "Completed"]
    elif view_filter == "Today's":
        filtered_df = filtered_df[filtered_df['date_dt'].dt.date == today_dt]
    elif view_filter == "Yesterday":
        yesterday = today_dt - pd.Timedelta(days=1)
        filtered_df = filtered_df[filtered_df['date_dt'].dt.date == yesterday]

    if len(date_range) == 2:
        start_date, end_date = date_range
        filtered_df = filtered_df[(filtered_df['date_dt'].dt.date >= start_date) & (filtered_df['date_dt'].dt.date <= end_date)]

    st.markdown(f"### 📊 Live Status Overview ({view_filter})")
    db_c1, db_c2, db_c3, db_c4, db_c5 = st.columns(5)
    
    with db_c1:
        st.metric("Total", len(filtered_df))
    with db_c2:
        p_count = len(filtered_df[filtered_df['status'] == "Pending"])
        st.metric("⏳ Pending", p_count)
    with db_c3:
        h_prio = len(filtered_df[(filtered_df['priority'] == "High") & (filtered_df['status'] != "Completed")])
        st.metric("🔥 High Priority", h_prio)
    with db_c4:
        h_count = len(filtered_df[filtered_df['status'] == "Hold"])
        st.metric("⏸️ Hold", h_count)
    with db_c5:
        c_count = len(filtered_df[filtered_df['status'] == "Completed"])
        st.metric("✅ Done", c_count)
    st.divider()

    s1, s2, s3 = st.columns([2, 1, 1])
    search = s1.text_input("🔍 Search (Finance, Task, or Staff)", key="search_bar").lower()
    if search:
        filtered_df = filtered_df[
            (filtered_df['finance'].str.contains(search, case=False, na=False)) | 
            (filtered_df['task'].str.contains(search, case=False, na=False)) |
            (filtered_df['lan'].astype(str).str.contains(search, case=False, na=False))
        ]

    prio_map = {"High": 0, "Medium": 1, "Normal": 2}
    filtered_df['prio_num'] = filtered_df['priority'].map(prio_map)

    if view_filter == "All Tasks":
        filtered_df = filtered_df.sort_values(by='date_dt', ascending=False)
    else:
        filtered_df = filtered_df.sort_values(by=['prio_num', 'date_dt'], ascending=[True, False])

    if s2.button("🔄 Refresh Data"): st.rerun()
    with s3:
        export_df = filtered_df.copy()
        
        def extract_cat(text):
            if isinstance(text, str) and text.startswith("[") and "]" in text:
                return text.split("]")[0].replace("[", "").strip()
            return "None"

        def clean_task(text):
            if isinstance(text, str) and text.startswith("[") and "]" in text:
                return text.split("]", 1)[1].strip()
            return text

        export_df['Category'] = export_df['task'].apply(extract_cat)
        export_df['task'] = export_df['task'].apply(clean_task)

        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='openpyxl') as wr:
            export_df.drop(columns=['date_dt', 'prio_num'], errors='ignore').to_excel(wr, index=True)
        
        st.download_button(
            label="📥 Excel", 
            data=buf.getvalue(), 
            file_name=f"Export_{view_filter}.xlsx", 
            use_container_width=True
        )

# --- 8. THE UNIFIED TASK CARDS ---
keys = list(filtered_df.index) if not filtered_df.empty else []

for tid in keys[:150]:
    task = tasks_dict[tid]
    
    t_status = task.get('status', 'Pending')
    t_prio = task.get('priority', 'Normal')
    
    # Define exact theme colors for the left strip indicator
    b_class = "border-pending"
    indicator_color = "#FFC107"  # Yellow for Pending
    
    if t_status == "Completed": 
        b_class = "border-completed"
        indicator_color = "#28A745"  # Green for Completed
    elif t_status == "Hold": 
        b_class = "border-hold"
        indicator_color = "#E83E8C"  # Magenta Pink for Hold
    elif t_prio == "High" and t_status == "Pending": 
        b_class = "border-high"
        indicator_color = "#DC3545"  # High Priority Red

    with st.container(border=True):
        components.html(f"""
            <script>
                var elements = window.parent.document.querySelectorAll('[data-testid="stVerticalBlockBorderWrapper"]');
                var lastElement = elements[elements.length - 1];
                lastElement.classList.add('{b_class}');
            </script>
        """, height=0)

        # --- COMPACT LAYOUT: Combined title, info, and status row to eliminate spacing gaps ---
        c_main, c_side = st.columns([2.2, 1.2])
        
        with c_main:
            st.markdown(
                f"""
                <div style="border-left: 8px solid {indicator_color}; padding-left: 12px; margin-bottom: 0px;">
                    <h2 style="margin: 0 0 2px 0; padding: 0; line-height: 1.1;">{task.get('finance')}</h2>
                    <span style="font-size: 16px; color: #4A4A4A;"><b>LAN:</b> <code>{task.get('lan', 'N/A')}</code></span>
                </div>
                """, 
                unsafe_allow_html=True
            )
            
        with c_side:
            # Inline HTML styling removes native block spacing stack limits entirely
            st.markdown(
                f"""
                <div style="text-align: right; font-size: 15px; line-height: 1.3; color: #1A1A1A; margin-top: 2px;">
                    <b>Status:</b> <span style="text-transform: uppercase; font-weight: bold; color: {indicator_color};">{t_status}</span><br>
                    <span style="color: #666; font-size: 13px;">Created: {task.get('assigned_at')}</span><br>
                    <span style="color: #666; font-size: 13px;">By: {task.get('assigner')}</span>
                </div>
                """,
                unsafe_allow_html=True
            )

        # Content Details Block
        st.markdown(f"**Task:** {task.get('task')}")
        
        if t_status == "Hold":
            st.error(f"⏸️ ON HOLD: {task.get('hold_by')} said: {task.get('comment', 'N/A')}")

        st.divider()

        if t_status == "Completed":
            st.success(f"✅ Closed by {task.get('completed_by')} | Type: {task.get('work_type')}")
            st.info(f"Final Note: {task.get('comment', 'N/A')}")
        else:
            c_note, c_type, c_hold, c_done = st.columns([1.5, 0.8, 0.7, 1])
            note = c_note.text_input("Comment", key=f"n_{tid}", label_visibility="collapsed", placeholder="Note...")
            w_type = c_type.selectbox("Type", ["Regular", "Major"], key=f"t_{tid}", label_visibility="collapsed")
            
            h_label = "⏸️ Hold" if t_status != "Hold" else "Unhold"
            if c_hold.button(h_label, key=f"h_{tid}", use_container_width=True):
                if t_status != "Hold":
                    payload = {"status": "Hold", "comment": note, "hold_by": user['name'], "hold_at": get_now_ist()}
                else:
                    payload = {"status": "Pending", "comment": note, "hold_by": None, "hold_at": None}
                requests.patch(f"{DB_BASE_URL}/tasks/{tid}.json", json=payload)
                st.rerun()
                
            if c_done.button("✅ Done", key=f"d_{tid}", use_container_width=True, type="primary"):
                requests.patch(f"{DB_BASE_URL}/tasks/{tid}.json", json={
                    "status": "Completed", "completed_by": user['name'], 
                    "work_type": w_type, "comment": note, "finished_at": get_now_ist()
                })
                st.rerun()

        if user['role'] == "ADMIN" or task.get('assigner') == user['name']:
            st.write("") 
            adm1, adm2 = st.columns([1, 1])
            if adm1.button("✏️ Modify Details", key=f"m_{tid}", use_container_width=True):
                edit_task_dialog(tid, task)
            
            if adm2.checkbox("🗑️ Delete", key=f"del_chk_{tid}"):
                if st.button("CONFIRM DELETE", key=f"del_btn_{tid}", use_container_width=True):
                    requests.delete(f"{DB_BASE_URL}/tasks/{tid}.json")
                    st.rerun()

    st.write("")