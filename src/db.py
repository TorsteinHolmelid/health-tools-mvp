import os
from supabase import create_client, Client
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def get_db_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

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
    client.auth.sign_out()
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
