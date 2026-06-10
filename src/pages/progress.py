import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import uuid
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta, timezone
from db import get_db_client, get_user_history, has_premium_access

st.set_page_config(page_title="My Progress", page_icon="📈", layout="centered")

if "user_id" not in st.session_state:
    st.session_state["user_id"] = str(uuid.uuid4())
user_id = st.session_state["user_id"]

db = get_db_client()
is_premium = has_premium_access(db, user_id)

st.markdown("# 📈 My Progress")

if not is_premium:
    st.warning("Premium feature. Please upgrade.")
    st.link_button("Unlock for 4.99 USD", "https://buy.stripe.com/fZu00kbeq6J50LsdYk1Fe02")
    st.stop()

history = get_user_history(db, user_id)
if not history:
    st.info("No measurements yet. Go to main page and calculate.")
    st.stop()

df = pd.DataFrame(history)
df["created_at"] = pd.to_datetime(df["created_at"], utc=True)
df = df.sort_values("created_at").reset_index(drop=True)

for col in ["weight", "bmi", "vo2max", "bio_age", "weekly_activity_minutes", "resting_hr"]:
    if col not in df.columns:
        df[col] = None
    df[col] = pd.to_numeric(df[col], errors="coerce")

option = st.select_slider("Time range", ["Last 30 days", "Last 90 days", "Last year", "All time"])
days_map = {"Last 30 days": 30, "Last 90 days": 90, "Last year": 365, "All time": None}
days = days_map[option]
now_utc = datetime.now(timezone.utc)
if days:
    cutoff = now_utc - timedelta(days=days)
    df = df[df["created_at"] >= cutoff]

if df.empty:
    st.warning("No data in selected range.")
    st.stop()

st.metric("Number of measurements", len(df))

def plot_metric(col, title, unit, color):
    if col in df.columns and df[col].notna().any():
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["created_at"], y=df[col], mode="lines+markers", name=unit, line=dict(color=color)))
        fig.update_layout(title=title, xaxis_title="Date", yaxis_title=unit)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption(f"No {title.lower()} data available.")

c1, c2 = st.columns(2)
with c1:
    plot_metric("weight", "Weight", "kg", "#3B82F6")
    plot_metric("vo2max", "VO2max", "ml/kg/min", "#22C55E")
with c2:
    plot_metric("bmi", "BMI", "", "#0EA5A3")
    plot_metric("bio_age", "Biological age", "years", "#EC4899")

c3, c4 = st.columns(2)
with c3:
    plot_metric("weekly_activity_minutes", "Weekly activity", "min", "#F59E0B")
with c4:
    plot_metric("resting_hr", "Resting heart rate", "bpm", "#F97316")
