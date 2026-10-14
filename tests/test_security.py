"""Security regression tests.

These cover error-message disclosure, cross-user isolation, session
invalidation and CSRF enforcement. Every account here is synthetic and no
real credential is used.
"""
import sqlite3

import app as app_module
from app import create_app


def make_client(tmp_path, csrf_enabled=False, name='security'):
    database = tmp_path / f'{name}.db'
    config = {
        'TESTING': True,
        'SECRET_KEY': 'security-test-secret',
        'DATABASE': str(database),
        'CSRF_ENABLED': csrf_enabled,
    }
    application = create_app(config)
    return application, application.test_client(), database


def register(client, email, password='farmer123'):
    return client.post('/register', data={
        'name': 'Security Farmer', 'email': email, 'password': password,
    })


def create_farm(client, farm_name, **overrides):
    data = {
        'farm_name': farm_name, 'area': '2.5', 'location_name': 'Pune',
        'latitude': '18.5', 'longitude': '73.8',
        'nitrogen': '90', 'phosphorus': '42', 'potassium': '43', 'ph': '6.5',
    }
    data.update(overrides)
    return client.post('/farm/setup', data=data)


def test_weather_api_does_not_leak_internal_exception_text(tmp_path, monkeypatch):
    _, client, _ = make_client(tmp_path)
    register(client, 'weather-leak@example.com')
    create_farm(client, 'Leak Farm')

    def boom(*_args):
        raise RuntimeError('could not read artifact at C:\\secret\\path\\database.db')

    monkeypatch.setattr(app_module, 'fetch_weather_data', boom)
    response = client.get('/api/weather')

    assert response.status_code == 400
    payload = response.get_json()
    assert payload['success'] is False
    assert 'database.db' not in payload['message']
    assert 'RuntimeError' not in payload['message']
    assert 'temporarily unavailable' in payload['message'].lower()


def test_weather_api_still_surfaces_weather_error_wording(tmp_path, monkeypatch):
    """WeatherError messages are intentionally user-facing and must survive."""
    from services.weather_service import WeatherError

    _, client, _ = make_client(tmp_path)
    register(client, 'weather-wording@example.com')
    create_farm(client, 'Wording Farm')

    monkeypatch.setattr(
        app_module, 'fetch_weather_data',
        lambda *_args: (_ for _ in ()).throw(WeatherError('Coordinates out of bounds.')),
    )
    response = client.get('/api/weather')

    assert response.status_code == 400
    assert response.get_json()['message'] == 'Coordinates out of bounds.'


def test_reverse_geocode_api_does_not_leak_internal_exception_text(tmp_path, monkeypatch):
    _, client, _ = make_client(tmp_path)
    register(client, 'geocode-leak@example.com')
    create_farm(client, 'Geocode Farm')

    def boom(*_args):
        raise RuntimeError('HTTPSConnectionPool(host=secret.internal:443): Max retries exceeded')

    monkeypatch.setattr(app_module, 'reverse_geocode', boom)
    response = client.post('/api/reverse-geocode', json={'latitude': 18.5, 'longitude': 73.8})

    assert response.status_code == 502
    payload = response.get_json()
    assert payload['success'] is False
    assert 'secret.internal' not in payload['message']
    assert 'HTTPSConnectionPool' not in payload['message']
    assert 'Max retries' not in payload['message']



def test_second_user_cannot_mutate_first_user_activity(tmp_path):
    _, client, database = make_client(tmp_path)
    register(client, 'owner@example.com')
    create_farm(client, 'Owner Farm')
    client.post('/activities/create', data={
        'title': 'Owner private task', 'activity_type': 'Field inspection',
        'description': 'Owner only', 'due_date': '2030-01-01',
    })

    with sqlite3.connect(database) as connection:
        activity_id = connection.execute(
            'SELECT id FROM farm_activities WHERE title = ?', ('Owner private task',)
        ).fetchone()[0]

    client.post('/logout')
    register(client, 'intruder@example.com', password='intruder123')
    create_farm(client, 'Intruder Farm')

    response = client.post(f'/activities/{activity_id}/status', data={'status': 'COMPLETED'})
    assert response.status_code in (302, 403, 404)

    with sqlite3.connect(database) as connection:
        status = connection.execute(
            'SELECT status FROM farm_activities WHERE id = ?', (activity_id,)
        ).fetchone()[0]
        assert status == 'PENDING', 'cross-user activity mutation must not succeed'


def test_intruder_dashboard_does_not_expose_other_farm_name(tmp_path):
    _, client, _ = make_client(tmp_path)
    register(client, 'farm-owner@example.com')
    create_farm(client, 'Secret Owner Farm')
    client.post('/logout')

    register(client, 'farm-intruder@example.com', password='intruder123')
    create_farm(client, 'Intruder Farm')
    page = client.get('/dashboard')

    assert page.status_code == 200
    assert b'Secret Owner Farm' not in page.data


