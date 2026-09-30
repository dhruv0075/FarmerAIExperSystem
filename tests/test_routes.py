import uuid

from app import create_app


def test_registration_and_login_flow(tmp_path):
    app = create_app({'TESTING': True, 'SECRET_KEY': 'test-secret', 'DATABASE': str(tmp_path / 'routes.db')})
    client = app.test_client()
    email = f'user_{uuid.uuid4().hex[:8]}@example.com'

    response = client.post('/register', data={'name': 'Test User', 'email': email, 'password': 'secret123'}, follow_redirects=True)
    assert response.status_code == 200
    assert b'AgriWise AI' in response.data

    response = client.post('/register', data={'name': 'Another', 'email': email, 'password': 'secret123'}, follow_redirects=True)
    assert response.status_code == 200
    assert b'already registered' in response.data.lower()

    response = client.get('/dashboard')
    assert response.status_code == 302
    assert response.location.endswith('/farm/setup')
    client.post('/farm', data={'farm_name': 'Test Farm', 'area': '2'})
    response = client.get('/dashboard')
    assert response.status_code == 200

    for path in ['/farm', '/crop-recommendation', '/weather', '/lifecycle', '/advisories', '/history', '/activities', '/compare-crops', '/what-if', '/risk-analysis', '/ml-analytics', '/expert-system', '/research', '/report']:
        response = client.get(path)
        assert response.status_code == 200, path

    response = client.get('/logout')
    assert response.status_code == 302

    response = client.post('/login', data={'email': email, 'password': 'wrongpass'}, follow_redirects=True)
    assert b'invalid email or password' in response.data.lower()

    response = client.post('/login', data={'email': email, 'password': 'secret123'}, follow_redirects=True)
    assert response.status_code == 200
