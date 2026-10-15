import io
import json

from PIL import Image

import app as app_module
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
    i18n_service._RESOURCE_CACHE.clear()
    try:
        assert i18n_service.translate("mr", "detection.fallback_test") == "English fallback"
        assert i18n_service.translate("mr", "detection.absent_key") == "detection.absent_key"
    finally:
        i18n_service._RESOURCE_CACHE.clear()


def test_translation_resources_refresh_when_locale_file_changes(tmp_path, monkeypatch):
    (tmp_path / "en.json").write_text(
        json.dumps({"common": {"reload_test": "English"}}, ensure_ascii=False),
        encoding="utf-8",
    )
    marathi_path = tmp_path / "mr.json"
    marathi_path.write_text(
        json.dumps({"common": {"reload_test": "पहिली आवृत्ती"}}, ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.setattr(i18n_service, "LOCALE_DIRECTORY", tmp_path)
    i18n_service._RESOURCE_CACHE.clear()
    try:
        assert i18n_service.translate("mr", "common.reload_test") == "पहिली आवृत्ती"
        marathi_path.write_text(
            json.dumps({"common": {"reload_test": "अद्ययावत भाषांतर"}}, ensure_ascii=False),
            encoding="utf-8",
        )
        assert i18n_service.translate("mr", "common.reload_test") == "अद्ययावत भाषांतर"
    finally:
        i18n_service._RESOURCE_CACHE.clear()


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


def test_language_changes_shared_navigation_and_expenses_page_body(tmp_path):
    _, client, _ = setup_client(tmp_path)

    for language, nav_label, title, heading in (
        ("mr", "डॅशबोर्ड", "शेतखर्च आणि प्रत्यक्ष नफा", "शेतखर्च आणि आर्थिक नोंदी"),
        ("hi", "डैशबोर्ड", "खेत का खर्च और वास्तविक लाभ", "खेत का खर्च और वित्तीय रिकॉर्ड"),
    ):
        assert client.post("/language", data={"language": language}).status_code == 302
        response = client.get("/expenses")
        page = response.get_data(as_text=True)

        assert response.status_code == 200
        assert f'lang="{language}"' in page
        assert nav_label in page
        assert title in page
        assert heading in page
        assert "Farm Expenses & Financial Tracking" not in page
        assert "Realized Sales Revenue" not in page


def test_language_changes_lifecycle_and_activity_page_copy(tmp_path):
    _, client, _ = setup_client(tmp_path)
    client.post(
        "/lifecycle",
        data={"crop_name": "rice", "sowing_date": "2020-01-01"},
    )

    for language, lifecycle_title, activity_title, activity_filter in (
        ("mr", "तारखांसह पिकाची वाढ पाहा.", "शेतीची कामे", "कामांची नोंद फिल्टर करा"),
        ("hi", "तारीखों के साथ फसल की वृद्धि देखें।", "खेती के कार्य", "कार्य सूची फ़िल्टर करें"),
    ):
        assert client.post("/language", data={"language": language}).status_code == 302
        lifecycle = client.get("/lifecycle").get_data(as_text=True)
        activities = client.get("/activities").get_data(as_text=True)

        assert lifecycle_title in lifecycle
        assert "Growth, with the dates in view." not in lifecycle
        assert "Crop stage timeline" not in lifecycle
        assert activity_title in activities
        assert activity_filter in activities
        assert "Filter activity log" not in activities


def test_weather_page_labels_render_in_selected_language(tmp_path, monkeypatch):
    _, client, _ = setup_client(tmp_path)
    client.post(
        "/farm",
        data={
            "farm_name": "Test farm",
            "area": 2,
            "latitude": 18.5,
            "longitude": 73.8,
            "location_name": "Pune",
            "nitrogen": 90,
            "phosphorus": 42,
            "potassium": 43,
            "ph": 6.5,
        },
    )
    monkeypatch.setattr(
        app_module,
        "fetch_weather_data",
        lambda *_args: {
            "current": {
                "temperature": 30,
                "feels_like": 31,
                "humidity": 55,
                "precipitation": 0,
                "rain_probability": 0,
                "wind_speed": 5,
            },
            "forecast": [
                {
                    "date": "2025-01-01",
                    "temperature_min": 20,
                    "temperature_max": 30,
                    "precipitation": 0,
                    "rain_probability": 0,
                    "humidity": 55,
                }
            ],
        },
    )

    for language, heading, temperature, forecast_details in (
        ("en", "Weather Intelligence", "Temperature", "Forecast details"),
        ("mr", "हवामान माहिती", "तापमान", "अंदाजाचा तपशील"),
        ("hi", "मौसम की जानकारी", "तापमान", "पूर्वानुमान का विवरण"),
    ):
        assert client.post("/language", data={"language": language}).status_code == 302
        response = client.get("/weather")
        page = response.get_data(as_text=True)

        assert response.status_code == 200
        assert f'lang="{language}"' in page
        assert heading in page
        assert temperature in page
        assert forecast_details in page


def test_crop_recommendation_page_labels_render_in_all_languages(tmp_path):
    _, client, _ = setup_client(tmp_path)

    for language, title, field_section in (
        ("en", "AI Crop Recommendation &amp; Planning", "Soil &amp; Ambient Microclimate Parameters"),
        ("mr", "AI पीक शिफारस आणि नियोजन", "माती आणि स्थानिक सूक्ष्महवामानाची माहिती"),
        ("hi", "AI फसल सुझाव और योजना", "मिट्टी और स्थानीय सूक्ष्म जलवायु के मापदंड"),
    ):
        assert client.post("/language", data={"language": language}).status_code == 302
        response = client.get("/crop-recommendation")
        page = response.get_data(as_text=True)

        assert response.status_code == 200
        assert f'lang="{language}"' in page
        assert title in page
        assert field_section in page


def test_farm_setup_settings_notifications_and_advisories_localize(tmp_path):
    _, client, _ = setup_client(tmp_path)
    routes_and_copy = {
        "en": (
            ("/farm/setup", "Farm Characteristics", "Enter measured values from a Soil Health Card"),
            ("/settings", "Account &amp; System Settings", "Security &amp; Data Isolation"),
            ("/notifications", "No Notifications", "Automated advisories"),
            ("/advisories", "Advisories", "No advisories have been generated"),
            ("/report-problem", "Field Symptom Intake", "This page saves the symptoms"),
        ),
        "mr": (
            ("/farm/setup", "शेताची वैशिष्ट्ये", "माती आणि पोषक घटकांची प्राथमिक माहिती"),
            ("/settings", "खाते आणि प्रणाली सेटिंग्ज", "सुरक्षा आणि डेटा विभाजन"),
            ("/notifications", "सूचना नाहीत", "स्वयंचलित सल्ले"),
            ("/advisories", "सल्ले", "अद्याप कोणताही सल्ला तयार केलेला नाही"),
            ("/report-problem", "शेतातील लक्षणांची नोंद", "या पृष्ठावर लक्षणे"),
        ),
        "hi": (
            ("/farm/setup", "खेत की विशेषताएँ", "मिट्टी और पोषक तत्वों का आधार"),
            ("/settings", "खाता और सिस्टम सेटिंग", "सुरक्षा और डेटा पृथक्करण"),
            ("/notifications", "कोई सूचना नहीं", "स्वचालित सलाह"),
            ("/advisories", "सलाह", "अभी तक कोई सलाह तैयार नहीं हुई"),
            ("/report-problem", "खेत में दिखे लक्षण दर्ज करें", "यह पृष्ठ लक्षण और वैकल्पिक संदर्भ तस्वीर सहेजता है"),
        ),
    }

    for language, pages in routes_and_copy.items():
        assert client.post("/language", data={"language": language}).status_code == 302
        for route, *expected_copy in pages:
            response = client.get(route)
            page = response.get_data(as_text=True)
            assert response.status_code == 200, route
            assert f'lang="{language}"' in page
            for expected in expected_copy:
                assert expected in page, (language, route, expected)


def test_secondary_workflow_pages_render_in_all_languages(tmp_path):
    _, client, _ = setup_client(tmp_path)
    routes_and_titles = {
        "en": {
            "/market": "Market Prices",
            "/compare-crops": "Crop Comparison Analysis",
            "/what-if": "What-if analysis",
            "/risk-analysis": "Risk Analysis",
            "/history": "Farm History",
            "/report": "Farm Report",
            "/about": "About AgriWise AI",
        },
        "mr": {
            "/market": "बाजारभाव",
            "/compare-crops": "पीक तुलना विश्लेषण",
            "/what-if": "काय-तर विश्लेषण",
            "/risk-analysis": "जोखीम विश्लेषण",
            "/history": "शेताचा इतिहास",
            "/report": "शेत अहवाल",
            "/about": "AgriWise AI विषयी",
        },
        "hi": {
            "/market": "मंडी भाव",
            "/compare-crops": "फसल तुलना विश्लेषण",
            "/what-if": "क्या-हो-अगर विश्लेषण",
            "/risk-analysis": "जोखिम विश्लेषण",
            "/history": "खेत का इतिहास",
            "/report": "खेत की रिपोर्ट",
            "/about": "AgriWise AI के बारे में",
        },
    }

    for language, pages in routes_and_titles.items():
        assert client.post("/language", data={"language": language}).status_code == 302
        for route, title in pages.items():
            response = client.get(route)
            page = response.get_data(as_text=True)

            assert response.status_code == 200, (language, route)
            assert f'lang="{language}"' in page
            assert title in page, (language, route, title)


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
