from pdf2image import convert_from_bytes
from pdf_premium import create_pdf_bytes_premium as create_pdf_bytes_ultimate
from datetime import datetime, timezone

# Fyll inn realistiske testverdiar her
test_report = {
    "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    "inputs": {"age": 35, "sex": "M", "height_cm": 180, "weight_kg": 80},
    "bmi":      {"value": 24.7, "category": "Normal"},
    "bodyfat":  {"value": 18.5},
    "whr":      {"value": 0.88, "category": "Moderate risk"},
    "vo2":      {"value": 48.2, "percentile": 72, "rating": "Good",
                 "age_band": "30-39", "mean": 42.4, "tips": [], "top_descriptor": "Top 28%"},
    "bio_age":  {"value": 32.5},
    "bio_factors": [
        {"label": "Resting HR", "delta": -1.2},
        {"label": "BMI",        "delta":  0.3},
        {"label": "Sleep",      "delta": -0.8},
        {"label": "Stress",     "delta":  0.5},
    ],
    "triage": {"level": "Info", "message": "OK"},
    "triage_recommendations": ["Walk 30 min daily", "Reduce processed foods"],
    "plan": {
        "current_needs_kcal": 2400,
        "recommended_daily_kcal": 1900,
        "kg_per_week": -0.5,
        "milestones": [
            {"Week": 1,  "Projected weight (kg)": 79.5, "Focus": "Build routine"},
            {"Week": 4,  "Projected weight (kg)": 78.0, "Focus": "Maintain consistency"},
            {"Week": 8,  "Projected weight (kg)": 76.0, "Focus": "Review progress"},
            {"Week": 12, "Projected weight (kg)": 74.0, "Focus": "Re-check and set next goal"},
        ],
    },
    "exercise_log": {
        "activity": "Running/jogging", "intensity": "Moderate",
        "minutes": 45, "sessions_per_week": 3,
        "kcal_per_session": 420, "kcal_per_week": 1260,
    },
    "selected_activities": ["Running/jogging", "Strength training (weights)"],
}

pdf_bytes = create_pdf_bytes_ultimate(test_report)
pages = convert_from_bytes(pdf_bytes, dpi=150)

print(f"Antal sider: {len(pages)}")
for i, page in enumerate(pages):
    fname = f"side_{i+1:02d}.png"
    page.save(fname)
    print(f"  → {fname}  {page.size[0]}×{page.size[1]} px")
