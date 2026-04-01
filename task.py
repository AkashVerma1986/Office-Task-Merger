import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# --- CONFIG (Your Original Firebase) ---
DB_BASE_URL = "https://office-task-ledger-default-rtdb.asia-southeast1.firebasedatabase.app/tasks"
DB_URL = f"{DB_BASE_URL}.json"
ADMIN_PASSWORD = "1586"

# --- PAGE CONFIG ---
st.set_page_config(page_title="Report Correction Ledger Pro", page_icon="🍎", layout="wide")

# --- PRO DARK RED THEME (Matching your Midnight Palette) ---
st.markdown("""
    <style>
    .stApp { background-color: #050505; color: #E0E0E0; }
    [data-testid="stSidebar"] { background-color: #0A0A0A; border-right: 1px solid #1A1A1A; }
    .stButton>button { 
        background-color: #B71C1C !important; color: white !important; 
        border-radius: 8px; font-weight: bold; border: none;
    }
    .task-card { 
        background: #0A0A0A; padding: 20px; border-radius: 12px; 
        margin-bottom: 12px; border-left: 8px solid #B71C1C;
        border-top: 1px solid #1A1A1A; border-right: 1px solid #1A1A1A;
    }
    .priority-high { color: #FF5252; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 1. AUTHENTICATION LOGIC ---
if 'auth' not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🍎 Office Ledger Pro Login")
    user = st.text_input("User Name")
    passwd = st.text_input("Password", type="password")
    if st.button("LOGIN"):
        if passwd in ["1234", "1586"]:
            st.session_state.auth = True
            st.session_state.user = user.upper()
            st.rerun()
    st.stop()

# --- 2. DATA FETCHING ---
@st.cache_data(ttl=5) # Auto-refresh data every 5 seconds
def fetch_tasks():
    try:
        return requests.get(DB_URL).json() or {}
    except: return {}

tasks_dict = fetch_tasks()

# --- 3. PRO FILTERS (The Search & Toggle logic) ---
st.sidebar.title(f"🍎 {st.session_state.user}")
search_query = st.sidebar.text_input("🔍 Search Ledger", "")
filter_dept = st.sidebar.selectbox("Finance Filter", ["All Finances"] + sorted(list(set(t.get('finance', 'N/A') for t in tasks_dict.values()))))
sort_priority = st.sidebar.checkbox("📌 Sort by High Priority")

# --- 4. MAIN UI ---
tab1, tab2 = st.tabs(["📝 New Entry", "📊 Active Ledger"])

with tab1:
    with st.form("new_task"):
        f_name = st.text_input("Finance Name").upper()
        cat = st.selectbox("Category", ["Rate Correction", "Spelling/Address", "Digital Sign", "Report Upload"])
        pri = st.select_slider("Priority", options=["Normal", "Medium", "High"])
        detail = st.text_area("Task Details")
        if st.form_submit_button("ADD TO LEDGER"):
            pld = {"finance": f_name, "task": f"[{cat}] {detail}", "priority": pri, "assigner": st.session_state.user, "status": "Pending", "assigned_at": datetime.now().strftime("%d/%b/%Y %H:%M:%S")}
            requests.post(DB_URL, json=pld)
            st.toast("Task Added Successfully!")
            st.rerun()

with tab2:
    # Sorting logic
    items = list(tasks_dict.items())
    if sort_priority:
        items.sort(key=lambda x: ({"High": 3, "Medium": 2, "Normal": 1}.get(x[1].get('priority'), 1)), reverse=True)
    else:
        items.reverse() # Show newest first

    for tid, t in items:
        # Filter Logic
        if filter_dept != "All Finances" and t.get('finance') != filter_dept: continue
        if search_query.lower() not in t.get('task','').lower() and search_query.lower() not in t.get('finance','').lower(): continue

        # Display Card
        with st.container():
            st.markdown(f"""
            <div class="task-card">
                <small style='color:#808080;'>{t.get('assigned_at')} | {t.get('assigner')}</small>
                <h3 style='margin:5px 0; color:#E0E0E0;'>{t.get('finance')}</h3>
                <p style='color:#B0B0B0;'>{t.get('task')}</p>
                <p style='color:{"#FF5252" if t.get("priority")=="High" else "#3E91D4"}; font-weight:bold;'>PRIORITY: {t.get('priority').upper()}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Action Row
            col1, col2 = st.columns([3, 1])
            if t.get('status') == "Pending":
                with col1:
                    note = st.text_input("Completion Note", key=f"n_{tid}", label_visibility="collapsed", placeholder="Enter note...")
                with col2:
                    if st.button("DONE", key=f"d_{tid}"):
                        upd = {"status": "Completed", "comment": note, "completed_by": st.session_state.user, "finished_at": datetime.now().strftime("%d/%b/%Y %H:%M:%S")}
                        requests.patch(f"{DB_BASE_URL}/{tid}.json", json=upd)
                        st.rerun()