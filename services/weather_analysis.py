from __future__ import annotations

from typing import Any, Dict, List


def score_weather_risk(day: Dict[str, Any], crop_stage: str = "") -> Dict[str, Any]:
    score = 0
    evidence = []
    rain = float(day.get("precipitation") or 0)
    probability = day.get("rain_probability")
    probability = float(probability) if probability is not None else None
    maximum = day.get("temperature_max")
    minimum = day.get("temperature_min")
    wind = float(day.get("wind_speed") or 0)
    humidity = day.get("humidity")

    if rain >= 50:
        score += 35
        evidence.append("daily rainfall at or above 50 mm")
    elif rain >= 25:
        score += 25
        evidence.append("daily rainfall at or above 25 mm")
    elif rain >= 10:
        score += 15
        evidence.append("daily rainfall at or above 10 mm")
    if probability is not None and probability >= 80:
        score += 25
        evidence.append("rain probability at or above 80%")
    elif probability is not None and probability >= 60:
        score += 15
        evidence.append("rain probability at or above 60%")
    if maximum is not None and float(maximum) >= 40:
        score += 25
        evidence.append("maximum temperature at or above 40 C")
    elif maximum is not None and float(maximum) >= 35:
        score += 15
        evidence.append("maximum temperature at or above 35 C")
    if minimum is not None and float(minimum) <= 5:
        score += 20
        evidence.append("minimum temperature at or below 5 C")
    if wind >= 50:
        score += 15
        evidence.append("wind speed at or above 50 km/h")
    elif wind >= 30:
        score += 8
        evidence.append("wind speed at or above 30 km/h")
    if humidity is not None and float(humidity) >= 90:
        score += 10
        evidence.append("daily humidity at or above 90%")
    if crop_stage.casefold() in {"maturity", "harvest", "harvest ready"} and probability is not None and probability >= 60:
        score += 10
        evidence.append("rain exposure during a harvest-stage crop")

    score = min(100, score)
    level = "Critical" if score >= 75 else "High" if score >= 50 else "Moderate" if score >= 25 else "Low"
    return {"score": score, "level": level, "evidence": evidence}


def analyze_forecast(forecast: List[Dict[str, Any]], crop: str = "", stage: str = "") -> Dict[str, Any]:
    days = [{**day, "risk": score_weather_risk(day, stage)} for day in forecast]
    highest = max(days, key=lambda day: day["risk"]["score"], default=None)
    actions = []
    if not days:
        summary = "A forecast is not available, so near-term agricultural weather risk cannot be assessed."
    elif highest and highest["risk"]["score"] >= 50:
        summary = f"The highest configured weather-risk score is {highest['risk']['score']}/100 on {highest['date']} ({highest['risk']['level'].lower()})."
    else:
        summary = "No high weather-risk day was identified by the configured seven-day screening rules."
    heavy_rain_days = [day for day in days if float(day.get("precipitation") or 0) >= 25 or (day.get("rain_probability") is not None and float(day["rain_probability"]) >= 80)]
    hot_days = [day for day in days if day.get("temperature_max") is not None and float(day["temperature_max"]) >= 35]
    humid_days = [day for day in days if day.get("humidity") is not None and float(day["humidity"]) >= 85]
    if heavy_rain_days:
        actions.append({"title": "Inspect drainage before forecast rain", "activity_type": "Field inspection", "reason": f"Configured heavy-rain threshold is met on {heavy_rain_days[0]['date']}."})
        actions.append({"title": "Review fertilizer timing", "activity_type": "Field inspection", "reason": "Avoid scheduling application immediately before a forecast heavy-rain window without local agronomic guidance."})
    if hot_days:
        actions.append({"title": "Check field moisture during hot conditions", "activity_type": "Field inspection", "reason": f"Forecast maximum temperature reaches {hot_days[0]['temperature_max']} C on {hot_days[0]['date']}; verify soil moisture before irrigating."})
    if humid_days:
        actions.append({"title": "Inspect crop for moisture-related symptoms", "activity_type": "Field inspection", "reason": f"Configured high-humidity threshold is met on {humid_days[0]['date']}."})
    impact = f"Weather screening is for {crop} at the {stage} stage." if crop and stage else "Weather screening uses the available forecast and configured thresholds."
    return {"days": days, "summary": summary, "impact": impact, "highest_risk_day": highest, "actions": actions}