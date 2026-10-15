import io
import json
import sqlite3

from PIL import Image

from test_extended_flows import setup_client
import app as app_module
from services.crop_ml_service import DATASET_PATH


def image_bytes():
    output = io.BytesIO()
    Image.new("RGB", (24, 24), color="green").save(output, format="PNG")
    return output.getvalue()


def test_standalone_disease_detection_route_is_removed(tmp_path):
    _, client, _ = setup_client(tmp_path)

    response = client.get("/disease-detection")

    assert response.status_code == 404


def test_problem_report_stores_reference_photo_without_image_screening(tmp_path, monkeypatch):
    application, client, database = setup_client(tmp_path)
    monkeypatch.setattr(app_module, "UPLOAD_FOLDER", tmp_path / "private_uploads")

    response = client.post(
        "/report-problem",
        data={
            "crop": "Tomato",
            "symptoms": "Brown spots on lower leaves",
            "photo": (io.BytesIO(image_bytes()), "leaf.png", "image/png"),
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"No confirmed diagnosis" in response.data
    assert b"not analyzed" in response.data
    with sqlite3.connect(database) as connection:
        report = connection.execute(
            """SELECT d.image_path, p.likely_condition, p.confidence,
                      p.recommendations_json
               FROM disease_reports d
               JOIN disease_predictions p ON p.report_id = d.id"""
        ).fetchone()

    assert report[0]
    assert report[1] == "Diagnosis unavailable; expert inspection needed"
    assert report[2] is None
    stored_diagnosis = json.loads(report[3])
    assert stored_diagnosis["image_analysis"]["screening_status"] == "not_requested"
    assert "stored as reference material" in stored_diagnosis["image_analysis"]["message"]


def test_crop_recommendation_uses_original_crop_dataset():
    assert DATASET_PATH.name == "Crop_recommendation.csv"
    assert DATASET_PATH.parent.name == "data"
    assert DATASET_PATH.is_file()
