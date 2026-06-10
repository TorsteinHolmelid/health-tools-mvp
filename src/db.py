import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import logging


@st.cache_resource
def get_db_client() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


def save_health_metrics(db, user_id, metrics):
    bmi_val = (metrics.get("bmi") or {}).get("value")
    bio_age_val = (metrics.get("bio_age") or {}).get("value")
    vo2_val = (metrics.get("vo2") or {}).get("value")

    # Pull exercise log data if present
    exercise_log = metrics.get("exercise_log") or {}
    weekly_activity_minutes = None
    resting_hr = None

    if isinstance(exercise_log, dict):
        weekly_activity_minutes = exercise_log.get("total_minutes")
        resting_hr = exercise_log.get("resting_hr")

    data = {
        "user_id": user_id,
        "weight": metrics.get("weight"),
        "bmi": bmi_val,
        "bio_age": bio_age_val,
        "vo2max": vo2_val,
        "weekly_activity_minutes": weekly_activity_minutes,
        "resting_hr": resting_hr,
    }

    try:
        return db.table("health_metrics").insert(data).execute()
    except Exception:
        logging.exception("Could not save health_metrics")
        raise


def get_health_history(db, user_id):
    """Fetches history for chart display (legacy name kept for compatibility)."""
    return (
        db.table("health_metrics")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=False)
        .execute()
    )


def get_user_history(db, user_id) -> list:
    """
    Returns a list of all saved measurements for the given user,
    sorted by created_at ascending. Each item is a plain dict.
    Returns [] on any error.
    """
    try:
        result = (
            db.table("health_metrics")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=False)
            .execute()
        )
        return result.data or []
    except Exception:
        logging.exception("Could not fetch user history")
        return []


def save_premium_access(db, user_id: str, stripe_session_id: str) -> bool:
    """
    Records that a user has paid and should have premium access.
    Call this after a successful Stripe session is confirmed.
    Returns True on success.
    """
    try:
        db.table("premium_access").upsert(
            {
                "user_id": user_id,
                "stripe_session_id": stripe_session_id,
                "granted_at": datetime.utcnow().isoformat(),
            },
            on_conflict="user_id",
        ).execute()
        return True
    except Exception:
        logging.exception("Could not save premium_access")
        return False


def has_premium_access(db, user_id: str) -> bool:
    """
    Returns True if this user_id has a row in the premium_access table
    (i.e. they have paid at least once).
    Falls back gracefully to False on any error.
    """
    try:
        result = (
            db.table("premium_access")
            .select("user_id")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        return bool(result.data)
    except Exception:
        logging.exception("Could not check premium_access")
        return False
