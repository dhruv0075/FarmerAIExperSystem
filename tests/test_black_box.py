import io
import sqlite3
from datetime import date, timedelta

import pytest
from PIL import Image

import app as app_module
from app import create_app


def make_client(tmp_path, name='black-box'):
    database = tmp_path / f'{name}.db'
    application = create_app({'TESTING': True, 'SECRET_KEY': 'black-box-secret', 'DATABASE': str(database)})
    return application, application.test_client(), database


def register(client, name='Black Box Farmer', email='farmer@example.com', password='farmer123'):
    return client.post('/register', data={'name': name, 'email': email, 'password': password})


def create_farm(client, **overrides):
    data = {
        'farm_name': 'Black Box Farm', 'area': '2.5', 'location_name': 'Pune',
        'latitude': '18.5', 'longitude': '73.8',
        'nitrogen': '90', 'phosphorus': '42', 'potassium': '43', 'ph': '6.5',
    }
    data.update(overrides)
    return client.post('/farm/setup', data=data)


def crop_input(**overrides):
    values = {
        'nitrogen': '90', 'phosphorus': '42', 'potassium': '43', 'ph': '6.5',
        'temperature': '20.8', 'humidity': '82', 'rainfall': '210',
    }
    values.update(overrides)
    return values


@pytest.mark.parametrize(('name', 'email', 'password'), [
    ('', 'valid@example.com', 'farmer123'),
    ('Farmer', '', 'farmer123'),
    ('Farmer', 'invalid-email', 'farmer123'),
    ('Farmer', 'valid@example.com', ''),
    ('Farmer', 'valid@example.com', 'short1'),
    ('Farmer', 'valid@example.com', 'a' * 129 + '1'),
    ('Farmer', 'valid@example.com', '12345678'),
    ('Farmer', 'valid@example.com', 'abcdefgh'),
])
def test_registration_invalid_equivalence_partition(tmp_path, name, email, password):
    _, client, database = make_client(tmp_path)
    response = register(client, name, email, password)

    assert response.status_code == 200
    assert b'Unable to create an account with those details.' in response.data
    assert b'Traceback' not in response.data
    with sqlite3.connect(database) as connection:
        assert connection.execute('SELECT COUNT(*) FROM users').fetchone()[0] == 0


def test_registration_normalizes_email_and_does_not_disclose_duplicate(tmp_path):
    _, client, _ = make_client(tmp_path)
    first = register(client, email='  Farmer@Example.com  ')
    duplicate = register(client, name='Other farmer', email='farmer@example.com')

    assert first.status_code == 302
    assert duplicate.status_code == 200
    assert b'Unable to create an account with those details.' in duplicate.data
    assert b'already registered' not in duplicate.data.lower()
    client.post('/logout')
    assert client.post('/login', data={'email': 'FARMER@EXAMPLE.COM', 'password': 'farmer123'}).status_code == 302


@pytest.mark.parametrize('password', ['a1bcdefg', 'a' * 127 + '1'])
def test_registration_password_minimum_and_maximum_lengths(tmp_path, password):
    _, client, _ = make_client(tmp_path)

    response = register(client, password=password)

    assert response.status_code == 302


def test_name_with_special_characters_is_rendered_as_text(tmp_path):
    _, client, _ = make_client(tmp_path)
    name = '<script>alert(1)</script>'
    assert register(client, name=name).status_code == 302
    create_farm(client)

    dashboard = client.get('/dashboard')

    assert dashboard.status_code == 200
    assert name.encode() not in dashboard.data
    assert b'&lt;script&gt;alert(1)&lt;/script&gt;' in dashboard.data


@pytest.mark.parametrize(('email', 'password'), [
    ('farmer@example.com', 'wrong-pass1'),
    ('unknown@example.com', 'farmer123'),
    ('', 'farmer123'),
    ('farmer@example.com', ''),
])
def test_login_invalid_credentials_are_generic(tmp_path, email, password):
    _, client, _ = make_client(tmp_path)
    register(client)
    client.post('/logout')

    response = client.post('/login', data={'email': email, 'password': password})

    assert response.status_code == 200
    assert b'Invalid email or password.' in response.data
    assert b'No account' not in response.data


