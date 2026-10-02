"""Manual problem records and transparent contextual guidance; no image diagnosis."""
from typing import Any, Dict, List, Optional
from config import UPLOAD_DIR

def analyze_crop_issue(
    crop_name: str,
    plant_part: str = "Leaf",
    symptoms_text: str = "",
    category: str = "Unknown",
    weather_data: Optional[Dict[str, Any]] = None,
    image_bytes: Optional[bytes] = None,
    image_filename: Optional[str] = None,
    duration_days: int = 3,
    affected_area_pct: float = 15.0,
    severity: str = "Moderate",
) -> Dict[str, Any]:
    steps = ["Document affected plant parts and how symptoms spread.", "Contact a local agricultural extension officer."]
    evidence = [f"Farmer reports symptoms on {plant_part} of {crop_name}: {symptoms_text}"]
    current = (weather_data or {}).get("current", {})
    humidity = current.get("humidity")
    if humidity is not None and humidity >= 85:
        steps.append("Check damp or densely shaded foliage for changes; high humidity alone does not identify a disease.")
        evidence.append(f"Reported weather humidity: {humidity}%.")
    if any(word in symptoms_text.lower() for word in ("pest", "insect", "chew", "hole")):
        steps.append("Inspect leaf undersides for visible insects and photograph any damage for an expert.")
    if severity.lower() == "severe":
        steps.append("Seek prompt local expert assessment for the reported severe damage.")
    return {
        "supported_by_image_ai": False,
        "primary_diagnosis": {
            "condition": "Diagnosis unavailable; expert inspection needed",
            "confidence": None,
            "risk_level": "UNASSESSED",
            "weather_context": " ".join(evidence),
            "inspection_steps": steps,
            "management": ["Avoid chemical treatment until the cause has been confirmed."],
        },
        "alternatives": [],
        "image_analysis": {"has_image": bool(image_filename or image_bytes), "model_available": False},
        "disclaimer": "Manual symptom report, not an image diagnosis. Disease model and evaluation data are unavailable.",
    }

def get_past_problem_reports(farm_id: int, db_conn) -> List[Dict[str, Any]]:
    try:
        rows = db_conn.execute(
            "SELECT * FROM disease_reports WHERE farm_id = ? ORDER BY id DESC LIMIT 10",
            (farm_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []

