"""Deterministic journey; weather fixture is test-only, never production data."""
import sqlite3
from datetime import date

import app as module
from app import create_app


def test_closed_loop_journey_and_local_persistence(tmp_path, monkeypatch):
    weather = {'current': {'temperature': 30, 'humidity': 55, 'precipitation': 0,
                           'rain_probability': 0, 'wind_speed': 5}, 'forecast': []}
    monkeypatch.setattr(module, 'fetch_weather_data', lambda *a, **k: weather)
    database = tmp_path / 'journey.db'
    application = create_app({'TESTING': True, 'SECRET_KEY': 'test', 'DATABASE': str(database)})
    client = application.test_client()
    credentials = {'email': 'journey@example.com', 'password': 'test-pass123'}
    assert client.post('/register', data=dict(credentials, name='Journey')).status_code == 302
    client.post('/logout')
    assert client.post('/login', data=credentials).status_code == 302
    assert client.post('/farm', data={'farm_name': 'Journey Farm', 'area': 2,
           'latitude': 18.5, 'longitude': 73.8, 'location_name': 'Test location'}).status_code == 302
    assert client.get('/weather').status_code == 200
    response = client.post('/crop-recommendation', data={'nitrogen': 90, 'phosphorus': 42,
        'potassium': 43, 'ph': 6.5, 'temperature': 30, 'humidity': 55, 'rainfall': 100, 'moisture': 10})
    assert response.status_code == 200
    assert client.post('/lifecycle', data={'crop_name': 'rice', 'sowing_date': date.today().isoformat()}).status_code == 302
    assert client.post('/advisories/generate').status_code == 302
    with sqlite3.connect(database) as conn:
        row = conn.execute("SELECT id, status FROM farm_activities WHERE title='Irrigation recommended'").fetchone()
        assert row and row[1] == 'PENDING'
        before = conn.execute('SELECT max(id) FROM advisories').fetchone()[0]
    assert client.post(f'/activities/{row[0]}/status', data={'status': 'COMPLETED', 'farmer_note': 'Confirmed'}).status_code == 302
    client.post('/advisories/generate')
    with sqlite3.connect(database) as conn:
        titles = [r[0] for r in conn.execute('SELECT title FROM advisories WHERE id > ?', (before,))]
        assert 'Irrigation not required' in titles
        assert 'Irrigation recommended' not in titles
    assert client.post('/report-problem', data={'crop': 'rice', 'symptoms': 'yellow leaves', 'farmer_notes': 'Observed today'}, follow_redirects=True).status_code == 200
    assert client.get('/market').status_code == 200
    client.post('/logout')
    # Reopen the application with the same local database, rather than reusing its session.
    reopened = create_app({'TESTING': True, 'SECRET_KEY': 'test', 'DATABASE': str(database)}).test_client()
    reopened.post('/login', data=credentials)
    assert b'Journey Farm' in reopened.get('/dashboard').data
    assert b'yellow leaves' in reopened.get('/report-problem').data
    assert b'Irrigation not required' in reopened.get('/history').data


def test_daily_plan_keeps_future_and_weather_conflicting_tasks_out_of_today():
    from datetime import timedelta
    from services.decision_orchestrator import FarmState, build_unified_daily_farm_plan
    today = date.today().isoformat()
    activities = [
        {'id': 1, 'title': 'Water field', 'activity_type': 'Irrigation', 'status': 'PENDING', 'due_date': today},
        {'id': 2, 'title': 'Inspect later', 'activity_type': 'Field inspection', 'status': 'PENDING',
         'due_date': (date.today() + timedelta(days=3)).isoformat()},
    ]
    state = FarmState({}, {}, {}, {'crop_name': 'rice', 'current_stage': 'Tillering'},
                      {'current': {}, 'forecast': [{'precipitation': 18, 'rain_probability': 86}]}, activities, [], [], [])
    plan = build_unified_daily_farm_plan(state)
    assert not plan['today_tasks']
    assert plan['do_first'] is None or plan['do_first']['activity_id'] is None
    assert plan['upcoming'][0]['id'] == 2
    assert any('Water field' in item['action'] for item in plan['avoid'])
    assert all(item['status'] == 'PENDING' for item in activities)