@pytest.mark.parametrize(('current_password', 'new_password', 'confirm_password'), [
    ('wrong-pass1', 'new-pass123', 'new-pass123'),
    ('farmer123', 'short1', 'short1'),
    ('farmer123', '12345678', '12345678'),
    ('farmer123', 'abcdefgh', 'abcdefgh'),
    ('farmer123', 'a' * 129 + '1', 'a' * 129 + '1'),
    ('farmer123', 'new-pass123', 'different123'),
    ('farmer123', 'farmer123', 'farmer123'),
])
def test_invalid_password_change_preserves_existing_login(tmp_path, current_password, new_password, confirm_password):
    _, client, _ = make_client(tmp_path)
    register(client)

    response = client.post('/settings/change-password', data={
        'current_password': current_password,
        'new_password': new_password,
        'confirm_password': confirm_password,
    }, follow_redirects=True)
    client.post('/logout')
    old_password_login = client.post('/login', data={'email': 'farmer@example.com', 'password': 'farmer123'})

    assert response.status_code == 200
    assert old_password_login.status_code == 302


@pytest.mark.parametrize(('area', 'valid'), [('0', False), ('-0.1', False), ('0.1', True), ('2.5', True)])
def test_farm_area_boundary_inputs(tmp_path, area, valid):
    _, client, database = make_client(tmp_path)
    register(client)

    response = create_farm(client, area=area)

    if valid:
        assert response.status_code == 302
        with sqlite3.connect(database) as connection:
            assert connection.execute('SELECT area FROM farms').fetchone()[0] == float(area)
    else:
        assert response.status_code == 200
        assert b'Farm area must be a positive number.' in response.data
        with sqlite3.connect(database) as connection:
            assert connection.execute('SELECT COUNT(*) FROM farms').fetchone()[0] == 0


def test_farm_name_required_and_very_large_finite_area_does_not_crash(tmp_path):
    _, client, database = make_client(tmp_path)
    register(client)
    empty_name = create_farm(client, farm_name='')
    large_area = create_farm(client, area='1e100')

    assert empty_name.status_code == 200
    assert b'Farm name is required' in empty_name.data
    assert large_area.status_code == 302
    with sqlite3.connect(database) as connection:
        assert connection.execute('SELECT area FROM farms').fetchone()[0] == 1e100


def test_farm_setup_requires_measured_soil_values_and_saves_baseline(tmp_path):
    _, client, database = make_client(tmp_path)
    register(client)

    missing = create_farm(client, nitrogen='', phosphorus='', potassium='', ph='')
    assert missing.status_code == 200
    assert b'Enter measured nitrogen, phosphorus, potassium, and pH values' in missing.data
    with sqlite3.connect(database) as connection:
        assert connection.execute('SELECT COUNT(*) FROM farms').fetchone()[0] == 0
        assert connection.execute('SELECT COUNT(*) FROM soil_records').fetchone()[0] == 0

    created = create_farm(client, nitrogen='88', phosphorus='35', potassium='52', ph='6.7')
    assert created.status_code == 302
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            'SELECT nitrogen, phosphorus, potassium, ph FROM soil_records'
        ).fetchone() == (88.0, 35.0, 52.0, 6.7)

    setup_page = client.get('/farm/setup')
    crop_page = client.get('/crop-recommendation')
    assert b'name="no_soil_test"' not in setup_page.data
    assert b'name="nitrogen" value="88.0" required' in setup_page.data
    assert b'name="nitrogen" class="form-control" value="88.0" required' in crop_page.data


@pytest.mark.parametrize(('field', 'value'), [
    ('nitrogen', '-1'), ('phosphorus', 'nan'), ('potassium', 'inf'),
    ('ph', '14.1'), ('moisture', '100.1'),
])
def test_farm_setup_rejects_invalid_soil_values(tmp_path, field, value):
    _, client, database = make_client(tmp_path)
    register(client)

    response = create_farm(client, **{field: value})

    assert response.status_code == 200
    assert b'Enter measured nitrogen, phosphorus, potassium, and pH values' in response.data
    with sqlite3.connect(database) as connection:
        assert connection.execute('SELECT COUNT(*) FROM farms').fetchone()[0] == 0


