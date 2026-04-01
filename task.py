import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime

# --- 1. CONFIGURATION ---
DB_BASE_URL = "https://office-task-ledger-default-rtdb.asia-southeast1.firebasedatabase.app/tasks"
SETTINGS_URL = "https://office-task-ledger-default-rtdb.asia-southeast1.firebasedatabase.app/settings.json"
DB_URL = f"{DB_BASE_URL}.json"
ADMIN_PASSWORD = "1586"
STAFF_PASSWORD = "1234"

# --- 2. PAGE CONFIG ---
st.set_page_config(page_title="Report Correction Ledger Pro", page_icon="🍎", layout="wide")

# --- 3. PRO MIDNIGHT & RED THEME ---
st.markdown("""
    <style>
    .stApp { background-color: #050505; color: #E0E0E0; }
    [data-testid="stSidebar"] { background-color: #0A0A0A; border-right: 1px solid #1A1A1A; }
    .stButton>button { 
        background-color: #B71C1C !important; color: white !important; 
        border-radius: 8px; font-weight: bold; height: 3em; width: 100%;
    }
    .task-card { 
        background: #0D0D0D; padding: 20px; border-radius: 12px; 
        margin-bottom: 12px; border-left: 8px solid #B71C1C;
        border-top: 1px solid #1A1A1A; box-shadow: 0px 4px 10px rgba(0,0,0,0.3);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 4. LOGIN SYSTEM ---
if 'auth' not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    with st.container():
        st.title("🍎 Office Ledger Pro Login")
        u_name = st.text_input("Full Name").upper()
        u_pass = st.text_input("Password", type="password")
        if st.button("LOGIN"):
            if u_pass == ADMIN_PASSWORD:
                st.session_state.auth, st.session_state.role, st.session_state.user = True, "ADMIN", u_name
                st.rerun()
            elif u_pass == STAFF_PASSWORD:
                st.session_state.auth, st.session_state.role, st.session_state.user = True, "STAFF", u_name
                st.rerun()
            else: st.error("Invalid Password")
    st.stop()

# --- 5. DATA & SETTINGS FETCHING ---
def fetch_all():
    try:
        t_res = requests.get(DB_URL, timeout=5).json() or {}
        s_res = requests.get(SETTINGS_URL, timeout=5).json() or {"hidden": [], "renamed": {}}
        return t_res, s_res
    except: return {}, {"hidden": [], "renamed": {}}

tasks_dict, g_settings = fetch_all()
hidden_finances = set(g_settings.get("hidden", []))
renamed_finances = g_settings.get("renamed", {})

# --- 6. SIDEBAR (FILTERS & ADMIN TOOLS) ---
st.sidebar.title(f"🍎 {st.session_state.user}")
search = st.sidebar.text_input("🔍 Search Records", "")

# Finance Filter Logic (Rename/Hide applied)
all_raw = sorted(list(set(t.get('finance', 'N/A').upper() for t in tasks_dict.values())))
display_list = [renamed_finances.get(f, f) for f in all_raw if f not in hidden_finances]
filter_fin = st.sidebar.selectbox("Filter Ledger", ["--- ALL ---"] + sorted(list(set(display_list))))

show_pending = st.sidebar.checkbox("🕒 Show Pending Only", value=True)
sort_priority = st.sidebar.checkbox("📌 Sort by High Priority")

# --- 7. MAIN INTERFACE ---
tab1, tab2 = st.tabs(["📝 New Entry", "📊 Active Ledger"])

with tab1:
    with st.form("pro_form"):
        c1, c2 = st.columns(2)
        with c1:
            f_input = st.text_input("Finance Name (e.g. NANDAWATA)").upper()
            cat = st.selectbox("Category", ["1. Rate Correction", "2. Spelling/Address", "3. Digital Sign", "4. Report Upload", "5. Photos/Drafting"])
        with c2:
            pri = st.selectbox("Priority", ["Normal", "Medium", "High"])
            details = st.text_area("Correction Details")
        
        if st.form_submit_button("ADD TO CLOUD LEDGER"):
            if f_input and details:
                pld = {
                    "finance": f_input, "task": f"[{cat}] {details}", 
                    "priority": pri, "assigner": st.session_state.user, 
                    "status": "Pending", "assigned_at": datetime.now().strftime("%d/%b/%Y %H:%M:%S")
                }
                requests.post(DB_URL, json=pld)
                st.success("Task Added!")
                st.rerun()

with tab2:
    items = list(tasks_dict.items())
    if sort_priority:
        items.sort(key=lambda x: ({"High": 3, "Medium": 2, "Normal": 1}.get(x[1].get('priority', 'Normal'), 1)), reverse=True)
    else: items.reverse()

    for tid, t in items:
        f_raw = t.get('finance', 'N/A').upper()
        f_disp = renamed_finances.get(f_raw, f_raw)
        status = t.get('status', 'Pending')
        
        if f_raw in hidden_finances or f_disp in hidden_finances: continue
        if filter_fin != "--- ALL ---" and f_disp != filter_fin: continue
        if show_pending and status != "Pending": continue
        if search.lower() not in t.get('task','').lower() and search.lower() not in f_disp.lower(): continue

        with st.container():
            p_color = "#B71C1C" if t.get('priority','').upper() == "HIGH" else "#3E91D4"
            st.markdown(f"""
            <div class="task-card">
                <small style='color:#808080;'>{t.get('assigned_at')} | {t.get('assigner')}</small>
                <h3 style='margin:5px 0; color:#E0E0E0;'>{f_disp}</h3>
                <p>{t.get('task')}</p>
                <p style='color:{p_color}; font-weight:bold;'>PRIORITY: {t.get('priority','NORMAL').upper()}</p>
            </div>
            """, unsafe_allow_html=True)
            
            if status == "Pending":
                c1, c2 = st.columns([4, 1])
                note = c1.text_input("Note", key=f"n_{tid}", placeholder="Completion note...")
                if c2.button("DONE", key=f"b_{tid}"):
                    if note:
                        upd = {"status": "Completed", "comment": note, "completed_by": st.session_state.user, "finished_at": datetime.now().strftime("%d/%b/%Y %H:%M:%S")}
                        requests.patch(f"{DB_BASE_URL}/{tid}.json", json=upd)
                        st.rerun()

# --- 8. ADMIN MANAGEMENT TOOLS ---
if st.session_state.role == "ADMIN":
    st.sidebar.markdown("---")
    st.sidebar.subheader("⚙️ Finance Management")
    
    target_fin = st.sidebar.selectbox("Select Finance to Edit", ["--- Select ---"] + all_raw)
    if target_fin != "--- Select ---":
        new_name = st.sidebar.text_input(f"Rename {target_fin}")
        if st.sidebar.button("Update Name"):
            renamed_finances[target_fin] = new_name.upper()
            requests.put(SETTINGS_URL, json={"hidden": list(hidden_finances), "renamed": renamed_finances})
            st.rerun()
            
        if st.sidebar.button(f"Hide {target_fin} Globally"):
            hidden_finances.add(target_fin)
            requests.put(SETTINGS_URL, json={"hidden": list(hidden_finances), "renamed": renamed_finances})
            st.rerun()

if st.sidebar.button("📊 Export Excel Report"):
    df = pd.DataFrame.from_dict(tasks_dict, orient='index')
    st.sidebar.download_button("Download Now", df.to_csv(), "Office_Ledger.csv")