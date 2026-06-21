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

def get_service_client() -> Client:
    """Returnerer en admin-klient med service role (full tilgang)."""
    url = get_supabase_url()
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or st.secrets.get("SUPABASE_SERVICE_ROLE_KEY")
    if not key:
        raise Exception("Service role key missing. Legg til SUPABASE_SERVICE_ROLE_KEY i secrets.")
    return create_client(url, key)

def get_db_client() -> Client:
    """Returner lagret autentisert klient hvis den finnes, ellers opprett ny (anonym)."""
    if "supabase_client" in st.session_state:
        return st.session_state["supabase_client"]
    url = get_supabase_url()
    key = get_supabase_key()
    if not url or not key:
        raise Exception("Supabase credentials missing.")
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
        st.session_state["supabase_client"] = client   # <-- LAGRE autentisert klient
        st.session_state["user_id"] = response.user.id
        st.session_state["authenticated"] = True
        st.session_state["premium_checked"] = False
        return response.user, None
    except Exception as e:
        return None, str(e)

def sign_in_with_tokens(access_token: str, refresh_token: str):
    """
    Logg inn brukeren ved hjelp av et access_token + refresh_token-par
    (f.eks. fra en magic link-redirect). Setter session_state akkurat
    som sign_in() gjør ved vanlig e-post/passord-innlogging.
    """
    url = get_supabase_url()
    key = get_supabase_key()
    if not url or not key:
        return None, "Supabase credentials missing."

    client = create_client(url, key)
    try:
        response = client.auth.set_session(access_token, refresh_token)
        st.session_state["supabase_client"] = client
        st.session_state["user_id"] = response.user.id
        st.session_state["user_email"] = response.user.email
        st.session_state["authenticated"] = True
        st.session_state["premium_checked"] = False
        return response.user, None
    except Exception as e:
        return None, str(e)

def sign_out():
    st.session_state.pop("supabase_client", None)
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

def has_premium_access(db: Client = None) -> bool:
    """
    Sjekk om innlogget bruker har premiumtilgang.
    Bruker først medfølgende db-klient (eller henter vanlig klient).
    Hvis det ikke fungerer (f.eks. uautentisert klient), fallback til service role.
    """
    user_id = get_current_user_id()
    if not user_id:
        return False

    # Prøv først med vanlig klient (autentisert eller anonym)
    try:
        client = db if db is not None else get_db_client()
        resp = client.table("premium_access").select("*").eq("user_id", user_id).execute()
        if resp.data:
            return True
    except Exception:
        pass

    # Fallback: service role (krever SUPABASE_SERVICE_ROLE_KEY i secrets)
    try:
        admin_client = get_service_client()
        resp = admin_client.table("premium_access").select("*").eq("user_id", user_id).execute()
        return len(resp.data) > 0
    except Exception as e:
        print(f"Premium fallback feilet: {e}")  # eller bruk st.error i appen
        return False

def get_user_profile(db: Client):
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
