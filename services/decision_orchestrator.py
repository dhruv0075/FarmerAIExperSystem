from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from services.activity_service import is_overdue
from services.expert_system import latest_completed_activity, hours_since
from services.expert_system import evaluate_expert_system
from services.fertilizer_service import analyze_nutrients_and_advise
from services.market_service import get_market_prices_for_commodity
from services.risk_service import analyze_comprehensive_farm_risk


class FarmState:
    """
    Central persistent digital representation of the farm.
    Maintains synchronized state across sensors, weather, soil,
    activities, disease reports, markets, and lifecycle stages.
    """
    def __init__(
        self,
        farmer: Dict[str, Any],
        farm: Dict[str, Any],
        soil: Dict[str, Any],
        crop_cycle: Optional[Dict[str, Any]],
        weather: Dict[str, Any],
        activities: List[Dict[str, Any]],
        disease_reports: List[Dict[str, Any]],
        expenses: List[Dict[str, Any]],
        sales: List[Dict[str, Any]],
    ):
        self.farmer = farmer or {}
        self.farm = farm or {}
        self.soil = soil or {}
        self.crop_cycle = crop_cycle
        self.weather = weather or {}
        self.activities = activities or []
        self.disease_reports = disease_reports or []
        self.expenses = expenses or []
        self.sales = sales or []

    @property
    def crop_name(self) -> str:
        return self.crop_cycle.get("crop_name", "General Crop") if self.crop_cycle else "No Active Crop"

    @property
    def crop_stage(self) -> str:
        return self.crop_cycle.get("current_stage", "Vegetative") if self.crop_cycle else "Preparation"


def build_unified_daily_farm_plan(farm_state: FarmState) -> Dict[str, Any]:
    """
    Orchestrates decisions across all engines and produces Today's AgriWise Farm Plan:
    DO FIRST, TODAY, WATCH, AVOID, MARKET, WEATHER.
    """
    crop = farm_state.crop_name
    stage = farm_state.crop_stage
    weather = farm_state.weather
    soil = farm_state.soil
    farm = farm_state.farm
    activities = farm_state.activities

    # 1. Run Expert Inference
    expert_res = evaluate_expert_system(
        crop=crop,
        crop_stage=stage,
        weather=weather,
        soil=soil,
        activity_history=activities,
    )

    # 2. Run Risk Analysis
    risk_res = analyze_comprehensive_farm_risk(
        crop_name=crop,
        crop_stage=stage,
        weather=weather,
        soil=soil,
        farm=farm,
        activities=activities,
        disease_reports=farm_state.disease_reports,
    )

    # 3. Market Intelligence
    market_res = get_market_prices_for_commodity(
        commodity=crop,
        farm_lat=farm.get("latitude"),
        farm_lon=farm.get("longitude"),
    )
    best_market = market_res.get("best_market")

    # 4. Construct DO FIRST, TODAY, WATCH, AVOID
    do_first = None
    today_tasks = []
    watch_items = []
    avoid_items = []

    # Check for urgent weather / conflict advisories to populate AVOID
    curr_wind = float(weather.get("current", {}).get("wind_speed", 0.0) or 0.0)
    if curr_wind > 25.0:
        avoid_items.append({
            "action": "Do NOT perform foliar pesticide or herbicide spraying",
            "reason": f"Wind speed ({curr_wind:.1f} km/h) exceeds safe threshold of 25 km/h.",
        })

    # Check if rain is coming to populate AVOID irrigation
    rain_48h = sum(float(d.get("precipitation", 0.0) or 0.0) for d in weather.get("forecast", [])[:2])
    if rain_48h > 12.0:
        avoid_items.append({
            "action": "Do NOT apply flood or furrow irrigation",
            "reason": f"Natural rainfall ({rain_48h:.1f} mm forecast) will provide adequate moisture.",
        })
        avoid_items.append({
            "action": "Do NOT broadcast surface Urea or granular fertilizer",
            "reason": "Heavy rain will cause nitrogen leaching and nutrient runoff.",
        })

    # Find pending and overdue tasks for DO FIRST and TODAY
    pending_tasks = [a for a in activities if str(a.get("status", "")).upper() in ["PENDING", "OVERDUE"]]
    pending_tasks.sort(key=lambda a: 0 if str(a.get("urgency", "")).upper() == "CRITICAL" else (1 if str(a.get("urgency", "")).upper() == "URGENT" else 2))

    if pending_tasks:
        first = pending_tasks[0]
        do_first = {
            "title": first.get("title"),
            "category": first.get("activity_type"),
            "urgency": first.get("urgency", "IMPORTANT"),
            "due_date": first.get("due_date"),
            "reason": first.get("reason"),
            "activity_id": first.get("id"),
        }
        today_tasks = pending_tasks[1:5]
    else:
        # Default DO FIRST from expert triggered rules
        if expert_res["rules_triggered"]:
            top_rule = expert_res["rules_triggered"][0]
            adv = top_rule.get("advisory", {})
            do_first = {
                "title": adv.get("title", top_rule.get("name")),
                "category": adv.get("type", "General"),
                "urgency": adv.get("severity", "IMPORTANT"),
                "due_date": date.today().isoformat(),
                "reason": adv.get("reason", top_rule.get("evidence")),
                "activity_id": None,
            }

    # Populate WATCH
    curr_hum = float(weather.get("current", {}).get("humidity", 0.0) or 0.0)
    curr_temp = float(weather.get("current", {}).get("temperature", 0.0) or 0.0)
    if curr_hum > 85.0:
        watch_items.append(f"High canopy humidity ({curr_hum:.0f}%) — monitor for leaf spots and fungal symptoms.")
    if curr_temp > 35.0:
        watch_items.append(f"Elevated midday temperature ({curr_temp:.1f}°C) — observe crop canopy for wilting.")
    if any(float(d.get("precipitation", 0) or 0) > 10.0 for d in weather.get("forecast", [])[:3]):
        watch_items.append("Rainfall forecast in next 72h — verify farm drainage outlets are unobstructed.")
    if not watch_items:
        watch_items.append("Microclimatic and field moisture conditions remain within normal tolerance limits.")

    return {
        "farm_name": farm.get("farm_name", "My Farm"),
        "crop_name": crop,
        "crop_stage": stage,
        "date_today": date.today().isoformat(),
        "do_first": do_first,
        "today_tasks": today_tasks,
        "watch": watch_items,
        "avoid": avoid_items,
        "market": {
            "has_market": best_market is not None,
            "market_name": best_market.get("market_name") if best_market else "Regional Mandi",
            "modal_price": best_market.get("modal_price") if best_market else None,
            "distance_km": best_market.get("distance_km") if best_market else None,
            "trend": best_market.get("price_trend") if best_market else "Stable",
            "explanation": market_res.get("decision_explanation", ""),
        },
        "weather": {
            "temperature": weather.get("current", {}).get("temperature"),
            "rain_probability": weather.get("current", {}).get("rain_probability"),
            "wind_speed": weather.get("current", {}).get("wind_speed"),
            "humidity": weather.get("current", {}).get("humidity"),
        },
        "condition_score": risk_res["condition_score"],
        "overall_risk_category": risk_res["overall_risk_category"],
    }


