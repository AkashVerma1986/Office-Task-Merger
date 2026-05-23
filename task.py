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

# --- 2. THE ULTIMATE CSS (White Theme & Dynamic Tight Spacing Layout) ---
st.markdown(f"""
    <style>
    html, body, [class*="st-"], .stMarkdown p, .stTextInput input, .stSelectbox div {{ 
        font-size: {int(22 * scale_mod)}px !important; 
        color: #1A1A1A !important;
    }} 
    
    div[data-baseweb="select"] * {{
        color: #1A1A1A !important;
        opacity: 1.0 !important;
        font-weight: 500 !important;
    }}
    
    ul[role="listbox"] li {{
        color: #1A1A1A !important;
        opacity: 1.0 !important;
    }}
    
    .stApp {{ 
        color: #1A1A1A; 
        overscroll-behavior-y: contain !important; 
    }}

    .stAppViewMain .block-container {{
        padding-top: 1.5rem !important;
        padding-bottom: 1.5rem !important;
        gap: 0.5rem !important; 
    }}
    
    .stButton > button {{
        background-color: #F0F2F6 !important; 
        color: #1A1A1A !important;
        border: 1px solid #DDE1E7 !important;
        border-radius: 8px !important;
        padding: {int(10 * scale_mod)}px {int(20 * scale_mod)}px !important;
        font-weight: 600 !important;
        width: 100%;
        text-transform: uppercase;
        font-size: {int(18 * scale_mod)}px !important;
    }}

    .stButton > button:hover {{
        background-color: #E0E4EB !important;
        border-color: #B0B7C3 !important;
        color: #000000 !important;
    }}

    hr {{
        margin: 0.4rem 0 !important;
    }}

    .gallocation-bar {{ width: 8px; flex-shrink: 0; }}
    .card-body {{ 
        flex-grow: 1; 
        display: block; 
        width: 100%; 
        padding-bottom: 10px;
    }}
    .card-text {{ padding: 15px; border-bottom: 1px solid #F0F0F0; color: #1A1A1A; }}
    
    .status-pending {{ background-color: #FFC107 !important; }}
    .status-completed {{ background-color: #28A745 !important; }}
    .status-hold {{ background-color: #E83E8C !important; }}
    .status-high {{ background-color: #DC3545 !important; }}

    .completion-box {{ 
        background-color: #E9F7EF; 
        border: 1px solid #28A745; 
        padding: 10px; 
        border-radius: 5px; 
        color: #155724; 
        margin: 10px;
    }}

    div[data-testid="stMetric"] div {{ font-size: {int(20 * scale_mod)}px !important; }}
    div[data-testid="stMetricLabel"] > div {{ font-size: {int(14 * scale_mod)}px !important; }}
    </style>
""", unsafe_allow_html=True)

# --- 3. AUTH & DEVICE LOCK ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if "edit_mode" not in st.session_state: st.session_state.edit_mode = False
if "edit_tid" not in st.session_state: st.session_state.edit_tid = None
if "my_tasks_only" not in st.session_state: st.session_state.my_tasks_only = True

# Persistent filters setup
if "shared_filter_value" not in st.session_state:
    st.session_state.shared_filter_value = "Today's"

def sync_filters(source_key):
    st.session_state.shared_filter_value = st.session_state[source_key]

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
        if "login_name" in qp heart and "login_role" in qp:
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

