from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import requests

# In-memory weather cache: {(round(lat, 2), round(lon, 2)): (timestamp, weather_dict)}
_WEATHER_CACHE: Dict[tuple, tuple[float, Dict[str, Any]]] = {}
CACHE_TTL_SECONDS = 1800  # 30 minutes


class WeatherError(RuntimeError):
    pass


def fetch_weather_data(latitude: float, longitude: float, force_refresh: bool = False) -> Dict[str, Any]:
    """
    Fetches live weather from Open-Meteo API with caching and fallback.
    Includes current conditions, 7-day daily forecast, agricultural ET0, soil metrics,
    and agricultural weather risk interpretations.
    """
    if latitude is None or longitude is None:
        raise WeatherError("Missing location coordinates.")

    try:
        lat = float(latitude)
        lon = float(longitude)
    except (TypeError, ValueError):
        raise WeatherError("Invalid numeric coordinates.")

    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise WeatherError("Coordinates out of bounds.")
    cache_key = (round(lat, 2), round(lon, 2))
    now_ts = time.time()

    # Return cached data if valid
    if not force_refresh and cache_key in _WEATHER_CACHE:
        cached_time, cached_payload = _WEATHER_CACHE[cache_key]
        if now_ts - cached_time < CACHE_TTL_SECONDS:
            res = dict(cached_payload)
            res["is_cached"] = True
            res["data_source"] = "CACHED LIVE WEATHER (Open-Meteo)"
            return res

    # Request Open-Meteo with comprehensive agricultural parameters
    try:
        response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,wind_speed_10m,wind_gusts_10m",
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,wind_speed_10m_max,et0_fao_evapotranspiration",
                "hourly": "temperature_2m,relative_humidity_2m,precipitation_probability,precipitation,wind_speed_10m,soil_temperature_0cm,soil_moisture_0_to_1cm",
                "timezone": "auto",
                "forecast_days": 10,
            },
            timeout=8,
        )
        if response.status_code == 200:
            payload = response.json()
            parsed = _parse_open_meteo_payload(lat, lon, payload)
            _WEATHER_CACHE[cache_key] = (now_ts, parsed)
            return parsed
    except Exception as exc:
        # Check if we have an older cached record to fall back on
        if cache_key in _WEATHER_CACHE:
            _, stale_payload = _WEATHER_CACHE[cache_key]
            stale_copy = dict(stale_payload)
            stale_copy["is_cached"] = True
            stale_copy["is_stale"] = True
            stale_copy["data_source"] = "PREVIOUS CACHE (Offline Fallback)"
            return stale_copy

    if cache_key in _WEATHER_CACHE:
        stale_copy = dict(_WEATHER_CACHE[cache_key][1])
        stale_copy.update(is_cached=True, is_stale=True)
        return stale_copy
    raise WeatherError("Weather unavailable: provider failed and no cached observation exists.")


