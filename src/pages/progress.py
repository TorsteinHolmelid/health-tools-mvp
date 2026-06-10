import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
from db import get_db_client, get_user_history

st.set_page_config(page_title="Progress Test")
st.write("# Progress Test")

user_id = st.session_state.get("user_id")
if not user_id:
    import uuid
    user_id = str(uuid.uuid4())
    st.session_state["user_id"] = user_id

db = get_db_client()
history = get_user_history(db, user_id)

if not history:
    st.info("Ingen data. Gå til hovudsida og lagre nokre målingar.")
else:
    df = pd.DataFrame(history)
    st.write(f"Fant {len(df)} målingar")
    st.dataframe(df.head())