# --- 4. DATA FETCH ---
user = st.session_state.user_data
tasks_dict = requests.get(TASKS_URL).json() or {}
master_fin_data = requests.get(FINANCE_MASTER_URL).json() or {}
master_cat_data = requests.get(CATEGORIES_URL).json() or {}
all_cats = sorted([c for c in master_cat_data.keys()])
all_fins = sorted([f.upper() for f in master_fin_data.keys()])

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
        
    st.write("") 
    search = st.text_input("🔍 Search (Finance, Task, or LAN)", key="search_bar", placeholder="Type to filter...").lower()
    st.divider()
    
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
            st.session_state["main_finance_picker"] = "--- SELECT ---"
            st.session_state["main_cat_picker"] = "---"
            st.session_state["main_applicant_input"] = ""
            st.session_state["main_lan_input"] = ""
            st.session_state["main_task_details"] = ""
            st.session_state["main_prio_slider"] = "Normal"
            if "main_screenshot_uploader" in st.session_state:
                del st.session_state["main_screenshot_uploader"]
            st.session_state.show_submit_popup = False
            st.rerun()

    if st.session_state.get("show_submit_popup"):
        show_success_popup(st.session_state.get("last_sub_lan", ""), user['name'])

    st.subheader("📝 Create New Task")
    with st.expander("Ledger Entry Form", expanded=True):
        row1_col1, row1_col2 = st.columns(2)
        with row1_col1:
            f_sel = st.selectbox("Finance", ["--- SELECT ---"] + all_fins, key="main_finance_picker")
            fin_active = f_sel
        with row1_col2:
            cat = st.selectbox("Category", ["---"] + all_cats, key="main_cat_picker")
            
        row2_col1, row2_col2 = st.columns(2)
        with row2_col1:
            applicant_name = st.text_input("Applicant Name", placeholder="Required", key="main_applicant_input")
        with row2_col2:
            lan_no = st.text_input("LAN No.", placeholder="Required", key="main_lan_input").strip()
            
        prio = st.select_slider("Priority", ["Normal", "Medium", "High"], key="main_prio_slider")
            
        dtl_main = st.text_area("Task Details", key="main_task_details")
        
        if "uploader_version" not in st.session_state:
            st.session_state.uploader_version = 0
            
        uploaded_file = st.file_uploader(
            "📸 Attach Guidance Screenshot", 
            type=["jpg", "jpeg", "png"], 
            key=f"main_screenshot_uploader_{st.session_state.uploader_version}"
        )
        
        img_b64 = ""
        if uploaded_file is not None:
            img_b64 = base64.b64encode(uploaded_file.read()).decode("utf-8")
        
        paste_component_html = """
        <div id="drop-zone" style="border: 2px dashed #B0B7C3; border-radius: 8px; padding: 18px; text-align: center; background: #F8F9FA; cursor: pointer; color: #4A4A4A; font-family: sans-serif; font-size: 14px;">
            <div id="prompt-msg">Click here & press <b>Ctrl + V</b> to Paste, or drag & drop image file</div>
            <img id="preview" style="max-height: 100px; display: none; margin: 8px auto 0 auto; border-radius: 4px;" />
        </div>
        <script>
            const zone = document.getElementById('drop-zone');
            const preview = document.getElementById('preview');
            const msg = document.getElementById('prompt-msg');
            function sendToStreamlit(b64Str) {
                window.parent.postMessage({type: 'streamlit:set_component_value', value: b64Str}, '*');
            }
            window.addEventListener('paste', (e) => {
                const items = (e.clipboardData || e.originalEvent.clipboardData).items;
                for (let i = 0; i < items.length; i++) {
                    if (items[i].type.indexOf('image') !== -1) {
                        const file = items[i].getAsFile();
                        const reader = new FileReader();
                        reader.onload = (event) => {
                            const rawB64 = event.target.result.split(',')[1];
                            preview.src = event.target.result;
                            preview.style.display = 'block';
                            msg.innerHTML = "✅ Image pasted successfully!";
                            sendToStreamlit(rawB64);
                        };
                        reader.readAsDataURL(file);
                    }
                }
            });
        </script>
        """
        if not isinstance(img_b64, str):
            img_b64 = ""
        
        if st.button("SUBMIT", use_container_width=True, type="primary"):
            if fin_active != "--- SELECT ---" and lan_no and dtl_main:
                payload = {
                    "finance": fin_active, 
                    "lan": lan_no,
                    "applicant_name": st.session_state.get("main_applicant_input", "").strip(),
                    "task": f"[{cat}] {dtl_main}" if cat != "---" else dtl_main, 
                    "priority": prio, 
                    "assigner": user['name'], 
                    "status": "Pending", 
                    "assigned_at": get_now_ist(),
                    "screenshot": img_b64
                }
                
                requests.post(TASKS_URL, json=payload)
                requests.patch(FINANCE_MASTER_URL, json={fin_active: True})
                
                st.session_state.last_sub_lan = lan_no
                st.session_state.show_submit_popup = True
                
                for k in ["main_applicant_input", "main_lan_input", "main_task_details", "main_screenshot_uploader", "paste_img_b64"]:
                    if k in st.session_state:
                        del st.session_state[k]
                st.rerun()
            elif not lan_no:
                st.error("🛑 LAN No. is mandatory!")
            else:
                st.warning("⚠️ Please fill in Finance and Task Details.")
                
    st.markdown("<br>", unsafe_allow_html=True)
    st.divider()

    # --- SECTION 2: OPERATIONS CONTROL PANEL ---
    st.subheader("🔍 Operations Control Panel")
    filter_options_left = ["Today's", "All Tasks", "Pending", "Hold", "Completed", "Yesterday"]
    
    view_filter = st.selectbox(
        "📂 View Filter", 
        filter_options_left, 
        index=filter_options_left.index(st.session_state.shared_filter_value),
        key="left_filter_unique_key",
        on_change=sync_filters,
        args=("left_filter_unique_key",)
    )

    if st.session_state.my_tasks_only:
        st.info(f"Viewing tasks by: {user['name']}")

    date_range = st.date_input("📅 Filter by Date Range", value=[], help="Select Start and End date")

    if tasks_dict:
        df_calc = pd.DataFrame.from_dict(tasks_dict, orient='index')
        df_calc['date_dt'] = pd.to_datetime(df_calc['assigned_at'].str.strip(), format="%d/%b/%Y %H:%M:%S", errors='coerce')
        filtered_df = df_calc.copy()
        
        if st.session_state.my_tasks_only:
            filtered_df = filtered_df[filtered_df['assigner'] == user['name']]
        
        today_dt = datetime.now(IST).date()
        if view_filter == "Pending": filtered_df = filtered_df[filtered_df['status'] == "Pending"]
        elif view_filter == "Hold": filtered_df = filtered_df[filtered_df['status'] == "Hold"]
        elif view_filter == "Completed": filtered_df = filtered_df[filtered_df['status'] == "Completed"]
        elif view_filter == "Today's": filtered_df = filtered_df[filtered_df['date_dt'].dt.date == today_dt]
        elif view_filter == "Yesterday":
            filtered_df = filtered_df[filtered_df['date_dt'].dt.date == (today_dt - pd.Timedelta(days=1))]

        if len(date_range) == 2:
            filtered_df = filtered_df[(filtered_df['date_dt'].dt.date >= date_range[0]) & (filtered_df['date_dt'].dt.date <= date_range[1])]

        if search:
            filtered_df = filtered_df[
                (filtered_df['finance'].str.contains(search, case=False, na=False)) | 
                (filtered_df['task'].str.contains(search, case=False, na=False)) |
                (filtered_df['lan'].astype(str).str.contains(search, case=False, na=False))
            ]

        st.markdown(f"**Live Status Overview ({view_filter})**")
        m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
        m_col1.metric("Total", len(filtered_df))
        m_col2.metric("⏳ Pending", len(filtered_df[filtered_df['status'] == "Pending"]))
        m_col3.metric("🔥 High", len(filtered_df[(filtered_df['priority'] == "High") & (filtered_df['status'] != "Completed")]))
        m_col4.metric("⏸️ Hold", len(filtered_df[filtered_df['status'] == "Hold"]))
        m_col5.metric("✅ Done", len(filtered_df[filtered_df['status'] == "Completed"]))
        
        st.divider()

        filtered_df['prio_num'] = filtered_df['priority'].map({"High": 0, "Medium": 1, "Normal": 2})
        filtered_df = filtered_df.sort_values(by='date_dt' if view_filter == "All Tasks" else ['prio_num', 'date_dt'], ascending=[False] if view_filter == "All Tasks" else [True, False])

        act_col1, act_col2 = st.columns(2)
        with act_col1:
            if st.button("🔄 Refresh Data", key="left_ops_refresh", use_container_width=True):
                st.rerun(scope="fragment")
        with act_col2:
            export_df = filtered_df.copy()
            export_df['Category'] = export_df['task'].apply(lambda t: t.split("]")[0].replace("[", "").strip() if isinstance(t, str) and t.startswith("[") else "None")
            export_df['task'] = export_df['task'].apply(lambda t: t.split("]", 1)[1].strip() if isinstance(t, str) and t.startswith("[") else t)

            required_cols = ['assigned_at', 'assigner', 'finance', 'lan', 'Category', 'task', 'priority', 'work_type', 'completed_by', 'finished_at', 'status', 'hold_at', 'hold_by', 'comment']
            for col in required_cols:
                if col not in export_df.columns: export_df[col] = ""

            export_df['rt Done Comment'] = export_df.apply(lambda r: r['comment'] if r['status'] == 'Completed' else "", axis=1)
            export_df['Hold Reason'] = export_df.apply(lambda r: r['comment'] if r['status'] == 'Hold' else "", axis=1)

            final_cols = ['assigned_at', 'assigner', 'finance', 'lan', 'Category', 'task', 'priority', 'work_type', 'rt Done Comment', 'completed_by', 'finished_at', 'status', 'hold_at', 'hold_by', 'Hold Reason']
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

