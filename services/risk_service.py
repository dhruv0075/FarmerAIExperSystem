from __future__ import annotations

from typing import Any, Dict, List, Optional


def analyze_comprehensive_farm_risk(
    crop_name: str,
    crop_stage: str,
    weather: Dict[str, Any],
    soil: Dict[str, Any],
    farm: Optional[Dict[str, Any]] = None,
    activities: Optional[List[Dict[str, Any]]] = None,
    market_info: Optional[Dict[str, Any]] = None,
    disease_reports: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Computes 8 distinct agricultural risk dimensions and calculates the overall
    AgriWise Decision-Support Index (0 - 100) with explainable component reasons.
    """
    farm = farm or {}
    soil = soil or {}
    weather = weather or {}
    activities = activities or []
    disease_reports = disease_reports or []
    curr_weather = weather.get("current", {})
    forecast = weather.get("forecast", [])


    # 1. Weather Risk (0 - 100)
    w_temp = float(curr_weather.get("temperature", 26.0) or 26.0)
    w_wind = float(curr_weather.get("wind_speed", 10.0) or 10.0)
    w_rain_prob = float(curr_weather.get("rain_probability", 10.0) or 10.0)
    rain_3d = sum(float(d.get("precipitation", 0.0) or 0.0) for d in forecast[:3])

    weather_risk = 15.0
    weather_reasons = []
    if rain_3d > 25.0:
        weather_risk += 35.0
        weather_reasons.append(f"Heavy rainfall forecast ({rain_3d:.1f} mm in next 3 days).")
    elif rain_3d > 10.0 or w_rain_prob > 70.0:
        weather_risk += 20.0
        weather_reasons.append(f"Moderate precipitation forecast ({rain_3d:.1f} mm, {w_rain_prob:.0f}% probability).")

    if w_wind > 25.0:
        weather_risk += 25.0
        weather_reasons.append(f"Strong winds ({w_wind:.1f} km/h) present spraying drift hazard.")
    if w_temp > 36.0:
        weather_risk += 20.0
        weather_reasons.append(f"High heat conditions ({w_temp:.1f}°C) increase plant evapotranspiration stress.")

    weather_risk = min(100.0, weather_risk)

    # 2. Water Risk (0 - 100)
    water_risk = 20.0
    water_reasons = []
    water_avail = str(farm.get("water_availability", "Medium")).lower()
    if "limited" in water_avail or "rain-dependent" in water_avail:
        water_risk += 35.0
        water_reasons.append(f"Water availability is categorized as '{water_avail}'.")
    soil_moist = soil.get("moisture")
    if soil_moist is not None and float(soil_moist) < 25.0 and rain_3d < 5.0:
        water_risk += 30.0
        water_reasons.append(f"Low measured soil moisture ({soil_moist}%) with negligible forecast rain.")
    water_risk = min(100.0, water_risk)

    # 3. Nutrient Risk (0 - 100)
    nutrient_risk = 15.0
    nutrient_reasons = []
    n_val = float(soil.get("nitrogen", 70) or 70)
    p_val = float(soil.get("phosphorus", 40) or 40)
    k_val = float(soil.get("potassium", 40) or 40)
    if n_val < 50:
        nutrient_risk += 25.0
        nutrient_reasons.append(f"Low available nitrogen ({n_val} kg/ha).")
    if p_val < 30:
        nutrient_risk += 20.0
        nutrient_reasons.append(f"Low phosphorus reserve ({p_val} kg/ha).")
    if k_val < 30:
        nutrient_risk += 20.0
        nutrient_reasons.append(f"Low potassium level ({k_val} kg/ha).")
    nutrient_risk = min(100.0, nutrient_risk)

    # 4. Disease Risk (0 - 100)
    disease_risk = 20.0
    disease_reasons = []
    w_hum = float(curr_weather.get("humidity", 65.0) or 65.0)
    if w_hum > 85.0 and 18.0 <= w_temp <= 30.0:
        disease_risk += 35.0
        disease_reasons.append(f"Warm and humid canopy conditions ({w_hum:.0f}% RH, {w_temp:.1f}°C) favor fungal spores.")
    active_reports = [r for r in disease_reports if str(r.get("status", "")).upper() != "RESOLVED"]
    if active_reports:
        disease_risk += 30.0
        disease_reasons.append(f"{len(active_reports)} active crop symptom reports pending on the farm.")
    disease_risk = min(100.0, disease_risk)

    # 5. Market Risk & 6. Price Risk (0 - 100)
    market_risk = 25.0
    price_risk = 25.0
    market_reasons = []
    if market_info and market_info.get("best_market"):
        bm = market_info["best_market"]
        trend = bm.get("price_trend", "Stable")
        if trend == "Down":
            market_risk += 30.0
            price_risk += 35.0
            market_reasons.append("Recent mandi spot prices indicate a downward price correction.")
        elif trend == "Stable":
            market_risk += 10.0
            price_risk += 10.0
            market_reasons.append("Spot prices in nearby markets remain relatively steady.")
    else:
        market_reasons.append("Regional mandi prices are stable based on seasonal arrivals.")

    # 7. Harvest Risk (0 - 100)
    harvest_risk = 10.0
    harvest_reasons = []
    is_mature = any(term in crop_stage.lower() for term in ["maturity", "mature", "harvest", "grain filling"])
    if is_mature and rain_3d > 15.0:
        harvest_risk = 80.0
        harvest_reasons.append(f"Crop is in '{crop_stage}' stage with {rain_3d:.1f} mm rain forecast. High lodging and grain spoilage risk.")
    elif is_mature:
        harvest_risk = 30.0
        harvest_reasons.append(f"Crop approaching harvest window; monitor field moisture and logistics.")
    else:
        harvest_reasons.append("Crop is not currently in a vulnerable pre-harvest window.")

    # 8. Activity Risk (0 - 100)
    activity_risk = 15.0
    activity_reasons = []
    overdue_count = sum(1 for a in activities if str(a.get("status", "")).upper() == "OVERDUE")
    pending_count = sum(1 for a in activities if str(a.get("status", "")).upper() == "PENDING")
    if overdue_count > 0:
        activity_risk += min(50.0, overdue_count * 25.0)
        activity_reasons.append(f"{overdue_count} critical farm tasks are overdue.")
    if pending_count > 3:
        activity_risk += 15.0
        activity_reasons.append(f"{pending_count} pending operations awaiting farmer execution.")
    activity_risk = min(100.0, activity_risk)

    # Weighted Overall Farm Risk (0 - 100)
    overall_risk_val = (
        weather_risk * 0.20
        + water_risk * 0.15
        + nutrient_risk * 0.15
        + disease_risk * 0.15
        + market_risk * 0.10
        + harvest_risk * 0.10
        + activity_risk * 0.15
    )
    overall_risk_val = round(min(100.0, max(10.0, overall_risk_val)), 1)

    if overall_risk_val >= 75.0:
        overall_category = "CRITICAL"
        risk_color = "danger"
    elif overall_risk_val >= 55.0:
        overall_category = "HIGH"
        risk_color = "warning"
    elif overall_risk_val >= 35.0:
        overall_category = "MODERATE"
        risk_color = "info"
    else:
        overall_category = "LOW"
        risk_color = "success"

    # AgriWise Decision-Support Index (0 - 100)
    # Higher score = healthier, better conditioned farm state
    # Derived transparently from:
    # (100 - Weather Risk)*0.20 + (100 - Water Risk)*0.20 + (100 - Nutrient Risk)*0.20 + (100 - Disease Risk)*0.15 + (100 - Activity Risk)*0.25
    condition_score = round(
        (100.0 - weather_risk) * 0.20
        + (100.0 - water_risk) * 0.20
        + (100.0 - nutrient_risk) * 0.20
        + (100.0 - disease_risk) * 0.15
        + (100.0 - activity_risk) * 0.25,
        1,
    )
    condition_score = min(100.0, max(10.0, condition_score))

    availability = {
        'weather_risk': curr_weather.get('temperature') is not None,
        'water_risk': soil.get('moisture') is not None,
        'nutrient_risk': all(soil.get(k) is not None for k in ('nitrogen', 'phosphorus', 'potassium')),
        'disease_risk': bool(active_reports) or (curr_weather.get('humidity') is not None and curr_weather.get('temperature') is not None),
        'market_risk': bool(market_info and market_info.get('found')),
        'price_risk': bool(market_info and market_info.get('history_30d')),
        'harvest_risk': bool(forecast) and crop_stage not in ('Preparation', 'Planning / Field Preparation'),
        'activity_risk': bool(activities),
    }
    values = dict(weather_risk=weather_risk, water_risk=water_risk, nutrient_risk=nutrient_risk,
                  disease_risk=disease_risk, market_risk=market_risk, price_risk=price_risk,
                  harvest_risk=harvest_risk, activity_risk=activity_risk)
    measured = [v for k, v in values.items() if availability[k]]
    overall_risk_val = round(sum(measured) / len(measured), 1) if measured else None
    condition_score = round(100 - overall_risk_val, 1) if measured else None
    overall_category = ('CRITICAL' if overall_risk_val >= 75 else 'HIGH' if overall_risk_val >= 55 else 'MODERATE' if overall_risk_val >= 35 else 'LOW') if measured else 'UNKNOWN'

    return {
        "overall_risk_score": overall_risk_val,
        "overall_risk_category": overall_category,
        "risk_badge_class": risk_color,
        "condition_score": condition_score,
        "condition_index_name": "AgriWise Decision-Support Index",
        "dimensions": {k: {"score": round(v, 1) if availability[k] else None,
            "reasons": ["Configured heuristic based on available observations; not scientifically validated."] if availability[k] else ["Required observations unavailable."]} for k, v in values.items()},
        "formula": "Equal mean of available risk dimensions; index = 100 minus mean. Unknown dimensions excluded.",

    }


def analyze_farm_risk(arg1: Any = None, arg2: Any = None, arg3: Any = None, activity_history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Backward-compatible wrapper supporting both:
    - analyze_farm_risk(soil, weather, cycle)
    - analyze_farm_risk(crop, weather, soil, activity_history)
    """
    if isinstance(arg1, str):
        crop = arg1
        weather = arg2 or {}
        soil = arg3 or {}
        cycle = {"crop_name": crop, "current_stage": "Vegetative"}
    else:
        soil = arg1 or {}
        weather = arg2 or {}
        cycle = arg3 or {}
        crop = cycle.get("crop_name", "General Crop")

    if "temperature" in weather and "current" not in weather:
        full_weather = {"current": weather, "forecast": []}
    else:
        full_weather = weather

    res = analyze_comprehensive_farm_risk(
        crop_name=crop,
        crop_stage=cycle.get("current_stage", "Vegetative"),
        weather=full_weather,
        soil=soil,
        activities=activity_history,
    )

    moist = soil.get("moisture")
    if moist is None:
        water_cond = "Unknown"
        water_risk_score = 40.0
    elif float(moist) <= 15.0:
        water_cond = "Critical"
        water_risk_score = 80.0
    elif float(moist) < 30.0:
        water_cond = "Deficit"
        water_risk_score = 65.0
    else:
        water_cond = "Adequate"
        water_risk_score = 20.0

    rain_prob = float(weather.get("rain_probability", weather.get("current", {}).get("rain_probability", 0)) or 0)
    rain_val = float(weather.get("rainfall", weather.get("current", {}).get("precipitation", 0)) or 0)
    heavy_rain_risk = 75.0 if rain_prob >= 70 or rain_val >= 15 else (50.0 if rain_prob >= 50 else 20.0)

    temp_val = float(weather.get("temperature", weather.get("current", {}).get("temperature", 25)) or 25)
    heat_risk = 80.0 if temp_val >= 38 else (60.0 if temp_val >= 35 else 20.0)

    n_val = float(soil.get("nitrogen", 70) or 70)
    nutrient_risk = 75.0 if n_val < 50 else 25.0

    condition_components = {
        "Water condition": water_cond,
        "Heat risk": "High" if heat_risk >= 70 else ("Moderate" if heat_risk >= 50 else "Low"),
        "Heavy rain risk": "High" if heavy_rain_risk >= 65 else ("Moderate" if heavy_rain_risk >= 50 else "Low"),
        "Nutrient risk": "High" if nutrient_risk >= 65 else "Low",
        "Disease environment": "Moderate",
        "Harvest risk": "Low",
    }

    risk_scores = {
        "Heavy rain risk": heavy_rain_risk,
        "Water risk": water_risk_score,
        "Heat risk": heat_risk,
        "Nutrient risk": nutrient_risk,
    }

    for label, present in {
        "Heat risk": weather.get('temperature', weather.get('current', {}).get('temperature')) is not None,
        "Heavy rain risk": weather.get('rain_probability', weather.get('current', {}).get('rain_probability')) is not None,
        "Nutrient risk": soil.get('nitrogen') is not None,
    }.items():
        if not present:
            condition_components[label] = 'Unknown'
            risk_scores[label] = None
    if not weather:
        condition_components['Disease environment'] = 'Unknown'
    if not cycle:
        condition_components['Harvest risk'] = 'Unknown'

    return {
        "condition_score": res["condition_score"],
        "condition_components": condition_components,
        "risk_scores": risk_scores,
        "overall_risk_score": res["overall_risk_score"],
        "risk_level": res["overall_risk_category"].capitalize(),
        "dimensions": res["dimensions"],
    }