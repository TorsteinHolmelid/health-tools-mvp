# src/calculators.py
"""
Enkle helse- og energi-kalkulatorer brukt i Health Tools MVP.

Inneholder:
- bmr_mifflin: Basal Metabolic Rate (Mifflin-St Jeor)
- tdee_from_activity_factor: TDEE uten spesifikke treningskcal (aktivitetfaktor)
- calories_burned_from_mets: kcal fra MET-aktivitet
- weekly_exercise_calories: summerer ukentlige treningskcal
- tdee_including_weekly_exercise: TDEE + gjennomsnittlig treningskcal per dag
- bmi: Body Mass Index og kategori
- vo2_percentile_from_ref: prosentil (normal-tilnærming)
"""

from math import erf, sqrt


def bmr_mifflin(age: float, sex: str, weight_kg: float, height_cm: float) -> float:
    """
    Beregn BMR med Mifflin-St Jeor.
    sex: 'M' eller 'F' (case-insensitive)
    Returnerer BMR i kcal/day (float).
    """
    s = str(sex).strip().upper()
    if s.startswith("M"):
        return 10.0 * weight_kg + 6.25 * height_cm - 5.0 * age + 5.0
    else:
        return 10.0 * weight_kg + 6.25 * height_cm - 5.0 * age - 161.0


def tdee_from_activity_factor(bmr: float, activity_level: str) -> float:
    """
    Returnerer TDEE (kcal/day) ved bruk av vanlig aktivitetsfaktor.
    activity_level: en av 'sedentary','light','moderate','very','extra'
    """
    factors = {
        'sedentary': 1.2,    # little/no exercise
        'light': 1.375,      # 1-3 days/week
        'moderate': 1.55,    # 3-5 days/week
        'very': 1.725,       # 6-7 days/week
        'extra': 1.9         # very intense daily
    }
    f = factors.get(str(activity_level).lower(), 1.2)
    return bmr * f


def calories_burned_from_mets(weight_kg: float, met: float, minutes: float) -> float:
    """
    Estimerer kalorier forbrent basert på MET-verdi.
    Formel: kcal/min = MET * 3.5 * vekt_kg / 200
    Returnerer totalt kcal for økta (float).
    """
    if minutes <= 0 or met <= 0 or weight_kg <= 0:
        return 0.0
    kcal_per_min = met * 3.5 * weight_kg / 200.0
    return kcal_per_min * minutes


def weekly_exercise_calories(weight_kg: float, workouts: list) -> float:
    """
    Summér ukentlig kaloriforbrenning fra en liste med treningsøkter.
    workouts: liste av dicts: { 'met': float, 'minutes': float, 'sessions_per_week': int (optional) }
    Alternative enklere bruk: send en enkelt sesjon og multiplicer utenfor (som i app.py).
    Returnerer total kcal per uke.
    """
    total = 0.0
    for w in workouts:
        met = float(w.get('met', 0.0))
        minutes = float(w.get('minutes', 0.0))
        sessions = int(w.get('sessions_per_week', 1))
        total += calories_burned_from_mets(weight_kg, met, minutes) * max(1, sessions)
    return total


def tdee_including_weekly_exercise(bmr: float, activity_level: str, weekly_exercise_kcal: float) -> float:
    """
    Kombinerer basal TDEE (aktivitetfaktor) med gjennomsnittlig daglig treningskcal.
    weekly_exercise_kcal: total kcal fra trening per uke.
    Returnerer TDEE (kcal/day) inklusive trening fordelt på daglig basis.
    """
    base = tdee_from_activity_factor(bmr, activity_level)
    add_per_day = (weekly_exercise_kcal / 7.0) if weekly_exercise_kcal > 0 else 0.0
    return base + add_per_day


# Små hjelpefunksjoner ------------------------------------------------------

def bmi(weight_kg: float, height_cm: float) -> float:
    """
    Returnerer BMI (kg/m^2).
    """
    if height_cm <= 0:
        return 0.0
    h_m = height_cm / 100.0
    return weight_kg / (h_m * h_m)


def bmi_category(bmi_value: float) -> str:
    """
    Enkel kategorisering av BMI.
    """
    if bmi_value <= 0:
        return "Unknown"
    if bmi_value < 18.5:
        return "Underweight"
    if bmi_value < 25.0:
        return "Normal"
    if bmi_value < 30.0:
        return "Overweight"
    return "Obesity"


def normal_cdf(x: float, mu: float = 0.0, sigma: float = 1.0) -> float:
    """
    Normalfordelingens CDF via feilfunksjonen (erf).
    Returnerer verdi i [0,1].
    """
    z = (x - mu) / (sigma * sqrt(2.0))
    return 0.5 * (1.0 + erf(z))


def vo2_percentile_from_ref(user_vo2: float, ref_mean: float, ref_sd: float = 6.0) -> float:
    """
    Enkel tilnærming: antar normalfordeling rundt referansemiddelverdi.
    ref_mean: gjennomsnitt VO2 for aldersband
    ref_sd: standardavvik (default ~6 ml/kg/min, juster ved behov)
    Returnerer prosentil (0-100).
    """
    pct = normal_cdf(user_vo2, ref_mean, ref_sd) * 100.0
    if pct < 0.0:
        pct = 0.0
    if pct > 100.0:
        pct = 100.0
    return pct