def _parse_open_meteo_payload(lat: float, lon: float, payload: Dict[str, Any]) -> Dict[str, Any]:
    current = payload.get("current") or {}
    if any(current.get(key) is None for key in ("temperature_2m", "relative_humidity_2m", "wind_speed_10m", "precipitation")):
        raise WeatherError("Incomplete current weather response.")
    daily = payload.get("daily") or {}
    hourly = payload.get("hourly") or {}

    daily_times = daily.get("time", [])
    daily_max = daily.get("temperature_2m_max", [])
    daily_min = daily.get("temperature_2m_min", [])
    daily_precip = daily.get("precipitation_sum", [])
    daily_rain_prob = daily.get("precipitation_probability_max", [])
    daily_wind = daily.get("wind_speed_10m_max", [])
    daily_et0 = daily.get("et0_fao_evapotranspiration", [])

    hourly_times = hourly.get("time", [])
    hourly_humidity = hourly.get("relative_humidity_2m", [])
    hourly_rain_prob = hourly.get("precipitation_probability", [])
    hourly_soil_temp = hourly.get("soil_temperature_0cm", [])
    hourly_soil_moist = hourly.get("soil_moisture_0_to_1cm", [])

    forecast_days: List[Dict[str, Any]] = []
    for idx, day_str in enumerate(daily_times[:10]):
        # Match hourly humidity for the day
        matching_humidity = [
            hourly_humidity[p]
            for p, t in enumerate(hourly_times)
            if str(t).startswith(day_str) and p < len(hourly_humidity) and hourly_humidity[p] is not None
        ]
        avg_humidity = round(sum(matching_humidity) / len(matching_humidity), 1) if matching_humidity else None

        p_sum = daily_precip[idx] if idx < len(daily_precip) and daily_precip[idx] is not None else 0.0
        p_prob = daily_rain_prob[idx] if idx < len(daily_rain_prob) and daily_rain_prob[idx] is not None else 0.0
        w_max = daily_wind[idx] if idx < len(daily_wind) and daily_wind[idx] is not None else 10.0
        et0_val = daily_et0[idx] if idx < len(daily_et0) and daily_et0[idx] is not None else None

        # Daily weather risk calculation (0 - 100)
        day_risk_score = 15  # baseline low
        if p_sum > 30 or p_prob > 80:
            day_risk_score += 45
        elif p_sum > 10 or p_prob > 60:
            day_risk_score += 25
        if w_max > 30:
            day_risk_score += 25
        if et0_val is not None and et0_val > 6.0:
            day_risk_score += 15
        day_risk_score = min(100, day_risk_score)

        risk_category = "Low"
        if day_risk_score >= 70:
            risk_category = "Critical"
        elif day_risk_score >= 50:
            risk_category = "High"
        elif day_risk_score >= 30:
            risk_category = "Moderate"

        forecast_days.append({
            "date": day_str,
            "temperature_max": daily_max[idx] if idx < len(daily_max) else 30.0,
            "temperature_min": daily_min[idx] if idx < len(daily_min) else 20.0,
            "precipitation": round(float(p_sum), 1),
            "rain_probability": round(float(p_prob), 1),
            "wind_speed": round(float(w_max), 1),
            "humidity": avg_humidity,
            "et0": round(float(et0_val), 2) if et0_val is not None else None,
            "risk_score": day_risk_score,
            "risk_category": risk_category,
        })

    # Current matching hourly probability and soil metrics
    current_time_str = current.get("time")
    curr_prob = None
    curr_soil_temp = None
    curr_soil_moist = None

    if current_time_str and hourly_times:
        try:
            curr_dt = datetime.fromisoformat(current_time_str)
            closest_idx = 0
            min_diff = 9999999
            for i, ts in enumerate(hourly_times):
                try:
                    diff = abs((datetime.fromisoformat(ts) - curr_dt).total_seconds())
                    if diff < min_diff:
                        min_diff = diff
                        closest_idx = i
                except Exception:
                    continue
            if closest_idx < len(hourly_rain_prob) and hourly_rain_prob[closest_idx] is not None:
                curr_prob = float(hourly_rain_prob[closest_idx])
            if closest_idx < len(hourly_soil_temp) and hourly_soil_temp[closest_idx] is not None:
                curr_soil_temp = float(hourly_soil_temp[closest_idx])
            if closest_idx < len(hourly_soil_moist) and hourly_soil_moist[closest_idx] is not None:
                curr_soil_moist = float(hourly_soil_moist[closest_idx])
        except Exception:
            pass

    curr_temp = current.get("temperature_2m", 28.0)
    curr_humidity = current.get("relative_humidity_2m", 65.0)
    curr_wind = current.get("wind_speed_10m", 12.0)
    curr_precip = current.get("precipitation", 0.0)

    # Agricultural Interpretation Engine
    agri_alerts = []
    if curr_wind > 25.0:
        agri_alerts.append({
            "level": "WARNING",
            "title": "Spraying Unsuitable (High Wind)",
            "message": f"Current wind speed is {curr_wind:.1f} km/h. Postpone foliar spraying and dusting to prevent drift.",
        })
    if curr_humidity > 85.0 and 18.0 <= curr_temp <= 32.0:
        agri_alerts.append({
            "level": "WARNING",
            "title": "Fungal Infection Environment",
            "message": f"Warm temperature ({curr_temp:.1f}°C) and high humidity ({curr_humidity:.0f}%) favor fungal pathogen proliferation. Inspect crop foliage.",
        })
    if any(d["precipitation"] > 15.0 for d in forecast_days[:2]):
        agri_alerts.append({
            "level": "INFO",
            "title": "Rainfall Expected Soon",
            "message": "Heavy precipitation forecast over next 48 hours. Postpone planned irrigation and ensure field drainage channels are clear.",
        })
    if curr_temp > 36.0:
        agri_alerts.append({
            "level": "CAUTION",
            "title": "Heat Stress Condition",
            "message": f"Temperature ({curr_temp:.1f}°C) exceeds optimal threshold. Monitor for leaf wilting and maintain root-zone moisture.",
        })

    fetch_time_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    return {
        "latitude": lat,
        "longitude": lon,
        "fetch_timestamp": fetch_time_iso,
        "data_source": "LIVE WEATHER (Open-Meteo API)",
        "is_cached": False,
        "current": {
            "temperature": curr_temp,
            "apparent_temperature": current.get("apparent_temperature"),
            "feels_like": current.get("apparent_temperature"),
            "humidity": curr_humidity,
            "precipitation": curr_precip,
            "wind_speed": curr_wind,
            "wind_gusts": current.get("wind_gusts_10m"),
            "rain_probability": curr_prob,
            "soil_temperature": round(curr_soil_temp, 1) if curr_soil_temp is not None else None,
            "soil_moisture": round(curr_soil_moist, 3) if curr_soil_moist is not None else None,
        },
        "forecast": forecast_days,
        "agri_alerts": agri_alerts,
    }

