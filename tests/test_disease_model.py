from PIL import Image

from agriwise_disease_model import disease_predictor


def test_supplied_checkpoint_runs_raw_38_class_inference():
    image = Image.new("RGB", (224, 224), color="green")

    result = disease_predictor.predict_raw(image)

    assert len(disease_predictor.CLASS_NAMES) == 38
    assert result["predicted_class"] in disease_predictor.CLASS_NAMES
    assert 0 <= result["confidence"] <= 100


def test_public_screening_returns_candidate_with_clear_unverified_warning(monkeypatch):
    calls = []

    def raw_prediction(image):
        calls.append(image)
        return {
            "crop": "Tomato",
            "predicted_class": "Tomato___Early_blight",
            "disease": "Early blight",
            "confidence": 99.9,
        }

    monkeypatch.setattr(disease_predictor, "predict_raw", raw_prediction)
    result = disease_predictor.predict_disease(Image.new("RGB", (8, 8), "green"))

    assert len(calls) == 1
    assert result["status"] == "prediction"
    assert result["disease"] == "Early blight"
    assert result["confidence"] == 99.9
    assert "not a confirmed diagnosis" in result["message"]
    assert "uncalibrated" in result["message"]
