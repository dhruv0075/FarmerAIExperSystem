from services.expert_system import generate_advisories


def test_heavy_rain_and_low_nitrogen_rules():
    weather = {'current': {'temperature': 28, 'humidity': 87, 'wind_speed': 30, 'rain_probability': 80, 'precipitation': 18}}
    soil = {'nitrogen': 30, 'phosphorus': 40, 'potassium': 70, 'moisture': 15}
    forecast = [{'rain_probability': 88, 'precipitation': 25}, {'rain_probability': 70, 'precipitation': 20}]

    advisories = generate_advisories('Rice', 'Maturity', weather, soil, forecast)
    titles = [item['title'] for item in advisories]
    assert any('Delay irrigation' in title for title in titles)
    assert any('Nitrogen deficiency risk' in title for title in titles)
    assert any('Disease risk advisory' in title for title in titles)


def test_missing_soil_moisture_does_not_trigger_irrigation():
    weather = {'current': {'temperature': 36, 'humidity': 60, 'wind_speed': 5, 'rain_probability': 0, 'precipitation': 0}}
    advisories = generate_advisories('Rice', 'Vegetative', weather, {'nitrogen': 100}, [])
    assert not any(item['title'] == 'Irrigation recommended' for item in advisories)
