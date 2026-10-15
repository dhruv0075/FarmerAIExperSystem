import io
import json

from PIL import Image

from test_extended_flows import setup_client
from services import i18n_service


def make_image():
    output = io.BytesIO()
    Image.new("RGB", (24, 24), color="green").save(output, format="PNG")
    return output.getvalue()


def prediction(_image):
    return {
        "status": "prediction",
        "crop": "Tomato",
        "predicted_class": "Tomato___Early_blight",
        "disease": "Early blight",
        "confidence": 91.25,
        "message": "Raw uncalibrated model output.",
    }


def test_supported_language_translations_and_disease_labels_are_complete():
    class_labels = json.loads(
        (i18n_service.LOCALE_DIRECTORY.parent / "agriwise_disease_model" / "class_names.json").read_text(
            encoding="utf-8"
        )
    )
    english = i18n_service._load_resource("en")

    for language in i18n_service.SUPPORTED_LANGUAGES:
        resource = i18n_service._load_resource(language)
        assert resource["detection"].keys() == english["detection"].keys()
        assert all(resource["detection"][key].strip() for key in english["detection"])
        assert set(resource["disease_names"]) == set(class_labels)
        assert all(name.strip() for name in resource["disease_names"].values())


def test_missing_translation_falls_back_to_english(tmp_path, monkeypatch):
    (tmp_path / "en.json").write_text(
        json.dumps({"detection": {"fallback_test": "English fallback"}}, ensure_ascii=False),
        encoding="utf-8",
    )
    (tmp_path / "mr.json").write_text(
        json.dumps({"detection": {}}, ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.setattr(i18n_service, "LOCALE_DIRECTORY", tmp_path)
    i18n_service._load_resource.cache_clear()
    try:
        assert i18n_service.translate("mr", "detection.fallback_test") == "English fallback"
        assert i18n_service.translate("mr", "detection.absent_key") == "detection.absent_key"
    finally:
        i18n_service._load_resource.cache_clear()


def test_language_selector_persists_only_supported_codes_and_redirects_locally(tmp_path):
    _, client, _ = setup_client(tmp_path)

    response = client.post(
        "/language",
        data={"language": "mr", "next": "/disease-detection"},
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/disease-detection"
    translated_page = client.get("/disease-detection")
    assert 'lang="mr"' in translated_page.get_data(as_text=True)
    assert "रोग ओळख" in translated_page.get_data(as_text=True)

    invalid = client.post("/language", data={"language": "xx", "next": "//example.com"})
    assert invalid.status_code == 400
    with client.session_transaction() as session:
        assert session["language"] == "mr"


def test_language_selection_rejects_external_redirects(tmp_path):
    _, client, _ = setup_client(tmp_path)

    response = client.post(
        "/language",
        data={"language": "hi", "next": "https://example.com"},
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/"
    with client.session_transaction() as session:
        assert session["language"] == "hi"


def test_invalid_session_language_falls_back_to_english(tmp_path):
    _, client, _ = setup_client(tmp_path)
    with client.session_transaction() as session:
        session["language"] = ["invalid"]

    response = client.get("/disease-detection")

    assert response.status_code == 200
    assert 'lang="en"' in response.get_data(as_text=True)
    assert b"Disease Detection" in response.data
    with client.session_transaction() as session:
        assert session["language"] == "en"


def test_detection_result_renders_translated_copy_without_changing_model_labels(tmp_path):
    application, client, _ = setup_client(tmp_path)
    application.config["DISEASE_PREDICTOR"] = prediction

    for language, translated_name, title, warning in (
        ("en", "Early blight", "Disease Detection", "not a confirmed diagnosis"),
        ("mr", "लवकर येणारा करपा", "रोग ओळख", "हे निश्चित निदान नाही"),
        ("hi", "अगेती झुलसा", "रोग पहचान", "पक्का निदान नहीं"),
    ):
        assert client.post("/language", data={"language": language}).status_code == 302
        response = client.post(
            "/disease-detection",
            data={
                "crop": "Tomato",
                "photo": (io.BytesIO(make_image()), "leaf.png", "image/png"),
            },
        )
        page = response.get_data(as_text=True)

        assert response.status_code == 200
        assert f'lang="{language}"' in page
        assert title in page
        assert translated_name in page
        assert warning in page
        assert "Tomato___Early_blight" in page
        assert "91.25%" in page


def test_image_validation_errors_follow_selected_language(tmp_path):
    _, client, _ = setup_client(tmp_path)
    client.post("/language", data={"language": "hi"})

    response = client.post("/disease-detection", data={"crop": "Tomato"})

    assert response.status_code == 200
    assert "जाँच के लिए पौधे की तस्वीर चुनें।" in response.get_data(as_text=True)
