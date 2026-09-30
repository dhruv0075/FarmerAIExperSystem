from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional

from services.suitability_service import get_crop_knowledge


def latest_completed_activity(activities: Iterable[Dict[str, Any]], activity_type: str) -> Optional[Dict[str, Any]]:
    matches = [
        activity
        for activity in activities
        if str(activity.get("activity_type", "")).casefold() == activity_type.casefold()
        and str(activity.get("status", "")).casefold() == "completed"
        and activity.get("completed_at")
    ]
    return max(matches, key=lambda activity: str(activity["completed_at"])) if matches else None


def hours_since(timestamp: Optional[str], now: Optional[datetime] = None) -> Optional[float]:
    if not timestamp:
        return None
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return max(0.0, (current - parsed).total_seconds() / 3600)


def is_overdue(activity: Dict[str, Any], today: Optional[date] = None) -> bool:
    if str(activity.get("status", "")).casefold() != "pending" or not activity.get("due_date"):
        return False
    try:
        due = date.fromisoformat(str(activity["due_date"]))
    except ValueError:
        return False
    return due < (today or date.today())


def classify_activity_urgency(due_date_str: str, activity_type: str, weather: Optional[Dict[str, Any]] = None) -> str:
    """Computes urgency: LOW, NORMAL, IMPORTANT, URGENT, CRITICAL."""
    today = date.today()
    try:
        due = date.fromisoformat(due_date_str)
    except Exception:
        due = today

    days_diff = (due - today).days

    # Weather-triggered urgency escalation
    weather = weather or {}
    forecast = weather.get("forecast", [])
    rain_soon = any(float(d.get("precipitation", 0) or 0) > 15.0 for d in forecast[:2])

    if activity_type.lower() == "drainage" and rain_soon:
        return "URGENT"
    if activity_type.lower() == "harvest" and rain_soon:
        return "CRITICAL"
    if days_diff < 0:
        return "URGENT"  # overdue
    if days_diff == 0:
        return "IMPORTANT"
    if days_diff <= 2:
        return "NORMAL"
    return "LOW"


def generate_lifecycle_activities(
    crop_name: str,
    stage_name: str,
    stage_start_date: Optional[date] = None,
    weather: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Generates structured, agronomically sound activities for a given crop lifecycle stage.
    """
    crop_info = get_crop_knowledge(crop_name)
    start_d = stage_start_date or date.today()
    activities = []

    # Find matching stage tasks from knowledge base
    stages = crop_info.get("stages", [])
    matching_stage = next((s for s in stages if s["name"].lower() == stage_name.lower() or stage_name.lower() in s["name"].lower()), None)
    key_tasks = matching_stage.get("key_tasks", []) if matching_stage else []

    if not key_tasks:
        key_tasks = [
            f"Conduct field inspection for {stage_name} stage",
            "Monitor soil moisture and root zone aeration",
            "Check for early pest infestation or foliar symptoms",
        ]

    for idx, task_text in enumerate(key_tasks):
        rec_date = start_d + timedelta(days=idx * 4)
        due_date = rec_date + timedelta(days=3)

        # Categorize
        act_type = "Inspection"
        priority = "MEDIUM"
        t_low = task_text.lower()
        if "irrigat" in t_low or "water" in t_low:
            act_type = "Irrigation"
            priority = "HIGH"
        elif "fertiliz" in t_low or "urea" in t_low or "dap" in t_low or "dressing" in t_low:
            act_type = "Fertilizer"
            priority = "HIGH"
        elif "weed" in t_low:
            act_type = "Weed Management"
        elif "pest" in t_low or "spray" in t_low or "borer" in t_low:
            act_type = "Pest & Disease"
            priority = "HIGH"
        elif "harvest" in t_low:
            act_type = "Harvest"
            priority = "HIGH"

        urgency = classify_activity_urgency(due_date.isoformat(), act_type, weather)

        activities.append({
            "activity_type": act_type,
            "title": task_text,
            "description": f"Recommended task during {stage_name} phase of {crop_name}.",
            "reason": f"Optimal crop physiology timing during {stage_name} stage.",
            "evidence": f"Crop knowledge base recommendation for {crop_name}.",
            "crop_stage": stage_name,
            "recommended_date": rec_date.isoformat(),
            "due_date": due_date.isoformat(),
            "priority": priority,
            "urgency": urgency,
            "status": "PENDING",
        })

    return activities


def get_activity_counts(activities: List[Dict[str, Any]], today: Optional[date] = None) -> Dict[str, int]:
    today = today or date.today()
    counts = {"pending": 0, "overdue": 0, "due_today": 0, "completed_week": 0}
    week_start = (today - timedelta(days=6)).isoformat()
    for a in activities:
        st = str(a.get("status", "")).upper()
        due = str(a.get("due_date", ""))
        comp = str(a.get("completed_at", ""))
        if st == "PENDING":
            counts["pending"] += 1
            if due < today.isoformat():
                counts["overdue"] += 1
            if due == today.isoformat():
                counts["due_today"] += 1
        elif st == "COMPLETED" and comp[:10] >= week_start:
            counts["completed_week"] += 1
    return counts


generate_stage_activities = generate_lifecycle_activities