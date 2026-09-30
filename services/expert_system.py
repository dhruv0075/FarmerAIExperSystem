from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from services.activity_service import hours_since, latest_completed_activity


def _severity_from_risk(score: float) -> str:
    if score >= 0.8:
        return "URGENT"
    if score >= 0.6:
        return "WARNING"
    if score >= 0.4:
        return "CAUTION"
    return "INFO"


EXPERT_RULES_KNOWLEDGE_BASE = [
    {
        "id": "RULE_01",
        "name": "High Wind Spraying Restriction",
        "category": "Weather Safety",
        "condition_text": "IF current_wind is not None and wind > 25.0 km/h",
        "consequence_text": "THEN prohibit foliar spraying; issue wind drift hazard warning.",
        "priority": 1,
    },
    {
        "id": "RULE_02",
        "name": "Heavy Rain Pre-Harvest Warning",
        "category": "Harvest Protection",
        "condition_text": "IF crop_stage in ['maturity', 'harvest', 'grain filling'] AND 48h_rain_forecast > 15 mm",
        "consequence_text": "THEN issue urgent harvest weather warning; prepare emergency drainage.",
        "priority": 1,
    },
    {
        "id": "RULE_03",
        "name": "Rain Forecast Irrigation Postponement",
        "category": "Water Management",
        "condition_text": "IF rain_probability > 70% AND 3day_expected_rain > 10 mm",
        "consequence_text": "THEN delay scheduled irrigation; allow rainfall to replenish root zone.",
        "priority": 2,
    },
    {
        "id": "RULE_04",
        "name": "Recent Irrigation Lockout",
        "category": "Water Management",
        "condition_text": "IF hours_since_last_irrigation < 24.0",
        "consequence_text": "THEN do not repeat irrigation today; prevent root asphyxiation.",
        "priority": 2,
    },
    {
        "id": "RULE_05",
        "name": "Soil Moisture Deficit Irrigation Needed",
        "category": "Water Management",
        "condition_text": "IF soil_moisture < 30% AND rain_probability < 30% AND hours_since_last_irrigation >= 24",
        "consequence_text": "THEN schedule irrigation to maintain crop evapotranspiration needs.",
        "priority": 3,
    },
    {
        "id": "RULE_06",
        "name": "Fungal Microclimate Disease Risk",
        "category": "Disease Prevention",
        "condition_text": "IF current_humidity > 85% AND 16°C <= current_temp <= 30°C",
        "consequence_text": "THEN issue fungal spore proliferation warning; inspect lower leaf canopy.",
        "priority": 2,
    },
    {
        "id": "RULE_07",
        "name": "Heat Stress Warning",
        "category": "Crop Stress",
        "condition_text": "IF current_temp > 35°C AND soil_moisture < 35%",
        "consequence_text": "THEN issue heat stress alert; monitor for afternoon leaf wilting.",
        "priority": 2,
    },
    {
        "id": "RULE_08",
        "name": "Recent Fertilizer Lockout",
        "category": "Nutrient Management",
        "condition_text": "IF hours_since_last_fertilizer < 168.0 (7 days)",
        "consequence_text": "THEN withhold repeat application; allow root absorption and nutrient cycling.",
        "priority": 3,
    },
    {
        "id": "RULE_09",
        "name": "Nitrogen Deficiency Correction",
        "category": "Nutrient Management",
        "condition_text": "IF soil_nitrogen < 60 kg/ha AND hours_since_last_fertilizer >= 168.0",
        "consequence_text": "THEN recommend targeted Nitrogen top-dressing according to growth stage.",
        "priority": 4,
    },
    {
        "id": "RULE_10",
        "name": "Phosphorus Deficiency Support",
        "category": "Nutrient Management",
        "condition_text": "IF soil_phosphorus < 40 kg/ha",
        "consequence_text": "THEN recommend balanced phosphorus basal/placement support.",
        "priority": 4,
    },
    {
        "id": "RULE_11",
        "name": "Potassium Stress Defense",
        "category": "Nutrient Management",
        "condition_text": "IF soil_potassium < 50 kg/ha",
        "consequence_text": "THEN recommend potassium supplementation for cellular turgor and pest defense.",
        "priority": 4,
    },
]


