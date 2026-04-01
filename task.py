import streamlit as st
import pandas as pd
import requests
import json
import time
from datetime import datetime

# --- 1. CONFIGURATION ---
DB_BASE_URL = "https://office-task-ledger-default-rtdb.asia-southeast1.firebasedatabase.app/tasks"
DB_URL = f"{DB_BASE_URL}.json"

# --- 2. PAGE CONFIG ---
st.set_page_config(page_title="Real-Time Office Ledger", page_icon="🍎", layout="wide")

# --- 3. COMPACT MIDNIGHT CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #E0E0E0; }
    .task-card { 
        background: #0A0A0A; padding: 5px 12px; margin-bottom: 2px; 
        border-radius: 5px; border-left: 5px solid #B71C1C;
        border-top: 1px solid #1A1A1A;
    }
    .task-card p { margin: 0px; font-size: 13px; }
    .task-card h4 { margin: 0px; font-size: 14px; color: #E0E0E0; }
    
    /* Compact Inputs/Buttons */
    .stButton>button { height: 24px !important; font-size: 11px !important; width: 100%; }
    div[data-testid="stExpander"] { background: #0A0A0A; border: none; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. REAL-TIME ENGINE ---
if "last_data_hash" not in st.session_state:
    st.session_state.last_data_hash = ""

def fetch_data():
    try:
        res = requests.get(DB_URL, timeout=5)
        return res.json() or {}
    except: return {}

# --- 5. UI LAYOUT ---
st.title("🍎 Real-Time Ledger")

# --- ADD TASK SECTION (Hidden in Expander to save space) ---
with st.expander("➕ ADD NEW TASK"):
    with st.form("quick_add", clear_on_submit=True):
        f_name = st.text_input("Finance").upper()
        t_detail = st.text_area("Details")
        if st.form_submit_button("SYNC TO CLOUD"):
            pld = {"finance": f_name, "task": t_detail, "status": "Pending", "assigned_at": datetime.now().strftime("%H:%M:%S")}
            requests.post(DB_URL, json=pld)
            st.rerun()

# --- 6. THE LIVE LIST CONTAINER ---
placeholder = st.empty()

# --- 7. INFINITE SYNC LOOP ---
while True:
    current_data = fetch_data()
    # Create a unique 'fingerprint' of the data
    current_hash = json.dumps(current_data, sort_keys=True)

    # ONLY RE-RENDER IF DATA CHANGED
    if current_hash != st.session_state.last_data_hash:
        st.session_state.last_data_hash = current_hash
        
        with placeholder.container():
            items = list(current_data.items())
            items.reverse()
            
            for tid, t in items:
                status = t.get('status', 'Pending')
                if status == "Completed": continue
                
                accent = {"Pending": "#C29100", "Hold": "#880E4F"}.get(status, "#C29100")
                
                # COMPACT WINDOW
                st.markdown(f"""
                <div class="task-card" style="border-left-color: {accent};">
                    <h4>{t.get('finance', 'N/A')} <small style='color:#666; float:right;'>{t.get('assigned_at','')}</small></h4>
                    <p>{t.get('task', '')}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # ACTION ROW
                c1, c2, c3 = st.columns([3, 1, 1])
                note = c1.text_input("Note", key=f"n_{tid}", label_visibility="collapsed", placeholder="Note...")
                
                if c2.button("DONE", key=f"d_{tid}"):
                    requests.patch(f"{DB_BASE_URL}/{tid}.json", json={"status": "Completed", "comment": note})
                    st.rerun()
                
                h_lab = "UNHOLD" if status == "Hold" else "HOLD"
                if c3.button(h_lab, key=f"h_{tid}"):
                    new_s = "Pending" if status == "Hold" else "Hold"
                    requests.patch(f"{DB_BASE_URL}/{tid}.json", json={"status": new_s})
                    st.rerun()

    # Sleep for 1 second before checking Firebase again (prevents crashing your phone)
    time.sleep(1)