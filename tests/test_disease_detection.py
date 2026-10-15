import io
import json
import sqlite3

from PIL import Image

from test_extended_flows import setup_client
import app as app_module
from services.disease_service import analyze_crop_issue, is_suggestion_for_crop


def image_bytes():
    output = io.BytesIO()
    Image.new("RGB", (24, 24), color="green").save(output, format="PNG")
    return output.getvalue()


def raw_model_prediction(_image):
    return {
        "status": "prediction",
        "crop": "Tomato",
        "predicted_class": "Tomato___Early_blight",
        "disease": "Early blight",
        "confidence": 99.9,
        "message": "Raw model output; not calibrated.",
    }


def test_uncalibrated_image_prediction_is_exposed_only_as_a_suggestion():
    result = analyze_crop_issue(
        "Tomato",
        symptoms_text="Brown spots on lower leaves",
        image_bytes=image_bytes(),
        predictor=raw_model_prediction,
    )

    assert result["supported_by_image_ai"] is False
    assert result["image_analysis"]["screening_status"] == "suggestion"
    assert result["image_analysis"]["reason"] == "unverified_model_suggestion"
    assert result["image_analysis"]["model_available"] is True
    assert result["primary_diagnosis"]["condition"] == "Diagnosis unavailable; expert inspection needed"
    assert result["primary_diagnosis"]["confidence"] is None
    assert result["image_analysis"]["suggestion"] == {
        "crop": "Tomato",
        "disease": "Early blight",
        "class_label": "Tomato___Early_blight",
        "model_score": 99.9,
    }
    assert "not a confirmed diagnosis" in result["image_analysis"]["message"]


def test_model_suggestion_for_a_different_crop_is_suppressed():
    result = analyze_crop_issue(
        "Rice",
        symptoms_text="Brown spots on leaf",
        image_bytes=image_bytes(),
        predictor=raw_model_prediction,
    )

    assert result["image_analysis"]["screening_status"] == "unsupported"
    assert result["image_analysis"]["reason"] == "crop_mismatch"
    assert "suggestion" not in result["image_analysis"]
    assert "no matching crop class" in result["image_analysis"]["message"]
    assert not is_suggestion_for_crop("Rice", "Corn (maize)")
    assert is_suggestion_for_crop("Maize", "Corn (maize)")


def test_report_upload_saves_reference_image_without_running_disease_model(tmp_path, monkeypatch):
    application, client, database = setup_client(tmp_path)
    predictor_calls = []
    application.config["DISEASE_PREDICTOR"] = lambda image: predictor_calls.append(image) or raw_model_prediction(image)
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
    assert predictor_calls == []
    assert b"No confirmed diagnosis" in response.data
    assert b"No confirmed diagnosis" in response.data
    assert b"not screened on this report page" in response.data
    assert b"Image model suggestion" not in response.data
    assert b"Early blight" not in response.data
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


def test_saved_report_hides_a_legacy_suggestion_for_a_different_crop(tmp_path, monkeypatch):
    application, client, database = setup_client(tmp_path)
    application.config["DISEASE_PREDICTOR"] = raw_model_prediction
    monkeypatch.setattr(app_module, "UPLOAD_FOLDER", tmp_path / "private_uploads")
    response = client.post(
        "/report-problem",
        data={
            "crop": "Tomato",
            "symptoms": "Brown spots on leaves",
            "photo": (io.BytesIO(image_bytes()), "leaf.png", "image/png"),
        },
        follow_redirects=True,
    )
    report_id = int(response.request.path.rsplit("/", 1)[-1])
    legacy_prediction = analyze_crop_issue(
        "Tomato",
        symptoms_text="Brown spots on leaves",
        image_bytes=image_bytes(),
        predictor=raw_model_prediction,
    )

    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE disease_reports SET crop = 'Rice' WHERE id = ?", (report_id,))
        connection.execute(
            "UPDATE disease_predictions SET recommendations_json = ? WHERE report_id = ?",
            (json.dumps(legacy_prediction), report_id),
        )
        connection.commit()

    result_page = client.get(f"/disease-result/{report_id}")

    assert result_page.status_code == 200
    assert b"not screened on this report page" in result_page.data
    assert b"Early blight" not in result_page.data


