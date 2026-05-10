# src/calculators.py (minimal test version)
def bmi_calc(weight_kg: float, height_cm: float):
    height_m = height_cm / 100.0
    return round(weight_kg / (height_m ** 2), 2), "TestCategory"

COMMON_SYMPTOMS = ["fever", "cough"]
DEFAULT_RED_FLAGS = {"chest pain"}
