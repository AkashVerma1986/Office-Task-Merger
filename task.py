import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime

# --- 1. CONFIGURATION (From your Original Pro Script) ---
DB_BASE_URL = "https://office-task-ledger-default-rtdb.asia-southeast1.firebasedatabase.app/tasks"
SETTINGS_URL = "https://office-task-ledger-default-rtdb.asia-southeast1.firebasedatabase.app/settings.json"
DB_URL = f"{DB_BASE_URL}.json"
STAFF_PASSWORD = "1234"
ADMIN_PASSWORD = "1586"

# --- 2. PAGE SETTINGS ---
st.set_page_config(page_title="Report Correction Ledger Pro", page_icon="🍎", layout="wide")

# --- 3. PRO THEME CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #050505; color: #E0E0E0; }
    [data-testid="stSidebar"] { background-color: #0A0A0A; border-right: 1px solid #1A1A1A; }
    .stButton>button { 
        background-color: #B71C1C !important; color: white !important; 
        border-radius: 8px; font-weight: bold; border: none; height: 3em; width: 100%;
    }
    .task-card { 
        background: #0D0D0D; padding: 20px; border-radius: 12px; 
        margin-bottom: 12px; border-left: 8px solid #B71C1C;
        border-top: 1px solid #1A1A1A; box-shadow: 0px 4px 10px rgba(0,0,0,0.3);
    }
    .stTextInput>div>div>input { background-color: #000000 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. AUTHENTICATION ---
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

# --- 5. GLOBAL SETTINGS (Rename/Hide Logic) ---
def fetch_settings():
    try:
        res = requests.get(SETTINGS_URL, timeout=5)
        return res.json() or {"hidden": [], "renamed": {}}
    except: return {"hidden": [], "renamed": {}}

g_settings = fetch_settings()
hidden_finances = set(g_settings.get("hidden", []))
renamed_finances = g_settings.get("renamed", {})

# --- 6. DATA FETCHING ---
def fetch_data():
    try:
        res = requests.get(DB_URL, timeout=5)
        return res.json() or {}
    except: return {}

tasks_dict = fetch_data()

# --- 7. SIDEBAR (PRO CONTROLS) ---
st.sidebar.title(f"🍎 {st.session_state.user}")
st.sidebar.write(f"Access: {st.session_state.role}")

search = st.sidebar.text_input("🔍 Search Records", "")
all_raw_finances = sorted(list(set(t.get('finance', 'N/A').upper() for t in tasks_dict.values())))
# Apply rename/hide logic to the filter list
display_finances = [renamed_finances.get(f, f) for f in all_raw_finances if f not in hidden_finances]
filter_fin = st.sidebar.selectbox("Filter Ledger", ["--- ALL ---"] + sorted(list(set(display_finances))))

show_pending = st.sidebar.checkbox("🕒 Show Pending Only", value=True)
sort_priority = st.sidebar.checkbox("📌 Sort by High Priority")

# --- 8. MAIN UI ---
tab1, tab2 = st.tabs(["📝 New Entry", "📊 Active Ledger"])

with tab1:
    with st.form("pro_add_form"):
        c1, c2 = st.columns(2)
        with c1:
            f_input = st.text_input("Finance Name (e.g., NANDAWATA)").upper()
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
                st.success(f"Task for {f_input} saved to Firebase!")
                st.rerun()

with tab2:
    # Prepare and Sort Items
    items = list(tasks_dict.items())
    if sort_priority:
        items.sort(key=lambda x: ({"High": 3, "Medium": 2, "Normal": 1}.get(x[1].get('priority', 'Normal'), 1)), reverse=True)
    else:
        items.reverse()

    for tid, t in items:
        # Safety extractions
        f_raw = t.get('finance', 'N/A').upper()
        f_display = renamed_finances.get(f_raw, f_raw)
        status = t.get('status', 'Pending')
        p_raw = t.get('priority', 'Normal')
        
        # Filtering
        if f_raw in hidden_finances or f_display in hidden_finances: continue
        if filter_fin != "--- ALL ---" and f_display != filter_fin: continue
        if show_pending and status != "Pending": continue
        if search.lower() not in t.get('task','').lower() and search.lower() not in f_display.lower(): continue

        # Card Display
        with st.container():
            p_color = "#B71C1C" if p_raw.upper() == "HIGH" else "#3E91D4"
            st.markdown(f"""
            <div class="task-card">
                <small style='color:#808080;'>{t.get('assigned_at', '')} | By: {t.get('assigner', 'System')}</small>
                <h3 style='margin:5px 0; color:#E0E0E0;'>{f_display}</h3>
                <p style='font-size:16px;'>{t.get('task', '')}</p>
                <p style='color:{p_color}; font-weight:bold;'>PRIORITY: {p_raw.upper()}</p>
                {f"<small style='color:#1B5E20;'>✓ {status.upper()} by {t.get('completed_by')} on {t.get('finished_at')}</small>" if status != "Pending" else ""}
            </div>
            """, unsafe_allow_html=True)
            
            if status == "Pending":
                c1, c2 = st.columns([4, 1])
                note = c1.text_input("Completion Note", key=f"n_{tid}", placeholder="Add status note...")
                if c2.button("DONE", key=f"b_{tid}"):
                    if note:
                        upd = {"status": "Completed", "comment": note, "completed_by": st.session_state.user, "finished_at": datetime.now().strftime("%d/%b/%Y %H:%M:%S")}
                        requests.patch(f"{DB_BASE_URL}/{tid}.json", json=upd)
                        st.rerun()
                    else: st.warning("Note required.")

# --- 9. EXPORT & ADMIN TOOLS ---
st.sidebar.markdown("---")
if st.sidebar.button("📊 Export Full Excel"):
    df = pd.DataFrame.from_dict(tasks_dict, orient='index')
    st.sidebar.download_button("Download Now", df.to_csv(), "Office_Ledger.csv")

if st.session_state.role == "ADMIN":
    st.sidebar.subheader("Admin Tools")
    if st.sidebar.button("🗑 Clear Completed Tasks"):
        st.sidebar.warning("Feature coming soon...")