@pytest.mark.parametrize(('latitude', 'longitude'), [
    ('-90', '-180'), ('90', '180'), ('0', '0'), ('18.5', '73.8'),
])
def test_coordinate_boundary_values_are_accepted(tmp_path, latitude, longitude):
    _, client, database = make_client(tmp_path)
    register(client)

    response = create_farm(client, latitude=latitude, longitude=longitude)

    assert response.status_code == 302
    with sqlite3.connect(database) as connection:
        assert connection.execute('SELECT latitude, longitude FROM farms').fetchone() == (float(latitude), float(longitude))


@pytest.mark.parametrize(('latitude', 'longitude'), [
    ('-90.1', '0'), ('90.1', '0'), ('0', '-180.1'), ('0', '180.1'),
])
def test_coordinate_values_outside_bounds_are_rejected(tmp_path, latitude, longitude):
    _, client, database = make_client(tmp_path)
    register(client)

    response = create_farm(client, latitude=latitude, longitude=longitude)

    assert response.status_code == 200
    assert b'Coordinates are invalid' in response.data
    with sqlite3.connect(database) as connection:
        assert connection.execute('SELECT COUNT(*) FROM farms').fetchone()[0] == 0


@pytest.mark.parametrize(('field', 'value'), [
    ('nitrogen', '0'), ('phosphorus', '0'), ('potassium', '0'),
    ('ph', '0'), ('ph', '7'), ('ph', '14'),
    ('humidity', '0'), ('humidity', '50'), ('humidity', '100'),
    ('rainfall', '0'), ('temperature', '-10'), ('temperature', '50'),
])
def test_crop_soil_and_climate_boundary_values_are_accepted(tmp_path, field, value):
    _, client, database = make_client(tmp_path)
    register(client)
    create_farm(client)

    response = client.post('/crop-recommendation', data=crop_input(**{field: value}))

    assert response.status_code == 200
    assert b'ML confidence' in response.data
    with sqlite3.connect(database) as connection:
        assert connection.execute('SELECT COUNT(*) FROM crop_recommendations').fetchone()[0] == 1


@pytest.mark.parametrize(('field', 'value', 'message'), [
    ('nitrogen', '-1', 'Nutrients and rainfall must be nonnegative.'),
    ('phosphorus', '-1', 'Nutrients and rainfall must be nonnegative.'),
    ('potassium', '-1', 'Nutrients and rainfall must be nonnegative.'),
    ('ph', '-0.1', 'pH must be between 0 and 14.'),
    ('ph', '14.1', 'pH must be between 0 and 14.'),
    ('humidity', '-1', 'Humidity must be between 0 and 100.'),
    ('humidity', '101', 'Humidity must be between 0 and 100.'),
    ('rainfall', '-1', 'Nutrients and rainfall must be nonnegative.'),
    ('ph', 'nan', 'finite numeric values'),
    ('humidity', 'inf', 'finite numeric values'),
    ('nitrogen', '', 'valid numeric values'),
])
def test_invalid_crop_soil_and_climate_inputs_are_rejected(tmp_path, field, value, message):
    _, client, database = make_client(tmp_path)
    register(client)
    create_farm(client)

    response = client.post('/crop-recommendation', data=crop_input(**{field: value}))

    assert response.status_code == 200
    assert message.encode() in response.data
    with sqlite3.connect(database) as connection:
        assert connection.execute('SELECT COUNT(*) FROM crop_recommendations').fetchone()[0] == 0


def test_crop_form_missing_values_are_rejected_without_saving_soil(tmp_path):
    _, client, database = make_client(tmp_path)
    register(client)
    create_farm(client)

    response = client.post('/crop-recommendation', data={'nitrogen': '90'})

    assert response.status_code == 200
    assert b'valid numeric values' in response.data
    with sqlite3.connect(database) as connection:
        assert connection.execute('SELECT COUNT(*) FROM soil_records').fetchone()[0] == 1


