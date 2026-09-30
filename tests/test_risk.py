from services.risk_service import analyze_farm_risk


def test_risk_engine_keeps_unmeasured_water_unknown():
    result = analyze_farm_risk(
        {"nitrogen": 40, "phosphorus": 45, "potassium": 30, "ph": 6.4},
        {"temperature": 28, "humidity": 88, "rainfall": 2, "rain_probability": 80},
        {"current_stage": "Tillering"},
    )
    assert result["condition_score"] is not None
    assert result["condition_components"]["Water condition"] == "Unknown"
    assert result["risk_scores"]["Heavy rain risk"] >= 65
    assert result["risk_level"] in {"Low", "Moderate", "High", "Critical"}


def test_measured_moisture_contributes_to_condition_and_water_risk():
    result = analyze_farm_risk({"moisture": 15, "ph": 6.5}, {}, None)
    assert result["condition_components"]["Water condition"] == "Critical"
    assert result["risk_scores"]["Water risk"] == 80