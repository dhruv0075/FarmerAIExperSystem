from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
MARKET_DATA_PATH = BASE_DIR / "data" / "market_data.json"

_MARKET_CACHE: Dict[str, Any] = {}


def _load_market_data(filters=None) -> Dict[str, Any]:
    from services.official_market_service import load_official_market_data
    return load_official_market_data(filters)


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two geographic coordinates in kilometers."""
    R = 6371.0  # Earth radius in kilometers
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2.0) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(R * c, 1)


def get_market_prices_for_commodity(
    commodity: str,
    farm_lat: Optional[float] = None,
    farm_lon: Optional[float] = None,
    transport_cost_per_km_per_quintal: float = 0.50,  # ₹0.50 per quintal per km (~₹50/ton-km)
    state: str = '', district: str = '', market: str = '',
) -> Dict[str, Any]:
    filters = {'commodity': commodity.title()}
    filters.update({k: v for k, v in {'state': state, 'district': district, 'market': market}.items() if v})
    data = _load_market_data(filters)
    raw_key = commodity.lower().strip()
    commodities = data.get("commodities", {})

    # Match key
    matched_key = None
    if raw_key in commodities:
        matched_key = raw_key
    else:
        for k in commodities:
            if k in raw_key or raw_key in k:
                matched_key = k
                break

    if not matched_key:
        return {
            "commodity": commodity,
            "found": False,
            "message": data.get('message') or f"No official records match '{commodity}' in this sample.",
            "fetch_timestamp": data.get('updated_at'),
            "source_url": data.get('source_url'),
            "refresh_status": data.get('refresh_status', 'unavailable'),
            "refresh_in_progress": data.get('refresh_in_progress', False),
            "retry_after_seconds": data.get('retry_after_seconds', 0),
            "source": data.get("source", "Agmarknet / DMI Government of India"),
            "markets": [],
        }

    comm_info = commodities[matched_key]
    prices_by_market = comm_info.get("prices", {})
    all_markets = {m["name"]: m for m in data.get("markets", [])}

    results = []
    best_opportunity = None
    max_net_return = -1e9

    for market_name, pinfo in prices_by_market.items():
        m_meta = all_markets.get(market_name, {})
        m_lat = m_meta.get("latitude")
        m_lon = m_meta.get("longitude")

        distance_km = None
        est_transport_cost = None
        est_net_return = None

        if farm_lat is not None and farm_lon is not None and m_lat and m_lon:
            distance_km = haversine_distance_km(farm_lat, farm_lon, m_lat, m_lon)
            est_transport_cost = round(distance_km * transport_cost_per_km_per_quintal, 1)
            est_net_return = round(pinfo.get("modal", 0) - est_transport_cost, 1)

        # Opportunity Score (0 - 100) combining price and distance
        modal_val = float(pinfo.get("modal", 0))
        dist_factor = max(0.2, 1.0 - (distance_km / 300.0)) if distance_km is not None else 0.8
        trend_bonus = 5.0 if pinfo.get("trend") == "Up" else (0.0 if pinfo.get("trend") == "Stable" else -5.0)
        opp_score = min(100.0, max(20.0, round((modal_val / 30.0) * dist_factor + trend_bonus, 1)))

        m_entry = {
            "market_name": market_name,
            "district": m_meta.get("district", ""),
            "state": m_meta.get("state", ""),
            "latitude": m_lat,
            "longitude": m_lon,
            "min_price": pinfo.get("min"),
            "max_price": pinfo.get("max"),
            "modal_price": pinfo.get("modal"),
            "price_date": pinfo.get("date"),
            "is_stale": (datetime.now(timezone.utc).date() - datetime.fromisoformat(pinfo["date"]).date()).days > 3,
            "price_trend": pinfo.get("trend", "Stable"),
            "distance_km": distance_km,
            "estimated_transport_cost": est_transport_cost,
            "estimated_net_return": est_net_return,
            "opportunity_score": opp_score,
            "unit": comm_info.get("unit", "₹ / Quintal"),
        }
        results.append(m_entry)

        if est_net_return is not None and est_net_return > max_net_return:
            max_net_return = est_net_return
            best_opportunity = m_entry

    # Sort results by estimated net return descending
    results.sort(key=lambda x: x["modal_price"], reverse=True)

    # Build human explanation of best market selection
    explanation = "Transport-aware ranking unavailable without verified market coordinates and transport costs. Prices are gross observations, not guaranteed sale offers."
    if best_opportunity and len(results) > 1:
        nearest_m = min(results, key=lambda x: x["distance_km"] if x["distance_km"] is not None else 9999)
        highest_p = max(results, key=lambda x: x["modal_price"])

        if best_opportunity["market_name"] == nearest_m["market_name"] == highest_p["market_name"]:
            explanation = (
                f"{best_opportunity['market_name']} is currently both the closest market ({best_opportunity['distance_km']} km) "
                f"and offers the highest modal price of ₹{best_opportunity['modal_price']}/quintal."
            )
        elif best_opportunity["market_name"] == nearest_m["market_name"]:
            explanation = (
                f"{best_opportunity['market_name']} offers the best net return (₹{best_opportunity['estimated_net_return']}/quintal) "
                f"because lower transport impact outweighs slightly higher gross prices at more distant markets."
            )
        elif best_opportunity["market_name"] == highest_p["market_name"]:
            explanation = (
                f"{best_opportunity['market_name']} offers significantly higher modal price (₹{best_opportunity['modal_price']}/quintal) "
                f"which more than offsets the transport cost of traveling {best_opportunity['distance_km']} km."
            )
        else:
            explanation = (
                f"{best_opportunity['market_name']} provides the optimal balance of high market price and reasonable distance, "
                f"yielding estimated net return of ₹{best_opportunity['estimated_net_return']}/quintal."
            )

    return {
        "commodity": matched_key.capitalize(),
        "variety": comm_info.get("variety", "Standard"),
        "unit": comm_info.get("unit", "₹ / Quintal"),
        "found": True,
        "is_stale": data.get('is_stale', False),
        "refresh_status": data.get('refresh_status', 'unavailable'),
        "refresh_in_progress": data.get('refresh_in_progress', False),
        "retry_after_seconds": data.get('retry_after_seconds', 0),
        "source": data.get("source", "Agmarknet / DMI Government of India"),
        "fetch_timestamp": data.get("updated_at", datetime.now(timezone.utc).isoformat()),
        "history_30d": comm_info.get("history_30d", []),
        "markets": results,
        "best_market": best_opportunity,
        "decision_explanation": explanation,
        "transport_rate_used": transport_cost_per_km_per_quintal,
    }


def get_all_available_commodities() -> List[str]:
    data = _load_market_data()
    return sorted([k.capitalize() for k in data.get("commodities", {}).keys()])


get_all_commodities = get_all_available_commodities

