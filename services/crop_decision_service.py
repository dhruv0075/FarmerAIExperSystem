from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from services.crop_ml_service import predict_crop_ml
from services.market_service import get_market_prices_for_commodity
from services.suitability_service import calculate_suitability_score, get_crop_knowledge


def rank_and_explain_crops(
    soil: Dict[str, Any],
    weather: Dict[str, Any],
    farm: Optional[Dict[str, Any]] = None,
    farmer_preferences: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Two-Level Crop Recommendation Engine:
    - Level 1: ML Agronomic Probability from trained Random Forest classifier
    - Level 2: AgriWise Multi-Factor Decision Ranking integrating ML probability,
      agronomic match, weather compatibility, water availability, farm soil type,
      mandi market attractiveness, cultivation cost, and farmer risk preference.
    """
    farm = farm or {}
    farmer_preferences = farmer_preferences or {}
    risk_pref = (farmer_preferences.get("risk_preference") or farm.get("risk_preference") or "Balanced").strip().lower()
    crop_pref = (farmer_preferences.get("preferred_crop_type") or farm.get("preferred_crop_type") or "No preference").strip().lower()
    farm_lat = farm.get("latitude")
    farm_lon = farm.get("longitude")

    # 1. Level 1: ML Classifier
    ml_result = predict_crop_ml(soil)
    ml_probs = ml_result.get("all_probabilities", {})

    all_crop_keys = list(get_crop_knowledge().keys())
    candidate_scores = []

    for crop_key in all_crop_keys:
        crop_info = get_crop_knowledge(crop_key)
        if not crop_info:
            continue

        # ML Probability (0 - 100)
        ml_prob = float(ml_probs.get(crop_key, 0.0))

        # Suitability Engine (Agronomic, Weather, Farm)
        suitability = calculate_suitability_score(crop_key, soil, weather, farm)
        agro_score = suitability["overall_suitability"]
        weather_score = suitability["weather_score"]
        soil_score = suitability["soil_score"]
        farm_score = suitability["farm_score"]

        # Market Attractiveness
        market_res = get_market_prices_for_commodity(crop_key, farm_lat, farm_lon)
        market_score = 0.0
        best_market = market_res.get("best_market")
        if best_market:
            market_score = float(best_market.get("opportunity_score", 65.0))

        # Risk preference weighting
        crop_risk_category = "Low" if crop_info.get("water_category") in ["Low", "Very Low"] else "Moderate"
        if crop_info.get("category", "").startswith("Cash") or crop_info.get("category", "").startswith("Fruit"):
            crop_risk_category = "Higher"

        risk_fit = 80.0
        if "low" in risk_pref:
            if crop_risk_category == "Low":
                risk_fit = 100.0
            elif crop_risk_category == "Higher":
                risk_fit = 40.0
        elif "high" in risk_pref or "profit" in risk_pref:
            if crop_risk_category == "Higher":
                risk_fit = 100.0
            elif crop_risk_category == "Low":
                risk_fit = 60.0

        # Preferred crop type filter bonus
        pref_bonus = 0.0
        if crop_pref != "no preference":
            c_cat = crop_info.get("category", "").lower()
            if "cash" in crop_pref and "cash" in c_cat:
                pref_bonus = 10.0
            elif "food" in crop_pref and ("cereal" in c_cat or "pulse" in c_cat):
                pref_bonus = 10.0
            elif "fruit" in crop_pref and "fruit" in c_cat:
                pref_bonus = 10.0
            elif "vegetable" in crop_pref and "vegetable" in c_cat:
                pref_bonus = 10.0

        # Weighted Decision Ranking Formula:
        # ML Prob: 25%, Agronomic/Soil Suitability: 25%, Weather Suitability: 20%,
        # Farm Compatibility: 10%, Market Attractiveness: 10%, Risk Fit: 10%
        final_decision_score = (
            ml_prob * 0.25
            + agro_score * 0.25
            + weather_score * 0.20
            + farm_score * 0.10
            + market_score * 0.10
            + risk_fit * 0.10
            + pref_bonus
        )
        final_decision_score = round(min(100.0, max(10.0, final_decision_score)), 1)

        # Economics estimation
        econ = crop_info.get("economics", {})
        yield_range = econ.get("yield_range_quintals_per_acre", [10, 20])
        cost_range = econ.get("input_cost_range_per_acre", [15000, 25000])
        price_bench = econ.get("benchmark_selling_price_per_quintal", [2000, 3000])
        if best_market and best_market.get("modal_price"):
            m_modal = float(best_market["modal_price"])
            price_bench = [round(m_modal * 0.95, 0), round(m_modal * 1.05, 0)]

        rev_min = round(yield_range[0] * price_bench[0], 0)
        rev_max = round(yield_range[1] * price_bench[1], 0)
        profit_min = round(rev_min - cost_range[1], 0)
        profit_max = round(rev_max - cost_range[0], 0)

        candidate_scores.append({
            "crop_key": crop_key,
            "crop_name": crop_info.get("name", crop_key.capitalize()),
            "category": crop_info.get("category", "General"),
            "season": crop_info.get("season", "All"),
            "water_category": crop_info.get("water_category", "Medium"),
            "duration_days": crop_info.get("total_duration_days", 120),
            "ml_confidence": round(ml_prob, 1),
            "ml_probability": round(ml_prob, 1),
            "decision_score": final_decision_score,
            "final_decision_score": final_decision_score,
            "suitability_score": agro_score,
            "weather_score": weather_score,
            "soil_score": soil_score,
            "farm_score": farm_score,
            "market_score": market_score,
            "risk_category": crop_risk_category,
            "economics": {} if not econ.get("verified_source_url") else {
                "expected_price_range": price_bench,
                "yield_range_quintals": yield_range,
                "cost_range_inr": cost_range,
                "revenue_range_inr": [rev_min, rev_max],
                "profit_range_inr": [profit_min, profit_max],
                "source": econ.get("source", "Agricultural Universities / ICAR"),
            },
            "best_market": best_market,
            "suitability_details": suitability["details"],
        })

    # Sort descending by AgriWise Multi-Factor Decision Score
    candidate_scores.sort(key=lambda x: x["decision_score"], reverse=True)

    top_crop = candidate_scores[0]
    top_3_alternatives = candidate_scores[1:4]

    # Generate Explainable AI Explanation for Top Recommendation
    explanation = _build_recommendation_explanation(top_crop, soil, weather, farm)

    return {
        "primary_recommendation": top_crop,
        "alternatives": top_3_alternatives,
        "all_ranked_candidates": candidate_scores[:10],
        "decision_ranked_crops": candidate_scores,
        "ranked_crops": candidate_scores,
        "explanation": explanation,
        "ml_top_crop": ml_result["recommended_crop"],
        "ml_top_confidence": ml_result["confidence"],
    }


def _build_recommendation_explanation(
    crop_item: Dict[str, Any],
    soil: Dict[str, Any],
    weather: Dict[str, Any],
    farm: Dict[str, Any],
) -> Dict[str, Any]:
    name = crop_item["crop_name"]
    details = crop_item["suitability_details"]
    c_curr = weather.get("current", {})

    positive_factors = []
    risk_factors = []
    weather_factors = []
    soil_factors = []
    market_factors = []

    # Soil factors
    if details.get("ph_match", 0) >= 80:
        soil_factors.append(f"Soil pH ({soil.get('ph', 6.5)}) is optimal for {name} root nutrient uptake.")
    if details.get("nitrogen_match", 0) >= 75:
        soil_factors.append(f"Available Nitrogen ({soil.get('nitrogen', 60)} kg/ha) matches agronomic threshold.")
    positive_factors.extend(soil_factors)

    # Weather factors
    w_temp = c_curr.get("temperature", 28.0)
    w_hum = c_curr.get("humidity", 65.0)
    if details.get("temperature_match", 0) >= 75:
        weather_factors.append(f"Ambient temperature of {w_temp:.1f}°C aligns with growth tolerance ranges.")
    if details.get("humidity_match", 0) >= 70:
        weather_factors.append(f"Relative humidity of {w_hum:.0f}% supports steady vegetative development.")
    positive_factors.extend(weather_factors)

    # Market factors
    bm = crop_item.get("best_market")
    if bm:
        market_factors.append(
            f"Favorable mandi demand at {bm['market_name']} with latest modal price of ₹{bm['modal_price']}/quintal "
            f"and trend '{bm.get('price_trend', 'Stable')}'."
        )
        positive_factors.extend(market_factors)

    # Risk factors
    if crop_item.get("water_category") == "High" and str(farm.get("water_availability", "")).lower() in ["limited", "seasonal"]:
        risk_factors.append("High water demand may require supplemental irrigation during dry periods.")
    if float(c_curr.get("wind_speed", 0)) > 20:
        risk_factors.append("Current moderate winds may affect seedling establishment.")
    if not risk_factors:
        risk_factors.append("Standard crop management vigilance required; no immediate critical agronomic barriers detected.")

    summary = (
        f"{name} is strongly recommended with an AgriWise Decision Score of {crop_item['decision_score']}/100. "
        f"The agronomic soil match is {crop_item['soil_score']}%, current weather compatibility is {crop_item['weather_score']}%, "
        f"market data is {'available' if bm else 'unavailable; profit cannot be established'}."
    )

    return {
        "summary": summary,
        "positive_factors": positive_factors,
        "risk_factors": risk_factors,
        "soil_factors": soil_factors,
        "weather_factors": weather_factors,
        "market_factors": market_factors,
        "data_provenance": "Local ML dataset and configured agronomic heuristics; provenance not verified. Market observations are included only when fetched from the official API.",
    }