def test_disease_detection_page_is_separate_and_lists_model_dataset(tmp_path):
    _, client, _ = setup_client(tmp_path)
    response = client.get("/disease-detection")

    assert response.status_code == 200
    assert b"Disease Detection" in response.data
    assert b"does not create or change a Problem Report" in response.data
    assert b"54,306 images" in response.data
    assert b"all 38 class labels" in response.data
    assert b"https://huggingface.co/datasets/mohanty/PlantVillage" in response.data
    assert b'href="/disease-detection"' in response.data


def test_standalone_detection_shows_suggestion_without_saving_problem_report(tmp_path):
    application, client, database = setup_client(tmp_path)
    application.config["DISEASE_PREDICTOR"] = raw_model_prediction

    response = client.post(
        "/disease-detection",
        data={
            "crop": "Tomato",
            "photo": (io.BytesIO(image_bytes()), "leaf.png", "image/png"),
        },
    )

    assert response.status_code == 200
    assert b"Closest model match: Tomato \xe2\x80\x94 Early blight" in response.data
    assert b"not a confirmed diagnosis" in response.data
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM disease_reports").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM disease_predictions").fetchone()[0] == 0


def test_detection_uses_lifecycle_crop_without_asking_or_accepting_an_override(tmp_path):
    application, client, _ = setup_client(tmp_path)
    application.config["DISEASE_PREDICTOR"] = raw_model_prediction
    client.post("/lifecycle", data={
        "crop_name": "tomato",
        "sowing_date": "2020-01-01",
    })

    page = client.get("/disease-detection")

    assert page.status_code == 200
    assert b'value="Tomato"' not in page.data
    assert b'name="crop"' not in page.data
    assert b"Using the crop selected in your current crop lifecycle." in page.data

    response = client.post(
        "/disease-detection",
        data={
            "crop": "Potato",
            "photo": (io.BytesIO(image_bytes()), "leaf.png", "image/png"),
        },
    )

    assert response.status_code == 200
    assert b"Closest model match: Tomato" in response.data
    assert b"no matching crop class" not in response.data


def test_standalone_detection_blocks_unsupported_rice_crop(tmp_path):
    application, client, database = setup_client(tmp_path)
    application.config["DISEASE_PREDICTOR"] = raw_model_prediction

    response = client.post(
        "/disease-detection",
        data={
            "crop": "Rice",
            "photo": (io.BytesIO(image_bytes()), "leaf.png", "image/png"),
        },
    )

    assert response.status_code == 200
    assert b"No disease suggestion available" in response.data
    assert b"no matching crop class" in response.data
    assert b"Closest model match:" not in response.data
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM disease_reports").fetchone()[0] == 0


def test_disease_detection_upload_requires_a_valid_image(tmp_path):
    _, client, _ = setup_client(tmp_path)
    response = client.post(
        "/disease-detection",
        data={"crop": "Tomato", "photo": (io.BytesIO(b"not an image"), "leaf.png", "image/png")},
    )

    assert response.status_code == 200
    assert b"Upload a valid JPEG, PNG, or WebP image" in response.data


def test_missing_model_and_missing_image_are_reported_without_false_diagnosis():
    missing_model = analyze_crop_issue(
        "Tomato",
        symptoms_text="Yellow leaves",
        image_bytes=image_bytes(),
        predictor=lambda _image: (_ for _ in ()).throw(FileNotFoundError("model missing")),
    )
    no_image = analyze_crop_issue("Tomato", symptoms_text="Yellow leaves")

    assert missing_model["image_analysis"]["screening_status"] == "uncertain"
    assert missing_model["image_analysis"]["reason"] == "model_unavailable"
    assert no_image["image_analysis"]["screening_status"] == "not_requested"
    assert no_image["image_analysis"]["has_image"] is False
    assert missing_model["primary_diagnosis"]["confidence"] is None
    assert no_image["primary_diagnosis"]["confidence"] is None


def test_invalid_model_response_fails_closed():
    result = analyze_crop_issue(
        "Tomato",
        symptoms_text="Wilting leaves",
        image_bytes=image_bytes(),
        predictor=lambda _image: {"status": "prediction"},
    )

    assert result["image_analysis"]["screening_status"] == "uncertain"
    assert result["image_analysis"]["reason"] == "invalid_model_response"
    assert result["primary_diagnosis"]["confidence"] is None
