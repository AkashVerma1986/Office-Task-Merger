import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# --- CONFIGURATION (From your original code) ---
DB_BASE_URL = "https://office-task-ledger-default-rtdb.asia-southeast1.firebasedatabase.app/tasks"
DB_URL = f"{DB_BASE_URL}.json"
STAFF_PASSWORD = "1234"
ADMIN_PASSWORD = "1586"

# --- PAGE CONFIG ---
st.set_page_config(page_title="Report Correction Ledger Pro", page_icon="🍎", layout="wide")

# --- RED APPLE THEME CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #fff1f2; }
    .stButton>button { 
        background-color: #e11d48 !important; color: white !important; 
        border-radius: 12px; font-weight: bold; height: 3em; width: 100%;
    }
    .task-card { 
        background: white; padding: 15px; border-radius: 12px; 
        margin-bottom: 12px; border-left: 10px solid #e11d48;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.05);
    }
    .priority-high { color: #b91c1c; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- AUTHENTICATION ---
if 'auth' not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    with st.form("login_form"):
        st.title("🍎 Office Ledger Login")
        user = st.text_input("Full Name")
        passwd = st.text_input("Password", type="password")
        if st.form_submit_button("LOGIN"):
            if passwd == ADMIN_PASSWORD:
                st.session_state.role = "ADMIN"
                st.session_state.user = user.upper()
                st.session_state.auth = True
                st.rerun()
            elif passwd == STAFF_PASSWORD:
                st.session_state.role = "STAFF"
                st.session_state.user = user.upper()
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("Invalid Password")
    st.stop()

# --- DATA FETCHING ---
def fetch_data():
    try:
        res = requests.get(DB_URL, timeout=5)
        return res.json() or {}
    except:
        return {}

tasks_dict = fetch_data()

# --- SIDEBAR CONTROL PANEL ---
st.sidebar.title(f"🍎 {st.session_state.user}")
st.sidebar.write(f"Role: {st.session_state.role}")
nav_filter = st.sidebar.selectbox("Filter by Dept", ["All"] + sorted(list(set(t.get('finance', 'N/A') for t in tasks_dict.values()))))
show_pending_only = st.sidebar.checkbox("🕒 Pending Only", value=True)

# --- ADD TASK TAB ---
tab1, tab2 = st.tabs(["📝 Add New Correction", "📊 View Ledger"])

with tab1:
    with st.form("add_task"):
        f_name = st.text_input("Finance Name").upper()
        cat = st.selectbox("Category", ["1. Rate Correction", "2. Spelling/Address", "3. Digital Sign", "4. Report Upload", "5. Photos/Drafting"])
        pri = st.selectbox("Priority", ["Normal", "Medium", "High"])
        task_detail = st.text_area("Correction Details")
        
        if st.form_submit_button("ADD TO LEDGER"):
            if f_name and task_detail:
                assigned_time = datetime.now().strftime("%d/%b/%Y %H:%M:%S")
                pld = {
                    "finance": f_name, 
                    "task": f"[{cat}] {task_detail}", 
                    "priority": pri, 
                    "assigner": st.session_state.user, 
                    "status": "Pending", 
                    "assigned_at": assigned_time
                }
                requests.post(DB_URL, json=pld)
                st.success("Task Added!")
                st.rerun()

with tab2:
    search = st.text_input("🔍 Search tasks...")
    
    # Filtering logic from your original code
    for tid, t in reversed(list(tasks_dict.items())):
        status = t.get('status', 'Pending')
        finance = t.get('finance', '').upper()
        
        if show_pending_only and status != "Pending": continue
        if nav_filter != "All" and finance != nav_filter: continue
        if search.lower() not in t.get('task','').lower() and search.lower() not in finance.lower(): continue

        with st.container():
            st.markdown(f"""
            <div class="task-card">
                <p style='margin:0; font-size:12px; color:#e11d48;'><b>{t.get('priority','').upper()}</b> | {t.get('assigned_at','')}</p>
                <h4 style='margin:5px 0;'>{finance} • {t.get('assigner','')}</h4>
                <p style='color:#374151;'>{t.get('task','')}</p>
            </div>
            """, unsafe_allow_html=True)
            
            if status == "Pending":
                note = st.text_input("Completion Note", key=f"note_{tid}")
                if st.button("Mark Completed", key=f"btn_{tid}"):
                    if note:
                        finished_time = datetime.now().strftime("%d/%b/%Y %H:%M:%S")
                        upd = {"status": "Completed", "comment": note, "completed_by": st.session_state.user, "finished_at": finished_time}
                        requests.patch(f"{DB_BASE_URL}/{tid}.json", json=upd)
                        st.rerun()
                    else:
                        st.warning("Please add a note first.")

# --- EXCEL EXPORT ---
if st.sidebar.button("📊 Export to Excel"):
    df = pd.DataFrame.from_dict(tasks_dict, orient='index')
    st.sidebar.download_button("Download File", df.to_csv(), "Ledger_Export.csv")