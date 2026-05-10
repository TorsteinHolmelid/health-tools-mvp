# app.py (Innhold til å lime inn)
import streamlit as st
from io import BytesIO
from datetime import datetime
import calculators
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

st.set_page_config(page_title="Helse-App MVP", layout="centered")
st.title("Helse & Trening MVP")
st.warning("Educational tool — Ikkje eit medisinsk diagnoseverktøy.")

step = st.sidebar.radio("Navigasjon", ("Vitals", "Livsstil", "Symptom", "Resultat"))

if "data" not in st.session_state:
    st.session_state["data"] = {}

def get_pdf(context):
    buf = BytesIO()
    p = canvas.Canvas(buf, pagesize=A4)
    p.drawString(100, 800, f"Helsereport - {datetime.now().strftime('%d.%m.%Y')}")
    p.drawString(100, 780, f"BMI: {context['bmi']} ({context['bmi_cat']})")
    p.drawString(100, 760, f"Bioalder (Estimat): {context['bio_age']} år")
    p.drawString(100, 740, f"Triage: {context['advice']}")
    p.showPage()
    p.save()
    return buf.getvalue()

if step == "Vitals":
    st.header("1. Grunnleggande info")
    age = st.number_input("Alder罩", 0, 120, 30)
    sex = st.selectbox("Kjønn", ["M", "F"])
    h = st.number_input("Høgde (cm)", 50, 250, 175)
    w = st.number_input("Vekt (kg)", 20, 300, 75)
    st.session_state.data.update({"age": age, "sex": sex, "h": h, "w": w})

elif step == "Livsstil":
    st.header("2. Livsstil")
    smoker = st.checkbox("Røyker du?")
    activity = st.select_slider("Aktivitetsnivå", ["low", "medium", "high"])
    diabetes = st.checkbox("Har du diabetes?")
    st.session_state.data.update({"smoker": smoker, "activity": activity, "diabetes": diabetes})

elif step == "Symptom":
    st.header("3. Symptom-velger")
    symp = st.multiselect("Velg symptom", ["Brystsmerter", "Feber", "Hodepine", "Alvorlig tungpust", "Kvalme"])
    st.session_state.data["symptoms"] = symp

elif step == "Resultat":
    st.header("4. Analyse")
    d = st.session_state.data
    if "h" in d:
        bmi, cat = calculators.bmi_calc(d['w'], d['h'])
        bio = calculators.estimate_biological_age(d['age'], d['smoker'], bmi, d['activity'], d['diabetes'])
        adv_lvl, msg = calculators.triage_decision(d.get('symptoms', []), d)
        
        st.metric("Din BMI", f"{bmi}", cat)
        st.metric("Bio-alder (estimat)", f"{bio} år")
        
        if adv_lvl == "Emergency":
            st.error(msg)
        else:
            st.info(f"Råd: {msg}")
            
        pdf = get_pdf({"bmi": bmi, "bmi_cat": cat, "bio_age": bio, "advice": msg})
        st.download_button("Last ned PDF-rapport", pdf, "rapport.pdf", "application/pdf")
    else:
        st.write("Vennligst fyll ut vitals først.")