def test_crop_recommendation_handles_missing_model_without_server_error(tmp_path, monkeypatch):
    application, client, _ = make_client(tmp_path)
    application.config['PROPAGATE_EXCEPTIONS'] = False
    register(client)
    create_farm(client)
    monkeypatch.setattr(app_module, 'predict_crop', lambda _inputs: (_ for _ in ()).throw(FileNotFoundError('model unavailable')))

    response = client.post('/crop-recommendation', data=crop_input())

    assert response.status_code == 503
    assert b'temporarily unavailable' in response.data.lower()
    with sqlite3.connect(client.application.config['DATABASE']) as connection:
        assert connection.execute('SELECT COUNT(*) FROM soil_records').fetchone()[0] == 1


def test_weather_without_coordinates_and_provider_timeout_are_clear(tmp_path, monkeypatch):
    _, client, _ = make_client(tmp_path)
    register(client)
    create_farm(client, latitude='', longitude='')
    response = client.get('/api/weather')
    assert response.status_code == 400
    assert b'Set farm coordinates first' in response.data

    create_farm(client, latitude='18.5', longitude='73.8')
    monkeypatch.setattr(app_module, 'fetch_weather_data', lambda *_args: (_ for _ in ()).throw(TimeoutError()))
    response = client.get('/api/weather')
    assert response.status_code == 400
    assert b'success' in response.data


def test_lifecycle_accepts_today_and_rejects_future_date(tmp_path):
    _, client, database = make_client(tmp_path)
    register(client)
    create_farm(client)

    today = client.post('/lifecycle', data={'crop_name': 'Rice', 'sowing_date': date.today().isoformat()})
    future = client.post('/lifecycle', data={
        'crop_name': 'Rice', 'sowing_date': (date.today() + timedelta(days=1)).isoformat()
    }, follow_redirects=True)

    assert today.status_code == 302
    assert future.status_code == 200
    assert b'valid sowing date' in future.data
    with sqlite3.connect(database) as connection:
        assert connection.execute('SELECT COUNT(*) FROM crop_cycles').fetchone()[0] == 1


def test_lifecycle_rejects_unsupported_crop_and_old_date_is_accepted(tmp_path):
    _, client, database = make_client(tmp_path)
    register(client)
    create_farm(client)
    old_date = (date.today() - timedelta(days=3650)).isoformat()

    accepted = client.post('/lifecycle', data={'crop_name': 'Wheat', 'sowing_date': old_date})
    unsupported = client.post('/lifecycle', data={'crop_name': 'Unknown Crop', 'sowing_date': date.today().isoformat()})

    assert accepted.status_code == 302
    assert unsupported.status_code == 302
    with sqlite3.connect(database) as connection:
        assert connection.execute('SELECT COUNT(*) FROM crop_cycles').fetchone()[0] == 1


def test_problem_report_escapes_script_text_and_handles_fake_image(tmp_path, monkeypatch):
    application, client, database = make_client(tmp_path)
    register(client)
    create_farm(client)
    monkeypatch.setattr(app_module, 'UPLOAD_FOLDER', tmp_path / 'private_uploads')

    report = client.post('/report-problem', data={
        'crop': 'Rice', 'symptoms': '<script>alert(1)</script>', 'farmer_notes': '<img src=x onerror=alert(1)>',
    }, follow_redirects=True)
    fake_image = client.post('/report-problem', data={
        'symptoms': 'spots', 'photo': (io.BytesIO(b'not an image'), 'fake.jpg', 'image/jpeg'),
    })

    assert report.status_code == 200
    assert b'<script>alert(1)</script>' not in report.data
    assert b'&lt;script&gt;' in report.data
    assert fake_image.status_code == 400
    with sqlite3.connect(database) as connection:
        assert connection.execute('SELECT COUNT(*) FROM disease_reports').fetchone()[0] == 1


