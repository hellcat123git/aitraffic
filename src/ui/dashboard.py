import sys
import os
import time
import pandas as pd
import plotly.express as px
import streamlit as st
import requests

# Add the project root to sys.path
sys.path.append(os.getcwd())

from src.utils.gemini_helper import GeminiWarden

# --- Config ---
API_URL = "http://localhost:8000/data"

st.set_page_config(page_title="AI-Traffic | Smart City Hub", layout="wide")

# Initialize Warden
if "warden" not in st.session_state:
    st.session_state.warden = GeminiWarden()

# --- Title ---
st.title("🚦 AI-Traffic: Smart City Orchestrator")
st.markdown("---")

# Data Fetching
def fetch_data():
    try:
        response = requests.get(API_URL, timeout=0.5)
        return response.json()
    except:
        return None

data = fetch_data()

# --- Sidebar (Settings) ---
st.sidebar.header("AI Traffic Warden (Gemini)")
api_key = st.sidebar.text_input("Gemini API Key:", type="password")
if api_key:
    st.session_state.warden = GeminiWarden(api_key=api_key)

user_query = st.sidebar.text_input("Ask the Warden:", placeholder="How is the traffic today?")
if user_query and data:
    with st.sidebar.spinner("Warden is thinking..."):
        response = st.session_state.warden.ask(user_query, data)
        st.sidebar.info(f"AI Response: {response}")

# --- Layout: Main Stats ---
if not data:
    st.warning("🚦 **Connecting to AI Data Hub...**")
    st.write("Ensure the API server is running on port 8000.")
    time.sleep(2)
    st.rerun()

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Total Vehicles", data["road1_count"] + data["road2_count"])
with col2:
    st.metric("CO2 Saved (kg)", data["total_co2_saved"])
with col3:
    st.metric("Active Road", f"Road {1 if data['road1_signal'] == 'GREEN' else 2}")

# --- Live Feed Simulator & Metrics ---
st.markdown("### Real-time Analysis")
c1, c2 = st.columns(2)

with c1:
    st.subheader("Road 1")
    st.progress(min(data["road1_count"] * 10, 100))
    st.write(f"Signal: **{data['road1_signal']}**")
    if data["road1_emergency"] > 0:
        st.error("!!! EMERGENCY DETECTED !!!")

with c2:
    st.subheader("Road 2")
    st.progress(min(data["road2_count"] * 10, 100))
    st.write(f"Signal: **{data['road2_signal']}**")
    if data["road2_emergency"] > 0:
        st.error("!!! EMERGENCY DETECTED !!!")

# --- Chart: Mock History ---
st.markdown("---")
st.markdown("### Historical Congestion Analysis")
chart_data = pd.DataFrame({
    "Time": ["10:00", "10:15", "10:30", "10:45", "11:00"],
    "Wait Time (Sec)": [45, 30, 15, 20, 10]
})
fig = px.line(chart_data, x="Time", y="Wait Time (Sec)", title="Avg. Wait Time Reduction")
st.plotly_chart(fig, use_container_width=True)

# --- Auto-refresh ---
time.sleep(1)
st.rerun()
