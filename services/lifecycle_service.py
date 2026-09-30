from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List

CROP_LIFECYCLE_PROFILES = {
    "Rice": {
        "stages": ["Germination", "Seedling", "Vegetative", "Tillering", "Panicle Initiation", "Flowering", "Grain Filling", "Maturity"],
        "durations": [10, 15, 20, 20, 20, 15, 25, 30],
        "activities": {
            "Germination": ["Check seedbed moisture", "Monitor field drainage", "Ensure uniform germination"],
            "Seedling": ["Inspect plant stand", "Manage early nutrient needs", "Remove weeds"],
            "Vegetative": ["Monitor leaf growth", "Check irrigation timing", "Observe pest pressure"],
            "Tillering": ["Control weeds", "Check nitrogen need", "Assess tiller density"],
            "Panicle Initiation": ["Monitor water levels", "Inspect plant health", "Prepare for reproductive phase"],
            "Flowering": ["Protect flowers from stress", "Assess humidity", "Manage drainage"],
            "Grain Filling": ["Support grain development", "Schedule irrigation carefully", "Watch for lodging"],
            "Maturity": ["Assess grain maturity", "Prepare harvest logistics", "Review weather forecast"],
        },
    },
    "Wheat": {
        "stages": ["Germination", "Tillering", "Jointing", "Heading", "Flowering", "Grain Filling", "Maturity"],
        "durations": [12, 18, 20, 18, 18, 25, 30],
        "activities": {
            "Germination": ["Check soil moisture", "Inspect seed covering"],
            "Tillering": ["Monitor nutrient needs", "Assess weed pressure"],
            "Jointing": ["Review irrigation", "Watch for lodging"],
            "Heading": ["Assess crop vigor", "Monitor disease risk"],
            "Flowering": ["Avoid stress", "Check pollination conditions"],
            "Grain Filling": ["Optimize moisture", "Inspect grain heads"],
            "Maturity": ["Prepare harvest", "Check weather risk"],
        },
    },
    "Maize": {
        "stages": ["Emergence", "Vegetative", "Silking", "Grain Filling", "Maturity"],
        "durations": [12, 25, 18, 30, 28],
        "activities": {
            "Emergence": ["Check seedling stand", "Inspect moisture"],
            "Vegetative": ["Monitor weed pressure", "Review nutrient plan"],
            "Silking": ["Ensure pollination support", "Watch heat stress"],
            "Grain Filling": ["Manage irrigation", "Inspect ears"],
            "Maturity": ["Prepare harvest", "Review forecast"],
        },
    },
    "Cotton": {
        "stages": ["Germination", "Vegetative", "Squaring", "Flowering", "Boll Development", "Maturity"],
        "durations": [10, 25, 20, 25, 35, 30],
        "activities": {
            "Germination": ["Watch soil crusting", "Inspect stand"],
            "Vegetative": ["Monitor nitrogen", "Control weeds"],
            "Squaring": ["Check insect pressure", "Assess nutrient status"],
            "Flowering": ["Protect bolls", "Watch for stress"],
            "Boll Development": ["Assess irrigation", "Review weather"],
            "Maturity": ["Prepare harvest planning", "Check rain risk"],
        },
    },
    "Chickpea": {
        "stages": ["Emergence", "Vegetative", "Flowering", "Pod Formation", "Maturity"],
        "durations": [10, 25, 20, 25, 30],
        "activities": {
            "Emergence": ["Check moisture", "Inspect stand"],
            "Vegetative": ["Watch weeds", "Manage nutrition"],
            "Flowering": ["Monitor stress", "Assess flowers"],
            "Pod Formation": ["Adjust irrigation", "Inspect pods"],
            "Maturity": ["Plan harvest", "Check rain risk"],
        },
    },
    "Pigeon Pea": {
        "stages": ["Emergence", "Vegetative", "Flowering", "Pod Development", "Maturity"],
        "durations": [12, 25, 20, 30, 35],
        "activities": {
            "Emergence": ["Inspect seedling vigor", "Ensure moisture"],
            "Vegetative": ["Monitor growth", "Manage weed pressure"],
            "Flowering": ["Check insect stress", "Assess canopy"],
            "Pod Development": ["Manage nutrient balance", "Check pod set"],
            "Maturity": ["Prepare harvest", "Review climate"],
        },
    },
    "Groundnut": {
        "stages": ["Emergence", "Vegetative", "Flowering", "Pegging", "Maturity"],
        "durations": [12, 25, 20, 28, 35],
        "activities": {
            "Emergence": ["Check moisture", "Ensure stand"],
            "Vegetative": ["Assess foliar health", "Watch weeds"],
            "Flowering": ["Check pollination", "Review rainfall"],
            "Pegging": ["Monitor soil moisture", "Inspect pegging"],
            "Maturity": ["Prepare harvest", "Check weather"],
        },
    },
    "Tomato": {
        "stages": ["Transplanting", "Vegetative", "Flowering", "Fruit Set", "Harvest"],
        "durations": [15, 25, 20, 25, 35],
        "activities": {
            "Transplanting": ["Check root establishment", "Monitor moisture"],
            "Vegetative": ["Inspect canopy", "Manage irrigation"],
            "Flowering": ["Watch heat stress", "Support pollination"],
            "Fruit Set": ["Manage nutrient boosts", "Inspect fruit load"],
            "Harvest": ["Schedule harvest windows", "Review weather risk"],
        },
    },
    "Onion": {
        "stages": ["Germination", "Leaf Development", "Bulb Initiation", "Bulb Maturity", "Harvest"],
        "durations": [12, 20, 18, 25, 30],
        "activities": {
            "Germination": ["Maintain moisture", "Check stand"],
            "Leaf Development": ["Assess nutrients", "Watch weeds"],
            "Bulb Initiation": ["Monitor soil moisture", "Manage irrigation"],
            "Bulb Maturity": ["Review size progress", "Check weather"],
            "Harvest": ["Plan harvest timing", "Check rain risk"],
        },
    },
}


