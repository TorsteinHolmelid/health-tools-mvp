from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple


COMMON_SYMPTOMS = [
    "abdominal pain",
    "back pain",
    "blurred vision",
    "blood in urine",
    "chest pain",
    "chills",
    "confusion",
    "cough",
    "depression",
    "diarrhea",
    "difficulty swallowing",
    "dizziness",
    "ear pain",
    "anxiety",
    "eye pain",
    "fatigue",
    "fever",
    "heart racing",
    "hoarseness",
    "headache",
    "insomnia",
    "itching",
    "joint pain",
    "leg swelling",
    "loss of appetite",
    "loss of smell",
    "loss of taste",
    "memory problems",
    "muscle pain",
    "nausea",
    "neck pain",
    "nosebleed",
    "numbness",
    "palpitations",
    "rash",
    "runny nose",
    "shortness of breath",
    "sore throat",
    "sweating",
    "tingling",
    "tremor",
    "urinary frequency",
    "vomiting",
    "weakness",
    "weight loss",
    "wheezing",
]

DEFAULT_RED_FLAGS = {
    "blue lips or face",
    "chest pain",
    "difficulty breathing",
    "loss of consciousness",
    "severe bleeding",
    "severe shortness of breath",
    "sudden severe headache",
    "sudden weakness or numbness",
    "unresponsive",
}

ALL_SYMPTOMS = sorted(list(set(COMMON_SYMPTOMS) | set(DEFAULT_RED_FLAGS)))


# ----------------------------
# BMI / body composition
# ----------------------------
def bmi_calc(weight_kg: float, height_cm: float) -> Tuple[float, str]:
    if height_cm <= 0:
        raise ValueError("height_cm must be > 0")
    if weight_kg <= 0:
        raise ValueError("weight_kg must be > 0")

    height_m = height_cm / 100.0
    bmi = weight_kg / (height_m ** 2)

    if bmi < 18.5:
        category = "Underweight"
    elif bmi < 25:
        category = "Normal"
    elif bmi < 30:
        category = "Overweight"
    else:
        category = "Obesity"

    return round(bmi, 2), category


def waist_hip_ratio(waist_cm: float, hip_cm: float) -> float:
    if hip_cm <= 0:
        raise ValueError("hip_cm must be > 0")
    if waist_cm <= 0:
        raise ValueError("waist_cm must be > 0")
    return round(waist_cm / hip_cm, 2)


def whr_category(sex: str, ratio: float) -> str:
    s = str(sex).upper()
    if s == "M":
        if ratio <= 0.90:
            return "Low risk"
        elif ratio <= 0.99:
            return "Moderate risk"
        return "High risk"
    else:
        if ratio <= 0.80:
            return "Low risk"
        elif ratio <= 0.84:
            return "Moderate risk"
        return "High risk"


def body_fat_navy(
    sex: str,
    height_cm: float,
    neck_cm: float,
    waist_cm: float,
    hip_cm: Optional[float] = None,
) -> float:
    sex = str(sex).upper()

    if height_cm <= 0 or neck_cm <= 0 or waist_cm <= 0:
        raise ValueError("Body measurements must be > 0")

    if sex == "M":
        if waist_cm - neck_cm <= 0:
            raise ValueError("waist_cm must be larger than neck_cm for male Navy formula")
        denom = 1.0324 - 0.19077 * math.log10(waist_cm - neck_cm) + 0.15456 * math.log10(height_cm)
    else:
        if hip_cm is None:
            raise ValueError("hip_cm required for female Navy formula")
        if waist_cm + hip_cm - neck_cm <= 0:
            raise ValueError("Invalid body measurements for female Navy formula")
        denom = 1.29579 - 0.35004 * math.log10(waist_cm + hip_cm - neck_cm) + 0.22100 * math.log10(height_cm)

    bf = 495.0 / denom - 450.0
    return round(max(2.0, min(60.0, bf)), 1)


