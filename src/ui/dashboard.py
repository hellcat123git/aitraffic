"""
dashboard.py — AI-Traffic Smart City Orchestrator
High-fidelity Streamlit dashboard for real-time SUMO simulation monitoring.

Launch:
    streamlit run src/ui/dashboard.py
"""

import os
import sys
import json
import time
import threading
import datetime

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI-Traffic | Smart City Orchestrator",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT_DIR         = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LIVE_JSON        = os.path.join(ROOT_DIR, "sumo", "output", "live_metrics.json")
BENCHMARK_JSON   = os.path.join(ROOT_DIR, "sumo", "output", "benchmark_summary.json")
BENCHMARK_CSV    = os.path.join(ROOT_DIR, "benchmark_report.csv")

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap');

  html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
  }

  /* Dark gradient background */
  .stApp {
    background: linear-gradient(135deg, #0a0e1a 0%, #0d1530 50%, #0a1628 100%);
  }

  /* KPI cards */
  .kpi-card {
    background: linear-gradient(145deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02));
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 16px;
    padding: 20px 24px;
    text-align: center;
    backdrop-filter: blur(10px);
    margin-bottom: 12px;
    transition: transform 0.2s ease;
  }
  .kpi-card:hover { transform: translateY(-2px); }

  .kpi-label {
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: rgba(255,255,255,0.45);
    margin-bottom: 6px;
  }
  .kpi-value {
    font-size: 2.4rem;
    font-weight: 800;
    line-height: 1.1;
    color: #ffffff;
  }
  .kpi-unit  { font-size: 14px; font-weight: 400; color: rgba(255,255,255,0.5); margin-left: 4px; }
  .kpi-delta-pos { font-size: 13px; color: #22c55e; font-weight: 600; }
  .kpi-delta-neg { font-size: 13px; color: #f43f5e; font-weight: 600; }

  /* Mode badge */
  .badge-ai   { background:#1d4ed8; color:#fff; padding:3px 12px; border-radius:20px; font-size:12px; font-weight:700; }
  .badge-base { background:#374151; color:#ccc; padding:3px 12px; border-radius:20px; font-size:12px; font-weight:700; }
  .badge-evp  { background:#dc2626; color:#fff; padding:3px 12px; border-radius:20px; font-size:12px; font-weight:700; animation: pulse 1s infinite; }

  /* EVP pulse */
  @keyframes pulse {
    0%  { box-shadow: 0 0 0 0 rgba(220,38,38,0.7); }
    70% { box-shadow: 0 0 0 10px rgba(220,38,38,0); }
    100%{ box-shadow: 0 0 0 0   rgba(220,38,38,0); }
  }

  /* Signal light */
  .sig-light-green  { width:22px; height:22px; border-radius:50%; background:#22c55e; box-shadow: 0 0 12px #22c55e; display:inline-block; }
  .sig-light-yellow { width:22px; height:22px; border-radius:50%; background:#eab308; box-shadow: 0 0 12px #eab308; display:inline-block; }
  .sig-light-red    { width:22px; height:22px; border-radius:50%; background:#ef4444; box-shadow: 0 0 8px  #ef4444; display:inline-block; }

  /* Section headers */
  .section-title {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: rgba(255,255,255,0.35);
    margin: 18px 0 10px;
  }

  /* Comparison table */
  .cmp-table { width:100%; border-collapse:collapse; }
  .cmp-table th, .cmp-table td {
    padding: 10px 16px;
    border-bottom: 1px solid rgba(255,255,255,0.07);
    font-size: 14px;
    color: rgba(255,255,255,0.85);
  }
  .cmp-table th { font-weight:700; color:rgba(255,255,255,0.45); font-size:11px; letter-spacing:1px; }
  .cmp-win { color: #22c55e; font-weight: 700; }
  .cmp-lose{ color: #f43f5e; font-weight: 700; }

  /* Scrollbar */
  ::-webkit-scrollbar { width: 6px; }
  ::-webkit-scrollbar-track { background: #0a0e1a; }
  ::-webkit-scrollbar-thumb { background: #1d4ed8; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)


# ── Session State Init ────────────────────────────────────────────────────────
if "history" not in st.session_state:
    st.session_state.history = {
        "step": [], "co2_mg": [], "avg_wait_s": [],
        "vehicle_count": [], "timestamp": [],
    }
if "esp32_connected" not in st.session_state:
    st.session_state.esp32_connected = False
if "esp32_ser" not in st.session_state:
    st.session_state.esp32_ser = None
if "auto_refresh" not in st.session_state:
    st.session_state.auto_refresh = True
if "refresh_interval" not in st.session_state:
    st.session_state.refresh_interval = 2


# ── Data loaders ──────────────────────────────────────────────────────────────
def load_live_metrics():
    """Load the latest SUMO metrics from JSON."""
    if not os.path.isfile(LIVE_JSON):
        return None
    try:
        with open(LIVE_JSON, "r") as f:
            data = json.load(f)
        # Append to history
        h = st.session_state.history
        h["step"].append(data.get("step", 0))
        h["co2_mg"].append(data.get("co2_mg", 0))
        h["avg_wait_s"].append(data.get("avg_wait_s", 0))
        h["vehicle_count"].append(data.get("vehicle_count", 0))
        h["timestamp"].append(datetime.datetime.now().strftime("%H:%M:%S"))
        # Keep last 120 samples
        for k in h:
            if len(h[k]) > 120:
                h[k] = h[k][-120:]
        return data
    except Exception:
        return None


def load_benchmark():
    """Load benchmark summary JSON if available."""
    if not os.path.isfile(BENCHMARK_JSON):
        return None
    try:
        with open(BENCHMARK_JSON, "r") as f:
            return json.load(f)
    except Exception:
        return None


def load_benchmark_csv():
    """Load benchmark CSV timeseries if available."""
    if not os.path.isfile(BENCHMARK_CSV):
        return None
    try:
        return pd.read_csv(BENCHMARK_CSV)
    except Exception:
        return None


# ── ESP32 helper ──────────────────────────────────────────────────────────────
def esp32_connect(port: str, baud: int):
    try:
        import serial
        ser = serial.Serial(port, baud, timeout=1)
        time.sleep(2)
        st.session_state.esp32_ser = ser
        st.session_state.esp32_connected = True
        return True, "Connected"
    except Exception as e:
        st.session_state.esp32_connected = False
        return False, str(e)


def esp32_send(cmd: str):
    ser = st.session_state.esp32_ser
    if ser and ser.is_open:
        try:
            ser.write((cmd + "\n").encode())
            return True
        except Exception:
            pass
    return False


def esp32_disconnect():
    ser = st.session_state.esp32_ser
    if ser:
        try:
            ser.close()
        except Exception:
            pass
    st.session_state.esp32_ser = None
    st.session_state.esp32_connected = False


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🚦 AI-Traffic Control")
    st.markdown("---")

    # Auto-refresh
    st.markdown('<div class="section-title">Dashboard Settings</div>', unsafe_allow_html=True)
    auto_refresh = st.toggle("Auto-Refresh", value=st.session_state.auto_refresh, key="auto_toggle")
    st.session_state.auto_refresh = auto_refresh
    if auto_refresh:
        refresh_int = st.slider("Refresh Interval (s)", 1, 10, value=st.session_state.refresh_interval)
        st.session_state.refresh_interval = refresh_int

    st.markdown("---")
    st.markdown('<div class="section-title">ESP32 Hardware Control</div>', unsafe_allow_html=True)

    esp32_enabled = st.toggle("Enable ESP32 Serial", value=False, key="esp32_toggle")

    if esp32_enabled:
        col_port, col_baud = st.columns(2)
        with col_port:
            esp_port = st.text_input("COM Port", value="COM5", key="esp_port")
        with col_baud:
            esp_baud = st.selectbox("Baud", [115200, 9600, 57600], index=0, key="esp_baud")

        if not st.session_state.esp32_connected:
            if st.button("Connect", type="primary", key="esp_connect_btn"):
                ok, msg = esp32_connect(esp_port, int(esp_baud))
                if ok:
                    st.success(f"Connected to {esp_port}")
                else:
                    st.error(f"Failed: {msg}")
        else:
            st.success(f"Connected: {esp_port}")
            st.markdown("**Send Command:**")
            cmd_col1, cmd_col2 = st.columns(2)
            with cmd_col1:
                if st.button("S1 GREEN", key="esp_s1g"):  esp32_send("S1_GREEN")
                if st.button("S2 GREEN", key="esp_s2g"):  esp32_send("S2_GREEN")
            with cmd_col2:
                if st.button("ALL RED",  key="esp_allr"): esp32_send("ALL_RED")
                if st.button("Disconnect", key="esp_disc"): esp32_disconnect(); st.rerun()
    else:
        if st.session_state.esp32_connected:
            esp32_disconnect()

    st.markdown("---")
    st.markdown('<div class="section-title">Simulation Hints</div>', unsafe_allow_html=True)
    st.caption("Run benchmark:\n```\npython run_benchmark.py --steps 1000\n```")
    st.caption("Launch AI mode:\n```\npython run_smart_city.py --no-gui\n```")

    st.markdown("---")
    st.caption(f"Last update: {datetime.datetime.now().strftime('%H:%M:%S')}")


# ── Main Content ──────────────────────────────────────────────────────────────
# Header
st.markdown("""
<div style="display:flex; align-items:center; gap:16px; margin-bottom:8px;">
  <div>
    <h1 style="margin:0; font-size:2rem; font-weight:800; color:#fff;">
      🚦 AI-Traffic <span style="color:#3b82f6;">Smart City</span> Orchestrator
    </h1>
    <p style="margin:4px 0 0; color:rgba(255,255,255,0.45); font-size:14px;">
      Real-time SUMO Simulation · EVP · CO2 Analytics · ESP32 Hardware Bridge
    </p>
  </div>
</div>
""", unsafe_allow_html=True)

# Load data
metrics = load_live_metrics()
benchmark = load_benchmark()

# Status bar
if metrics:
    mode_label = metrics.get("mode", "ai")
    evp = metrics.get("evp_active", False)
    evp_road = metrics.get("evp_road", "")
    sim_step = metrics.get("step", 0)

    mode_badge = (
        f'<span class="badge-evp">🚑 EVP ACTIVE — {evp_road.upper()}</span>'
        if evp else
        (f'<span class="badge-ai">AI-OPTIMIZED</span>' if "ai" in mode_label else f'<span class="badge-base">BASELINE</span>')
    )
    st.markdown(
        f'<div style="display:flex;gap:10px;align-items:center;margin-bottom:18px;">'
        f'{mode_badge} '
        f'<span style="color:rgba(255,255,255,0.4);font-size:13px;">Step {sim_step}</span>'
        f'<span style="color:rgba(255,255,255,0.25);font-size:13px;">|</span>'
        f'<span style="color:#22c55e;font-size:13px;">● LIVE</span>'
        f'</div>',
        unsafe_allow_html=True
    )
else:
    st.markdown(
        '<div style="margin-bottom:18px;">'
        '<span style="color:rgba(255,255,255,0.35);font-size:13px;">○ Waiting for simulation data… '
        f'(<code>{LIVE_JSON}</code>)</span></div>',
        unsafe_allow_html=True
    )

# ── KPI Row ───────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Live Performance Metrics</div>', unsafe_allow_html=True)
k1, k2, k3, k4 = st.columns(4)

co2_val    = metrics.get("co2_mg", 0) if metrics else 0
wait_val   = metrics.get("avg_wait_s", 0) if metrics else 0
evp_val    = metrics.get("emergency_resp_s", -1) if metrics else -1
veh_cnt    = metrics.get("vehicle_count", 0) if metrics else 0

with k1:
    st.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-label">Cumulative CO₂</div>
      <div class="kpi-value">{co2_val:,.0f}<span class="kpi-unit">mg</span></div>
      <div class="kpi-delta-neg">{'Simulation active' if metrics else '—'}</div>
    </div>""", unsafe_allow_html=True)

with k2:
    color_cls = "kpi-delta-pos" if wait_val < 10 else "kpi-delta-neg"
    label = "Low wait ✓" if wait_val < 10 else "High congestion"
    st.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-label">Avg Wait Time</div>
      <div class="kpi-value">{wait_val:.1f}<span class="kpi-unit">s</span></div>
      <div class="{color_cls}">{label if metrics else '—'}</div>
    </div>""", unsafe_allow_html=True)

with k3:
    evp_display = f"{evp_val:.1f}" if evp_val >= 0 else "—"
    st.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-label">EVP Response Time</div>
      <div class="kpi-value">{evp_display}<span class="kpi-unit">s</span></div>
      <div class="kpi-delta-pos">{'EVP Logged' if evp_val >= 0 else 'No event yet'}</div>
    </div>""", unsafe_allow_html=True)

with k4:
    st.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-label">Active Vehicles</div>
      <div class="kpi-value">{veh_cnt}</div>
      <div class="kpi-delta-pos">{'In simulation' if metrics else '—'}</div>
    </div>""", unsafe_allow_html=True)

# ── Live Map Row ──────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Live Intersection Map</div>', unsafe_allow_html=True)
if metrics and "positions" in metrics and metrics["positions"]:
    pos_data = metrics["positions"] # [[x, y, type], ...]
    df_pos = pd.DataFrame(pos_data, columns=["x", "y", "type"])
    
    # Custom colors for vehicle types
    color_map = {
        "passenger": "#3b82f6", # Blue
        "emergency": "#ef4444", # Red
        "bus": "#10b981",       # Green
        "truck": "#f59e0b"      # Amber
    }
    df_pos["color"] = df_pos["type"].map(lambda x: color_map.get(x, "#94a3b8"))

    fig_map = px.scatter(
        df_pos, x="x", y="y", color="type",
        color_discrete_map=color_map,
        range_x=[-250, 250], range_y=[-250, 250],
        title="Real-time Vehicle Positions"
    )
    fig_map.update_traces(marker=dict(size=10, opacity=0.8, line=dict(width=1, color='white')))
    fig_map.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.03)",
        font=dict(color="rgba(255,255,255,0.6)"),
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis=dict(showgrid=False, zeroline=True, zerolinecolor="rgba(255,255,255,0.1)"),
        yaxis=dict(showgrid=False, zeroline=True, zerolinecolor="rgba(255,255,255,0.1)"),
        height=500,
        showlegend=True
    )
    # Add intersection lines
    fig_map.add_shape(type="line", x0=-250, y0=0, x1=250, y1=0, line=dict(color="rgba(255,255,255,0.05)", width=20))
    fig_map.add_shape(type="line", x0=0, y0=-250, x1=0, y1=250, line=dict(color="rgba(255,255,255,0.05)", width=20))
    
    st.plotly_chart(fig_map, use_container_width=True)
else:
    st.info("Awaiting spatial data for intersection map...")

# ── Time-series charts ────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Real-Time Telemetry</div>', unsafe_allow_html=True)
chart_left, chart_right = st.columns(2)

h = st.session_state.history
steps_x = h["step"]

with chart_left:
    if steps_x:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=steps_x, y=h["co2_mg"],
            fill="tozeroy",
            line=dict(color="#3b82f6", width=2.5),
            fillcolor="rgba(59,130,246,0.15)",
            name="CO₂ (mg)",
        ))
        fig.update_layout(
            title=dict(text="Cumulative CO₂ Emissions (mg)", font=dict(size=13, color="rgba(255,255,255,0.7)")),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(255,255,255,0.03)",
            font=dict(color="rgba(255,255,255,0.6)"),
            margin=dict(l=10, r=10, t=40, b=10),
            xaxis=dict(showgrid=False, title="Step"),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
            height=260,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("CO₂ chart will appear once simulation starts.")

with chart_right:
    if steps_x:
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=steps_x, y=h["avg_wait_s"],
            fill="tozeroy",
            line=dict(color="#f59e0b", width=2.5),
            fillcolor="rgba(245,158,11,0.12)",
            name="Avg Wait (s)",
        ))
        fig2.update_layout(
            title=dict(text="Average Vehicle Wait Time (s)", font=dict(size=13, color="rgba(255,255,255,0.7)")),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(255,255,255,0.03)",
            font=dict(color="rgba(255,255,255,0.6)"),
            margin=dict(l=10, r=10, t=40, b=10),
            xaxis=dict(showgrid=False, title="Step"),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
            height=260,
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Wait time chart will appear once simulation starts.")

# ── Benchmark CSV time-series ─────────────────────────────────────────────────
bcsv = load_benchmark_csv()
if bcsv is not None:
    st.markdown('<div class="section-title">Benchmark: Baseline vs AI-Optimized</div>', unsafe_allow_html=True)

    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(
        x=bcsv["step"], y=bcsv["baseline_co2_mg"],
        name="Baseline CO₂",
        line=dict(color="#f43f5e", width=2),
        fill="tozeroy", fillcolor="rgba(244,63,94,0.10)",
    ))
    fig3.add_trace(go.Scatter(
        x=bcsv["step"], y=bcsv["ai_co2_mg"],
        name="AI-Optimized CO₂",
        line=dict(color="#22c55e", width=2),
        fill="tozeroy", fillcolor="rgba(34,197,94,0.10)",
    ))
    fig3.update_layout(
        title=dict(text="CO₂ Emission Comparison (mg)", font=dict(size=13, color="rgba(255,255,255,0.7)")),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.03)",
        font=dict(color="rgba(255,255,255,0.6)"),
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis=dict(showgrid=False, title="Step"),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
        legend=dict(bgcolor="rgba(0,0,0,0)", x=0.01, y=0.99),
        height=300,
    )
    st.plotly_chart(fig3, use_container_width=True)

    # Wait time comparison
    fig4 = go.Figure()
    fig4.add_trace(go.Scatter(
        x=bcsv["step"], y=bcsv["baseline_avg_wait_s"],
        name="Baseline Wait",
        line=dict(color="#f43f5e", width=2, dash="dot"),
    ))
    fig4.add_trace(go.Scatter(
        x=bcsv["step"], y=bcsv["ai_avg_wait_s"],
        name="AI Wait",
        line=dict(color="#22c55e", width=2),
    ))
    fig4.update_layout(
        title=dict(text="Average Wait Time Comparison (s)", font=dict(size=13, color="rgba(255,255,255,0.7)")),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.03)",
        font=dict(color="rgba(255,255,255,0.6)"),
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis=dict(showgrid=False, title="Step"),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
        legend=dict(bgcolor="rgba(0,0,0,0)", x=0.01, y=0.99),
        height=260,
    )
    st.plotly_chart(fig4, use_container_width=True)

# ── Judges' Report ────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Judges\' Benchmark Report</div>', unsafe_allow_html=True)

if benchmark:
    bj = benchmark
    co2_pct  = bj.get("co2_improvement_pct", 0)
    wait_pct = bj.get("wait_improvement_pct", 0)

    j1, j2, j3 = st.columns(3)

    with j1:
        sign = "+" if co2_pct > 0 else ""
        cls  = "kpi-delta-pos" if co2_pct > 0 else "kpi-delta-neg"
        st.markdown(f"""
        <div class="kpi-card">
          <div class="kpi-label">CO₂ Reduction AI vs Baseline</div>
          <div class="kpi-value" style="color:#22c55e;">{sign}{co2_pct:.1f}<span class="kpi-unit">%</span></div>
          <div style="font-size:12px;color:rgba(255,255,255,0.4);margin-top:8px;">
            Baseline: {bj.get('baseline_co2_mg',0):,.0f} mg &nbsp;→&nbsp; AI: {bj.get('ai_co2_mg',0):,.0f} mg
          </div>
        </div>""", unsafe_allow_html=True)

    with j2:
        sign2 = "+" if wait_pct > 0 else ""
        st.markdown(f"""
        <div class="kpi-card">
          <div class="kpi-label">Wait Time Reduction</div>
          <div class="kpi-value" style="color:#22c55e;">{sign2}{wait_pct:.1f}<span class="kpi-unit">%</span></div>
          <div style="font-size:12px;color:rgba(255,255,255,0.4);margin-top:8px;">
            Baseline: {bj.get('baseline_avg_wait_s',0):.2f}s &nbsp;→&nbsp; AI: {bj.get('ai_avg_wait_s',0):.2f}s
          </div>
        </div>""", unsafe_allow_html=True)

    with j3:
        evp_ai   = bj.get("ai_evp_response_s", -1)
        evp_base = bj.get("baseline_evp_response_s", -1)
        evp_ai_d   = f"{evp_ai:.1f}s"   if evp_ai >= 0   else "—"
        evp_base_d = f"{evp_base:.1f}s" if evp_base >= 0 else "—"
        st.markdown(f"""
        <div class="kpi-card">
          <div class="kpi-label">EVP Response Time</div>
          <div class="kpi-value" style="color:#f59e0b;">{evp_ai_d}</div>
          <div style="font-size:12px;color:rgba(255,255,255,0.4);margin-top:8px;">
            AI-optimized &nbsp;|&nbsp; Baseline: {evp_base_d}
          </div>
        </div>""", unsafe_allow_html=True)

    # Detailed comparison table
    st.markdown("""
    <table class="cmp-table">
      <thead>
        <tr><th>Metric</th><th>Baseline</th><th>AI-Optimized</th><th>Improvement</th></tr>
      </thead>
      <tbody>
    """ + f"""
        <tr>
          <td>CO₂ Emissions (mg)</td>
          <td class="cmp-lose">{bj.get('baseline_co2_mg',0):,.0f}</td>
          <td class="cmp-win">{bj.get('ai_co2_mg',0):,.0f}</td>
          <td class="cmp-win">+{co2_pct:.1f}%</td>
        </tr>
        <tr>
          <td>Avg Wait Time (s)</td>
          <td class="cmp-lose">{bj.get('baseline_avg_wait_s',0):.2f}</td>
          <td class="cmp-win">{bj.get('ai_avg_wait_s',0):.2f}</td>
          <td class="cmp-win">+{wait_pct:.1f}%</td>
        </tr>
        <tr>
          <td>Steps Simulated</td>
          <td>{bj.get('steps_run',0)}</td>
          <td>{bj.get('steps_run',0)}</td>
          <td>—</td>
        </tr>
    """ + """
      </tbody>
    </table>
    """, unsafe_allow_html=True)

    # Download buttons
    st.markdown("<br>", unsafe_allow_html=True)
    dl1, dl2 = st.columns(2)
    with dl1:
        st.download_button(
            "⬇ Download Benchmark JSON",
            data=json.dumps(bj, indent=2),
            file_name="benchmark_summary.json",
            mime="application/json",
        )
    with dl2:
        if bcsv is not None:
            st.download_button(
                "⬇ Download Benchmark CSV",
                data=bcsv.to_csv(index=False),
                file_name="benchmark_report.csv",
                mime="text/csv",
            )
else:
    st.info(
        "No benchmark data yet. Run the parallel benchmark to populate this section:\n\n"
        "```bash\npython run_benchmark.py --steps 1000\n```"
    )

# ── Live Feed Section ─────────────────────────────────────────────────────────
st.markdown("---")
st.markdown('<div class="section-title">Live Feed</div>', unsafe_allow_html=True)
feed_col, info_col = st.columns([2, 1])

with feed_col:
    if metrics and metrics.get("evp_active"):
        st.error(f"🚑 EMERGENCY VEHICLE PREEMPTION ACTIVE — Road: **{metrics.get('evp_road','').upper()}**")

    st.markdown("""
    <div style="
      background: rgba(255,255,255,0.03);
      border: 1px dashed rgba(255,255,255,0.12);
      border-radius: 12px;
      height: 240px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      color: rgba(255,255,255,0.35);
      font-size: 14px;
      gap: 10px;
    ">
      <div style="font-size: 3rem;">🎥</div>
      <div><strong>SUMO Simulation Mode</strong></div>
      <div style="font-size:12px;">Launch with <code>--gui</code> flag for visual traffic simulation</div>
      <div style="font-size:12px;">Switch to <code>--mode video</code> for YOLOv8 live camera feed</div>
    </div>
    """, unsafe_allow_html=True)

with info_col:
    st.markdown("**System Mode**")
    st.markdown("""
    | Mode | Status |
    |------|--------|
    | SUMO Simulation | 🟢 Active |
    | YOLOv8 Detection | ⚪ Standby |
    | ESP32 Hardware | {} |
    | EVP Sensor | 🟢 Monitoring |
    """.format("🟢 Connected" if st.session_state.esp32_connected else "🔴 Offline"))

    if metrics:
        approaches = {k: metrics.get(k, 0) for k in ("north","south","east","west") if k in metrics}
        if any(v > 0 for v in approaches.values()):
            st.markdown("**Intersection Load**")
            for road, cnt in approaches.items():
                bar = "█" * min(cnt, 20) + "░" * max(0, 20-cnt)
                st.markdown(f"`{road.upper()}` {bar} {cnt}")

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    '<div style="text-align:center;color:rgba(255,255,255,0.2);font-size:11px;">'
    'AI-Traffic Smart City Orchestrator · Powered by SUMO TraCI + YOLOv8 + Streamlit'
    '</div>',
    unsafe_allow_html=True
)

# ── Auto-refresh & Heartbeat ──────────────────────────────────────────────────
if st.session_state.auto_refresh:
    # Send heartbeat to ESP32 if connected
    if st.session_state.esp32_connected:
        esp32_send("OK")
    
    time.sleep(st.session_state.refresh_interval)
    st.rerun()
