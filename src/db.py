import streamlit as st
from supabase import create_client, Client
from datetime import datetime
# Vi brukar @st.cache_resource for at appen ikkje skal koble til 
# databasen på nytt kvar gong brukaren trykker på ein knapp (effektivitet)
@st.cache_resource
def get_db_client() -> Client:
    url = st.secrets["https://nrjanqqbjcxbmblpthtf.supabase.co"]
    key = st.secrets["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5yamFucXFiamN4Ym1ibHB0aHRmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzk4ODQzMTcsImV4cCI6MjA5NTQ2MDMxN30.AYjOImaxb_QLaJZtsDaYATZOrfcWBug85U1UokJgRSo"]
    return create_client(url, key)
# Legg til dette i db.py

def save_health_metrics(db, user_id, metrics):
    """Lagrar brukar-data til Supabase."""
    data = {
        "user_id": user_id,
        "weight": metrics.get("weight"),
        "bmi": metrics.get("bmi"),
        "bio_age": metrics.get("bio_age"),
        "created_at": datetime.utcnow().isoformat()
    }
    return db.table("health_metrics").insert(data).execute()

def get_health_history(db, user_id):
    """Hentar historikk for graf-visning."""
    return db.table("health_metrics") \
        .select("*") \
        .eq("user_id", user_id) \
        .order("created_at", desc=False) \
        .execute()
