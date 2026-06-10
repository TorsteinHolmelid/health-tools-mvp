import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import uuid
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta, timezone
from db import get_db_client, get_user_history, has_premium_access

# --- Sidekonfigurasjon ---
st.set_page_config(
    page_title="My Progress",
    page_icon="📈",
    layout="centered",
)

# --- Brukar-ID ---
if "user_id" not in st.session_state:
    st.session_state["user_id"] = str(uuid.uuid4())
user_id = st.session_state["user_id"]

# --- Sjekk premium (både database og mellombels session) ---
db = get_db_client()
_unlocked_session = st.session_state.get("report_unlocked", False)
_unlocked_db = has_premium_access(db, user_id)
is_premium = _unlocked_session or _unlocked_db

st.markdown("# 📈 My Progress")

if not is_premium:
    st.warning("This is a premium feature. Please upgrade to see your progress charts.")
    st.link_button("Unlock for 4.99 USD", "https://buy.stripe.com/fZu00kbeq6J50LsdYk1Fe02")
    st.stop()

# --- Hent data ---
history = get_user_history(db, user_id)
if not history:
    st.info("No measurements saved yet. Go to the main page and calculate your health metrics first.")
    st.stop()

df = pd.DataFrame(history)
df["created_at"] = pd.to_datetime(df["created_at"], utc=True)
df = df.sort_values("created_at").reset_index(drop=True)

# Sikre at kolonnar finst
for col in ["weight", "bmi", "vo2max", "bio_age", "weekly_activity_minutes", "resting_hr"]:
    if col not in df.columns:
        df[col] = None
    df[col] = pd.to_numeric(df[col], errors="coerce")

# --- Tidfilter ---
option = st.select_slider("Time range", ["Last 30 days", "Last 90 days", "Last year", "All time"])
days_map = {"Last 30 days": 30, "Last 90 days": 90, "Last year": 365, "All time": None}
days = days_map[option]
now_utc = datetime.now(timezone.utc)
if days:
    cutoff = now_utc - timedelta(days=days)
    df = df[df["created_at"] >= cutoff]

if df.empty:
    st.warning("No data in selected time range.")
    st.stop()

st.metric("Number of measurements", len(df))

# --- Vis BMI (sidan du har BMI-data) ---
if "bmi" in df.columns and df["bmi"].notna().any():
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["created_at"], y=df["bmi"], mode="lines+markers", name="BMI"))
    fig.update_layout(title="BMI over time", xaxis_title="Date", yaxis_title="BMI")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.caption("No BMI data available.")

st.success("More charts (BMI, VO2max, etc.) can be added the same way.")