def test_upload_path_traversal_is_stored_privately_and_oversize_is_rejected(tmp_path, monkeypatch):
    application, client, database = make_client(tmp_path)
    register(client)
    create_farm(client)
    upload_directory = tmp_path / 'private_uploads'
    monkeypatch.setattr(app_module, 'UPLOAD_FOLDER', upload_directory)
    image = io.BytesIO()
    Image.new('RGB', (2, 2), color='green').save(image, format='PNG')
    image.seek(0)

    response = client.post('/report-problem', data={
        'symptoms': 'leaf spots', 'photo': (image, '../../outside.png', 'image/png'),
    }, follow_redirects=True)
    with sqlite3.connect(database) as connection:
        image_path = connection.execute('SELECT image_path FROM disease_reports').fetchone()[0]
    too_large = client.post('/report-problem', data={
        'symptoms': 'large upload',
        'photo': (io.BytesIO(b'x' * (5 * 1024 * 1024 + 1)), 'large.png', 'image/png'),
    })

    assert response.status_code == 200
    assert '..' not in image_path and '/' not in image_path and '\\' not in image_path
    assert (upload_directory / image_path).is_file()
    assert too_large.status_code == 413
    assert b'Traceback' not in too_large.data


def test_valid_image_at_advertised_five_mib_limit_is_accepted(tmp_path, monkeypatch):
    _, client, _ = make_client(tmp_path)
    register(client)
    create_farm(client)
    monkeypatch.setattr(app_module, 'UPLOAD_FOLDER', tmp_path / 'private_uploads')
    image = io.BytesIO()
    Image.new('RGB', (2, 2), color='green').save(image, format='PNG')
    payload = image.getvalue()
    payload += b' ' * (5 * 1024 * 1024 - len(payload))

    response = client.post('/report-problem', data={
        'symptoms': 'maximum allowed image size',
        'photo': (io.BytesIO(payload), 'maximum.png', 'image/png'),
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'Symptom report saved' in response.data


def test_non_image_extension_is_rejected(tmp_path, monkeypatch):
    _, client, database = make_client(tmp_path)
    register(client)
    create_farm(client)
    monkeypatch.setattr(app_module, 'UPLOAD_FOLDER', tmp_path / 'private_uploads')

    response = client.post('/report-problem', data={
        'symptoms': 'leaf spots', 'photo': (io.BytesIO(b'program'), 'payload.exe', 'application/octet-stream'),
    })

    assert response.status_code == 400
    with sqlite3.connect(database) as connection:
        assert connection.execute('SELECT COUNT(*) FROM disease_reports').fetchone()[0] == 0


def test_unknown_route_and_protected_route_have_clean_responses(tmp_path):
    _, client, _ = make_client(tmp_path)

    missing = client.get('/route-that-does-not-exist')
    protected = client.get('/crop-recommendation')

    assert missing.status_code == 404
    assert b'Traceback' not in missing.data
    assert protected.status_code == 302
    assert protected.location.endswith('/login')


def test_missing_report_image_id_returns_not_found(tmp_path):
    _, client, _ = make_client(tmp_path)
    register(client)

    response = client.get('/disease-image/999999')

    assert response.status_code == 404
    assert b'Traceback' not in response.data


def test_farmer_pages_do_not_expose_another_accounts_records(tmp_path):
    application, owner, _ = make_client(tmp_path, 'two-farmer-isolation')
    register(owner, name='Owner Farmer', email='owner@example.com')
    create_farm(owner, farm_name='OWNER PRIVATE FARM')
    owner.post('/activities/create', data={
        'title': 'OWNER PRIVATE ACTIVITY', 'activity_type': 'Field inspection',
    })
    owner.post('/report-problem', data={'symptoms': 'OWNER_PRIVATE_SYMPTOM'})

    other = application.test_client()
    register(other, name='Other Farmer', email='other@example.com')
    create_farm(other, farm_name='OTHER FARM')

    for path in ['/dashboard', '/history', '/activities', '/report-problem']:
        response = other.get(path)
        assert response.status_code == 200, path
        assert b'OWNER PRIVATE FARM' not in response.data, path
        assert b'OWNER PRIVATE ACTIVITY' not in response.data, path
        assert b'OWNER_PRIVATE_SYMPTOM' not in response.data, path
    assert b'OTHER FARM' in other.get('/dashboard').data