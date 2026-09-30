import sqlite3
from datetime import date, datetime, timedelta, timezone
import uuid

import app as app_module
from app import create_app
from services.expert_system import generate_advisories


def register(client, name):
    email = f"{name}_{uuid.uuid4().hex}@example.com"
    response = client.post("/register", data={"name": name, "email": email, "password": "secret123"})
    assert response.status_code == 302
    return email


def test_activity_completion_skip_and_user_isolation(tmp_path):
    database = tmp_path / "activities.db"
    app = create_app({"TESTING": True, "SECRET_KEY": "test", "DATABASE": str(database)})
    first_client = app.test_client()
    register(first_client, "FarmerOne")
    first_client.post("/farm", data={"farm_name": "North Field", "area": "2"})
    response = first_client.post("/activities/create", data={
        "title": "Inspect soil moisture", "activity_type": "Field inspection",
        "description": "Check the east plots", "due_date": date.today().isoformat(),
    })
    assert response.status_code == 302

    with sqlite3.connect(database) as connection:
        activity_id, initial_status = connection.execute("SELECT id, status FROM farm_activities").fetchone()
    assert initial_status == "PENDING"

    first_client.post(f"/activities/{activity_id}/status", data={"status": "COMPLETED", "farmer_note": "Checked after sunrise"})
    with sqlite3.connect(database) as connection:
        status, completed_at, note = connection.execute(
            "SELECT status, completed_at, farmer_note FROM farm_activities WHERE id = ?", (activity_id,)
        ).fetchone()
    assert status == "COMPLETED"
    assert completed_at
    assert note == "Checked after sunrise"

    first_client.post("/activities/create", data={
        "title": "Inspect weed pressure", "activity_type": "Field inspection", "due_date": date.today().isoformat(),
    })
    with sqlite3.connect(database) as connection:
        skipped_id = connection.execute("SELECT id FROM farm_activities WHERE title = 'Inspect weed pressure'").fetchone()[0]
    first_client.post(f"/activities/{skipped_id}/status", data={"status": "SKIPPED", "skip_reason": "Rain occurred"})
    with sqlite3.connect(database) as connection:
        status, skipped_at, completed_at, note = connection.execute(
            "SELECT status, skipped_at, completed_at, farmer_note FROM farm_activities WHERE id = ?", (skipped_id,)
        ).fetchone()
    assert status == "SKIPPED"
    assert skipped_at
    assert completed_at is None
    assert note == "Rain occurred"

    second_client = app.test_client()
    register(second_client, "FarmerTwo")
    response = second_client.post(f"/activities/{activity_id}/status", data={"status": "SKIPPED"}, follow_redirects=True)
    assert b"Activity not found" in response.data


def test_overdue_activity_is_derived_not_saved_as_completion(tmp_path):
    database = tmp_path / "overdue.db"
    app = create_app({"TESTING": True, "SECRET_KEY": "test", "DATABASE": str(database)})
    client = app.test_client()
    register(client, "OverdueFarmer")
    client.post("/farm", data={"farm_name": "Old Field", "area": "1"})
    client.post("/activities/create", data={
        "title": "Inspect drainage", "activity_type": "Field inspection",
        "due_date": (date.today() - timedelta(days=1)).isoformat(),
    })
    response = client.get("/activities?status=overdue")
    assert response.status_code == 200
    assert b"Overdue" in response.data
    with sqlite3.connect(database) as connection:
        status, completed_at = connection.execute("SELECT status, completed_at FROM farm_activities").fetchone()
    assert status == "PENDING"
    assert completed_at is None


def test_recent_confirmed_actions_suppress_repeated_recommendations():
    completed = datetime.now(timezone.utc).isoformat(timespec="seconds")
    activity_history = [
        {"activity_type": "Irrigation", "status": "COMPLETED", "completed_at": completed},
        {"activity_type": "Fertilizer", "status": "COMPLETED", "completed_at": completed},
        {"activity_type": "Irrigation", "status": "SKIPPED", "completed_at": None},
    ]
    advisories = generate_advisories(
        "Rice", "Tillering",
        {"current": {"temperature": 36, "humidity": 55, "wind_speed": 5, "rain_probability": 0, "precipitation": 0}},
        {"nitrogen": 30, "phosphorus": 50, "potassium": 40, "moisture": 10},
        [], activity_history,
    )
    titles = [item["title"] for item in advisories]
    assert "Irrigation not required" in titles
    assert "Irrigation recommended" not in titles
    assert "Review recent fertilizer application" in titles
    assert "Nitrogen deficiency risk" not in titles


