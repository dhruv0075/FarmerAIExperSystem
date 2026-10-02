from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from services.market_service import haversine_distance_km

BASE_DIR = Path(__file__).resolve().parent.parent
from config import DATA_DIR
CATALOG_PATH = DATA_DIR / "resource_catalog.json"

_RESOURCE_CACHE: List[Dict[str, Any]] = []


def _load_resources() -> List[Dict[str, Any]]:
    # The bundled catalog was generated in scripts/, not obtained from sellers
    # or a directory. Preserve it on disk, but never present it as verified.
    return []


def find_nearby_resources(
    farm_lat: Optional[float] = None,
    farm_lon: Optional[float] = None,
    category: Optional[str] = None,
    max_radius_km: float = 100.0,
) -> Dict[str, Any]:
    """
    Finds verified agricultural resources near the farm, computes distances,
    and formats items with transparent stock and pricing disclosures.
    """
    raw_resources = _load_resources()
    category_filter = category.upper().strip() if category and category.lower() != "all" else None

    results = []
    for entry in raw_resources:
        if category_filter and entry.get("category") != category_filter:
            continue

        res_lat = entry.get("latitude")
        res_lon = entry.get("longitude")
        dist = None
        if farm_lat is not None and farm_lon is not None and res_lat and res_lon:
            dist = haversine_distance_km(farm_lat, farm_lon, res_lat, res_lon)
            if dist > max_radius_km:
                continue

        # Format items with honest disclosures
        formatted_items = []
        for it in entry.get("items", []):
            p_status = it.get("price_status", "UNAVAILABLE")
            price_display = f"₹{it.get('price'):.2f} / {it.get('unit')}" if it.get("price") else "Price unavailable — contact seller"
            if p_status == "SELLER_LISTED":
                price_badge = "Seller-Listed Price"
            elif p_status == "VERIFIED":
                price_badge = "Verified Govt / MRP Price"
            else:
                price_badge = "Price Not Confirmed"

            formatted_items.append({
                "item_name": it.get("item_name"),
                "brand": it.get("brand", "Standard"),
                "composition": it.get("composition", ""),
                "price": it.get("price"),
                "price_display": price_display,
                "price_badge": price_badge,
                "stock_status": it.get("stock_status", "Availability not confirmed"),
            })

        # Directions URL via OpenStreetMap
        directions_url = f"https://www.openstreetmap.org/directions?engine=fossgis_osrm_car&route={farm_lat}%2C{farm_lon}%3B{res_lat}%2C{res_lon}" if farm_lat and res_lat else f"https://www.openstreetmap.org/?mlat={res_lat}&mlon={res_lon}#map=15/{res_lat}/{res_lon}"

        results.append({
            "name": entry.get("name"),
            "category": entry.get("category"),
            "seller_name": entry.get("seller_name"),
            "address": entry.get("address"),
            "district": entry.get("district"),
            "state": entry.get("state"),
            "latitude": res_lat,
            "longitude": res_lon,
            "contact_phone": entry.get("contact_phone"),
            "is_seller_listed": entry.get("is_seller_listed", False),
            "distance_km": dist,
            "directions_url": directions_url,
            "items": formatted_items,
        })

    # Sort results by distance ascending
    results.sort(key=lambda x: x["distance_km"] if x["distance_km"] is not None else 9999)

    return {
        "farm_coordinates": {"latitude": farm_lat, "longitude": farm_lon} if farm_lat else None,
        "category_filtered": category_filter or "ALL",
        "total_found": len(results),
        "resources": results,
    }


def add_custom_resource_listing(listing_data: Dict[str, Any]) -> Dict[str, Any]:
    """Allows adding custom or local dealer listings, clearly labeled as seller-listed."""
    resources = _load_resources()
    new_entry = {
        "name": listing_data.get("name", "Local Agri Supplier"),
        "category": listing_data.get("category", "SUPPLY").upper(),
        "seller_name": listing_data.get("seller_name", "Local Vendor"),
        "address": listing_data.get("address", ""),
        "district": listing_data.get("district", ""),
        "state": listing_data.get("state", "Maharashtra"),
        "latitude": float(listing_data.get("latitude", 18.52)),
        "longitude": float(listing_data.get("longitude", 73.85)),
        "contact_phone": listing_data.get("contact_phone", ""),
        "is_seller_listed": True,
        "items": [
            {
                "item_name": listing_data.get("item_name", "Agricultural Input"),
                "brand": listing_data.get("brand", "Local"),
                "composition": listing_data.get("composition", "Standard"),
                "price": float(listing_data.get("price", 0.0)) if listing_data.get("price") else None,
                "unit": listing_data.get("unit", "Unit"),
                "stock_status": listing_data.get("stock_status", "Available on request"),
                "price_status": "SELLER_LISTED",
            }
        ] if listing_data.get("item_name") else [],
    }
    resources.append(new_entry)
    CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CATALOG_PATH.open("w", encoding="utf-8") as f:
        json.dump(resources, f, indent=2)
    return new_entry


def get_nearby_resources(
    farm_lat: Optional[float] = None,
    farm_lon: Optional[float] = None,
    category: Optional[str] = None,
    max_radius_km: float = 100.0,
    verified_only: bool = False,
) -> List[Dict[str, Any]]:
    res_dict = find_nearby_resources(farm_lat, farm_lon, category, max_radius_km)
    items = res_dict.get("resources", [])
    if verified_only:
        items = [it for it in items if not it.get("is_seller_listed", False)]
    return items


def get_resource_types() -> List[str]:
    return ["All", "Fertilizer Retailer", "Seed Store", "Soil Testing Lab", "Cold Storage", "Custom Hiring Center"]