# ----------------------------
# VO2max
# ----------------------------
def vo2_cooper_from_distance(distance_m: float) -> float:
    if distance_m <= 0:
        raise ValueError("distance_m must be > 0")
    vo2 = (distance_m - 504.9) / 44.73
    return round(max(5.0, vo2), 1)


def vo2_rockport_1mile(
    time_min: float,
    hr_at_end: int,
    weight_kg: float,
    age: int,
    sex: str,
) -> float:
    if time_min <= 0:
        raise ValueError("time_min must be > 0")
    if hr_at_end <= 0:
        raise ValueError("hr_at_end must be > 0")
    if weight_kg <= 0:
        raise ValueError("weight_kg must be > 0")

    weight_lbs = weight_kg * 2.20462
    gender = 1 if str(sex).upper() == "M" else 0

    vo2 = (
        132.853
        - (0.0769 * weight_lbs)
        - (0.3877 * age)
        + (6.315 * gender)
        - (3.2649 * time_min)
        - (0.1565 * hr_at_end)
    )
    return round(max(5.0, vo2), 1)


def vo2_questionnaire_estimate(
    age: int,
    sex: str,
    weekly_minutes: int,
    session_intensity_score: int,
    activity_level: str,
    bmi: Optional[float] = None,
    resting_hr: Optional[int] = None,
    max_hr: Optional[int] = None,
) -> float:
    sex = str(sex).upper()
    level = str(activity_level).strip().lower()

    base = 42.0 if sex == "M" else 36.0
    age_penalty = 0.22 * max(age - 25, 0)

    level_bonus = {
        "sedentary": -5.0,
        "light": -2.0,
        "moderate": 0.0,
        "active": 3.0,
        "very active": 5.0,
        "athlete": 7.0,
    }.get(level, 0.0)

    volume_bonus = min(12.0, max(0.0, weekly_minutes) / 180.0 * 6.0)
    intensity_bonus = (session_intensity_score - 3) * 1.6

    hr_bonus = 0.0
    if resting_hr is not None and resting_hr > 0:
        if resting_hr <= 55:
            hr_bonus += 2.0
        elif resting_hr <= 65:
            hr_bonus += 1.0
        elif resting_hr >= 85:
            hr_bonus -= 2.0
        elif resting_hr >= 75:
            hr_bonus -= 1.0

    reserve_bonus = 0.0
    if resting_hr is not None and max_hr is not None and max_hr > resting_hr > 0:
        reserve = max_hr - resting_hr
        if reserve >= 120:
            reserve_bonus += 1.5
        elif reserve >= 100:
            reserve_bonus += 1.0
        elif reserve < 80:
            reserve_bonus -= 1.0

    bmi_penalty = 0.0
    if bmi is not None:
        if bmi >= 30:
            bmi_penalty = -4.0
        elif bmi >= 25:
            bmi_penalty = -2.0

    vo2 = base - age_penalty + level_bonus + volume_bonus + intensity_bonus + hr_bonus + reserve_bonus + bmi_penalty
    return round(max(5.0, vo2), 1)


def vo2_measured_value(measured_vo2: float) -> float:
    if measured_vo2 <= 0:
        raise ValueError("measured_vo2 must be > 0")
    return round(measured_vo2, 1)


VO2_REFERENCE_BANDS = [
    {"Age band": "18-29", "M mean": 46.0, "M sd": 7.0, "F mean": 39.0, "F sd": 6.0},
    {"Age band": "30-39", "M mean": 43.0, "M sd": 7.0, "F mean": 36.0, "F sd": 6.0},
    {"Age band": "40-49", "M mean": 40.0, "M sd": 6.5, "F mean": 33.0, "F sd": 5.5},
    {"Age band": "50-59", "M mean": 36.0, "M sd": 6.0, "F mean": 30.0, "F sd": 5.0},
    {"Age band": "60-69", "M mean": 32.0, "M sd": 5.5, "F mean": 27.0, "F sd": 4.8},
    {"Age band": "70+", "M mean": 29.0, "M sd": 5.0, "F mean": 24.0, "F sd": 4.5},
]