def build_seven_day_action_plan(farm_state: FarmState) -> List[Dict[str, Any]]:
    """
    Constructs an integrated 7-day calendar combining daily weather forecast,
    lifecycle operations, irrigation guidance, disease alerts, and market events.
    """
    weather = farm_state.weather
    forecast_days = weather.get("forecast", [])[:7]
    crop = farm_state.crop_name
    stage = farm_state.crop_stage
    activities = farm_state.activities

    seven_days = []
    today = date.today()

    for idx in range(7):
        day_forecast = next((d for d in forecast_days if d.get("date") == (today + timedelta(days=idx)).isoformat()), {})
        day_date = today + timedelta(days=idx)
        date_str = day_date.isoformat()

        # Find any matching activities scheduled for this date
        matching_acts = [
            a for a in activities
            if str(a.get("recommended_date", "")).startswith(date_str) or str(a.get("due_date", "")).startswith(date_str)
        ]

        # Determine daily irrigation recommendation
        p_val = float(day_forecast.get("precipitation", 0.0) or 0.0)
        p_prob = float(day_forecast.get("rain_probability", 0.0) or 0.0)
        if p_val > 10.0 or p_prob > 70.0:
            irr_status = "DELAY / NOT REQUIRED"
            irr_note = f"Rain forecast ({p_val:.1f} mm, {p_prob:.0f}% chance)"
        elif idx == 0 and (recent := latest_completed_activity(activities, "Irrigation")) and (age := hours_since(recent.get("completed_at"))) is not None and 0 <= age <= 48:
            irr_status = "NOT REQUIRED"
            irr_note = "Irrigated recently"
        elif not day_forecast:
            irr_status = "MONITOR"
            irr_note = "Forecast unavailable; inspect soil moisture before deciding."
        else:
            irr_status = "MONITOR"
            irr_note = "Check topsoil moisture"

        # Determine field work suitability
        w_max = float(day_forecast.get("wind_speed", 10.0) or 10.0)
        if w_max > 25.0:
            spraying_ok = False
            spraying_note = "Unfavorable (High Wind)"
        elif p_val > 5.0:
            spraying_ok = False
            spraying_note = "Unfavorable (Rain)"
        else:
            spraying_ok = False
            spraying_note = "Confirm current field conditions before spraying"

        seven_days.append({
            "day_number": idx + 1,
            "date": date_str,
            "day_name": day_date.strftime("%A"),
            "temperature_max": day_forecast.get("temperature_max"),
            "temperature_min": day_forecast.get("temperature_min"),
            "precipitation": p_val,
            "rain_probability": p_prob,
            "wind_speed": w_max,
            "risk_category": day_forecast.get("risk_category", "Not available"),
            "irrigation_advice": irr_status,
            "irrigation_reason": irr_note,
            "spraying_suitable": spraying_ok,
            "spraying_note": spraying_note,
            "scheduled_activities": matching_acts,
        })

    return seven_days