def evaluate_expert_system(
    crop: str,
    crop_stage: str,
    weather: Dict[str, Any],
    soil: Dict[str, Any],
    forecast: Optional[List[Dict[str, Any]]] = None,
    activity_history: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Executes a formal Forward Chaining Inference Engine:
    1. Asserts working facts from sensors, APIs, farm records, and activity confirmations.
    2. Matches knowledge base IF-THEN rules against asserted facts.
    3. Performs Conflict Resolution (e.g. Irrigation Needed vs Rain Approaching).
    4. Fires triggered rules and derives conclusion advisories.
    Returns complete forward-chaining trace suitable for viva examination and academic defense.
    """
    forecast = forecast or weather.get("forecast", [])
    activity_history = activity_history or []

    # 1. Assert Working Memory Facts
    curr = weather.get("current", {})
    temp = float(curr["temperature"]) if curr.get("temperature") is not None else None
    humidity = float(curr["humidity"]) if curr.get("humidity") is not None else None
    wind = float(curr["wind_speed"]) if curr.get("wind_speed") is not None else None
    rain_prob = float(curr["rain_probability"]) if curr.get("rain_probability") is not None else None

    rain_next_48h = sum(float(d.get("precipitation", 0.0) or 0.0) for d in forecast[:2])
    rain_next_3d = sum(float(d.get("precipitation", 0.0) or 0.0) for d in forecast[:3])
    max_rain_prob_3d = max([float(d.get("rain_probability", 0.0) or 0.0) for d in forecast[:3]] or [0.0])

    soil_n = float(soil["nitrogen"]) if soil.get("nitrogen") is not None else None
    soil_p = float(soil["phosphorus"]) if soil.get("phosphorus") is not None else None
    soil_k = float(soil["potassium"]) if soil.get("potassium") is not None else None
    soil_moist = soil.get("moisture")
    moist_val = float(soil_moist) if soil_moist is not None else None

    last_irr = latest_completed_activity(activity_history, "Irrigation")
    last_fert = latest_completed_activity(activity_history, "Fertilizer")
    irr_age = hours_since(last_irr.get("completed_at")) if last_irr else None
    fert_age = hours_since(last_fert.get("completed_at")) if last_fert else None

    facts = {
        "crop": crop,
        "crop_stage": crop_stage,
        "current_temperature_c": temp,
        "current_humidity_pct": humidity,
        "current_wind_speed_kmh": wind,
        "current_rain_prob_pct": rain_prob,
        "forecast_rain_next_48h_mm": round(rain_next_48h, 1),
        "forecast_rain_next_3d_mm": round(rain_next_3d, 1),
        "max_rain_probability_3d": round(max_rain_prob_3d, 1),
        "soil_nitrogen_kgha": soil_n,
        "soil_phosphorus_kgha": soil_p,
        "soil_potassium_kgha": soil_k,
        "soil_moisture_pct": moist_val,
        "hours_since_last_irrigation": round(irr_age, 1) if irr_age is not None else None,
        "hours_since_last_fertilizer": round(fert_age, 1) if fert_age is not None else None,
    }

    # 2. Rule Evaluation & Forward Chaining Match Phase
    rules_evaluated = []
    rules_triggered = []
    conflict_resolutions = []
    now_iso = datetime.now(timezone.utc).isoformat()

    # Rule 1: High Wind
    r1_fired = wind is not None and wind > 25.0
    rules_evaluated.append({
        "rule_id": "RULE_01",
        "name": "High Wind Spraying Restriction",
        "condition_satisfied": r1_fired,
        "evaluation_detail": f"wind={wind} > 25.0 -> {r1_fired}",
    })
    if r1_fired:
        rules_triggered.append({
            "rule_id": "RULE_01",
            "name": "High Wind Spraying Restriction",
            "evidence": f"Current wind speed {wind} km/h exceeds 25 km/h threshold.",
            "action": "Avoid spraying foliar agrochemicals to prevent drift loss and non-target toxicity.",
            "advisory": {
                "type": "Weather",
                "title": "Strong wind advisory — Postpone spraying",
                "recommendation": "Avoid foliar pesticide/fertilizer spraying; strong winds cause severe chemical drift.",
                "reason": f"Observed wind speed of {wind} km/h exceeds safe spraying limits (25 km/h).",
                "severity": "WARNING",
                "timestamp": now_iso,
            }
        })

    # Rule 2: Heavy Rain Pre-Harvest
    is_mature = crop_stage.lower() in {"maturity", "harvest ready", "mature", "grain filling"}
    r2_fired = is_mature and (rain_next_48h > 15.0 or any(float(d.get("rain_probability", 0) or 0) > 70 for d in forecast[:2]))
    rules_evaluated.append({
        "rule_id": "RULE_02",
        "name": "Heavy Rain Pre-Harvest Warning",
        "condition_satisfied": r2_fired,
        "evaluation_detail": f"is_mature={is_mature}, rain_48h={rain_next_48h:.1f}mm -> {r2_fired}",
    })
    if r2_fired:
        rules_triggered.append({
            "rule_id": "RULE_02",
            "name": "Heavy Rain Pre-Harvest Warning",
            "evidence": f"Crop stage '{crop_stage}' combined with {rain_next_48h:.1f} mm rain forecast in next 48h.",
            "action": "Issue urgent harvest weather warning; clear drains and harvest immediately if field allows.",
            "advisory": {
                "type": "Harvest",
                "title": "Urgent Harvest Weather Warning",
                "recommendation": "Advance harvesting if physiological maturity is reached; protect grains from wet lodging.",
                "reason": f"Expected rain ({rain_next_48h:.1f} mm) threatens mature crop with mold and germination in earheads.",
                "severity": "URGENT",
                "timestamp": now_iso,
            }
        })

    # Rule 3 & 4 & 5: Water Management & Conflict Resolution
    irrigated_recently = irr_age is not None and irr_age < 24.0
    rain_expected_soon = (rain_prob is not None and rain_prob > 70.0 and rain_next_3d > 10.0) or (rain_next_48h > 12.0)
    soil_dry = moist_val is not None and moist_val < 30.0 and not irrigated_recently

    # Rule 4: Recent irrigation lockout
    r4_fired = irrigated_recently
    rules_evaluated.append({
        "rule_id": "RULE_04",
        "name": "Recent Irrigation Lockout",
        "condition_satisfied": r4_fired,
        "evaluation_detail": f"irr_age={irr_age} < 24.0 -> {r4_fired}",
    })
    if r4_fired:
        rules_triggered.append({
            "rule_id": "RULE_04",
            "name": "Recent Irrigation Lockout",
            "evidence": f"Confirmed farmer irrigation recorded {irr_age:.1f} hours ago.",
            "action": "Suppress irrigation; maintain optimal root aeration.",
            "advisory": {
                "type": "Irrigation",
                "title": "Irrigation not required",
                "recommendation": "Do not repeat irrigation today; allow root zone to utilize applied water.",

                "reason": f"A farmer-confirmed irrigation was completed {irr_age:.1f} hours ago.",
                "severity": "INFO",
                "timestamp": now_iso,
            }
        })

    # Rule 3: Rain postponement
    r3_fired = not irrigated_recently and rain_expected_soon
    rules_evaluated.append({
        "rule_id": "RULE_03",
        "name": "Rain Forecast Irrigation Postponement",
        "condition_satisfied": r3_fired,
        "evaluation_detail": f"rain_expected_soon={rain_expected_soon} -> {r3_fired}",
    })

    # Rule 5: Soil dry
    r5_fired = soil_dry and not irrigated_recently
    rules_evaluated.append({
        "rule_id": "RULE_05",
        "name": "Soil Moisture Deficit Irrigation Needed",
        "condition_satisfied": r5_fired,
        "evaluation_detail": f"soil_moist={moist_val} < 30% -> {r5_fired}",
    })

    # CONFLICT RESOLUTION: If both R3 (Rain Expected) and R5 (Soil Dry) fire:
    if r3_fired and r5_fired:
        conflict_resolutions.append({
            "conflict": "Soil moisture is low (R5), but significant rainfall is forecast within 48h (R3).",
            "resolution_principle": "Priority: Weather Inflow Conservation over Routine Watering.",
            "chosen_action": "Postpone irrigation by 24-48 hours to conserve water and prevent waterlogging.",
        })
        rules_triggered.append({
            "rule_id": "RULE_03",
            "name": "Rain Forecast Irrigation Postponement (Conflict Resolved)",
            "evidence": f"Low soil moisture ({moist_val}%) observed, but {rain_next_3d:.1f} mm rain forecast in 72h.",
            "action": "Postpone irrigation; let anticipated rainfall replenish the root zone naturally.",
            "advisory": {
                "type": "Irrigation",
                "title": "Delay irrigation — Rain approaching",
                "recommendation": "Postpone irrigation. Forecast rain is projected to meet moisture demands without manual pumping.",
                "reason": f"Upcoming rainfall ({rain_next_3d:.1f} mm expected) will replenish soil naturally, preventing energy waste.",
                "severity": "INFO",
                "timestamp": now_iso,
            }

        })
    elif r3_fired:
        rules_triggered.append({
            "rule_id": "RULE_03",
            "name": "Rain Forecast Irrigation Postponement",
            "evidence": f"Rain forecast of {rain_next_3d:.1f} mm over 3 days.",
            "action": "Delay irrigation.",
            "advisory": {
                "type": "Irrigation",
                "title": "Delay irrigation — Rain approaching",
                "recommendation": "Postpone irrigation as precipitation is expected to fulfill crop requirements.",
                "reason": f"Rain probability ({rain_prob}%) and forecast rainfall indicate sufficient incoming moisture.",
                "severity": "INFO",
                "timestamp": now_iso,
            }
        })
    elif r5_fired:
        rules_triggered.append({
            "rule_id": "RULE_05",
            "name": "Soil Moisture Deficit Irrigation Needed",
            "evidence": f"Soil moisture is {moist_val}% with no incoming rain.",
            "action": "Schedule crop irrigation.",
            "advisory": {
                "type": "Irrigation",
                "title": "Irrigation recommended",
                "recommendation": "Apply irrigation to prevent root moisture deficit and maintain transpiration.",
                "reason": f"Soil moisture ({moist_val}%) has dropped below critical threshold with low rain probability.",
                "severity": "CAUTION",
                "timestamp": now_iso,
            }
        })

    # Rule 6: Fungal microclimate
    r6_fired = humidity is not None and temp is not None and humidity > 85.0 and 15.0 <= temp <= 30.0
    rules_evaluated.append({
        "rule_id": "RULE_06",
        "name": "Fungal Microclimate Disease Risk",
        "condition_satisfied": r6_fired,
        "evaluation_detail": f"humidity={humidity} > 85 and temp={temp} -> {r6_fired}",
    })
    if r6_fired:
        rules_triggered.append({
            "rule_id": "RULE_06",
            "name": "Fungal Microclimate Disease Risk",
            "evidence": f"Relative humidity {humidity}% combined with ambient temp {temp}°C.",
            "action": "Issue fungal microclimate alert and schedule leaf inspection.",
            "advisory": {
                "type": "Disease Risk",
                "title": "Disease risk advisory — High fungal infection risk",
                "recommendation": "Inspect crop canopy for spots, downy growth, or blast lesions. Ensure good field aeration.",
                "reason": "Sustained high humidity and warm temperature create ideal spore germination conditions.",
                "severity": "WARNING",
                "timestamp": now_iso,
            }
        })

    # Rule 7: Heat stress
    r7_fired = temp is not None and temp > 35.0 and moist_val is not None and moist_val < 35.0
    rules_evaluated.append({
        "rule_id": "RULE_07",
        "name": "Heat Stress Warning",
        "condition_satisfied": r7_fired,
        "evaluation_detail": f"temp={temp} > 35 and moist={moist_val} < 35 -> {r7_fired}",
    })
    if r7_fired:
        rules_triggered.append({
            "rule_id": "RULE_07",
            "name": "Heat Stress Warning",
            "evidence": f"High temperature {temp}°C and low moisture {moist_val}%.",
            "action": "Issue heat stress warning.",
            "advisory": {
                "type": "Weather",
                "title": "Heat stress warning",
                "recommendation": "Increase field monitoring and schedule light evening irrigation to reduce thermal stress.",
                "reason": "Elevated daytime temperature combined with low moisture accelerates evapotranspiration wilting.",
                "severity": "WARNING",
                "timestamp": now_iso,
            }
        })

    # Rule 8 & 9: Nitrogen
    fertilized_recently = fert_age is not None and fert_age < 168.0
    r8_fired = fertilized_recently
    rules_evaluated.append({
        "rule_id": "RULE_08",
        "name": "Recent Fertilizer Lockout",
        "condition_satisfied": r8_fired,
        "evaluation_detail": f"fert_age={fert_age} < 168.0 -> {r8_fired}",
    })

    r9_fired = soil_n is not None and soil_n < 60.0
    rules_evaluated.append({
        "rule_id": "RULE_09",
        "name": "Nitrogen Deficiency Correction",
        "condition_satisfied": r9_fired,
        "evaluation_detail": f"soil_n={soil_n} < 60.0 -> {r9_fired}",
    })

    if r9_fired:
        if fertilized_recently:
            conflict_resolutions.append({
                "conflict": f"Soil test shows low N ({soil_n} kg/ha), but fertilizer task was logged {fert_age:.1f}h ago.",
                "resolution_principle": "Closed-loop feedback: Wait for plant nutrient uptake before re-dosing.",
                "chosen_action": "Suppress duplicate fertilizer recommendation; advise monitoring response.",
            })
            rules_triggered.append({
                "rule_id": "RULE_08",
                "name": "Recent Fertilizer Lockout (Suppressed N Alert)",
                "evidence": f"Confirmed fertilizer application recorded {fert_age:.1f} hours ago.",
                "action": "Do not repeat fertilizer today.",
                "advisory": {
                    "type": "Fertilizer",
                    "title": "Review recent fertilizer application",
                    "recommendation": "Reassess crop response and canopy color before repeating nitrogen top-dressing.",

                    "reason": f"A farmer-confirmed fertilizer application was recorded {fert_age:.1f} hours ago.",
                    "severity": "INFO",
                    "timestamp": now_iso,
                }
            })
        else:
            rules_triggered.append({
                "rule_id": "RULE_09",
                "name": "Nitrogen Deficiency Correction",
                "evidence": f"Soil Nitrogen {soil_n} kg/ha is below the 60 kg/ha threshold.",
                "action": "Recommend nitrogen supplementation.",
                "advisory": {
                    "type": "Fertilizer",
                    "title": "Nitrogen deficiency risk",
                    "recommendation": "Consider appropriate nitrogen supplementation (e.g., Neem Coated Urea or Ammonium Sulphate).",
                    "reason": f"Available soil Nitrogen ({soil_n} kg/ha) is low relative to crop nutrient demand.",
                    "severity": "CAUTION",
                    "timestamp": now_iso,
                }

            })

    # Rule 10: Phosphorus
    r10_fired = soil_p is not None and soil_p < 40.0 and not fertilized_recently
    rules_evaluated.append({
        "rule_id": "RULE_10",
        "name": "Phosphorus Deficiency Support",
        "condition_satisfied": r10_fired,
        "evaluation_detail": f"soil_p={soil_p} < 40.0 -> {r10_fired}",
    })
    if r10_fired:
        rules_triggered.append({
            "rule_id": "RULE_10",
            "name": "Phosphorus Deficiency Support",
            "evidence": f"Soil Phosphorus {soil_p} kg/ha is below threshold.",
            "action": "Recommend balanced phosphorus support (DAP or SSP).",
            "advisory": {
                "type": "Fertilizer",
                "title": "Phosphorus Support Needed",
                "recommendation": "Assess phosphorus availability and consider balanced fertilization (DAP or SSP).",
                "reason": "Phosphorus is below the recommended range for vigorous root development.",
                "severity": "INFO",
                "timestamp": now_iso,
            }
        })

    # Rule 11: Potassium
    r11_fired = soil_k is not None and soil_k < 50.0 and not fertilized_recently
    rules_evaluated.append({
        "rule_id": "RULE_11",
        "name": "Potassium Stress Defense",
        "condition_satisfied": r11_fired,
        "evaluation_detail": f"soil_k={soil_k} < 50.0 -> {r11_fired}",
    })
    if r11_fired:
        rules_triggered.append({
            "rule_id": "RULE_11",
            "name": "Potassium Stress Defense",
            "evidence": f"Soil Potassium {soil_k} kg/ha is below threshold.",
            "action": "Recommend potassium management.",
            "advisory": {
                "type": "Fertilizer",
                "title": "Potassium Management",
                "recommendation": "Review potassium status and plan nutrient supplementation (MOP or SOP for fruits).",
                "reason": "Potassium is low and may affect cellular osmotic pressure and disease resistance.",
                "severity": "INFO",
                "timestamp": now_iso,
            }
        })

    # Extract clean advisories list
    final_advisories = [item["advisory"] for item in rules_triggered if "advisory" in item]
    if not final_advisories:
        final_advisories.append({
            "type": "General",
            "title": "Monitor field conditions",
            "recommendation": "No action rule fired from available observations. Missing observations do not establish safe conditions; inspect the field.",
            "reason": "No critical agronomic or climatic thresholds were exceeded during forward chaining inference.",
            "severity": "INFO",
            "timestamp": now_iso,
        })

    return {
        "facts": facts,
        "rules_evaluated": rules_evaluated,
        "rules_triggered": rules_triggered,
        "conflict_resolutions": conflict_resolutions,
        "advisories": final_advisories,
        "total_rules_in_kb": len(EXPERT_RULES_KNOWLEDGE_BASE),
        "rules_catalog": EXPERT_RULES_KNOWLEDGE_BASE,
    }


def generate_advisories(
    crop: str,
    crop_stage: str,
    weather: Dict[str, Any],
    soil: Dict[str, Any],
    forecast: Optional[List[Dict[str, Any]]] = None,
    activity_history: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Backward compatible wrapper returning list of advisory dictionaries."""
    res = evaluate_expert_system(crop, crop_stage, weather, soil, forecast, activity_history)
    return res["advisories"]
