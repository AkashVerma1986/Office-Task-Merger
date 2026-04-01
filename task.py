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

# --- 2. PAGE CONFIG & COMPACT MIDNIGHT THEME ---
st.set_page_config(page_title="Report Correction Ledger Pro", page_icon="🍎", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #E0E0E0; }
    [data-testid="stSidebar"] { background-color: #0A0A0A; border-right: 1px solid #1A1A1A; }
    
    /* ULTRA COMPACT TASK CARDS */
    .task-card { 
        background: #0A0A0A; 
        padding: 6px 12px !important; 
        margin-bottom: 4px !important; 
        border-radius: 6px; 
        border-left: 6px solid #B71C1C;
        border-top: 1px solid #1A1A1A;
        line-height: 1.2;
    }
    .task-card h4 { margin: 0px !important; font-size: 14px !important; color: #E0E0E0; }
    .task-card p { margin: 2px 0px !important; font-size: 13px !important; color: #B0B0B0; }
    
    /* Small Buttons to save height */
    .stButton>button { 
        height: 28px !important; 
        font-size: 11px !important; 
        background-color: #1A1A1A !important;
        border: 1px solid #333 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. AUTHENTICATION ---
if 'auth' not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🍎 Midnight Ledger Login")
    u_name = st.text_input("Name").upper()
    u_pass = st.text_input("Password", type="password")
    if st.button("LOGIN"):
        if u_pass in [ADMIN_PASSWORD, STAFF_PASSWORD]:
            st.session_state.update({"auth": True, "role": "ADMIN" if u_pass == ADMIN_PASSWORD else "STAFF", "user": u_name})
            st.rerun()
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

# --- 5. SIDEBAR & SYNC ---
st.sidebar.title(f"🍎 {st.session_state.user}")
if st.sidebar.button("🔄 SYNC DATA"):
    st.rerun()

search = st.sidebar.text_input("🔍 Search", "")
all_raw = sorted(list(set(t.get('finance', 'N/A').upper() for t in tasks_dict.values() if t.get('finance'))))
display_list = [renamed_finances.get(f, f) for f in all_raw if f not in hidden_finances]
filter_fin = st.sidebar.selectbox("Filter", ["--- ALL ---"] + sorted(list(set(display_list))))

# --- 6. MAIN UI ---
tab1, tab2 = st.tabs(["📝 New", "📊 Ledger"])

with tab1:
    with st.form("entry_form"):
        f_entry = st.text_input("Finance Name").upper()
        cat = st.selectbox("Category", ["1. Rate Correction", "2. Spelling/Address", "3. Digital Sign", "4. Report Upload", "5. Photos/Drafting"])
        pri = st.selectbox("Priority", ["Normal", "Medium", "High"])
        details = st.text_area("Details")
        if st.form_submit_button("ADD TO CLOUD"):
            pld = {"finance": f_entry, "task": f"[{cat}] {details}", "priority": pri, "assigner": st.session_state.user, "status": "Pending", "assigned_at": datetime.now().strftime("%H:%M:%S")}
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
        if filter_fin != "--- ALL ---" and f_disp != filter_fin: continue
        if search.lower() not in t.get('task','').lower() and search.lower() not in f_disp.lower(): continue
        if status == "Completed": continue

        with st.container():
            accent = {"Pending": "#C29100", "Hold": "#880E4F"}.get(status, "#C29100")
            st.markdown(f"""
            <div class="task-card" style="border-left-color: {accent};">
                <h4>{f_disp} <small style='color:#666; float:right;'>{t.get('assigned_at')}</small></h4>
                <p>{t.get('task')}</p>
            </div>
            """, unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns([3, 1, 1])
            note = c1.text_input("Note", key=f"n_{tid}", label_visibility="collapsed", placeholder="Note...")
            if c2.button("DONE", key=f"d_{tid}"):
                requests.patch(f"{DB_BASE_URL}/{tid}.json", json={"status": "Completed", "comment": note, "finished_at": datetime.now().strftime("%H:%M:%S")})
                st.rerun()
            h_lab = "UNHOLD" if status == "Hold" else "HOLD"
            if c3.button(h_lab, key=f"h_{tid}"):
                requests.patch(f"{DB_BASE_URL}/{tid}.json", json={"status": "Pending" if status == "Hold" else "Hold"})
                st.rerun()