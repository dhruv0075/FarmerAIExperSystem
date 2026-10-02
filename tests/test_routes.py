import uuid

import pytest

from app import create_app


def test_favicon_is_linked_and_available(tmp_path):
    app = create_app({'TESTING': True, 'SECRET_KEY': 'test-secret', 'DATABASE': str(tmp_path / 'favicon.db')})
    client = app.test_client()

    assert b'/static/img/favicon.svg' in client.get('/').data
    response = client.get('/static/img/favicon.svg')
    assert response.status_code == 200
    assert response.mimetype == 'image/svg+xml'


def test_registration_and_login_flow(tmp_path):
    app = create_app({'TESTING': True, 'SECRET_KEY': 'test-secret', 'DATABASE': str(tmp_path / 'routes.db')})
    client = app.test_client()
    email = f'user_{uuid.uuid4().hex[:8]}@example.com'

    response = client.post('/register', data={'name': 'Test User', 'email': email, 'password': 'secret123'}, follow_redirects=True)
    assert response.status_code == 200
    assert b'AgriWise AI' in response.data
    invalid = client.post('/register', data={'name': 'Another', 'email': 'invalid', 'password': 'short'})

    response = client.post('/register', data={'name': 'Another', 'email': email.upper(), 'password': 'secret123'}, follow_redirects=True)
    assert response.status_code == 200
    assert b'unable to create an account with those details' in response.data.lower()
    assert b'unable to create an account with those details' in invalid.data.lower()
    assert b'already registered' not in response.data.lower()

    response = client.get('/dashboard')
    assert response.status_code == 302
    assert response.location.endswith('/farm/setup')
    client.post('/farm', data={'farm_name': 'Test Farm', 'area': '2'})
    response = client.get('/dashboard')
    assert response.status_code == 200

    for path in ['/farm', '/crop-recommendation', '/weather', '/lifecycle', '/advisories', '/history', '/activities', '/compare-crops', '/what-if', '/risk-analysis', '/ml-analytics', '/expert-system', '/research', '/report']:
        response = client.get(path)
        assert response.status_code == 200, path

    response = client.post('/logout')
    assert response.status_code == 302

    response = client.post('/login', data={'email': email, 'password': 'wrongpass'}, follow_redirects=True)
    assert b'invalid email or password' in response.data.lower()

    response = client.post('/login', data={'email': email, 'password': 'secret123'}, follow_redirects=True)
    assert response.status_code == 200
    with client.session_transaction() as session:
        assert session.permanent is True


def test_password_change_requires_current_password_and_invalidates_session(tmp_path):
    app = create_app({'TESTING': True, 'SECRET_KEY': 'test-secret', 'DATABASE': str(tmp_path / 'password.db')})
    client = app.test_client()
    client.post('/register', data={'name': 'Test User', 'email': 'farmer@example.com', 'password': 'secret123'})

    assert client.post('/settings/change-password', data={
        'current_password': 'wrong-pass1', 'new_password': 'new-pass123', 'confirm_password': 'new-pass123'
    }).status_code == 302
    assert client.get('/settings').status_code == 200
    assert client.post('/settings/change-password', data={
        'current_password': 'secret123', 'new_password': 'new-pass123', 'confirm_password': 'new-pass123'
    }).status_code == 302
    assert client.get('/settings').status_code == 302
    assert client.post('/login', data={'email': 'farmer@example.com', 'password': 'secret123'}).status_code == 200
    assert client.post('/login', data={'email': 'farmer@example.com', 'password': 'new-pass123'}).status_code == 302


def test_weak_password_and_invalid_email_are_rejected(tmp_path):
    app = create_app({'TESTING': True, 'SECRET_KEY': 'test-secret', 'DATABASE': str(tmp_path / 'validation.db')})
    client = app.test_client()

    response = client.post('/register', data={'name': 'Test User', 'email': 'not-an-email', 'password': 'short'})
    assert b'unable to create an account with those details' in response.data.lower()
    assert client.post('/login', data={'email': 'not-an-email', 'password': 'short'}).status_code == 200