def _vo2_band_for_age(age: int) -> Dict[str, float]:
    if age < 30:
        return VO2_REFERENCE_BANDS[0]
    if age < 40:
        return VO2_REFERENCE_BANDS[1]
    if age < 50:
        return VO2_REFERENCE_BANDS[2]
    if age < 60:
        return VO2_REFERENCE_BANDS[3]
    if age < 70:
        return VO2_REFERENCE_BANDS[4]
    return VO2_REFERENCE_BANDS[5]


def vo2_reference(age: int, sex: str, vo2_value: float) -> Dict[str, float]:
    band = _vo2_band_for_age(age)
    s = str(sex).upper()
    mean = band["M mean"] if s == "M" else band["F mean"]
    sd = band["M sd"] if s == "M" else band["F sd"]

    z = (vo2_value - mean) / (sd or 1.0)
    percentile = 50.0 * (1.0 + math.erf(z / math.sqrt(2.0)))
    percentile = max(1.0, min(99.0, percentile))

    if percentile < 10:
        rating = "Very low"
    elif percentile < 25:
        rating = "Below average"
    elif percentile < 60:
        rating = "Average"
    elif percentile < 85:
        rating = "Good"
    else:
        rating = "Excellent"

    return {
        "age_band": band["Age band"],
        "mean": round(mean, 1),
        "sd": round(sd, 1),
        "zscore": round(z, 2),
        "percentile": int(round(percentile)),
        "rating": rating,
    }


def vo2_age_reference_table(sex: str) -> List[Dict[str, object]]:
    s = str(sex).upper()
    rows = []
    for band in VO2_REFERENCE_BANDS:
        mean = band["M mean"] if s == "M" else band["F mean"]
        sd = band["M sd"] if s == "M" else band["F sd"]
        rows.append(
            {
                "Age band": band["Age band"],
                "Approx. below avg": round(mean - sd, 1),
                "Approx. average": round(mean, 1),
                "Approx. good": round(mean + sd, 1),
                "Approx. excellent": round(mean + 2 * sd, 1),
            }
        )
    return rows


def vo2_improvement_tips(
    vo2_value: float,
    sex: str,
    age: int,
    activity_level: str,
    weekly_minutes: Optional[int] = None,
) -> List[str]:
    tips: List[str] = []

    level = str(activity_level).strip().lower()
    if weekly_minutes is not None and weekly_minutes < 150:
        tips.append("Build gradually toward 150–300 minutes per week of moderate-to-vigorous activity.")
    if level in {"sedentary", "light"}:
        tips.append("Add 2–4 extra brisk-walk or cycling sessions each week.")
    if vo2_value < 25:
        tips.append("Start with brisk walking, stair intervals, or cycling intervals, then increase volume slowly.")
    elif vo2_value < 35:
        tips.append("Add 1–2 interval sessions per week plus one longer steady cardio session.")
    else:
        tips.append("Use a mix of intervals, threshold work, and one longer aerobic session each week.")

    tips.append("Sleep, recovery, and progressive overload matter as much as the workouts themselves.")
    tips.append("If you have symptoms, medical issues, or chest pain, get personalized advice before increasing intensity.")

    return tips


