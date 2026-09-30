from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from services.expert_system import evaluate_expert_system
from services.fertilizer_service import analyze_nutrients_and_advise
from services.lifecycle_service import get_crop_stage_summary
from services.market_service import get_market_prices_for_commodity
from services.profit_service import aggregate_farm_financials, calculate_crop_profit_potential
from services.risk_service import analyze_comprehensive_farm_risk


def generate_comprehensive_farm_report(
    farmer: Dict[str, Any],
    farm: Dict[str, Any],
    soil: Dict[str, Any],
    crop_cycle: Optional[Dict[str, Any]],
    weather: Dict[str, Any],
    activities: List[Dict[str, Any]],
    disease_reports: List[Dict[str, Any]],
    expenses: List[Dict[str, Any]],
    sales: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Generates a unified, print-ready Farm Intelligence Dossier combining all farm dimensions.
    """
    crop_name = crop_cycle.get("crop_name", "General Crop") if crop_cycle else "No Active Crop"
    sowing_date = crop_cycle.get("sowing_date", "") if crop_cycle else ""

    # Lifecycle details
    lifecycle_info = None
    if crop_cycle and sowing_date:
        lifecycle_info = get_crop_stage_summary(crop_name, sowing_date)
        current_stage = lifecycle_info.get("current_stage", "Vegetative")
    else:
        current_stage = "Planning / Field Preparation"

    # Risk & Condition Score
    risk_info = analyze_comprehensive_farm_risk(
        crop_name=crop_name,
        crop_stage=current_stage,
        weather=weather,
        soil=soil,
        farm=farm,
        activities=activities,
        disease_reports=disease_reports,
    )

    # Expert System Analysis
    expert_info = evaluate_expert_system(
        crop=crop_name,
        crop_stage=current_stage,
        weather=weather,
        soil=soil,
        activity_history=activities,
    )

    # Fertilizer & Nutrients
    nutrient_info = analyze_nutrients_and_advise(
        crop_name=crop_name,
        crop_stage=current_stage,
        soil=soil,
        weather=weather,
        activity_history=activities,
    )

    # Market Intelligence
    market_info = get_market_prices_for_commodity(
        commodity=crop_name,
        farm_lat=farm.get("latitude"),
        farm_lon=farm.get("longitude"),
    )

    # Economics & Profitability
    exp_profit = calculate_crop_profit_potential(
        crop_name=crop_name,
        farm_area=farm.get("area", 1.0),
        area_unit=farm.get("area_unit", "acre"),
        farm_lat=farm.get("latitude"),
        farm_lon=farm.get("longitude"),
    )
    financials = aggregate_farm_financials(expenses, sales, exp_profit)

    # Activity Metrics
    completed_acts = [a for a in activities if str(a.get("status", "")).upper() == "COMPLETED"]
    pending_acts = [a for a in activities if str(a.get("status", "")).upper() == "PENDING"]
    overdue_acts = [a for a in activities if str(a.get("status", "")).upper() == "OVERDUE"]

    report_id = f"AGRI-{farm.get('id', 1):04d}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}"
    generated_at = datetime.now(timezone.utc).strftime("%d %B %Y, %I:%M %p UTC")

    return {
        "report_id": report_id,
        "generated_at": generated_at,
        "farmer": farmer,
        "farm": farm,
        "soil": soil,
        "crop_cycle": crop_cycle,
        "current_stage": current_stage,
        "lifecycle": lifecycle_info,
        "weather": weather,
        "risk_analysis": risk_info,
        "condition_score": risk_info["condition_score"],
        "expert_system": expert_info,
        "nutrient_intelligence": nutrient_info,
        "market_intelligence": market_info,
        "projected_profitability": exp_profit,
        "actual_financials": financials,
        "activity_summary": {
            "total_activities": len(activities),
            "completed": len(completed_acts),
            "pending": len(pending_acts),
            "overdue": len(overdue_acts),
            "recent_completed": completed_acts[:5],
            "pending_tasks": pending_acts[:5],
        },
        "disease_reports": disease_reports,
        "data_provenance": {
            "weather_provider": "Open-Meteo High-Resolution Numerical Weather Model",
            "market_data_source": "Agmarknet / DMI Government of India APMC Network",
            "crop_knowledge_source": "ICAR Agricultural Research Institutes & SAU Package of Practices",
            "soil_data_status": "Farmer Entered / Soil Health Card Baseline",
        },
    }
