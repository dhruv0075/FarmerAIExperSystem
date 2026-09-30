from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from services.suitability_service import get_crop_knowledge

# Agronomically verified nutrient compositions
FERTILIZER_DATABASE = {
    "nitrogen": [
        {
            "name": "Neem Coated Urea",
            "composition": "46% N",
            "n_pct": 46.0,
            "p_pct": 0.0,
            "k_pct": 0.0,
            "s_pct": 0.0,
            "category": "Inorganic / Standard",
            "best_for": "General vegetative top dressing across cereals, cotton, sugarcane",
            "precautions": "Incorporate immediately; avoid applying before heavy rainfall to minimize leaching.",
        },
        {
            "name": "Ammonium Sulphate",
            "composition": "20.5% N, 24% S",
            "n_pct": 20.5,
            "p_pct": 0.0,
            "k_pct": 0.0,
            "s_pct": 24.0,
            "category": "Inorganic / Acid-forming",
            "best_for": "Alkaline/calcareous soils and sulfur-loving crops (oilseeds, pulses, onion)",
            "precautions": "Equivalent ratio: 1 kg Urea ≈ 2.24 kg Ammonium Sulphate.",
        },
        {
            "name": "Calcium Ammonium Nitrate (CAN)",
            "composition": "25% N, 8% Ca",
            "n_pct": 25.0,
            "p_pct": 0.0,
            "k_pct": 0.0,
            "s_pct": 0.0,
            "category": "Inorganic / Neutral",
            "best_for": "Acidic soils, horticultural crops, fruits needing calcium",
            "precautions": "Equivalent ratio: 1 kg Urea ≈ 1.84 kg CAN.",
        },
    ],
    "phosphorus": [
        {
            "name": "Di-Ammonium Phosphate (DAP)",
            "composition": "18% N, 46% P2O5",
            "n_pct": 18.0,
            "p_pct": 46.0,
            "k_pct": 0.0,
            "s_pct": 0.0,
            "category": "Inorganic / Complex",
            "best_for": "Basal application at sowing for vigorous root proliferation",
            "precautions": "Place 3-5 cm below seed; contains 18% starter Nitrogen.",
        },
        {
            "name": "Single Super Phosphate (SSP)",
            "composition": "16% P2O5, 11% S, 19% Ca",
            "n_pct": 0.0,
            "p_pct": 16.0,
            "k_pct": 0.0,
            "s_pct": 11.0,
            "category": "Inorganic / Straight P",
            "best_for": "Oilseeds, pulses, and groundnut where sulfur and calcium boost oil content",
            "precautions": "Equivalent ratio: 1 kg DAP ≈ 2.87 kg SSP (plus add supplemental basal N).",
        },
        {
            "name": "Triple Super Phosphate (TSP)",
            "composition": "46% P2O5",
            "n_pct": 0.0,
            "p_pct": 46.0,
            "k_pct": 0.0,
            "s_pct": 0.0,
            "category": "Inorganic / Concentrated",
            "best_for": "Direct substitution of DAP when additional nitrogen is undesirable",
            "precautions": "Direct 1:1 phosphorus equivalent to DAP without the ammoniacal nitrogen.",
        },
    ],
    "potassium": [
        {
            "name": "Muriate of Potash (MOP / KCl)",
            "composition": "60% K2O, 47% Cl",
            "n_pct": 0.0,
            "p_pct": 0.0,
            "k_pct": 60.0,
            "s_pct": 0.0,
            "category": "Inorganic / Standard Potash",
            "best_for": "Paddy, wheat, maize, cotton, sugarcane",
            "precautions": "Contains chloride; avoid for chloride-sensitive crops like grapes, tobacco, and potato.",
        },
        {
            "name": "Sulphate of Potash (SOP / K2SO4)",
            "composition": "50% K2O, 17.5% S",
            "n_pct": 0.0,
            "p_pct": 0.0,
            "k_pct": 50.0,
            "s_pct": 17.5,
            "category": "Inorganic / Premium Potash",
            "best_for": "Chloride-sensitive fruits: grapes, banana, pomegranate, citrus, potato",
            "precautions": "Equivalent ratio: 1 kg MOP ≈ 1.2 kg SOP. Excellent fruit quality enhancer.",
        },
    ],
    "organic": [
        {
            "name": "Well-Decomposed Farm Yard Manure (FYM)",
            "composition": "0.5% N, 0.2% P, 0.5% K + Organic Carbon",
            "category": "Organic Manure",
            "best_for": "Soil structure improvement, microbial activity, long-term soil moisture retention",
            "precautions": "Incorporate 2-3 weeks before sowing during primary tillage.",
        },
        {
            "name": "Vermicompost",
            "composition": "1.5% N, 1.0% P, 1.5% K + Micronutrients & Humic Acid",
            "category": "Bio-Organic",
            "best_for": "High-value horticulture, seed beds, orchard ring application",
            "precautions": "Confirm composition and application rate with a local soil-test recommendation.",
        },
    ],
}


