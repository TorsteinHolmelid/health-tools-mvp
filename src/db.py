import streamlit as st
from supabase import create_client, Client
from datetime import datetime

@st.cache_resource
def get_db_client() -> Client:
    # Denne linjen er nå fjernet for at appen skal se fin ut
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    
    return create_client(url, key)

def save_health_metrics(db, user_id, metrics):
    # Eksempel: hent ut numeriske / flate verdiar frå results
    bmi_val = (metrics.get("bmi") or {}).get("value")
    bio_age_val = (metrics.get("bio_age") or {}).get("value")

    data = {
        "user_id": user_id,
        "weight": metrics.get("weight"),        # antatt numerisk i metrics
        "bmi": bmi_val,                         # send tal, ikkje sub-dict
        "bio_age": bio_age_val                  # send tal, ikkje sub-dict
        # Hvis Supabase har ein DEFAULT for created_at, LA DET VÆRE — ikkje legg det her.
    }

    # Fjern debug-utskrift (st.write) slik at testen ikkje forstyrrar produksjon.
    try:
        return db.table("health_metrics").insert(data).execute()
    except Exception:
        import logging
        logging.exception("Could not save health_metrics")
        # re-raise eller returner feilkode avhengig av korleis du vil handtere det:
        raise
def get_health_history(db, user_id):
    """Hentar historikk for graf-visning."""
    return db.table("health_metrics") \
        .select("*") \
        .eq("user_id", user_id) \
        .order("created_at", desc=False) \
        .execute()
