Here is the completely unified, clean codebase for **RAAS | Ultimate Ledger 5.0**.

I have combined the features from your previous app (the **Zoom Layout Scale slider**, **Applicant Name handling**, **Guidance Screenshot uploader**, **Optimistic fast-rendering state updates**, and **Streamlit Fragment scoping**) directly into the container-based DOM styling layout you shared.

All custom table elements have been swapped for your native Streamlit layouts, utilizing the custom document window selector injection script to draw your colorful indicators seamlessly.

```python
import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import pytz 
import io
import os
import time
import base64
import streamlit.components.v1 as components

# --- 1. CONFIGURATION ---
DB_BASE_URL = "https://office-task-ledger-default-rtdb.asia-southeast1.firebasedatabase.app"
TASKS_URL = f"{DB_BASE_URL}/tasks.json"
USERS_URL = f"{DB_BASE_URL}/users.json"
CATEGORIES_URL = f"{DB_BASE_URL}/categories.json"
FINANCE_MASTER_URL = f"{DB_BASE_URL}/finance_list.json"
IST = pytz.timezone('Asia/Kolkata') 

st.set_page_config(page_title="RAAS | Ultimate Ledger 5.0", layout="wide")

if "ui_scale" not in st.session_state: 
    st.session_state.ui_scale = 100

scale_mod = st.session_state.ui_scale / 100.0

# --- 2. THE ULTIMATE CSS (White Theme & High-Stability Grid) ---
st.markdown(f"""
    <style>
    /* Global Base Font System */
    html, body, [class*="st-"], .stMarkdown p, .stTextInput input, .stSelectbox div {{ 
        font-size: {int(22 * scale_mod)}px !important; 
        color: #1A1A1A !important;
    }} 
    
    /* Dedicated Label Styling */
    label [data-testid="stMarkdownContainer"] p {{
        font-size: {int(18 * scale_mod)}px !important;
        font-weight: 600 !important;
        color: #333333 !important;
    }}
    
    div[data-baseweb="select"] * {{
        color: #1A1A1A !important;
        opacity: 1.0 !important;
        font-weight: 500 !important;
        font-size: {int(22 * scale_mod)}px !important;
    }}
    
    ul[role="listbox"] li {{
        color: #1A1A1A !important;
        opacity: 1.0 !important;
        font-size: {int(22 * scale_mod)}px !important;
    }}
    
    .stApp {{ 
        color: #1A1A1A; 
        overscroll-behavior-y: contain !important; 
    }}

    /* Prevent Left & Right Layout Panes from stacking vertically */
    .stApp .stAppViewMain [data-testid="stMainBlockContainer"] > div > div > [data-testid="stHorizontalBlock"] {{
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        width: 100% !important;
        gap: 1.5rem !important;
    }}

    /* Allow standard inputs INSIDE forms and panels to adapt gracefully */
    [data-testid="stForm"] [data-testid="stHorizontalBlock"],
    .stExpander [data-testid="stHorizontalBlock"],
    [data-testid="stElementContainer"] [data-testid="stHorizontalBlock"] {{
        flex-wrap: wrap !important;
        align-items: flex-end !important;
        gap: 0.5rem !important;
    }}

    .stAppViewMain .block-container {{
        padding-top: 1.5rem !important;
        padding-bottom: 1.5rem !important;
        gap: 0.5rem !important; 
    }}
    
    /* Robust Dynamic Buttons */
    .stButton > button {{
        background-color: #F0F2F6 !important; 
        color: #1A1A1A !important;
        border: 1px solid #DDE1E7 !important;
        border-radius: 8px !important;
        padding: {int(10 * scale_mod)}px {int(20 * scale_mod)}px !important;
        font-weight: 600 !important;
        width: 100%;
        text-transform: uppercase;
        font-size: {int(16 * scale_mod)}px !important;
        min-height: 40px;
    }}

    .stButton > button:hover {{
        background-color: #E0E4EB !important;
        border-color: #B0B7C3 !important;
        color: #000000 !important;
    }}

    hr {{
        margin: 0.4rem 0 !important;
    }}

    /* Updated Card CSS Layout Gaps */
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        margin-bottom: 8px !important; 
    }}
    
    /* TARGETS THE NATIVE STREAMLIT BORDER CONTAINER WITH AN INTERNAL SECONDARY BOUNDARY */
    div[data-testid="stVerticalBlockBorderWrapper"].border-pending {{ 
        border: 2px solid #FFC107 !important; 
        border-left: 10px solid #FFC107 !important; 
        box-shadow: inset 0 0 0 4px #FFFFFF, inset 0 0 0 6px #FFC107 !important;
    }}
    div[data-testid="stVerticalBlockBorderWrapper"].border-completed {{ 
        border: 2px solid #28A745 !important; 
        border-left: 10px solid #28A745 !important; 
        box-shadow: inset 0 0 0 4px #FFFFFF, inset 0 0 0 6px #28A745 !important;
    }}
    div[data-testid="stVerticalBlockBorderWrapper"].border-hold {{ 
        border: 2px solid #E83E8C !important; 
        border-left: 10px solid #E83E8C !important; 
        box-shadow: inset 0 0 0 4px #FFFFFF, inset 0 0 0 6px #E83E8C !important;
    }}
    div[data-testid="stVerticalBlockBorderWrapper"].border-high {{ 
        border: 2px solid #DC3545 !important; 
        border-left: 10px solid #DC3545 !important; 
        box-shadow: inset 0 0 0 4px #FFFFFF, inset 0 0 0 6px #DC3545 !important;
    }}

    /* Tightens padding inside the cards and squishes row gaps */
    div[data-testid="stVerticalBlockBorderWrapper"] > div {{
        padding: 4px 12px !important;   
        gap: 0.3rem !important;            
    }}
    
    /* Strip layout margins on element containers to stop the expanded look */
    div[data-testid="element-container"] {{
        margin-bottom: 0px !important;
    }}

    div[data-testid="stMetric"] div {{ font-size: {int(20 * scale_mod)}px !important; }}
    div[data-testid="stMetricLabel"] > div {{ font-size: {int(13 * scale_mod)}px !important; }}
    </style>
""", unsafe_allow_html=True)

# --- 3. AUTH & DEVICE LOCK ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if "edit_mode" not in st.session_state: st.session_state.edit_mode = False
if "edit_tid" not in st.session_state: st.session_state.edit_tid = None
if "my_tasks_only" not in st.session_state: st.session_state.my_tasks_only = True
if "form_version" not in st.session_state: st.session_state.form_version = 0

def get_now_ist(): 
    return datetime.now(IST).strftime("%d/%b/%Y %H:%M:%S")

def get_device_id():
    try:
        return st.context.headers.get("User-Agent", "unknown_device")
    except:
        return "default_device"

if not st.session_state.authenticated:
    if "saved_user" in st.session_state and "saved_role" in st.session_state:
        st.session_state.user_data = {
            "name": st.session_state.saved_user,
            "role": st.session_state.saved_role
        }
        st.session_state.authenticated = True
        st.rerun()

if not st.session_state.authenticated:
    pad_left, center_col, pad_right = st.columns([1.5, 1.2, 1.5])
    
    with center_col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(script_dir, "your_logo_filename.jpg")
        
        if os.path.exists(logo_path):
            st.image(logo_path, width=180)
        else:
            st.caption(f"⚠️ Looking for logo in: {logo_path}")
            
        st.title("🔐 REAL APPLE CORRECTION LEDGER")
        name_in = st.text_input("Name", key="portal_username_input").upper().strip()
        pwd_in = st.text_input("Password", type="password", key="portal_password_input")
        
        components.html("""
            <script>
                const stored = localStorage.getItem("raas_user_session");
                if (stored && !window.parent.location.search.includes("auth_active")) {
                    const user = JSON.parse(stored);
                    const url = new URL(window.parent.location.href);
                    url.searchParams.set("login_name", user.name);
                    url.searchParams.set("login_role", user.role);
                    url.searchParams.set("auth_active", "1");
                    window.parent.location.href = url.toString();
                }
            </script>
        """, height=0)

        qp = st.query_params
        if "login_name" in qp and "login_role" in qp:
            st.session_state.user_data = {
                "name": qp["login_name"].upper(),
                "role": qp["login_role"].upper()
            }
            st.session_state.authenticated = True
            st.query_params.clear()
            st.rerun()
        
        if st.button("LOGIN", key="submit_portal_login_btn"):
            if not name_in or not pwd_in:
                st.warning("⚠️ Please fill in both Name and Password fields.")
            else:
                users_db = requests.get(USERS_URL).json() or {}
                is_admin = (pwd_in == "1586")
                dev_id = get_device_id()

                if name_in and (is_admin or pwd_in == "1234"):
                    user_entry = users_db.get(name_in, {})
                    approved = user_entry.get("approved_devices", [])
                    pending = user_entry.get("pending_devices", [])
                    
                    if not isinstance(approved, list): approved = []
                    if not isinstance(pending, list): pending = []

                    session_data = None
                    if is_admin:
                        session_data = {"name": name_in, "role": "ADMIN"}
                    elif name_in in users_db and dev_id in approved:
                        session_data = {"name": name_in, "role": "STAFF"}
                    else:
                        if name_in in users_db and dev_id not in approved and dev_id not in pending:
                            pending.append(dev_id)
                            requests.patch(f"{DB_BASE_URL}/users/{name_in}.json", json={"pending_devices": pending})
                            st.error("🚫 Device not approved. Contact Admin to authorize this device.")
                        elif name_in not in users_db:
                            st.error("🚫 Access Denied. No Slot.")

                    if session_data:
                        st.session_state.user_data = session_data
                        st.session_state.authenticated = True
                        
                        st.session_state.saved_user = session_data["name"]
                        st.session_state.saved_role = session_data["role"]
                        
                        components.html(f"""
                            <script>
                                localStorage.setItem("raas_user_session", '{{ "name": "{session_data['name']}", "role": "{session_data['role']}" }}');
                                const url = new URL(window.parent.location.href);
                                url.search = ""; 
                                window.parent.location.href = url.toString();
                            </script>
                        """, height=0)
                        time.sleep(0.4)
                        st.rerun()
    st.stop()

# --- 4. DATA FETCH (OPTIMIZED FOR SMOOTH REFRESH) ---
user = st.session_state.user_data

if "cached_tasks" not in st.session_state:
    st.session_state.cached_tasks = requests.get(TASKS_URL).json() or {}

tasks_dict = st.session_state.cached_tasks
master_fin_data = requests.get(FINANCE_MASTER_URL).json() or {}
master_cat_data = requests.get(CATEGORIES_URL).json() or {}
all_cats = sorted([c for c in master_cat_data.keys()])
all_fins = sorted([f.upper() for f in master_fin_data.keys()])

df_all = pd.DataFrame.from_dict(tasks_dict, orient='index')
search = st.session_state.get("raas_ultimate_search_deck", "").lower()

@st.dialog("Edit Task Details", width="large")
def edit_task_dialog(tid, task):
    ec1, ec_cat, ec_l, ec2 = st.columns([2, 2, 2, 2])
    
    current_f = task.get('finance', "")
    f_idx = all_fins.index(current_f) if current_f in all_fins else 0
    e_fin = ec1.selectbox("Update Finance", all_fins, index=f_idx, key=f"ef_dlg_{tid}")
    
    full_task_text = task.get('task', "")
    current_c = "---"
    clean_task_text = full_task_text
    
    if isinstance(full_task_text, str) and full_task_text.startswith("[") and "]" in full_task_text:
        try:
            parts = full_task_text.split("]", 1)
            current_c = parts[0].replace("[", "").strip()
            clean_task_text = parts[1].strip()
        except Exception:
            clean_task_text = full_task_text
    
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
        time.sleep(2)
        msg_placeholder.empty()
        st.rerun()

# --- 5. ADMIN SIDEBAR ---
if user['role'] == "ADMIN":
    with st.sidebar:
        st.header("⚙️ Control Panel")
        st.markdown("### 📊 Task Ledger Summary")
        
        if not df_all.empty:
            tot_p = len(df_all[df_all['status'] == "Pending"])
            tot_h = len(df_all[df_all['status'] == "Hold"])
            tot_c = len(df_all[df_all['status'] == "Completed"])
        else:
            tot_p, tot_h, tot_c = 0, 0, 0

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
                        btn_col1, btn_col2 = st.columns(2)
                        with btn_col1:
                            if st.button("✅ Approve", key=f"app_{u_name}_{d_id}", use_container_width=True):
                                if len(a_list) < 2:
                                    a_list.append(d_id)
                                    p_list.remove(d_id)
                                    requests.patch(f"{DB_BASE_URL}/users/{u_name}.json", 
                                                   json={"approved_devices": a_list, "pending_devices": p_list})
                                    st.success("Device Linked!")
                                    st.rerun()
                                else:
                                    st.error("User already has 2 devices!")
                                    
                        with btn_col2:
                            if st.button("❌ Reject", key=f"rej_{u_name}_{d_id}", use_container_width=True):
                                p_list.remove(d_id)
                                requests.patch(f"{DB_BASE_URL}/users/{u_name}.json", 
                                               json={"pending_devices": p_list})
                                st.warning("Request Rejected!")
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
                if st.button("Update Globally", use_container_width=True):
                    requests.patch(FINANCE_MASTER_URL, json={rename_f: True})
                    requests.delete(f"{DB_BASE_URL}/finance_list/{target_f}.json")
                    for tid, d in tasks_dict.items():
                        if d.get('finance') == target_f:
                            requests.patch(f"{DB_BASE_URL}/tasks/{tid}.json", json={"finance": rename_f})
                    st.rerun()

                if st.checkbox(f"Remove '{target_f}' from List?"):
                    if st.button("🗑️ DELETE FROM DROPDOWN", use_container_width=True):
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
                if st.button("Update Category Globally", key="btn_upd_cat", use_container_width=True):
                    requests.patch(CATEGORIES_URL, json={rename_c: True})
                    requests.delete(f"{DB_BASE_URL}/categories/{target_c}.json")
                    for tid, d in tasks_dict.items():
                        if f"[{target_c}]" in d.get('task', ''):
                            new_text = d.get('task').replace(f"[{target_c}]", f"[{rename_c}]")
                            requests.patch(f"{DB_BASE_URL}/tasks/{tid}.json", json={"task": new_text})
                    st.rerun()

                if st.checkbox(f"Remove '{target_c}' from List?", key="del_cat_chk"):
                    if st.button("🗑️ DELETE CATEGORY", key="btn_final_del_cat", use_container_width=True):
                        requests.delete(f"{DB_BASE_URL}/categories/{target_c}.json")
                        st.rerun()

# --- 6. SPLIT SCREEN THREE-SECTION LAYOUT ---
left_pane, right_pane = st.columns([1.3, 1.7], gap="medium")

# ==========================================
# LEFT PANE: SECTION 1 & SECTION 2
# ==========================================
with left_pane:
    logo_col, operator_box_col = st.columns([1.4, 1.3])
    
    with logo_col:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(script_dir, "your_logo_filename.jpg")
        if os.path.exists(logo_path):
            st.image(logo_path, use_container_width=True)
        else:
            st.caption(f"⚠️ Looking in: {logo_path}")
            
    with operator_box_col:
        st.markdown("<div style='margin-top: 25px;'></div>", unsafe_allow_html=True)
        with st.container(border=True):
            card_left, card_right = st.columns([1.6, 1.1])
            with card_left:
                st.markdown(f"""
                    <div style="margin: -6px 0 0 0; padding: 0;">
                        <span style="font-size: {int(18 * scale_mod)}px; color: #555555; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; display: block; margin-bottom: 2px;">Real Apple</span>
                        <h3 style="margin: 0; padding: 0; color: #1A1A1A; font-weight: 700; font-size: {int(24 * scale_mod)}px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;"> {user['name']}</h3>
                    </div>
                """, unsafe_allow_html=True)
            with card_right:
                st.markdown("<div style='margin-top: 2px;'></div>", unsafe_allow_html=True)
                if st.button("🔒 LOGOUT", key="app_logout_btn", use_container_width=True):
                    st.session_state.authenticated = False
                    if "user_data" in st.session_state: del st.session_state.user_data
                    if "saved_user" in st.session_state: del st.session_state.saved_user
                    if "saved_role" in st.session_state: del st.session_state.saved_role
                    
                    components.html("""
                        <script>
                            localStorage.removeItem("raas_user_session");
                            const url = new URL(window.parent.location.href);
                            url.search = "";
                            window.parent.location.href = url.toString();
                        </script>
                    """, height=0)
                    time.sleep(0.4)
                    st.rerun()
        
    @st.dialog("✨ Task Registered Successfully", width="small")
    def show_success_popup(lan, user_name):
        st.write("") 
        st.markdown(f"""
        <div style="text-align: center;">
            <h1 style="font-size: 50px; margin: 0;">🎉</h1>
            <p style="font-weight: bold; margin-top: 10px; color: #28A745;">📢 New Task Added by {user_name}!</p>
            <p style="color: #4A4A4A; font-size: 16px;">Task for LAN <b>{lan}</b> has been successfully added to the ledger.</p>
        </div>
        """, unsafe_allow_html=True)
        st.write("")
        if st.button("👍 OK", use_container_width=True, type="primary"):
            for target_key in ["main_finance_picker", "main_cat_picker", "main_applicant_input", "main_lan_input", "main_prio_slider", "main_task_details", "main_screenshot_uploader"]:
                if target_key in st.session_state:
                    del st.session_state[target_key]
            st.session_state.show_submit_popup = False
            st.rerun()

    if st.session_state.get("show_submit_popup"):
        show_success_popup(st.session_state.get("last_sub_lan", ""), user['name'])

    st.subheader("📝 Create New Task")
    with st.expander("Ledger Entry Form", expanded=True):
        with st.container(key=f"form_container_v_{st.session_state.form_version}"):
            c1, c2, c_lan, c3 = st.columns([1.5, 1, 1, 1])
            with c1:
                f_sel = st.selectbox("Finance", ["--- SELECT ---"] + all_fins, key=f"main_fin_{st.session_state.form_version}")
                fin_active = f_sel
            with c2:
                cat = st.selectbox("Category", ["---"] + all_cats, key=f"main_cat_{st.session_state.form_version}")
            with c_lan:
                applicant_name = st.text_input("Applicant Name", placeholder="Required", key=f"main_app_{st.session_state.form_version}")
            with c3:
                lan_no = st.text_input("LAN No.", placeholder="Required", key=f"main_lan_{st.session_state.form_version}").strip()
                
            prio = st.select_slider("Priority", ["Normal", "Medium", "High"], key=f"main_prio_{st.session_state.form_version}")
            dtl_main = st.text_area("Task Details", key=f"main_dtl_{st.session_state.form_version}")
            uploaded_file = st.file_uploader("📸 Attach Guidance Screenshot", type=["jpg", "jpeg", "png"], key=f"main_img_{st.session_state.form_version}")
            
            img_b64 = ""
            if uploaded_file is not None:
                img_b64 = base64.b64encode(uploaded_file.read()).decode("utf-8")
            
            if st.button("SUBMIT", use_container_width=True, type="primary", key=f"main_sub_btn_{st.session_state.form_version}"):
                if fin_active != "--- SELECT ---" and lan_no and dtl_main:
                    payload = {
                        "finance": fin_active, 
                        "lan": lan_no,
                        "applicant_name": applicant_name.strip(),
                        "task": f"[{cat}] {dtl_main}" if cat != "---" else dtl_main, 
                        "priority": prio, 
                        "assigner": user['name'], 
                        "status": "Pending", 
                        "assigned_at": get_now_ist(),
                        "screenshot": img_b64
                    }
                    
                    res = requests.post(TASKS_URL, json=payload)
                    requests.patch(FINANCE_MASTER_URL, json={fin_active: True})
                    st.session_state.cached_tasks = requests.get(TASKS_URL).json() or {}
                    
                    st.session_state.last_sub_lan = lan_no
                    st.session_state.show_submit_popup = True

                    st.session_state.form_version += 1
                    st.rerun()
                elif not lan_no:
                    st.error("🛑 LAN No. is mandatory!")
                else:
                    st.warning("⚠️ Please fill in Finance and Task Details.")

    st.markdown("<br>", unsafe_allow_html=True)
    st.divider()

    # --- SECTION 2: OPERATIONS CONTROL PANEL ---
    st.subheader("🔍 Operations Control Panel")
    
    vf_col, toggle_col = st.columns([2, 1])
    with vf_col:
        view_filter = st.selectbox("📂 View Filter", ["Today's", "All Tasks", "Pending", "Hold", "Completed", "Yesterday"], key="view_filter_main", label_visibility="collapsed")
    with toggle_col:
        btn_label = "Show All" if st.session_state.my_tasks_only else "My Tasks"
        if st.button(btn_label, key="my_tasks_toggle", use_container_width=True):
            st.session_state.my_tasks_only = not st.session_state.my_tasks_only
            st.rerun()

    if st.session_state.my_tasks_only:
        st.info(f"Viewing tasks by: {user['name']}")

    date_range = st.date_input("📅 Filter by Date Range", value=[], help="Select Start and End date")

    if not df_all.empty:
        df_all['date_dt'] = pd.to_datetime(df_all['assigned_at'].str.strip(), format="%d/%b/%Y %H:%M:%S", errors='coerce')
        df_all['task_date'] = df_all['date_dt'].dt.date
        filtered_df = df_all.copy()
        
        if st.session_state.my_tasks_only:
            filtered_df = filtered_df[filtered_df['assigner'] == user['name']]
        
        today_dt = datetime.now(IST).date()
        if view_filter == "Pending": filtered_df = filtered_df[filtered_df['status'] == "Pending"]
        elif view_filter == "Hold": filtered_df = filtered_df[filtered_df['status'] == "Hold"]
        elif view_filter == "Completed": filtered_df = filtered_df[filtered_df['status'] == "Completed"]
        elif view_filter == "Today's": filtered_df = filtered_df[filtered_df['task_date'] == today_dt]
        elif view_filter == "Yesterday":
            filtered_df = filtered_df[filtered_df['task_date'] == (today_dt - pd.Timedelta(days=1))]
        if len(date_range) == 2:
            filtered_df = filtered_df[(filtered_df['date_dt'].dt.date >= date_range[0]) & (filtered_df['date_dt'].dt.date <= date_range[1])]

        st.markdown(f"**Live Status Overview ({view_filter})**")
        
        m_total = len(filtered_df)
        m_pending = len(filtered_df[filtered_df['status'] == "Pending"])
        m_high = len(filtered_df[(filtered_df['priority'] == "High") & (filtered_df['status'] != "Completed")])
        m_hold = len(filtered_df[filtered_df['status'] == "Hold"])
        m_done = len(filtered_df[filtered_df['status'] == "Completed"])

        m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
        m_col1.metric("Total", m_total)
        m_col2.metric("⏳ Pending", m_pending)
        m_col3.metric("🔥 High", m_high)
        m_col4.metric("⏸️ Hold", m_hold)
        m_col5.metric("✅ Done", m_done)
        
        st.divider()

        search = st.text_input("🔍 Search (Finance, Task, or LAN)", key="search_bar", placeholder="Type to filter...").lower()
        if search:
            filtered_df = filtered_df[
                (filtered_df['finance'].str.contains(search, case=False, na=False)) | 
                (filtered_df['task'].str.contains(search, case=False, na=False)) |
                (filtered_df['lan'].astype(str).str.contains(search, case=False, na=False))
            ]

        filtered_df['prio_num'] = filtered_df['priority'].map({"High": 0, "Medium": 1, "Normal": 2})
        if view_filter == "All Tasks":
            filtered_df = filtered_df.sort_values(by='date_dt', ascending=False)
        else:
            filtered_df = filtered_df.sort_values(by=['prio_num', 'date_dt'], ascending=[True, False])

        act_col1, act_col2 = st.columns(2)
        with act_col1:
            if st.button("🔄 Refresh Data", key="left_ops_refresh", use_container_width=True): 
                st.rerun()
        with act_col2:
            export_df = filtered_df.copy()
            export_df['Category'] = export_df['task'].apply(lambda t: t.split("]")[0].replace("[", "").strip() if isinstance(t, str) and t.startswith("[") else "None")
            export_df['task'] = export_df['task'].apply(lambda t: t.split("]", 1)[1].strip() if isinstance(t, str) and t.startswith("[") else t)

            required_cols = ['assigned_at', 'assigner', 'finance', 'applicant_name', 'lan', 'Category', 'task', 'priority', 'work_type', 'completed_by', 'finished_at', 'status', 'hold_at', 'hold_by', 'comment']
            for col in required_cols:
                if col not in export_df.columns: export_df[col] = ""

            export_df['rt Done Comment'] = export_df.apply(lambda r: r['comment'] if r['status'] == 'Completed' else "", axis=1)
            export_df['Hold Reason'] = export_df.apply(lambda r: r['comment'] if r['status'] == 'Hold' else "", axis=1)

            final_cols = ['assigned_at', 'assigner', 'finance', 'applicant_name', 'lan', 'Category', 'task', 'priority', 'work_type', 'rt Done Comment', 'completed_by', 'finished_at', 'status', 'hold_at', 'hold_by', 'Hold Reason']
            export_df = export_df[final_cols]

            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='openpyxl') as wr:
                export_df.to_excel(wr, index=False)
            
            st.download_button(label="📥 Excel Export", data=buf.getvalue(), file_name=f"Export_{view_filter}.xlsx", use_container_width=True)

        st.write("") 
        new_scale = st.slider("🔍 Zoom Layout Scale (%)", 10, 150, value=st.session_state.ui_scale, step=5, key="global_zoom_slider")
        if new_scale != st.session_state.ui_scale:
            st.session_state.ui_scale = new_scale
            st.rerun()
    else:
        filtered_df = pd.DataFrame()

# ==========================================
# RIGHT PANE: SECTION 3 (TASK CARDS)
# ==========================================
with right_pane:
    @st.fragment
    def render_task_deck():
        st.subheader("📋 All Tasks")
        
        keys = list(filtered_df.index) if not filtered_df.empty else []

        if not keys:
            st.info("No matching tasks found for the current configuration details.")
        
        for tid in keys[:150]:
            tsk = tasks_dict[tid]
            stat = tsk.get('status', 'Pending')
            prio_val = tsk.get('priority', 'Normal')
            
            b_class = "border-pending"
            col_ind = "#FFC107"
            
            if stat == "Completed": 
                b_class = "border-completed"
                col_ind = "#28A745"
            elif stat == "Hold": 
                b_class = "border-hold"
                col_ind = "#E83E8C"
            elif prio_val == "High" and stat == "Pending": 
                b_class = "border-high"
                col_ind = "#DC3545"

            with st.container(border=True):
                components.html(f"""
                    <script>
                        var elements = window.parent.document.querySelectorAll('[data-testid="stVerticalBlockBorderWrapper"]');
                        var lastElement = elements[elements.length - 1];
                        lastElement.classList.add('{b_class}');
                    </script>
                """, height=0)

                c_main, c_side = st.columns([2.0, 1.4])
                
                with c_main:
                    app_name = tsk.get('applicant_name', '').strip()
                    app_display = f"<b>Applicant:</b> {app_name} | " if app_name else ""
                    st.markdown(f"""
                        <div style="border-left: 8px solid {col_ind}; padding-left: 12px; margin-bottom: 0px;">
                            <h2 style="margin: 0 0 2px 0; padding: 0; line-height: 1.1; font-size:{int(24 * scale_mod)}px;">{tsk.get('finance')}</h2>
                            <span style="font-size: {int(16 * scale_mod)}px; color: #4A4A4A;">{app_display}<b>LAN:</b> <code>{tsk.get('lan', 'N/A')}</code></span>
                        </div>
                    """, unsafe_allow_html=True)
                    
                with c_side:
                    st.markdown(f"""
                        <div style="text-align: right; font-size: {int(14 * scale_mod)}px; line-height: 1.3; color: #1A1A1A; margin-top: 2px;">
                            <b>Status:</b> <span style="text-transform: uppercase; font-weight: bold; color: {col_ind};">{stat}</span><br>
                            <span style="color: #666; font-size: {int(12 * scale_mod)}px;">Created: {tsk.get('assigned_at')}</span><br>
                            <span style="color: #666; font-size: {int(12 * scale_mod)}px;">By: {tsk.get('assigner')}</span>
                        </div>
                    """, unsafe_allow_html=True)

                raw_task_text = str(tsk.get('task', ''))
                first_line = raw_task_text.split('\n')[0]
                if len(first_line) > 90:
                    first_line = first_line[:87] + "..."
                    
                st.markdown(f"**Task Preview:** {first_line}")
                
                with st.expander("📄 View Full Details & Actions", expanded=False):
                    st.markdown(f"**Full Task Description:**\n{raw_task_text}")
                    
                    if tsk.get("screenshot") and str(tsk.get("screenshot")).strip() != "":
                        try:
                            st.image(f"data:image/png;base64,{tsk.get('screenshot')}", use_container_width=True)
                        except:
                            st.caption("⚠️ Failed to display attachment image.")
                    
                    if stat == "Hold":
                        st.error(f"⏸️ ON HOLD: {tsk.get('hold_by')} said: {tsk.get('comment', 'N/A')}")

                    st.divider()

                    if stat == "Completed":
                        st.success(f"✅ Closed by {tsk.get('completed_by')} | Type: {tsk.get('work_type')}")
                        st.info(f"Final Note: {tsk.get('comment', 'N/A')}")
                    else:
                        c_note, c_type, c_hold, c_done = st.columns([1.3, 0.7, 0.8, 0.8])
                        note = c_note.text_input("Comment", key=f"n_{tid}", label_visibility="collapsed", placeholder="Note...")
                        w_type = c_type.selectbox("Type", ["Regular", "Major"], key=f"t_{tid}", label_visibility="collapsed")
                        
                        h_label = "⏸️ Hold" if stat != "Hold" else "Unhold"
                        if c_hold.button(h_label, key=f"h_{tid}", use_container_width=True):
                            if stat != "Hold" and not note.strip():
                                st.error("🛑 Hold note is required.")
                            else:
                                if stat != "Hold":
                                    p_load = {"status": "Hold", "comment": note, "hold_by": user['name'], "hold_at": get_now_ist()}
                                else:
                                    p_load = {"status": "Pending", "comment": note, "hold_by": "", "hold_at": ""}
                                
                                st.session_state.cached_tasks[tid].update(p_load)
                                try:
                                    requests.patch(f"{DB_BASE_URL}/tasks/{tid}.json", json=p_load)
                                except:
                                    pass
                                st.rerun(scope="fragment")
                                
                        if c_done.button("✅ Done", key=f"d_{tid}", use_container_width=True, type="primary"):
                            if not note.strip():
                                st.error("🛑 Closing note is required.")
                            else:
                                p_load = {
                                    "status": "Completed", "completed_by": user['name'], 
                                    "work_type": w_type, "comment": note, "finished_at": get_now_ist()
                                }
                                st.session_state.cached_tasks[tid].update(p_load)
                                requests.patch(f"{DB_BASE_URL}/tasks/{tid}.json", json=p_load)
                                st.rerun(scope="fragment")

                    if user['role'] == "ADMIN" or tsk.get('assigner') == user['name']:
                        st.write("") 
                        adm1, adm2 = st.columns([1, 1])
                        if adm1.button("✏️ Modify Details", key=f"m_{tid}", use_container_width=True):
                            edit_task_dialog(tid, tsk)
                        
                        with adm2:
                            if st.checkbox("🗑️ Delete", key=f"del_chk_{tid}"):
                                if st.button("CONFIRM DELETE", key=f"del_btn_{tid}", use_container_width=True):
                                    requests.delete(f"{DB_BASE_URL}/tasks/{tid}.json")
                                    st.rerun(scope="fragment")
            st.write("")

    render_task_deck()

```