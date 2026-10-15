"""Image screening and non-diagnostic advisories for crop problems."""
import io
import logging
from typing import Any, Callable, Dict, List, Optional

from PIL import Image


LOGGER = logging.getLogger(__name__)

_CROP_ALIASES = {
    "corn": "maize",
    "cornmaize": "maize",
    "maize": "maize",
    "cherryincludingsour": "cherry",
    "cherry": "cherry",
    "pepperbell": "bellpepper",
    "bellpepper": "bellpepper",
}


def _canonical_crop_name(crop_name: str) -> str:
    normalized = "".join(character for character in crop_name.casefold() if character.isalnum())
    return _CROP_ALIASES.get(normalized, normalized)


def is_suggestion_for_crop(reported_crop: str, suggested_crop: str) -> bool:
    return (
        isinstance(reported_crop, str)
        and isinstance(suggested_crop, str)
        and bool(_canonical_crop_name(reported_crop))
        and _canonical_crop_name(reported_crop) == _canonical_crop_name(suggested_crop)
    )


def _unavailable_screening(
    reason: str,
    message: str,
    model_available: bool = False,
    screening_status: str = "uncertain",
) -> Dict[str, Any]:
    return {
        "has_image": True,
        "model_available": model_available,
        "screening_status": screening_status,
        "reason": reason,
        "message": message,
    }


def _screen_image(
    image_bytes: Optional[bytes],
    predictor: Optional[Callable[[Image.Image], Dict[str, Any]]],
    image_filename: Optional[str] = None,
    crop_name: str = "",
) -> Dict[str, Any]:
    if not image_bytes:
        if image_filename:
            return _unavailable_screening(
                "image_unavailable",
                "An image is attached to the report, but its contents were unavailable for screening.",
            )
        return {
            "has_image": False,
            "model_available": False,
            "screening_status": "not_requested",
            "reason": "no_image",
            "message": "No image was provided, so image screening was not run.",
        }

    try:
        if predictor is None:
            from agriwise_disease_model.disease_predictor import predict_disease

            predictor = predict_disease
        with Image.open(io.BytesIO(image_bytes)) as uploaded:
            uploaded.load()
            result = predictor(uploaded.convert("RGB"))
    except (ImportError, FileNotFoundError, OSError, RuntimeError, ValueError):
        LOGGER.exception("Disease image screening could not load or run the configured model")
        return _unavailable_screening(
            "model_unavailable",
            "The image could not be screened because the disease model is unavailable. Install the optional model dependencies and verify the model files.",
        )

    if not isinstance(result, dict):
        LOGGER.error("Disease predictor returned a non-object response")
        return _unavailable_screening(
            "invalid_model_response",
            "Image screening returned an invalid response. Please try again later.",
            model_available=True,
        )

    status = result.get("status")
    if status == "prediction":
        crop = result.get("crop")
        predicted_class = result.get("predicted_class")
        disease = result.get("disease")
        confidence = result.get("confidence")
        message = result.get("message")
        valid_prediction = (
            all(isinstance(value, str) and value.strip() for value in (crop, predicted_class, disease, message))
            and not isinstance(confidence, bool)
            and isinstance(confidence, (int, float))
            and 0 <= confidence <= 100
        )
        if not valid_prediction:
            LOGGER.error("Disease predictor returned an invalid prediction payload")
            return _unavailable_screening(
                "invalid_model_response",
                "Image screening returned an invalid response. Please try again later.",
                model_available=True,
            )
        if not is_suggestion_for_crop(crop_name, crop):
            screening = _unavailable_screening(
                "crop_mismatch",
                (
                    f"The model's closest class is for {crop.strip()}, which does not match "
                    f"the selected crop {crop_name.strip()}. No disease suggestion is shown "
                    "because this classifier has no matching crop class."
                ),
                model_available=True,
                screening_status="unsupported",
            )
            screening["suggested_crop"] = crop.strip()
            return screening
        return {
            "has_image": True,
            "model_available": True,
            "screening_status": "suggestion",
            "reason": "unverified_model_suggestion",
            "message": (
                "This is the model's closest match among its 38 PlantVillage classes, "
                "not a confirmed diagnosis. Its score is uncalibrated, and unfamiliar "
                "field images may be misclassified. Consult a qualified agricultural expert."
            ),
            "suggestion": {
                "crop": crop.strip(),
                "disease": disease.strip(),
                "class_label": predicted_class,
                "model_score": round(float(confidence), 2),
            },
        }
    if status in {"uncertain", "unsupported"}:
        message = result.get("message")
        reason = result.get("reason")
        if isinstance(message, str) and message.strip() and isinstance(reason, str) and reason.strip():
            return _unavailable_screening(
                reason.strip(),
                message.strip(),
                model_available=True,
            )

    LOGGER.error("Disease predictor returned an unsupported response status")
    return _unavailable_screening(
        "invalid_model_response",
        "The model returned an unsupported screening response.",
        model_available=True,
    )


def screen_crop_image(
    crop_name: str,
    image_bytes: bytes,
    image_filename: Optional[str] = None,
    predictor: Optional[Callable[[Image.Image], Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Screen one image without creating or changing a problem report."""
    return _screen_image(image_bytes, predictor, image_filename, crop_name)


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
    predictor: Optional[Callable[[Image.Image], Dict[str, Any]]] = None,
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

    screening = _screen_image(image_bytes, predictor, image_filename, crop_name)
    if screening["has_image"]:
        evidence.append(screening["message"])

    return {
        "supported_by_image_ai": False,
        "image_analysis": screening,
        "primary_diagnosis": {
            "condition": "Diagnosis unavailable; expert inspection needed",
            "confidence": None,
            "risk_level": "UNASSESSED",
            "weather_context": " ".join(evidence),
            "inspection_steps": steps,
            "management": ["Avoid chemical treatment until the cause has been confirmed."],
        },
        "alternatives": [],
        "disclaimer": (
            "Any image-model match is an unverified screening suggestion, not a confirmed diagnosis. "
            "Its score is not a calibrated probability or an accuracy measurement; seek qualified local advice."
        ),
    }


def get_past_problem_reports(farm_id: int, db_conn) -> List[Dict[str, Any]]:
    rows = db_conn.execute(
        "SELECT * FROM disease_reports WHERE farm_id = ? ORDER BY id DESC LIMIT 10",
        (farm_id,),
    ).fetchall()
    return [dict(r) for r in rows]