def test_production_cookie_and_security_headers(tmp_path, monkeypatch):
    monkeypatch.setenv('AGRIWISE_ENV', 'production')
    monkeypatch.setenv('AGRIWISE_SECRET_KEY', 'test-production-secret')
    app = create_app({'TESTING': True, 'DATABASE': str(tmp_path / 'security.db')})
    response = app.test_client().get('/')

    assert app.config['SECRET_KEY'] == 'test-production-secret'
    assert app.config['SESSION_COOKIE_SECURE'] is True
    assert app.config['SESSION_COOKIE_HTTPONLY'] is True
    assert app.config['SESSION_COOKIE_SAMESITE'] == 'Lax'
    assert app.config['PERMANENT_SESSION_LIFETIME'].total_seconds() == 12 * 60 * 60
    assert response.headers['X-Content-Type-Options'] == 'nosniff'
    assert response.headers['X-Frame-Options'] == 'DENY'
    assert response.headers['Referrer-Policy'] == 'strict-origin-when-cross-origin'
    assert "frame-ancestors 'none'" in response.headers['Content-Security-Policy']
    cookie = response.headers['Set-Cookie']
    assert 'Secure' in cookie and 'HttpOnly' in cookie and 'SameSite=Lax' in cookie


def test_production_requires_configured_secret(tmp_path, monkeypatch):
    monkeypatch.setenv('AGRIWISE_ENV', 'production')
    monkeypatch.delenv('AGRIWISE_SECRET_KEY', raising=False)

    with pytest.raises(RuntimeError, match='AGRIWISE_SECRET_KEY must be configured'):
        create_app({'TESTING': True, 'DATABASE': str(tmp_path / 'missing-secret.db')})


def test_logout_is_post_only_and_csrf_protected(tmp_path):
    app = create_app({'TESTING': True, 'SECRET_KEY': 'test-secret', 'DATABASE': str(tmp_path / 'logout.db')})
    client = app.test_client()
    client.post('/register', data={'name': 'Test User', 'email': 'farmer@example.com', 'password': 'secret123'})
    app.config['CSRF_ENABLED'] = True

    assert client.get('/logout').status_code == 405
    assert client.post('/logout').status_code == 400
    with client.session_transaction() as session:
        token = session['csrf_token']
    assert client.post('/logout', data={'csrf_token': token}).status_code == 302
    assert client.get('/settings').status_code == 302


def test_stale_or_mismatched_session_redirects_instead_of_raising(tmp_path):
    app = create_app({'SECRET_KEY': 'test-secret', 'DATABASE': str(tmp_path / 'stale-session.db')})
    client = app.test_client()
    with client.session_transaction() as session:
        session['user_id'] = 987654
        session['auth_token'] = 'token-from-another-instance'

    response = client.get('/crop-recommendation')

    assert response.status_code == 302
    assert response.location.endswith('/login')
    with client.session_transaction() as session:
        assert 'user_id' not in session
        assert 'auth_token' not in session


def test_session_from_another_instance_cannot_match_reused_user_id(tmp_path):
    first_app = create_app({'TESTING': True, 'SECRET_KEY': 'shared-test-secret', 'DATABASE': str(tmp_path / 'instance-a.db')})
    second_app = create_app({'TESTING': True, 'SECRET_KEY': 'shared-test-secret', 'DATABASE': str(tmp_path / 'instance-b.db')})
    first_client = first_app.test_client()
    second_client = second_app.test_client()
    first_client.post('/register', data={
        'name': 'First Farmer', 'email': 'first@example.com', 'password': 'first-pass123'
    })
    second_client.post('/register', data={
        'name': 'Second Farmer', 'email': 'second@example.com', 'password': 'second-pass123'
    })
    first_cookie = first_client.get_cookie('session')
    assert first_cookie is not None

    second_client.set_cookie('session', first_cookie.value)
    response = second_client.get('/crop-recommendation')

    assert response.status_code == 302
    assert response.location.endswith('/login')
