import os
import streamlit as st
from supabase import create_client, Client

# Hent konfigurasjon – støttar både lokalt (os.getenv) og Streamlit Cloud (st.secrets)
def get_supabase_url() -> str:
    try:
        # På Streamlit Cloud
        return st.secrets["SUPABASE_URL"]
    except:
        # Lokalt (frå .env eller miljøvariabel)
        return os.getenv("SUPABASE_URL", "")

def get_supabase_key() -> str:
    try:
        return st.secrets["SUPABASE_KEY"]
    except:
        return os.getenv("SUPABASE_KEY", "")

def get_db_client() -> Client:
    url = get_supabase_url()
    key = get_supabase_key()
    if not url or not key:
        raise Exception("Supabase credentials missing. Set SUPABASE_URL and SUPABASE_KEY in .env (lokalt) or Streamlit secrets (cloud).")
    return create_client(url, key)

def get_current_user_id() -> str:
    """Hent ID-en til den innlogga brukaren frå Streamlit session_state"""
    return st.session_state.get("user_id", None)

def is_authenticated() -> bool:
    """Sjekk om brukaren er innlogga"""
    return st.session_state.get("authenticated", False)

def sign_up(email: str, password: str):
    """Registrer ny brukar"""
    client = get_db_client()
    try:
        response = client.auth.sign_up({"email": email, "password": password})
        return response.user, None
    except Exception as e:
        return None, str(e)

def sign_in(email: str, password: str):
    """Logg inn eksisterande brukar"""
    client = get_db_client()
    try:
        response = client.auth.sign_in_with_password({"email": email, "password": password})
        return response.user, None
    except Exception as e:
        return None, str(e)

def sign_out():
    """Logg ut"""
    client = get_db_client()
    try:
        client.auth.sign_out()
    except:
        pass
    st.session_state["authenticated"] = False
    st.session_state["user_id"] = None

def save_health_metrics(db: Client, weight: float, bmi: float, vo2max: float, 
                        bio_age: float, weekly_activity_minutes: float, resting_hr: float):
    """Lagrar helsedata for innlogga brukar"""
    user_id = get_current_user_id()
    if not user_id:
        raise Exception("Ikkje innlogga")
    
    data = {
        "user_id": user_id,
        "weight": weight,
        "bmi": bmi,
        "vo2max": vo2max,
        "bio_age": bio_age,
        "weekly_activity_minutes": weekly_activity_minutes,
        "resting_hr": resting_hr,
    }
    return db.table("health_metrics").insert(data).execute()

def get_user_history(db: Client):
    """Hent historikk for innlogga brukar"""
    user_id = get_current_user_id()
    if not user_id:
        return []
    
    response = db.table("health_metrics").select("*").eq("user_id", user_id).order("created_at").execute()
    return response.data

def has_premium_access(db: Client) -> bool:
    """Sjekk om innlogga brukar har premium"""
    user_id = get_current_user_id()
    if not user_id:
        return False
    
    response = db.table("premium_access").select("*").eq("user_id", user_id).execute()
    return len(response.data) > 0

def save_premium_access(db: Client, stripe_session_id: str):
    """Lagrar premium-tilgang for innlogga brukar"""
    user_id = get_current_user_id()
    if not user_id:
        raise Exception("Ikkje innlogga")
    
    data = {
        "user_id": user_id,
        "stripe_session_id": stripe_session_id,
    }
    return db.table("premium_access").insert(data).execute()
