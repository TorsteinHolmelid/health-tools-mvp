import math

def bmi_calc(weight_kg: float, height_cm: float):
    if height_cm <= 0:
        raise ValueError("height_cm must be > 0")
    height_m = height_cm / 100.0
    bmi = weight_kg / (height_m ** 2)
    bmi_rounded = round(bmi, 2)
    if bmi < 18.5:
        cat = "Undervekt"
    elif bmi < 25:
        cat = "Normal"
    elif bmi < 30:
        cat = "Overvekt"
    else:
        cat = "Obesitas"
    return bmi_rounded, cat

def vo2_simple_heuristic(age: int, sex: str, bmi: float, activity_level: str):
    base = 60.0 - 0.3 * (age - 20)
    sex_adj = 0 if sex.upper() == 'M' else -5.0
    if bmi < 18.5:
        bmi_adj = -2.0
    elif bmi < 25:
        bmi_adj = 0.0
    elif bmi < 30:
        bmi_adj = -3.0
    else:
        bmi_adj = -6.0
    act_map = {'low': -4.0, 'medium': 0.0, 'high': 4.0}
    act_adj = act_map.get(activity_level, 0.0)
    vo2 = base + sex_adj + bmi_adj + act_adj
    return max(5.0, round(vo2, 2))

def estimate_biological_age(age: int, smoker: bool, bmi: float, physical_activity: str, diabetes: bool=False, heart_disease: bool=False, systolic_bp: float=None):
    bio = age
    if smoker: bio += 8
    if bmi < 25: bio += 0
    elif bmi < 30: bio += 3
    else: bio += 6
    pa_map = {'low': 4, 'medium': 0, 'high': -3}
    bio += pa_map.get(physical_activity, 0)
    if diabetes: bio += 7
    if heart_disease: bio += 10
    if systolic_bp and systolic_bp >= 140: bio += 3
    return int(round(bio))

def triage_decision(selected_symptoms: list, risk_factors: dict=None):
    red_flags = {'Brystsmerter', 'Alvorlig tungpust', 'Bevissthetsendring', 'Akutt lammelse', 'Alvorlig blødning'}
    selected_set = set(selected_symptoms)
    if selected_set & red_flags:
        return "Emergency", "Kontakt nødtjeneste (113) med ein gong!"
    num = len(selected_set)
    if num >= 2 or (num >= 1 and (risk_factors.get('age', 0) > 65 or risk_factors.get('diabetes'))):
        return "See GP", "Kontakt fastlegen for ein sjekk."
    return "Monitor/Self-care", "Kvile og følg med på utviklinga."
