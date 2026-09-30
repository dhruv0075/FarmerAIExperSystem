from services import weather_service
import pytest


def test_weather_outage_never_invents_observations(monkeypatch):
    weather_service._WEATHER_CACHE.clear()
    def unavailable(*args, **kwargs):
        raise weather_service.requests.Timeout()
    monkeypatch.setattr(weather_service.requests, 'get', unavailable)
    with pytest.raises(weather_service.WeatherError):
        weather_service.fetch_weather_data(18, 73)


def test_weather_http_error_uses_original_cache(monkeypatch):
    weather_service._WEATHER_CACHE[(18, 73)] = (0, {'current': {'temperature': 24}, 'fetch_timestamp': 'original'})
    monkeypatch.setattr(weather_service.requests, 'get', lambda *a, **k: type('Response', (), {'status_code': 503})())
    result = weather_service.fetch_weather_data(18, 73)
    assert result['is_stale']
    assert result['fetch_timestamp'] == 'original'
    assert result['current']['temperature'] == 24


def test_fetch_weather_data_parses_response(monkeypatch):
    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {
                'current': {
                    'time': '2026-09-30T12:00',
                    'temperature_2m': 27.5,
                    'apparent_temperature': 28.2,
                    'relative_humidity_2m': 66,
                    'precipitation': 4.5,
                    'wind_speed_10m': 14,
                },
                'daily': {
                    'time': ['2026-09-30', '2026-10-01'],
                    'temperature_2m_max': [29.0, 30.0],
                    'temperature_2m_min': [21.0, 22.0],
                    'precipitation_sum': [2.0, 5.0],
                    'precipitation_probability_max': [30, 40],
                    'wind_speed_10m_max': [15, 18],
                },
                'hourly': {
                    'time': ['2026-09-30', '2026-10-01'],
                    'relative_humidity_2m': [66, 70],
                    'precipitation_probability': [20, 45],
                },
            }

    def fake_get(*args, **kwargs):
        return FakeResponse()

    monkeypatch.setattr(weather_service.requests, 'get', fake_get)
    result = weather_service.fetch_weather_data(19.076, 72.8777)
    assert result['current']['temperature'] == 27.5
    assert result['current']['feels_like'] == 28.2
    assert result['current']['rain_probability'] == 20
    assert len(result['forecast']) == 2
    assert result['forecast'][0]['rain_probability'] == 30


def test_weather_analysis_scores_risk_and_creates_actions():
    from services.weather_analysis import analyze_forecast

    analysis = analyze_forecast([{
        'date': '2026-10-01', 'temperature_max': 36, 'temperature_min': 22,
        'precipitation': 30, 'rain_probability': 85, 'wind_speed': 12, 'humidity': 88,
    }], 'Rice', 'Tillering')
    assert analysis['days'][0]['risk']['score'] >= 50
    assert analysis['days'][0]['risk']['level'] == 'High'
    assert any(item['activity_type'] == 'Field inspection' for item in analysis['actions'])
    assert any('drainage' in item['title'].lower() for item in analysis['actions'])