def test_recommendation_saves_measured_moisture_and_shows_distinct_fit(tmp_path):
    database = tmp_path / "recommendation.db"
    app = create_app({"TESTING": True, "SECRET_KEY": "test", "DATABASE": str(database)})
    client = app.test_client()
    register(client, "CropFarmer")
    client.post("/farm", data={"farm_name": "Trial Farm", "area": "3"})
    response = client.post("/crop-recommendation", data={
        "nitrogen": "90", "phosphorus": "42", "potassium": "43", "ph": "6.5",
        "temperature": "20.8", "humidity": "82", "rainfall": "210", "moisture": "24",
    })
    assert response.status_code == 200
    assert b"ML confidence" in response.data
    assert b"Dataset-profile match" in response.data
    with sqlite3.connect(database) as connection:
        nitrogen, phosphorus, potassium, moisture = connection.execute(
            "SELECT nitrogen, phosphorus, potassium, moisture FROM soil_records"
        ).fetchone()
        recommendation_id, recommended_crop = connection.execute(
            "SELECT id, recommended_crop FROM crop_recommendations"
        ).fetchone()
    assert (nitrogen, phosphorus, potassium, moisture) == (90, 42, 43, 24)
    client.post(f"/recommendations/{recommendation_id}/select", data={"selected_crop": recommended_crop})
    with sqlite3.connect(database) as connection:
        selected_crop = connection.execute("SELECT selected_crop FROM crop_recommendations WHERE id = ?", (recommendation_id,)).fetchone()[0]
    assert selected_crop == recommended_crop
    lifecycle_response = client.get(f"/lifecycle?crop={recommended_crop}")
    assert f'<option selected>{recommended_crop}</option>'.encode() in lifecycle_response.data
    comparison_crop = "Rice" if recommended_crop != "Rice" else "Wheat"
    conditions = {
        "nitrogen": "90", "phosphorus": "42", "potassium": "43", "ph": "6.5",
        "temperature": "20.8", "humidity": "82", "rainfall": "210",
    }
    comparison = client.post("/compare-crops", data={**conditions, "crop": [recommended_crop, comparison_crop]})
    assert comparison.status_code == 200
    assert b"dataset-fit" in comparison.data
    with sqlite3.connect(database) as connection:
        soil_count_before_simulation = connection.execute("SELECT COUNT(*) FROM soil_records").fetchone()[0]
    what_if = client.post("/what-if", data=conditions | {"temperature": "25"})
    assert what_if.status_code == 200
    assert b"Scenario results" in what_if.data
    with sqlite3.connect(database) as connection:
        soil_count_after_simulation = connection.execute("SELECT COUNT(*) FROM soil_records").fetchone()[0]
    assert soil_count_after_simulation == soil_count_before_simulation


def test_advisory_generation_creates_pending_trackable_activity(tmp_path, monkeypatch):
    database = tmp_path / "advisory_activity.db"
    app = create_app({"TESTING": True, "SECRET_KEY": "test", "DATABASE": str(database)})
    client = app.test_client()
    register(client, "AdvisoryFarmer")
    client.post("/farm", data={"farm_name": "Weather Farm", "area": "2", "latitude": "18.5", "longitude": "73.8"})
    client.post("/lifecycle", data={"crop_name": "Rice", "sowing_date": date.today().isoformat()})
    client.post("/crop-recommendation", data={
        "nitrogen": "50", "phosphorus": "50", "potassium": "50", "ph": "6.5",
        "temperature": "25", "humidity": "80", "rainfall": "100", "moisture": "45",
    })
    weather = {
        "current": {"temperature": 27, "humidity": 90, "precipitation": 0, "rain_probability": 20, "wind_speed": 5},
        "forecast": [],
    }
    monkeypatch.setattr(app_module, "fetch_weather_data", lambda *_: weather)
    response = client.post("/advisories/generate", follow_redirects=True)
    assert response.status_code == 200
    assert b"Generated" in response.data
    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            "SELECT activity_type, title, status, advisory_id FROM farm_activities"
        ).fetchall()
    assert rows
    assert any(row[0] == "Disease Risk" and row[2] == "PENDING" and row[3] is not None for row in rows)


def test_confirmed_harvest_marks_its_crop_cycle_harvested(tmp_path):
    database = tmp_path / "harvest.db"
    app = create_app({"TESTING": True, "SECRET_KEY": "test", "DATABASE": str(database)})
    client = app.test_client()
    register(client, "HarvestFarmer")
    client.post("/farm", data={"farm_name": "Harvest Field", "area": "2"})
    client.post("/lifecycle", data={"crop_name": "Wheat", "sowing_date": date.today().isoformat()})
    with sqlite3.connect(database) as connection:
        farm_id, cycle_id = connection.execute("SELECT id, (SELECT id FROM crop_cycles LIMIT 1) FROM farms").fetchone()
        connection.execute(
            """INSERT INTO farm_activities (crop_cycle_id, farm_id, activity_type, title, recommended_date, due_date)
               VALUES (?, ?, 'Harvest', 'Harvest crop', ?, ?)""",
            (cycle_id, farm_id, date.today().isoformat(), date.today().isoformat()),
        )
        activity_id = connection.execute("SELECT id FROM farm_activities").fetchone()[0]
        connection.commit()
    client.post(f"/activities/{activity_id}/status", data={"status": "COMPLETED"})
    with sqlite3.connect(database) as connection:
        cycle_status = connection.execute("SELECT status FROM crop_cycles WHERE id = ?", (cycle_id,)).fetchone()[0]
    assert cycle_status == "harvested"