# ==========================================
# RIGHT PANE: SECTION 3 (TASK CARDS)
# ==========================================
with right_pane:
    @st.fragment
    def render_task_deck():
        hdr_title_col, hdr_filter_col, hdr_btn1, hdr_btn2 = st.columns([1.1, 1.2, 0.9, 0.8])
        hdr_title_col.subheader("📋 All Tasks")
        
        filter_options_right = ["Today's", "All Tasks", "Pending", "Hold", "Completed", "Yesterday"]
        
        view_filter_right = hdr_filter_col.selectbox(
            "📂 View Filter Right", 
            filter_options_right, 
            index=filter_options_right.index(st.session_state.shared_filter_value),
            key="right_filter_unique_key", 
            label_visibility="collapsed",
            on_change=sync_filters,
            args=("right_filter_unique_key",)
        )
            
        if hdr_btn1.button("REFRESH", key="right_pane_refresh", use_container_width=True):
            st.rerun(scope="fragment")
                
        btn_label = "Show All" if st.session_state.my_tasks_only else "My Tasks"
        if hdr_btn2.button(btn_label, key="right_pane_my_tasks_toggle", use_container_width=True):
            st.session_state.my_tasks_only = not st.session_state.my_tasks_only
            st.rerun(scope="fragment")
                
        st.write("") 
        
        live_tasks = requests.get(TASKS_URL).json() or {}
        live_df = pd.DataFrame.from_dict(live_tasks, orient='index')
        
        if not live_df.empty:
            live_df['date_dt'] = pd.to_datetime(live_df['assigned_at'].str.strip(), format="%d/%b/%Y %H:%M:%S", errors='coerce')
            f_df = live_df.copy()
            
            if st.session_state.my_tasks_only:
                f_df = f_df[f_df['assigner'] == user['name']]
            
            t_dt = datetime.now(IST).date()
            if view_filter_right == "Pending": f_df = f_df[f_df['status'] == "Pending"]
            elif view_filter_right == "Hold": f_df = f_df[f_df['status'] == "Hold"]
            elif view_filter_right == "Completed": f_df = f_df[f_df['status'] == "Completed"]
            elif view_filter_right == "Today's": f_df = f_df[f_df['date_dt'].dt.date == t_dt]
            elif view_filter_right == "Yesterday": f_df = f_df[f_df['date_dt'].dt.date == (t_dt - pd.Timedelta(days=1))]

            f_df['prio_num'] = f_df['priority'].map({"High": 0, "Medium": 1, "Normal": 2})
            f_df = f_df.sort_values(by='date_dt' if view_filter_right == "All Tasks" else ['prio_num', 'date_dt'], ascending=[False] if view_filter_right == "All Tasks" else [True, False])
            keys = list(f_df.index)
        else:
            keys = []

        if not keys:
            st.info("No matching tasks found.")
        
        for tid in keys[:150]:
            tsk = live_tasks[tid]
            stat = tsk.get('status', 'Pending')
            prio_val = tsk.get('priority', 'Normal')
            
            col_ind = "#FFC107"
            if stat == "Completed": col_ind = "#28A745"
            elif stat == "Hold": col_ind = "#E83E8C"
            elif prio_val == "High" and stat == "Pending": col_ind = "#DC3545"

            with st.container(border=True):
                app_name = tsk.get('applicant_name', '').strip()
                app_string = app_name if app_name else 'N/A'
                lan_string = tsk.get('lan', 'N/A')
                
                combined_details_html = f"""
                <div style="display: flex; flex-wrap: wrap; gap: 15px; align-items: center; margin-top: 4px; margin-bottom: 2px;">
                    <span style="font-size: {int(17 * scale_mod)}px; color: #1A1A1A;"><b>Applicant:</b> {app_string}</span>
                    <span style="font-size: {int(17 * scale_mod)}px; color: #4A4A4A;"><b>LAN:</b> <code style="background-color: #F0F2F6; padding: 2px 6px; border-radius: 4px; color: #1A1A1A;">{lan_string}</code></span>
                </div>
                """
                
                card_header_html = f"""
                    <div style="border-left: 10px solid {col_ind}; margin: -12px -16px 12px -16px; padding: 16px 20px; background-color: #FFFFFF;">
                        <table style="width: 100%; border-collapse: collapse; border: none;">
                            <tr>
                                <td style="vertical-align: top; text-align: left; padding: 0;">
                                    <h2 style="margin: 0 0 2px 0; line-height: 1.1; font-size:{int(30 * scale_mod)}px; font-weight: 500; color: #1A1A1A;">{tsk.get('finance')}</h2>
                                    {combined_details_html}
                                </td>
                            </tr>
                        </table>
                    </div>
                """
                
                st.markdown(card_header_html, unsafe_allow_html=True)

                raw_txt = str(tsk.get('task', ''))
                f_line = raw_txt.split('\n')[0]
                if len(f_line) > 50: 
                    f_line = f_line[:47] + "..."
                
                clean_toggle_label = f"🔍 Details: {f_line}".replace("<", "&lt;").replace(">", "&gt;")

                if st.toggle(clean_toggle_label, key=f"card_exp_state_{tid}"):
                    st.markdown(f"""
                        <div style="margin-top: 10px; padding: 14px; background-color: #F8F9FA; border-radius: 8px; border: 1px solid #DDE1E7; white-space: pre-wrap; font-size: {int(18 * scale_mod)}px; color: #1A1A1A;">
                            <b>Full Task Description:</b><br>{raw_txt}
                        </div>
                    """, unsafe_allow_html=True)
                    
                    if tsk.get("screenshot") and str(tsk.get("screenshot")).strip() != "":
                        try:
                            st.image(f"data:image/png;base64,{tsk.get('screenshot')}", use_container_width=True)
                        except:
                            st.caption("⚠️ Failed to display attachment image.")
                    
                    if stat == "Hold":
                        st.markdown(f'<div style="color:#E83E8C; padding:10px;"><b>⏸️ HOLD REASON:</b> {tsk.get("comment")}</div>', unsafe_allow_html=True)
                    
                    st.divider()

                    if stat == "Completed":
                        st.success(f"✅ Closed by {tsk.get('completed_by')} | Note: {tsk.get('comment', 'N/A')}")
                    else:
                        c_note, c_type, c_hold, c_done = st.columns([1.3, 0.7, 0.8, 0.8])
                        note = c_note.text_input("Comment", key=f"n_{tid}", placeholder="Note...", label_visibility="collapsed")
                        w_type = c_type.selectbox("Type", ["Regular", "Major"], key=f"t_{tid}", label_visibility="collapsed")
                        
                        if c_hold.button("Unhold" if stat == "Hold" else "⏸️ Hold", key=f"h_{tid}", use_container_width=True):
                            if stat != "Hold" and not note.strip():
                                st.error("🛑 Hold note is required.")
                            else:
                                p_load = {"status": "Hold", "comment": note, "hold_by": user['name'], "hold_at": get_now_ist()} if stat != "Hold" else {"status": "Pending", "comment": note, "hold_by": None, "hold_at": None}
                                requests.patch(f"{DB_BASE_URL}/tasks/{tid}.json", json=p_load)
                                st.rerun(scope="fragment")
                                
                        if c_done.button("✅ Done", key=f"d_{tid}", use_container_width=True, type="primary"):
                            if not note.strip():
                                st.error("🛑 Closing note is required.")
                            else:
                                requests.patch(f"{DB_BASE_URL}/tasks/{tid}.json", json={
                                    "status": "Completed", "completed_by": user['name'], 
                                    "work_type": w_type, "comment": note, "finished_at": get_now_ist(), "screenshot": None
                                })
                                st.rerun(scope="fragment")

                    if (user['role'] == "ADMIN" or tsk.get('assigner') == user['name']) and stat != "Completed":
                        st.write("")
                        adm1, adm2 = st.columns(2)
                        if adm1.button("✏️ Modify Details", key=f"m_{tid}", use_container_width=True):
                            edit_task_dialog(tid, tsk)
                        with adm2:
                            if st.checkbox("🗑️ Delete", key=f"del_chk_{tid}"):
                                if st.button("CONFIRM", key=f"del_btn_{tid}", use_container_width=True):
                                    requests.delete(f"{DB_BASE_URL}/tasks/{tid}.json")
                                    st.rerun(scope="fragment")
            st.write("")

    render_task_deck()