def analyze_nutrients_and_advise(
    crop_name: str,
    crop_stage: str,
    soil: Dict[str, Any],
    weather: Dict[str, Any],
    activity_history: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Evaluates soil N-P-K levels against crop agronomic benchmarks and returns
    nutrient condition (Low/Adequate/High), timing recommendations, weather-aware warnings,
    and agronomically valid alternative fertilizer sources with exact compositions.
    """
    if any(soil.get(k) is None for k in ('nitrogen', 'phosphorus', 'potassium', 'ph')):
        return {
            "crop_name": crop_name, "crop_stage": crop_stage,
            "soil_analysis": {k: {"value": soil.get(k), "status": "UNKNOWN", "optimal": []} for k in ('nitrogen', 'phosphorus', 'potassium', 'ph')},
            "timing_guidance": "Obtain a soil test before choosing fertilizer. Nutrient sufficiency is unknown.",
            "advisories": [], "recommendations": [], "organic_supplements": [],
            "safe_usage_disclaimer": "No dosage can be established without a verified local recommendation.",
        }
    crop_info = get_crop_knowledge(crop_name)
    opt = crop_info.get("optimal_ranges", {})

    n_val = float(soil.get("nitrogen", soil.get("N", 60)) or 0)
    p_val = float(soil.get("phosphorus", soil.get("P", 40)) or 0)
    k_val = float(soil.get("potassium", soil.get("K", 40)) or 0)
    ph_val = float(soil.get("ph", 6.5) or 0)

    n_opt = opt.get("N", [50, 90])
    p_opt = opt.get("P", [30, 60])
    k_opt = opt.get("K", [30, 60])

    def _eval_level(val: float, bounds: List[float]) -> str:
        if val < bounds[0]:
            return "LOW"
        if val > bounds[1]:
            return "HIGH"
        return "ADEQUATE"

    n_status = _eval_level(n_val, n_opt)
    p_status = _eval_level(p_val, p_opt)
    k_status = _eval_level(k_val, k_opt)

    # Check recent fertilizer activity
    activity_history = activity_history or []
    recent_fert = False
    hours_ago = None
    for act in activity_history:
        if act.get("status") == "COMPLETED" and "fertiliz" in str(act.get("activity_type", "")).lower():
            comp_at = act.get("completed_at")
            if comp_at:
                try:
                    dt = datetime.fromisoformat(comp_at.replace("Z", "+00:00"))
                    diff = (datetime.now(timezone.utc) - dt).total_seconds() / 3600.0
                    if diff < 168.0:  # 7 days
                        recent_fert = True
                        hours_ago = round(diff, 1)
                        break
                except Exception:
                    pass

    # Check upcoming rain forecast (next 48h)
    forecast = weather.get("forecast", [])
    rain_next_48h = sum(float(d.get("precipitation", 0.0) or 0.0) for d in forecast[:2])
    max_rain_prob_48h = max([float(d.get("rain_probability", 0.0) or 0.0) for d in forecast[:2]] or [0.0])
    rain_postpone = rain_next_48h > 15.0 or max_rain_prob_48h > 75.0

    advisories = []
    timing_guidance = ""

    if recent_fert:
        advisories.append({
            "type": "RECENT_APPLICATION",
            "level": "INFO",
            "title": "Recent Fertilizer Application Recorded",
            "message": f"A fertilizer task was completed {hours_ago} hours ago. Allow 7-10 days for root uptake before evaluating deficiency or repeating application.",
        })
    elif rain_postpone:
        advisories.append({
            "type": "WEATHER_RESTRICTION",
            "level": "WARNING",
            "title": "Postpone Fertilizer Application (Rain Approaching)",
            "message": f"Rainfall ({rain_next_48h:.1f} mm, {max_rain_prob_48h:.0f}% probability) is forecast over the next 48 hours. Postpone surface broadcast of Urea or DAP to prevent leaching and surface runoff.",
        })
    else:
        # Stage-specific guidance
        stage_lower = crop_stage.lower()
        if "sow" in stage_lower or "seedling" in stage_lower or "emergence" in stage_lower or "basal" in stage_lower:
            timing_guidance = "Discuss basal nutrition with a local agronomist using your soil test; no application rate is established here."
        elif "tillering" in stage_lower or "vegetative" in stage_lower:
            timing_guidance = "Optimal timing for 1st top dressing: Apply split dose of Nitrogen (Neem Coated Urea) to promote tillering and leafy vigor."
        elif "flower" in stage_lower or "panicle" in stage_lower or "silking" in stage_lower:
            timing_guidance = "Optimal timing for 2nd top dressing: Apply balance Nitrogen and foliar spray of Potassium Nitrate (13:0:45) to enhance flowering and grain setting."
        elif "fruit" in stage_lower or "grain filling" in stage_lower:
            timing_guidance = "Nutrient focus: Apply potassium fertigation (0:0:50) to enhance fruit sizing, weight, and sugar accumulation. Avoid high nitrogen."
        else:
            timing_guidance = "Maintain soil organic matter and monitor crop canopy color for nutrient balancing."

    # Identify primary and alternative fertilizers
    recommendations_list = []
    if n_status == "LOW" and not recent_fert:
        recommendations_list.append({
            "nutrient": "Nitrogen (N)",
            "status": "Deficient",
            "observed_value": f"{n_val} kg/ha (Optimal: {n_opt[0]}-{n_opt[1]})",
            "primary": FERTILIZER_DATABASE["nitrogen"][0],
            "alternatives": FERTILIZER_DATABASE["nitrogen"][1:],
            "dosage_note": "Apply split dose as per state agricultural university package of practices. Avoid over-application.",
        })

    if p_status == "LOW" and not recent_fert:
        recommendations_list.append({
            "nutrient": "Phosphorus (P2O5)",
            "status": "Deficient",
            "observed_value": f"{p_val} kg/ha (Optimal: {p_opt[0]}-{p_opt[1]})",
            "primary": FERTILIZER_DATABASE["phosphorus"][0],
            "alternatives": FERTILIZER_DATABASE["phosphorus"][1:],
            "dosage_note": "Apply as basal placement near the root zone. SSP is preferred for sulfur-demanding pulses and oilseeds.",
        })

    if k_status == "LOW" and not recent_fert:
        # If crop is grapes, potato, banana, fruit: recommend SOP over MOP
        is_fruit_crop = crop_info.get("category", "").startswith("Fruit") or crop_name.lower() in ["grapes", "banana", "potato"]
        primary_k = FERTILIZER_DATABASE["potassium"][1] if is_fruit_crop else FERTILIZER_DATABASE["potassium"][0]
        alt_k = [FERTILIZER_DATABASE["potassium"][0]] if is_fruit_crop else [FERTILIZER_DATABASE["potassium"][1]]

        recommendations_list.append({
            "nutrient": "Potassium (K2O)",
            "status": "Deficient",
            "observed_value": f"{k_val} kg/ha (Optimal: {k_opt[0]}-{k_opt[1]})",
            "primary": primary_k,
            "alternatives": alt_k,
            "dosage_note": f"Potassium improves disease resistance and water stress tolerance. {'SOP is recommended to avoid chloride toxicity.' if is_fruit_crop else 'MOP is cost-effective for general field crops.'}",
        })

    if not recommendations_list and not recent_fert:
        recommendations_list.append({
            "nutrient": "Balanced Maintenance",
            "status": "Adequate",
            "observed_value": f"N: {n_val}, P: {p_val}, K: {k_val} kg/ha",
            "primary": FERTILIZER_DATABASE["organic"][1],
            "alternatives": [FERTILIZER_DATABASE["organic"][0]],
            "dosage_note": "Soil test levels are currently balanced. Maintain soil fertility through organic compost additions and biofertilizers.",
        })

    return {
        "crop_name": crop_name,
        "crop_stage": crop_stage,
        "soil_analysis": {
            "nitrogen": {"value": n_val, "status": n_status, "optimal": n_opt},
            "phosphorus": {"value": p_val, "status": p_status, "optimal": p_opt},
            "potassium": {"value": k_val, "status": k_status, "optimal": k_opt},
            "ph": {"value": ph_val, "status": "OPTIMAL" if 6.0 <= ph_val <= 7.5 else "SUB-OPTIMAL"},
        },
        "timing_guidance": timing_guidance,
        "advisories": advisories,
        "recommendations": recommendations_list,
        "organic_supplements": [],
        "safe_usage_disclaimer": "Dosage recommendations are agronomic planning guidelines based on Indian Council of Agricultural Research (ICAR) benchmarks. Consult your local Krishi Vigyan Kendra (KVK) or official soil health card recommendations for precise field calibration.",
    }