# ----------------------------
# Biological age
# ----------------------------
def estimate_biological_age_detailed(
    age: int,
    sex: str = "M",
    smoker: bool = False,
    bmi: Optional[float] = None,
    activity_level: str = "Moderate",
    sleep_hours: Optional[float] = None,
    alcohol_units_per_week: Optional[int] = None,
    fruit_veg_servings: Optional[int] = None,
    perceived_stress: Optional[int] = None,
    grip_strength_kg: Optional[float] = None,
    bp_systolic: Optional[float] = None,
    cholesterol_mg_dl: Optional[float] = None,
    diabetes: bool = False,
    resting_hr: Optional[int] = None,
    waist_to_hip_ratio: Optional[float] = None,
    family_history: bool = False,
    menopause: bool = False,
    measured_vo2: Optional[float] = None,
) -> Tuple[int, List[Dict[str, float]]]:
    bio = float(age)
    factors: List[Dict[str, float]] = []

    def add(delta: float, label: str) -> None:
        nonlocal bio
        if delta == 0:
            return
        bio += float(delta)
        factors.append({"label": label, "delta": float(delta)})

    s = str(sex).upper()
    level = str(activity_level).strip().lower()

    if smoker:
        add(7, "Smoking status")
    if diabetes:
        add(7, "Diabetes")
    if family_history:
        add(2, "Family history of premature cardiovascular disease")

    if bmi is not None:
        if bmi >= 35:
            add(8, "BMI 35+")
        elif bmi >= 30:
            add(6, "BMI 30–34.9")
        elif bmi >= 25:
            add(2, "BMI 25–29.9")
        elif bmi < 18.5:
            add(1, "BMI under 18.5")

    activity_map = {
        "sedentary": 4,
        "light": 2,
        "moderate": 0,
        "active": -2,
        "very active": -4,
        "athlete": -5,
    }
    add(activity_map.get(level, 0), f"Activity level ({activity_level})")

    if sleep_hours is not None:
        if sleep_hours < 6:
            add(2, "Short sleep")
        elif 7 <= sleep_hours <= 9:
            add(-1, "Healthy sleep duration")
        elif sleep_hours > 10:
            add(1, "Very long sleep pattern")

    if alcohol_units_per_week is not None:
        if alcohol_units_per_week > 14:
            add(2, "High alcohol intake")
        elif alcohol_units_per_week > 7:
            add(1, "Moderate alcohol intake")
        elif alcohol_units_per_week == 0:
            add(-1, "No alcohol")

    if fruit_veg_servings is not None:
        if fruit_veg_servings >= 5:
            add(-1, "Good fruit & vegetable intake")
        elif fruit_veg_servings <= 1:
            add(1, "Low fruit & vegetable intake")

    if perceived_stress is not None:
        stress_delta = round((perceived_stress - 5) * 0.5)
        add(stress_delta, "Perceived stress")

    if grip_strength_kg is not None:
        if grip_strength_kg >= 40:
            add(-2, "Strong grip strength")
        elif grip_strength_kg < 25:
            add(1, "Low grip strength")

    if bp_systolic is not None:
        if bp_systolic >= 160:
            add(6, "High systolic BP")
        elif bp_systolic >= 140:
            add(3, "Elevated systolic BP")
        elif bp_systolic < 100:
            add(1, "Low systolic BP")

    if cholesterol_mg_dl is not None:
        if cholesterol_mg_dl >= 240:
            add(3, "High cholesterol")
        elif cholesterol_mg_dl <= 160:
            add(-1, "Favourable cholesterol")

    if resting_hr is not None:
        if resting_hr >= 90:
            add(2, "High resting heart rate")
        elif resting_hr <= 55:
            add(-1, "Low resting heart rate")

    if waist_to_hip_ratio is not None:
        if s == "M":
            if waist_to_hip_ratio > 0.95:
                add(2, "High waist-to-hip ratio")
            elif waist_to_hip_ratio > 0.90:
                add(1, "Moderately high waist-to-hip ratio")
        else:
            if waist_to_hip_ratio > 0.85:
                add(2, "High waist-to-hip ratio")
            elif waist_to_hip_ratio > 0.80:
                add(1, "Moderately high waist-to-hip ratio")

    if menopause and s == "F":
        add(1, "Post-menopausal status")

    if measured_vo2 is not None:
        if measured_vo2 >= 50:
            add(-3, "Very strong VO2max")
        elif measured_vo2 >= 45:
            add(-2, "Strong VO2max")
        elif measured_vo2 >= 35:
            add(-1, "Decent VO2max")
        elif measured_vo2 < 25:
            add(2, "Low VO2max")
        elif measured_vo2 < 20:
            add(4, "Very low VO2max")

    return int(round(bio)), factors


