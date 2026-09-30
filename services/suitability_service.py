from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_PATH = BASE_DIR / "data" / "crop_knowledge.json"

_CROP_KNOWLEDGE_CACHE: Dict[str, Any] = {}


def get_crop_knowledge(crop_name: str | None = None) -> Dict[str, Any]:
    global _CROP_KNOWLEDGE_CACHE
    if not _CROP_KNOWLEDGE_CACHE:
        if KNOWLEDGE_PATH.exists():
            with KNOWLEDGE_PATH.open("r", encoding="utf-8") as f:
                _CROP_KNOWLEDGE_CACHE = json.load(f)
        else:
            _CROP_KNOWLEDGE_CACHE = {}

    if crop_name:
        key = crop_name.lower().strip()
        # Direct lookup or alias
        if key in _CROP_KNOWLEDGE_CACHE:
            return _CROP_KNOWLEDGE_CACHE[key]
        for k, v in _CROP_KNOWLEDGE_CACHE.items():
            if k in key or key in k or v.get("name", "").lower() == key:
                return v
        return {}
    return _CROP_KNOWLEDGE_CACHE


def calculate_suitability_score(
    crop_key: str,
    soil: Dict[str, Any],
    weather: Dict[str, Any],
    farm: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Computes transparent agronomic, weather, and farm suitability indices (0 - 100)
    using verified crop threshold ranges from crop_knowledge.json.
    """
    crop_info = get_crop_knowledge(crop_key)
    if not crop_info:
        return {
            "agronomic_score": 70.0,
            "weather_score": 70.0,
            "soil_score": 70.0,
            "overall_suitability": 70.0,
            "details": {},
        }

    opt = crop_info.get("optimal_ranges", {})
    soil_types_allowed = [s.lower() for s in crop_info.get("soil_suitability", [])]

    # 1. Soil Parameters Matching (N, P, K, pH)
    def _score_param(val: float, bounds: List[float], weight: float = 1.0) -> float:
        if bounds is None or len(bounds) < 2:
            return 100.0
        low, high = bounds[0], bounds[1]
        mid = (low + high) / 2.0
        spread = max(1.0, (high - low) / 2.0)
        dist = abs(val - mid)
        if dist <= spread:
            return 100.0
        overshoot = dist - spread
        return max(20.0, 100.0 - (overshoot / spread) * 60.0)

    n_val = float(soil.get("nitrogen", soil.get("N", 70)) or 70)
    p_val = float(soil.get("phosphorus", soil.get("P", 40)) or 40)
    k_val = float(soil.get("potassium", soil.get("K", 40)) or 40)
    ph_val = float(soil.get("ph", 6.5) or 6.5)

    n_score = _score_param(n_val, opt.get("N", [40, 100]))
    p_score = _score_param(p_val, opt.get("P", [30, 70]))
    k_score = _score_param(k_val, opt.get("K", [30, 70]))
    ph_score = _score_param(ph_val, opt.get("ph", [6.0, 7.5]))

    soil_score = round(n_score * 0.25 + p_score * 0.25 + k_score * 0.25 + ph_score * 0.25, 1)

    # 2. Weather Parameters Matching (temp, humidity, rainfall)
    curr_weather = weather.get("current", {})
    temp_val = float(curr_weather.get("temperature", 26.0) or 26.0)
    humidity_val = float(curr_weather.get("humidity", 65.0) or 65.0)
    forecast_rain = sum(float(d.get("precipitation", 0.0) or 0.0) for d in weather.get("forecast", [])[:7])

    temp_score = _score_param(temp_val, opt.get("temperature", [20, 32]))
    hum_score = _score_param(humidity_val, opt.get("humidity", [50, 80]))
    rain_score = _score_param(forecast_rain * 4.0, opt.get("rainfall", [50, 150]))  # monthly projected

    weather_score = round(temp_score * 0.40 + hum_score * 0.30 + rain_score * 0.30, 1)

    # 3. Farm and Water Suitability
    farm_score = 80.0
    if farm:
        # Soil type compatibility
        farm_soil = str(farm.get("soil_type", "")).strip().lower()
        if farm_soil and farm_soil in soil_types_allowed:
            farm_score += 15.0
        elif farm_soil and farm_soil != "other / unknown":
            farm_score -= 10.0

        # Water source compatibility
        crop_water_cat = crop_info.get("water_category", "Medium")
        water_avail = str(farm.get("water_availability", "Medium")).strip().lower()
        if crop_water_cat == "High":
            if water_avail in ["high", "irrigated"]:
                farm_score += 10.0
            elif water_avail in ["limited", "seasonal", "rain-dependent"]:
                farm_score -= 25.0
        elif crop_water_cat == "Very Low" or crop_water_cat == "Low":
            if water_avail in ["limited", "seasonal"]:
                farm_score += 10.0  # excellent choice for limited water

    farm_score = max(20.0, min(100.0, farm_score))
    overall = round(soil_score * 0.35 + weather_score * 0.40 + farm_score * 0.25, 1)

    return {
        "overall_suitability": overall,
        "soil_score": soil_score,
        "weather_score": weather_score,
        "farm_score": round(farm_score, 1),
        "details": {
            "nitrogen_match": round(n_score, 1),
            "phosphorus_match": round(p_score, 1),
            "potassium_match": round(k_score, 1),
            "ph_match": round(ph_score, 1),
            "temperature_match": round(temp_score, 1),
            "humidity_match": round(hum_score, 1),
            "rainfall_match": round(rain_score, 1),
        },
    }
