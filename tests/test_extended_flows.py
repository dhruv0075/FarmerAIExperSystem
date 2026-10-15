import sqlite3
from datetime import date

from app import create_app


def setup_client(tmp_path):
    db = tmp_path / 'flow.db'
    app = create_app({'TESTING': True, 'SECRET_KEY': 'test', 'DATABASE': str(db)})
    client = app.test_client()
    client.post('/register', data={'name': 'Tester', 'email': 'tester@example.com', 'password': 'secret123'})
    client.post('/farm', data={'farm_name': 'Test farm', 'area': 2,
                              'nitrogen': 90, 'phosphorus': 42, 'potassium': 43, 'ph': 6.5})
    return app, client, db


def test_all_get_pages(tmp_path):
    app, client, _ = setup_client(tmp_path)
    for rule in app.url_map.iter_rules():
        if rule.arguments or 'GET' not in rule.methods or rule.rule.startswith('/api/') or rule.rule == '/logout':
            continue
        response = client.get(rule.rule, follow_redirects=True)
        assert response.status_code == 200, rule.rule


def test_expense_and_sale_persist_in_existing_schema(tmp_path):
    _, client, db = setup_client(tmp_path)
    client.post('/activities/create', data={
        'title': 'Apply fertilizer', 'activity_type': 'Fertilizer',
        'due_date': date.today().isoformat(),
    })
    with sqlite3.connect(db) as conn:
        activity_id = conn.execute(
            "SELECT id FROM farm_activities WHERE title = 'Apply fertilizer'"
        ).fetchone()[0]
    client.post(f'/activities/{activity_id}/status', data={
        'status': 'COMPLETED', 'amount_spent': '500',
    })
    client.post('/add-sale', data={'crop_name': 'Rice', 'quantity_kg': 100, 'price_per_kg': 25})
    with sqlite3.connect(db) as conn:
        assert conn.execute('SELECT amount, category, activity_id FROM farm_expenses').fetchone() == (500, 'FERTILIZER', activity_id)
        assert conn.execute('SELECT total_amount, unit FROM sales').fetchone() == (2500, 'kg')
    assert client.get('/expenses').status_code == 200


def test_legacy_add_expense_endpoint_redirects_without_writing(tmp_path):
    _, client, db = setup_client(tmp_path)
    response = client.post('/add-expense', data={'category': 'SEEDS', 'amount': 500})
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/activities')
    with sqlite3.connect(db) as conn:
        assert conn.execute('SELECT COUNT(*) FROM farm_expenses').fetchone()[0] == 0


def test_active_crop_scene_is_shown_on_lifecycle_and_dashboard(tmp_path):
    _, client, _ = setup_client(tmp_path)
    client.post('/lifecycle', data={
        'crop_name': 'rice',
        'sowing_date': date.today().isoformat(),
    })

    lifecycle = client.get('/lifecycle')
    dashboard = client.get('/dashboard')
    assert b'data-farm-scene="plant"' in lifecycle.data
    assert b'data-farm-scene="plant"' in dashboard.data
    assert b'farm-scene.js' in dashboard.data


def test_problem_report_persists(tmp_path):
    _, client, db = setup_client(tmp_path)
    response = client.post('/report-problem', data={'crop': 'rice', 'symptoms': 'yellow leaves', 'farmer_notes': 'First noticed yesterday'}, follow_redirects=True)
    assert response.status_code == 200
    assert b'yellow leaves' in response.data
    assert b'First noticed yesterday' in response.data
    assert b'Screening Confidence' not in response.data
    assert b'screening completed successfully' not in response.data
    with sqlite3.connect(db) as conn:
        assert conn.execute('SELECT duration_days, affected_area_pct, status FROM disease_reports').fetchone() == (None, None, 'REPORTED')


def test_problem_report_rejects_missing_symptoms(tmp_path):
    _, client, db = setup_client(tmp_path)
    assert client.post('/report-problem', data={'crop': 'rice', 'symptoms': ' '}).status_code == 400
    with sqlite3.connect(db) as conn:
        assert conn.execute('SELECT COUNT(*) FROM disease_reports').fetchone()[0] == 0