# ----------------------------
# Symptom triage
# ----------------------------
def triage_decision(
    selected_symptoms: List[str],
    red_flag_symptoms: Optional[set] = None,
    risk_factors: Optional[dict] = None,
) -> Tuple[str, str]:
    if red_flag_symptoms is None:
        red_flag_symptoms = DEFAULT_RED_FLAGS
    if risk_factors is None:
        risk_factors = {}

    selected_set = {str(s).strip().lower() for s in (selected_symptoms or []) if str(s).strip()}
    red_lower = {str(s).strip().lower() for s in red_flag_symptoms}

    if selected_set & red_lower:
        return "Emergency", "One or more red-flag symptoms selected. Seek emergency care immediately."

    try:
        age = int(risk_factors.get("age", 0) or 0)
    except Exception:
        age = 0

    has_comorbidity = bool(risk_factors.get("diabetes", False)) or bool(risk_factors.get("heart_disease", False))
    n = len(selected_set)

    if n >= 3 and (has_comorbidity or age >= 65):
        return "See GP", "Multiple symptoms plus risk factors — contact your primary care provider."
    if n >= 2:
        return "See GP", "Several symptoms — consider contacting a healthcare professional."
    if n == 1:
        return "Monitor/Self-care", "One symptom — monitor and seek care if it worsens."
    return "Monitor/Self-care", "No symptoms selected."


# ----------------------------
# Weight planning
# ----------------------------
def bmr_mifflin_sea(sex: str, weight_kg: float, height_cm: float, age: int) -> float:
    if str(sex).upper() == "M":
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161
    return round(bmr, 0)


def activity_factor_map(level: str) -> float:
    return {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
        "very active": 1.9,
        "athlete": 2.0,
    }.get(str(level).strip().lower(), 1.4)


def daily_calorie_needs(
    sex: str,
    weight_kg: float,
    height_cm: float,
    age: int,
    activity_level: str,
) -> int:
    bmr = bmr_mifflin_sea(sex, weight_kg, height_cm, age)
    af = activity_factor_map(activity_level)
    return int(round(bmr * af))


def generate_weight_plan(
    current_weight_kg: float,
    target_weight_kg: float,
    weeks: int,
    sex: str,
    height_cm: float,
    age: int,
    activity_level: str,
) -> Dict[str, object]:
    if weeks <= 0:
        raise ValueError("weeks must be > 0")

    delta = target_weight_kg - current_weight_kg
    kg_per_week = delta / weeks
    warning = None

    if kg_per_week < -1.0:
        warning = "Requested pace exceeds 1 kg/week weight loss. Recommendation capped to 1 kg/week for safety."
        kg_per_week = -1.0
    elif kg_per_week > 0.5:
        warning = "Requested pace exceeds 0.5 kg/week weight gain. Recommendation capped to 0.5 kg/week for safety."
        kg_per_week = 0.5

    daily_delta_kcal = kg_per_week * 7700 / 7.0
    current_needs = daily_calorie_needs(sex, current_weight_kg, height_cm, age, activity_level)
    recommended_daily = int(round(current_needs + daily_delta_kcal))

    if recommended_daily < 1200:
        warning = (warning + " " if warning else "") + "Estimated calorie target is very low; consider professional guidance."

    def milestone_focus(week: int, total_weeks: int) -> str:
        if week <= 2:
            return "Build routine"
        if week <= max(3, total_weeks // 2):
            return "Maintain consistency"
        if week < total_weeks:
            return "Review progress"
        return "Re-check and set next goal"

    if weeks <= 6:
        points = list(range(1, weeks + 1))
    else:
        points = sorted(set([1, 2, 3, max(4, weeks // 2), weeks - 2, weeks - 1, weeks]))

    milestones = []
    for w in points:
        projected = current_weight_kg + kg_per_week * w
        milestones.append(
            {
                "Week": w,
                "Projected weight (kg)": round(projected, 1),
                "Focus": milestone_focus(w, weeks),
            }
        )

    return {
        "current_needs_kcal": current_needs,
        "recommended_daily_kcal": recommended_daily,
        "kg_per_week": round(kg_per_week, 2),
        "daily_delta_kcal": int(round(daily_delta_kcal)),
        "weeks": weeks,
        "milestones": milestones,
        "warning": warning,
    }
