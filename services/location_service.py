from __future__ import annotations

import time
from typing import Any, Dict, Optional
import requests

# In-memory reverse geocoding cache: {(round(lat, 3), round(lon, 3)): (timestamp, result_dict)}
_GEOCODE_CACHE: Dict[tuple, tuple[float, Dict[str, Any]]] = {}
CACHE_TTL_SECONDS = 86400  # 24 hours


def validate_coordinates(latitude: Any, longitude: Any) -> tuple[float, float]:
    """Validates and converts latitude (-90 to 90) and longitude (-180 to 180)."""
    try:
        lat = float(latitude)
        lon = float(longitude)
    except (TypeError, ValueError):
        raise ValueError("Latitude and longitude must be valid numeric values.")

    if not (-90.0 <= lat <= 90.0):
        raise ValueError(f"Latitude {lat} is out of bounds (-90 to 90).")
    if not (-180.0 <= lon <= 180.0):
        raise ValueError(f"Longitude {lon} is out of bounds (-180 to 180).")

    return round(lat, 6), round(lon, 6)


def reverse_geocode(latitude: float, longitude: float) -> Dict[str, Any]:
    """
    Reverse geocodes coordinates to human-readable address fields:
    village, town, taluka/tehsil, district, state, country, postal_code, formatted_address.
    Uses Nominatim with BigDataCloud fallback, plus robust in-memory caching.
    """
    lat, lon = validate_coordinates(latitude, longitude)
    cache_key = (round(lat, 3), round(lon, 3))

    # Check cache
    if cache_key in _GEOCODE_CACHE:
        cached_time, cached_data = _GEOCODE_CACHE[cache_key]
        if time.time() - cached_time < CACHE_TTL_SECONDS:
            result = dict(cached_data)
            result["cached"] = True
            return result

    result = {
        "latitude": lat,
        "longitude": lon,
        "village": "",
        "town": "",
        "taluka": "",
        "district": "",
        "state": "",
        "country": "India",
        "postal_code": "",
        "formatted_address": f"{lat:.4f}°N, {lon:.4f}°E",
        "source": "Coordinates",
        "cached": False,
    }

    # Attempt 1: OpenStreetMap Nominatim
    try:
        headers = {"User-Agent": "AgriWise-AI-Platform/2.0 (Agricultural Decision Support System)"}
        resp = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lon, "format": "jsonv2", "zoom": 14, "addressdetails": 1},
            headers=headers,
            timeout=5,
        )
        if resp.status_code == 200:
            data = resp.json()
            addr = data.get("address", {})
            village = addr.get("village") or addr.get("hamlet") or addr.get("suburb") or ""
            town = addr.get("town") or addr.get("city") or addr.get("municipality") or ""
            taluka = addr.get("county") or addr.get("subdistrict") or addr.get("state_district") or ""
            district = addr.get("state_district") or addr.get("county") or addr.get("city") or ""
            state = addr.get("state") or ""
            country = addr.get("country") or "India"
            postcode = addr.get("postcode") or ""
            display_name = data.get("display_name", "")

            result.update({
                "village": village,
                "town": town,
                "taluka": taluka,
                "district": district,
                "state": state,
                "country": country,
                "postal_code": postcode,
                "formatted_address": display_name or f"{town or village}, {district}, {state}",
                "source": "OpenStreetMap Nominatim",
            })
            _GEOCODE_CACHE[cache_key] = (time.time(), result)
            return result
    except Exception:
        pass

    # Attempt 2: BigDataCloud Reverse Geocoding API (Fast public free fallback)
    try:
        resp2 = requests.get(
            "https://api.bigdatacloud.net/data/reverse-geocode-client",
            params={"latitude": lat, "longitude": lon, "localityLanguage": "en"},
            timeout=5,
        )
        if resp2.status_code == 200:
            data2 = resp2.json()
            locality = data2.get("locality") or ""
            city = data2.get("city") or locality
            state = data2.get("principalSubdivision") or ""
            country = data2.get("countryName") or "India"
            postcode = data2.get("postcode") or ""

            result.update({
                "village": locality if locality != city else "",
                "town": city,
                "taluka": locality,
                "district": city,
                "state": state,
                "country": country,
                "postal_code": postcode,
                "formatted_address": f"{city}, {state}, {country}".strip(", "),
                "source": "BigDataCloud",
            })
            _GEOCODE_CACHE[cache_key] = (time.time(), result)
            return result
    except Exception:
        pass

    # Graceful fallback: return formatted coordinates
    result["formatted_address"] = f"Farm at ({lat:.4f}, {lon:.4f})"
    result["source"] = "Estimated Coordinates"
    return result


def is_valid_coordinates(latitude: Any, longitude: Any) -> bool:
    try:
        lat = float(latitude)
        lon = float(longitude)
        return -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0
    except (TypeError, ValueError):
        return False


def get_default_farm_location() -> Dict[str, Any]:
    return {
        "latitude": 18.5204,
        "longitude": 73.8567,
        "village": "Haveli",
        "taluka": "Haveli",
        "district": "Pune",
        "state": "Maharashtra",
        "display_name": "Pune, Maharashtra, India",
    }

