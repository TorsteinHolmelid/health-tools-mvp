import os
import streamlit as st
from supabase import create_client, Client

def get_supabase_url() -> str:
    try:
        return st.secrets["SUPABASE_URL"]
    except:
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
        raise Exception("Supabase credentials missing. Set SUPABASE_URL and SUPABASE_KEY in .env or Streamlit secrets.")
    return create_client(url, key)

def get_current_user_id() -> str:
    return st.session_state.get("user_id", None)

def is_authenticated() -> bool:
    return st.session_state.get("authenticated", False)

def sign_up(email: str, password: str):
    client = get_db_client()
    try:
        response = client.auth.sign_up({"email": email, "password": password})
        return response.user, None
    except Exception as e:
        return None, str(e)

def sign_in(email: str, password: str):
    client = get_db_client()
    try:
        response = client.auth.sign_in_with_password({"email": email, "password": password})
        return response.user, None
    except Exception as e:
        return None, str(e)

def sign_out():
    client = get_db_client()
    try:
        client.auth.sign_out()
    except:
        pass
    st.session_state["authenticated"] = False
    st.session_state["user_id"] = None

def save_health_metrics(db: Client, weight=None, bmi=None, vo2max=None, 
                        bio_age=None, weekly_activity_minutes=None, resting_hr=None):
    user_id = get_current_user_id()
    if not user_id:
        raise Exception("Not logged in")
    data = {
        "user_id": user_id,
        "weight": weight,
        "bmi": bmi,
        "vo2max": vo2max,
        "bio_age": bio_age,
        "weekly_activity_minutes": weekly_activity_minutes,
        "resting_hr": resting_hr,
    }
    data = {k: v for k, v in data.items() if v is not None or k == "user_id"}
    return db.table("health_metrics").insert(data).execute()

def get_user_history(db: Client):
    user_id = get_current_user_id()
    if not user_id:
        return []
    response = db.table("health_metrics").select("*").eq("user_id", user_id).order("created_at").execute()
    return response.data

def has_premium_access(db: Client) -> bool:
    user_id = get_current_user_id()
    if not user_id:
        return False
    response = db.table("premium_access").select("*").eq("user_id", user_id).execute()
    return len(response.data) > 0

def get_user_profile(db: Client):
    """Hent lagra input-verdiar (siste innstillingar) for innlogga brukar."""
    user_id = get_current_user_id()
    if not user_id:
        return None
    try:
        response = db.table("profiles").select("data").eq("user_id", user_id).execute()
    except Exception:
        return None
    if response.data:
        return response.data[0].get("data")
    return None

def save_user_profile(db: Client, data: dict):
    """Lagre/oppdater input-verdiane til innlogga brukar."""
    user_id = get_current_user_id()
    if not user_id:
        return None
    try:
        existing = db.table("profiles").select("user_id").eq("user_id", user_id).execute()
        if existing.data:
            return db.table("profiles").update({"data": data}).eq("user_id", user_id).execute()
        else:
            return db.table("profiles").insert({"user_id": user_id, "data": data}).execute()
    except Exception:
        return None

def save_premium_access(db: Client, stripe_session_id: str):
    user_id = get_current_user_id()
    if not user_id:
        raise Exception("Not logged in")
    data = {
        "user_id": user_id,
        "stripe_session_id": stripe_session_id,
    }
    return db.table("premium_access").insert(data).execute()