def test_password_change_invalidates_existing_sessions(tmp_path):
    _, client, _ = make_client(tmp_path)
    register(client, 'rotate@example.com')
    create_farm(client, 'Rotate Farm')

    assert client.get('/dashboard').status_code == 200

    client.post('/settings/change-password', data={
        'current_password': 'farmer123',
        'new_password': 'rotated123',
        'confirm_password': 'rotated123',
    })
    assert client.get('/dashboard').status_code == 302
    assert client.post('/login', data={
        'email': 'rotate@example.com', 'password': 'rotated123',
    }).status_code == 302


def test_tampered_auth_token_is_rejected(tmp_path):
    _, client, _ = make_client(tmp_path)
    register(client, 'tamper@example.com')
    create_farm(client, 'Tamper Farm')

    with client.session_transaction() as session:
        session['auth_token'] = 'forged-token'

    assert client.get('/dashboard').status_code == 302


def test_protected_pages_do_not_render_tracebacks(tmp_path, monkeypatch):
    _, client, _ = make_client(tmp_path)
    register(client, 'trace@example.com')
    create_farm(client, 'Trace Farm')

    monkeypatch.setattr(
        app_module, 'predict_crop',
        lambda _values: (_ for _ in ()).throw(RuntimeError('internal detail /secret/path')),
    )
    response = client.post('/crop-recommendation', data={
        'nitrogen': '90', 'phosphorus': '42', 'potassium': '43', 'ph': '6.5',
        'temperature': '20.8', 'humidity': '82', 'rainfall': '210',
    })

    assert response.status_code == 503
    assert b'Traceback' not in response.data
    assert b'/secret/path' not in response.data
    assert b'temporarily unavailable' in response.data.lower()


def test_csrf_token_is_required_for_state_changing_posts(tmp_path):
    """CSRF is only enforced when CSRF_ENABLED is on, which is the production default."""
    _, client, database = make_client(tmp_path, csrf_enabled=True, name='security-csrf')

    # Establish a session so the CSRF token exists before any POST.
    client.get('/register')
    with client.session_transaction() as session:
        token = session['csrf_token']

    registered = client.post('/register', data={
        'csrf_token': token,
        'name': 'Security Farmer', 'email': 'csrf@example.com', 'password': 'farmer123',
    })
    assert registered.status_code == 302

    # Registration clears the session, so the CSRF token is re-minted on the
    # next request. A real browser always loads a page before posting a form.
    client.get('/farm/setup')
    with client.session_transaction() as session:
        token = session['csrf_token']

    setup = client.post('/farm/setup', data={
        'csrf_token': token,
        'farm_name': 'CSRF Farm', 'area': '2.5', 'location_name': 'Pune',
        'latitude': '18.5', 'longitude': '73.8',
        'nitrogen': '90', 'phosphorus': '42', 'potassium': '43', 'ph': '6.5',
    })
    assert setup.status_code == 302

    rejected = client.post('/activities/create', data={
        'csrf_token': 'wrong-token',
        'title': 'Forged task', 'activity_type': 'Field inspection',
        'description': 'x', 'due_date': '2030-01-01',
    })
    assert rejected.status_code == 400

    accepted = client.post('/activities/create', data={
        'csrf_token': token,
        'title': 'Legit task', 'activity_type': 'Field inspection',
        'description': 'x', 'due_date': '2030-01-01',
    })
    assert accepted.status_code == 302

    with sqlite3.connect(database) as connection:
        titles = {row[0] for row in connection.execute('SELECT title FROM farm_activities')}
    assert 'Legit task' in titles
    assert 'Forged task' not in titles

def test_reverse_geocode_api_rejects_out_of_bounds_coordinates(tmp_path):
    _, client, _ = make_client(tmp_path)
    register(client, 'geocode-bounds@example.com')
    create_farm(client, 'Bounds Farm')

    response = client.post('/api/reverse-geocode', json={'latitude': 91, 'longitude': 73.8})

    assert response.status_code == 400
    assert response.get_json()['success'] is False
    assert 'Coordinates out of bounds.' == response.get_json()['message']


def test_api_endpoints_require_authentication(tmp_path):
    _, client, _ = make_client(tmp_path)

    assert client.get('/api/weather').status_code == 302
    assert client.post('/api/reverse-geocode', json={'latitude': 18.5, 'longitude': 73.8}).status_code == 302
    assert client.post('/api/recommend-crop', json={}).status_code == 302
