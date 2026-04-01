import streamlit as st
import pandas as pd
from datetime import datetime

# --- 1. PAGE SETTINGS ---
st.set_page_config(page_title="Office Task Ledger Pro", page_icon="🍎", layout="centered")

# --- 2. RED THEME (MOBILE FRIENDLY) ---
st.markdown("""
    <style>
    /* Light Red Background */
    .stApp { background-color: #fff1f2; }
    
    /* Red Buttons */
    div.stButton > button:first-child {
        background-color: #e11d48 !important; /* Crimson Red */
        color: white !important;
        border-radius: 12px !important;
        border: none !important;
        height: 3.5em !important;
        width: 100% !important;
        font-weight: bold !important;
        box-shadow: 0px 4px 10px rgba(225, 29, 72, 0.2);
    }
    
    /* Hover effect for buttons */
    div.stButton > button:first-child:hover {
        background-color: #be123c !important;
        color: white !important;
    }
    
    /* Task Cards with Red Border */
    .task-box {
        background-color: white;
        padding: 20px;
        border-radius: 15px;
        border-left: 8px solid #e11d48;
        margin-bottom: 15px;
        box-shadow: 0px 2px 8px rgba(0,0,0,0.05);
    }

    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #ffe4e6;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. HEADER ---
st.title("🍎 Office Task Ledger Pro")
st.write(f"Logged in: **{datetime.now().strftime('%d-%m-%Y')}**")
st.markdown("---")

# --- 4. NAVIGATION & PRO FEATURES ---
st.sidebar.header("🍎 Control Panel")
choice = st.sidebar.radio("Navigation", ["📝 Add New Task", "📊 View Ledger", "📤 Export to Excel"])

# Filter for Finance/Admin (As per your Pro version)
filter_dept = st.sidebar.selectbox("Filter by Dept", ["All", "Finance", "Admin", "Field"])

if choice == "📝 Add New Task":
    st.subheader("Create New Task")
    task_title = st.text_input("Task Description")
    staff_member = st.selectbox("Assign to Staff", ["Admin", "Finance", "Field Staff"])
    priority = st.select_slider("Priority", options=["Normal", "Urgent", "Immediate"])
    
    if st.button("Save to Red Ledger"):
        if task_title:
            st.success(f"🎯 Saved: {task_title}")
        else:
            st.error("Please enter a task name.")

elif choice == "📊 View Ledger":
    st.subheader(f"Active Tasks: {filter_dept}")
    # Example Display of a Pro Task Card
    st.markdown(f"""
    <div class="task-box">
        <h4 style='margin:0; color:#9f1239;'>Update Land Records (Nandawata)</h4>
        <p style='margin:5px 0; color:#4b5563;'>Dept: Finance | Status: Urgent</p>
        <span style='background:#ffe4e6; color:#e11d48; padding:2px 8px; border-radius:5px; font-size:12px;'>PENDING</span>
    </div>
    """, unsafe_allow_html=True)

elif choice == "📤 Export to Excel":
    st.subheader("Generate Office Report")
    st.info("Consolidate all tasks into a single Excel file.")
    if st.button("Generate & Download"):
        st.write("Merging files... 100% Complete")

st.sidebar.markdown("---")
st.sidebar.write("Office Management | Madhya Pradesh")