def get_lifecycle_profile(crop_name: str) -> Dict[str, Any]:
    profile = CROP_LIFECYCLE_PROFILES.get(crop_name.title())
    if profile is not None:
        return profile
    return {
        "stages": ["Sowing", "Vegetative", "Flowering", "Harvest"],
        "durations": [20, 40, 35, 30],
        "activities": {
            "Sowing": ["Prepare soil", "Inspect moisture"],
            "Vegetative": ["Monitor crop health", "Manage nutrients"],
            "Flowering": ["Check stress", "Review weather"],
            "Harvest": ["Plan harvest logistics", "Assess rain risk"],
        },
    }


def get_crop_stage_summary(crop_name: str, sowing_date: str) -> Dict[str, Any]:
    profile = get_lifecycle_profile(crop_name)
    stages = profile["stages"]
    durations = profile["durations"]
    total_days = sum(durations)

    if isinstance(sowing_date, str):
        try:
            sowing = datetime.strptime(sowing_date, "%Y-%m-%d").date()
        except ValueError:
            sowing = date.today()
    else:
        sowing = date.today()

    today = date.today()
    days_since_sowing = max(0, (today - sowing).days)
    progress = min(100, round((days_since_sowing / total_days) * 100, 2)) if total_days else 0

    stage_index = len(stages) - 1
    days_in_stage = durations[-1]
    days_to_next_stage = 0
    days_remaining = days_since_sowing
    for idx, duration in enumerate(durations):
        if days_remaining < duration or idx == len(durations) - 1:
            stage_index = idx
            days_in_stage = min(days_remaining, duration)
            days_to_next_stage = max(0, duration - days_in_stage)
            break
        days_remaining -= duration

    current_stage = stages[min(stage_index, len(stages) - 1)]
    next_stage = stages[min(stage_index + 1, len(stages) - 1)] if stage_index < len(stages) - 1 else "Harvest"
    expected_harvest_date = sowing + timedelta(days=total_days)
    timeline = []
    for idx, stage in enumerate(stages):
        status = "COMPLETED" if idx < stage_index else "CURRENT" if idx == stage_index else "UPCOMING"
        timeline.append({"name": stage, "status": status, "duration_days": durations[idx]})

    return {
        "crop_name": crop_name.title(),
        "sowing_date": sowing.isoformat(),
        "days_since_sowing": days_since_sowing,
        "current_stage": current_stage,
        "next_stage": next_stage,
        "days_in_current_stage": days_in_stage,
        "days_until_next_stage": days_to_next_stage,
        "expected_harvest_date": expected_harvest_date.isoformat(),
        "progress": progress,
        "total_days": total_days,
        "stage_timeline": timeline,
        "activities": profile["activities"].get(current_stage, ["Monitor the crop and review field conditions"]),
    }


def get_all_supported_crops() -> List[str]:
    crops = sorted(list(k.lower() for k in CROP_LIFECYCLE_PROFILES.keys()))
    try:
        from services.suitability_service import get_crop_knowledge
        ck = get_crop_knowledge()
        all_c = sorted(list(set(crops + [k.lower() for k in ck.keys()])))
        return all_c
    except Exception:
        return crops

