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

# --- 2. PAGE CONFIG & MIDNIGHT UI ---
st.set_page_config(page_title="Report Correction Ledger Pro", page_icon="🍎", layout="wide")

st.markdown("""
    <style>
    /* Midnight Palette */
    .stApp { background-color: #000000; color: #E0E0E0; }
    [data-testid="stSidebar"] { background-color: #0A0A0A; border-right: 1px solid #1A1A1A; }
    
    /* Task Cards */
    .task-card { 
        background: #0A0A0A; padding: 20px; border-radius: 12px; 
        margin-bottom: 12px; border-left: 10px solid #B71C1C;
        border-top: 1px solid #1A1A1A; border-right: 1px solid #1A1A1A;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.8);
    }
    
    /* Buttons */
    .stButton>button { 
        background-color: #1A1A1A !important; color: white !important; 
        border: 1px solid #333 !important; border-radius: 8px; font-weight: bold;
    }
    .stButton>button:hover { border-color: #B71C1C !important; color: #B71C1C !important; }
    
    /* Input Fields */
    .stTextInput>div>div>input { background-color: #000000 !important; color: white !important; border-color: #333 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. AUTHENTICATION ---
if 'auth' not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    with st.container():
        st.title("🍎 Midnight Ledger Pro Login")
        u_name = st.text_input("Full Name").upper()
        u_pass = st.text_input("Password", type="password")
        if st.button("LOGIN"):
            if u_pass in [ADMIN_PASSWORD, STAFF_PASSWORD]:
                st.session_state.update({"auth": True, "role": "ADMIN" if u_pass == ADMIN_PASSWORD else "STAFF", "user": u_name})
                st.rerun()
            else: st.error("Invalid Password")
    st.stop()

# --- 4. DATA FETCHING ---
def fetch_all():
    try:
        t_res = requests.get(DB_URL, timeout=5).json() or {}
        s_res = requests.get(SETTINGS_URL, timeout=5).json() or {"hidden": [], "renamed": {}}
        return t_res, s_res
    except: return {}, {"hidden": [], "renamed": {}}

tasks_dict, g_settings = fetch_all()
hidden_finances = set(g_settings.get("hidden", []))
renamed_finances = g_settings.get("renamed", {})

# --- 5. SIDEBAR FILTERS ---
st.sidebar.title(f"🍎 {st.session_state.user}")
search = st.sidebar.text_input("🔍 Search Ledger", "")

# --- THE FINANCE DROP DOWN ---
all_raw = sorted(list(set(t.get('finance', 'N/A').upper() for t in tasks_dict.values() if t.get('finance'))))
display_list = [renamed_finances.get(f, f) for f in all_raw if f not in hidden_finances]
filter_fin = st.sidebar.selectbox("Finance Filter", ["--- ALL FINANCES ---"] + sorted(list(set(display_list))))

# --- 6. MAIN UI ---
tab1, tab2 = st.tabs(["📝 New Entry", "📊 Active Ledger"])

with tab1:
    with st.form("entry_form"):
        # The Finance Drop Down for entry
        f_entry = st.selectbox("Select Finance Name", sorted(list(set(display_list))))
        cat = st.selectbox("Category", ["1. Rate Correction", "2. Spelling/Address", "3. Digital Sign", "4. Report Upload", "5. Photos/Drafting"])
        pri = st.selectbox("Priority", ["Normal", "Medium", "High"])
        details = st.text_area("Correction Details")
        
        if st.form_submit_button("ADD TO CLOUD"):
            pld = {"finance": f_entry, "task": f"[{cat}] {details}", "priority": pri, "assigner": st.session_state.user, "status": "Pending", "assigned_at": datetime.now().strftime("%d/%b/%Y %H:%M:%S")}
            requests.post(DB_URL, json=pld)
            st.rerun()

with tab2:
    items = list(tasks_dict.items())
    items.reverse()

    for tid, t in items:
        f_raw = t.get('finance', 'N/A').upper()
        f_disp = renamed_finances.get(f_raw, f_raw)
        status = t.get('status', 'Pending')
        
        if f_raw in hidden_finances or f_disp in hidden_finances: continue
        if filter_fin != "--- ALL FINANCES ---" and f_disp != filter_fin: continue
        if search.lower() not in t.get('task','').lower() and search.lower() not in f_disp.lower(): continue

        with st.container():
            # Status colors matching your desktop app
            accent = {"Pending": "#C29100", "Completed": "#1B5E20", "Hold": "#880E4F"}.get(status, "#C29100")
            
            st.markdown(f"""
            <div class="task-card" style="border-left-color: {accent};">
                <small style='color:#808080;'>{t.get('assigned_at')} | {t.get('assigner')}</small>
                <h3 style='margin:5px 0; color:#E0E0E0;'>{f_disp}</h3>
                <p>{t.get('task')}</p>
                <p style='color:{accent}; font-weight:bold;'>STATUS: {status.upper()}</p>
            </div>
            """, unsafe_allow_html=True)
            
            if status != "Completed":
                c1, c2, c3 = st.columns([2, 1, 1])
                note = c1.text_input("Note", key=f"n_{tid}", placeholder="Add note...")
                
                # --- THE HOLD & DONE FUNCTIONS ---
                if c2.button("DONE", key=f"d_{tid}"):
                    if note:
                        upd = {"status": "Completed", "comment": note, "completed_by": st.session_state.user, "finished_at": datetime.now().strftime("%d/%b/%Y %H:%M:%S")}
                        requests.patch(f"{DB_BASE_URL}/{tid}.json", json=upd)
                        st.rerun()
                
                hold_label = "UNHOLD" if status == "Hold" else "HOLD"
                if c3.button(hold_label, key=f"h_{tid}"):
                    new_status = "Pending" if status == "Hold" else "Hold"
                    requests.patch(f"{DB_BASE_URL}/{tid}.json", json={"status": new_status})
                    st.rerun()