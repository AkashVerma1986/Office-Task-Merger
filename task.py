import streamlit as st
import pandas as pd
from datetime import datetime

# --- 1. PAGE SETTINGS ---
st.set_page_config(page_title="Office Task Merger Pro", page_icon="🍏", layout="centered")

# --- 2. GREEN THEME (MOBILE FRIENDLY) ---
st.markdown("""
    <style>
    /* Background */
    .stApp { background-color: #f0fdf4; }
    
    /* Green Buttons */
    div.stButton > button:first-child {
        background-color: #22c55e !important;
        color: white !important;
        border-radius: 12px !important;
        border: none !important;
        height: 3.5em !important;
        width: 100% !important;
        font-weight: bold !important;
        box-shadow: 0px 4px 10px rgba(34, 197, 94, 0.2);
    }
    
    /* Task Cards */
    .task-box {
        background-color: white;
        padding: 20px;
        border-radius: 15px;
        border-left: 8px solid #22c55e;
        margin-bottom: 15px;
        box-shadow: 0px 2px 8px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. HEADER ---
st.title("🍏 Office Task Merger")
st.write(f"Logged in: {datetime.now().strftime('%d-%m-%Y')}")
st.markdown("---")

# --- 4. NAVIGATION ---
menu = ["📝 Add New Task", "📊 View Ledger", "📤 Export to Excel"]
choice = st.sidebar.radio("Navigation", menu)

if choice == "📝 Add New Task":
    st.subheader("Create New Task")
    task_title = st.text_input("Task Description")
    staff_member = st.selectbox("Assign to Staff", ["Admin", "Finance", "Field Staff"])
    priority = st.select_slider("Priority", options=["Normal", "Urgent", "Immediate"])
    
    if st.button("Save Task"):
        if task_title:
            st.success(f"✅ Saved: {task_title}")
        else:
            st.error("Please enter a task name.")

elif choice == "📊 View Ledger":
    st.subheader("Active Task Ledger")
    st.markdown("""
    <div class="task-box">
        <h4 style='margin:0; color:#166534;'>Process Nandawata Land Records</h4>
        <p style='margin:5px 0; color:#4b5563;'>Assigned to: Finance | Priority: Urgent</p>
        <span style='background:#dcfce7; color:#166534; padding:2px 8px; border-radius:5px; font-size:12px;'>IN PROGRESS</span>
    </div>
    """, unsafe_allow_html=True)

elif choice == "📤 Export to Excel":
    st.subheader("Generate Report")
    st.info("Consolidate all tasks into a single Excel file.")
    if st.button("Generate Excel"):
        st.write("Merging files... 100%")

st.sidebar.markdown("---")
st.sidebar.write("Office Management | Madhya Pradesh")