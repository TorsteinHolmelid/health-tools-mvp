import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from __future__ import annotations

import uuid
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone

try:
    from db import get_db_client, get_user_history, has_premium_access
except ImportError as e:
    st.error(f"Kunne ikkje importere db: {e}")
    st.stop()

st.set_page_config(page_title="My Progress", page_icon="📈", layout="centered")

st.markdown("# 📈 My Progress")

# Enkel test – hent data
if "user_id" not in st.session_state:
    st.session_state["user_id"] = str(uuid.uuid4())

db = get_db_client()
user_id = st.session_state["user_id"]

# Sjekk premium (midlertidig skrudd av for testing – fjern seinare)
is_premium = True  # MIDLERTIDIG – fjern når alt fungerer

if not is_premium:
    st.warning("Premium påkrevd")
    st.stop()

history = get_user_history(db, user_id)
if not history:
    st.info("Ingen data enno")
else:
    st.write(f"Fant {len(history)} målingar")
    df = pd.DataFrame(history)
    st.dataframe(df)
