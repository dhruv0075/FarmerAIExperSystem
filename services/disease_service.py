"""Non-diagnostic advisories for farmer-reported crop problems."""
from typing import Any, Dict, List, Optional


def analyze_crop_issue(
    crop_name: str,
    plant_part: str = "Leaf",
    symptoms_text: str = "",
    category: str = "Unknown",
    weather_data: Optional[Dict[str, Any]] = None,
    image_bytes: Optional[bytes] = None,
    image_filename: Optional[str] = None,
    duration_days: Optional[int] = None,
    affected_area_pct: Optional[float] = None,
    severity: str = "Moderate",
) -> Dict[str, Any]:
    steps = [
        "Document affected plant parts and how symptoms spread.",
        "Contact a local agricultural extension officer for confirmation.",
    ]
    evidence = [f"Farmer reports symptoms on {plant_part} of {crop_name}: {symptoms_text}"]
    if category and category.lower() != "unknown":
        evidence.append(f"Farmer-selected problem category: {category}.")
    if duration_days is not None:
        evidence.append(f"Farmer-reported duration: {duration_days} days.")
    if affected_area_pct is not None:
        evidence.append(f"Farmer-estimated affected area: {affected_area_pct}%.")
    current = (weather_data or {}).get("current", {})
    humidity = current.get("humidity")
    if humidity is not None and humidity >= 85:
        steps.append("Check damp or densely shaded foliage for changes; high humidity alone does not identify a disease.")
        evidence.append(f"Reported weather humidity: {humidity}%.")
    if any(word in symptoms_text.lower() for word in ("pest", "insect", "chew", "hole")):
        steps.append("Inspect leaf undersides for visible insects and photograph any damage for an expert.")
    if severity.lower() == "severe":
        steps.append("Seek prompt local expert assessment for the reported severe damage.")

    has_reference_photo = bool(image_bytes or image_filename)
    image_analysis = {
        "has_image": has_reference_photo,
        "model_available": False,
        "screening_status": "not_requested",
        "reason": "problem_report_reference_only" if has_reference_photo else "no_image",
        "message": (
            "The photo is stored as reference material; no image screening is performed."
            if has_reference_photo
            else "No image was provided."
        ),
    }
    if has_reference_photo:
        evidence.append(image_analysis["message"])

    return {
        "supported_by_image_ai": False,
        "image_analysis": image_analysis,
        "primary_diagnosis": {
            "condition": "Diagnosis unavailable; expert inspection needed",
            "confidence": None,
            "risk_level": "UNASSESSED",
            "weather_context": " ".join(evidence),
            "inspection_steps": steps,
            "management": ["Avoid chemical treatment until the cause has been confirmed."],
        },
        "alternatives": [],
        "disclaimer": "This report does not provide a confirmed diagnosis; seek qualified local advice.",
    }


def get_past_problem_reports(farm_id: int, db_conn) -> List[Dict[str, Any]]:
    rows = db_conn.execute(
        "SELECT * FROM disease_reports WHERE farm_id = ? ORDER BY id DESC LIMIT 10",
        (farm_id,),
    ).fetchall()
    return [dict(r) for r in rows]
