import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta, timezone
from html import escape
from db import (
    get_db_client, get_user_history, has_premium_access,
    is_authenticated, sign_out, get_user_profile, set_user_password,
    get_supabase_url, get_supabase_key,
)

# --- Page config ---
st.set_page_config(
    page_title="My Progress · MyHealthTools",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# --- Shared CSS (mirrors app.py) ---
st.markdown("""
<style>
:root {
  --bg0: #060B14;
  --bg1: #0A1220;
  --bg2: #0F1A2E;
  --stroke: rgba(255,255,255,0.07);
  --text: #E5E7EB;
  --muted: #94A3B8;
  --muted2: #64748B;
  --accent: #0EC8C4;
  --radius: 14px;
}

/* Sidebar */
[data-testid="stSidebar"] {
  background: rgba(6,11,20,0.97) !important;
  border-right: 1px solid var(--stroke) !important;
}
[data-testid="stSidebar"] > div:first-child { background: transparent !important; }
[data-testid="stSidebarContent"] { background: transparent !important; }

/* Header og toolbar: synleg og på plass */
header[data-testid="stHeader"] {
  background: transparent !important;
  height: 3.5rem !important;
  overflow: visible !important;
  pointer-events: none !important;
}
[data-testid="stAppToolbar"] {
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  right: 0 !important;
  height: 3.5rem !important;
  z-index: 999998 !important;
  pointer-events: none !important;
  display: flex !important;
  align-items: center !important;
}

/* Sidebar-toggle — støttar nytt og gamalt Streamlit */
[data-testid="stExpandSidebarButton"],
[data-testid="stBaseButton-headerNoPadding"],
[data-testid="collapsedControl"],
button[kind="headerNoPadding"] {
  display: flex !important;
  visibility: visible !important;
  opacity: 1 !important;
  pointer-events: all !important;
  background: #0EC8C4 !important;
  border-radius: 50% !important;
  width: 2.5rem !important;
  height: 2.5rem !important;
  box-shadow: 0 0 16px rgba(14,200,196,0.6) !important;
  position: fixed !important;
  top: 0.75rem !important;
  left: 0.75rem !important;
  z-index: 999999 !important;
  border: none !important;
  cursor: pointer !important;
  align-items: center !important;
  justify-content: center !important;
}
[data-testid="stExpandSidebarButton"] svg,
[data-testid="stBaseButton-headerNoPadding"] svg,
[data-testid="collapsedControl"] svg {
  fill: #020F0F !important;
  color: #020F0F !important;
}

/* User card */
.ht-side-card {
  background: linear-gradient(160deg, rgba(14,165,163,0.08), rgba(15,23,42,0.9));
  border: 1px solid var(--stroke);
  border-radius: var(--radius);
  padding: 16px;
  margin: 1rem 0;
  box-shadow: 0 8px 24px rgba(0,0,0,.25);
}
.ht-side-user { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.ht-side-avatar {
  width: 36px; height: 36px; border-radius: 50%;
  background: linear-gradient(135deg, #0EA5A3, #0F766E);
  display: flex; align-items: center; justify-content: center;
  font-weight: 700; color: white; font-size: 0.95rem; flex-shrink: 0;
}
.ht-side-user-info { display: flex; flex-direction: column; min-width: 0; }
.ht-side-user-email {
  font-size: 0.8rem; font-weight: 600; color: var(--text);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.ht-side-user-status { font-size: 0.7rem; color: #34D399; }
.ht-side-divider { height: 1px; background: var(--stroke); border: none; margin: 12px 0; }
.ht-side-feature {
  display: flex; align-items: flex-start; gap: 8px;
  font-size: 0.75rem; color: var(--muted2); margin-bottom: 6px; line-height: 1.4;
}
.ht-side-feature:last-child { margin-bottom: 0; }

/* Buttons */
.stButton > button {
  border-radius: 40px !important;
  font-weight: 600 !important;
  font-size: 0.9rem !important;
  transition: all 0.2s ease !important;
}
.stButton > button[data-testid="baseButton-primary"] {
  background: linear-gradient(135deg, #0EC8C4, #0A9997) !important;
  color: #ffffff !important;
  border: 0 !important;
  box-shadow: 0 0 30px rgba(14,200,196,0.3) !important;
  text-shadow: 0 1px 2px rgba(0,0,0,0.4) !important;
}

/* App background */
.stApp {
  background: radial-gradient(ellipse 80vw 60vh at 10% -10%, rgba(14,200,196,0.07) 0%, transparent 60%),
              radial-gradient(ellipse 60vw 50vh at 90% 100%, rgba(59,130,246,0.06) 0%, transparent 55%),
              var(--bg0);
  color: var(--text);
}
</style>
""", unsafe_allow_html=True)

# --- Bevar widget-keys frå hovudsida ---
if is_authenticated():
    _db_preserve = get_db_client()
    _profile = get_user_profile(_db_preserve)
    if _profile:
        for _k, _v in _profile.items():
            if _k not in st.session_state:
                st.session_state[_k] = _v

# --- Sidebar ---
_logged_in = is_authenticated()

if _logged_in:
    st.sidebar.button("Log out", on_click=sign_out)

    _user_email = st.session_state.get("user_email", "")
    _avatar_letter = (_user_email[0].upper() if _user_email else "U")

    st.sidebar.markdown(
        f"""
<div class="ht-side-card">
  <div class="ht-side-user">
    <div class="ht-side-avatar">{_avatar_letter}</div>
    <div class="ht-side-user-info">
      <div class="ht-side-user-email">{escape(_user_email)}</div>
      <div class="ht-side-user-status">● Logged in</div>
    </div>
  </div>
  <hr class="ht-side-divider">
  <div class="ht-side-feature">🔒 256-bit encryption</div>
  <div class="ht-side-feature">🛡️ GDPR · no third parties</div>
  <div class="ht-side-feature">🔐 Your data — always yours alone</div>
</div>
""",
        unsafe_allow_html=True,
    )

    if not st.session_state.get("password_just_set", False):
        with st.sidebar.expander("🔑 Set a password (optional)", expanded=False):
            st.caption("Set a password so you can log in directly next time without an email link.")
            _new_pw = st.text_input("New password", type="password", key="prog_set_pw_input")
            _new_pw_confirm = st.text_input("Confirm password", type="password", key="prog_set_pw_confirm")
            if st.button("Save password", key="prog_set_pw_button"):
                if not _new_pw or len(_new_pw) < 6:
                    st.error("Password must be at least 6 characters.")
                elif _new_pw != _new_pw_confirm:
                    st.error("Passwords don't match.")
                else:
                    _pw_user, _pw_err = set_user_password(_new_pw)
                    if _pw_err:
                        st.error(f"Could not set password: {_pw_err}")
                    else:
                        st.session_state["password_just_set"] = True
                        st.success("✅ Password set!")
                        st.rerun()
    else:
        st.sidebar.success("✅ Password set for next time.")

    st.sidebar.markdown("---")
    st.sidebar.page_link("app.py", label="⬅️ Back to main page")

else:
    st.sidebar.markdown(
        """
<div style="padding:12px 0 8px 0;">
  <div style="font-size:13px;font-weight:700;color:#E5E7EB;margin-bottom:4px;">🔐 Log in / Sign up</div>
  <div style="font-size:12px;color:#9CA3AF;">Log in to view your progress.</div>
</div>
""",
        unsafe_allow_html=True,
    )

# --- Innloggingssjekk ---
if not _logged_in:
    st.warning("You must be logged in to see your progress.")
    st.info("Please go back to the main page and log in first.")
    st.page_link("app.py", label="⬅️ Go to main page", icon="🏠")
    st.stop()

# --- DB + premium check ---
db = get_db_client()
_unlocked_session = st.session_state.get("report_unlocked", False)
_unlocked_db = has_premium_access(db)
is_premium = _unlocked_session or _unlocked_db

st.markdown("# 📈 My Progress")

if not is_premium:
    st.warning("This is a premium feature. Please upgrade to see your progress charts.")
    if st.button("🔓 Unlock full report — 4.99 USD", type="primary", use_container_width=True):
        _uid = st.session_state.get("user_id", "")
        _email = st.session_state.get("user_email", "")
        _supabase_url = get_supabase_url()
        _anon_key = get_supabase_key()
        _fn_url = f"{_supabase_url}/functions/v1/stripe-checkout"
        try:
            import requests as _requests
            _resp = _requests.post(
                _fn_url,
                json={"user_id": _uid, "email": _email},
                headers={
                    "apikey": _anon_key,
                    "Authorization": f"Bearer {_anon_key}",
                    "Content-Type": "application/json",
                },
                timeout=10,
            )
            _data = _resp.json()
            if "url" in _data:
                components.html(
                    f"""
                    <script>
                    (function() {{
                        try {{
                            const doc = window.top.document;
                            let box = doc.getElementById("checkoutRedirectBox");
                            if (!box) {{
                                box = doc.createElement("div");
                                box.id = "checkoutRedirectBox";
                                box.style.cssText = "position:fixed;top:0;left:0;right:0;z-index:999999;padding:16px;background:#0EA5A3;text-align:center;font-family:sans-serif;";
                                doc.body.prepend(box);
                            }}
                            box.innerHTML = '<a href="{_data["url"]}" style="color:#fff;font-weight:700;font-size:16px;text-decoration:none;">💳 Click here to continue to payment &rarr;</a>';
                            try {{ window.top.location.href = "{_data["url"]}"; }} catch (e) {{}}
                        }} catch (e) {{ console.error(e); }}
                    }})();
                    </script>
                    """,
                    height=0,
                )
                st.info("💳 Click the green bar at the top of the page to continue to payment.")
            else:
                st.error("Could not create payment session.")
        except Exception as _e:
            st.error(f"Payment error: {_e}")
    st.stop()

# --- Hent data ---
history = get_user_history(db)
if not history:
    st.info("No measurements saved yet. Go to the main page and calculate your health metrics first.")
    st.page_link("app.py", label="⬅️ Go to main page", icon="🏠")
    st.stop()

df = pd.DataFrame(history)
df["created_at"] = pd.to_datetime(df["created_at"], utc=True)
df = df.sort_values("created_at").reset_index(drop=True)

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
st.markdown("---")

def plot_metric(df, col, title, unit, color, ref_line=None, ref_label=""):
    if col in df.columns and df[col].notna().any():
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df["created_at"], y=df[col],
            mode="lines+markers", name=unit,
            line=dict(color=color, width=2),
            marker=dict(size=6)
        ))
        if ref_line is not None:
            fig.add_hline(
                y=ref_line, line_dash="dot",
                line_color="rgba(148,163,184,0.5)",
                annotation_text=ref_label,
                annotation_font_color="#64748B",
            )
        fig.update_layout(
            title=dict(text=title, font=dict(color="#E5E7EB")),
            xaxis_title="Date", yaxis_title=unit,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#94A3B8"),
            xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
            yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption(f"No {title.lower()} data available yet.")

c1, c2 = st.columns(2)
with c1:
    plot_metric(df, "weight", "Weight", "kg", "#3B82F6")
with c2:
    plot_metric(df, "bmi", "BMI", "", "#0EA5A3", ref_line=25.0, ref_label="Overweight threshold")

c3, c4 = st.columns(2)
with c3:
    plot_metric(df, "vo2max", "VO₂max", "ml/kg/min", "#22C55E")
with c4:
    plot_metric(df, "bio_age", "Biological age", "years", "#EC4899")

c5, c6 = st.columns(2)
with c5:
    plot_metric(df, "weekly_activity_minutes", "Weekly activity", "min", "#F59E0B",
                ref_line=150.0, ref_label="WHO goal: 150 min")
with c6:
    plot_metric(df, "resting_hr", "Resting heart rate", "bpm", "#F97316",
                ref_line=60.0, ref_label="Good: ≤60 bpm")

st.markdown("---")
st.caption("Measurements are saved each time you calculate on the main page. Log in to keep your data across devices.")
