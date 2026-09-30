from __future__ import annotations

from typing import Any, Dict, List

from services.crop_service import compare_crop_dataset_fit


def build_explanation(prediction_result: Dict[str, Any], soil_values: Dict[str, Any]) -> Dict[str, Any]:
    crop_name = str(prediction_result.get("recommended_crop", ""))
    profile = compare_crop_dataset_fit(soil_values, [crop_name])
    feature_scores = profile[0]["feature_scores"] if profile else {}
    ordered_scores = sorted(feature_scores.items(), key=lambda item: item[1], reverse=True)
    positive_factors = [f"{name.title()} is relatively close to the {crop_name} examples in the supplied dataset ({score}/100 profile match)." for name, score in ordered_scores[:3] if score >= 50]
    improvement_factors = [f"{name.title()} is less similar to the supplied {crop_name} dataset profile ({score}/100 profile match); review local soil and weather evidence." for name, score in ordered_scores[-2:] if score < 50]
    top_3 = prediction_result.get("top_3", [])
    bullets = [f"The trained classifier ranked {crop_name} first with {prediction_result.get('confidence', 0)}% model confidence."]
    bullets.extend(positive_factors)
    if len(top_3) > 1:
        bullets.append(f"The next model alternative was {top_3[1]['crop']} at {top_3[1]['confidence']}% classifier probability.")

    return {
        "title": "Why this recommendation was generated",
        "confidence": prediction_result.get("confidence", 0),
        "bullets": bullets,
        "positive_factors": positive_factors,
        "improvement_factors": improvement_factors,
        "dataset_fit": profile[0]["dataset_fit"] if profile else None,
        "dataset_fit_note": "Dataset-profile match is a configured distance indicator, not model confidence or validated agronomic suitability.",
    }
