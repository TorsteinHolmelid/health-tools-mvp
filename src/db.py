import streamlit as st
from supabase import create_client, Client

# Vi brukar @st.cache_resource for at appen ikkje skal koble til 
# databasen på nytt kvar gong brukaren trykker på ein knapp (effektivitet)
@st.cache_resource
def get_db_client() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)
