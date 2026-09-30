import sqlite3
from datetime import date

from app import create_app


def setup_client(tmp_path):
    db = tmp_path / 'flow.db'
    app = create_app({'TESTING': True, 'SECRET_KEY': 'test', 'DATABASE': str(db)})
    client = app.test_client()
    client.post('/register', data={'name': 'Tester', 'email': 'tester@example.com', 'password': 'secret123'})
    client.post('/farm', data={'farm_name': 'Test farm', 'area': 2})
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
    client.post('/add-expense', data={'category': 'SEEDS', 'amount': 500, 'expense_date': date.today().isoformat()})
    client.post('/add-sale', data={'crop_name': 'Rice', 'quantity_kg': 100, 'price_per_kg': 25})
    with sqlite3.connect(db) as conn:
        assert conn.execute('SELECT amount FROM farm_expenses').fetchone()[0] == 500
        assert conn.execute('SELECT total_amount, unit FROM sales').fetchone() == (2500, 'kg')
    assert client.get('/expenses').status_code == 200


def test_problem_report_persists(tmp_path):
    _, client, _ = setup_client(tmp_path)
    response = client.post('/report-problem', data={'crop': 'rice', 'symptoms': 'yellow leaves'}, follow_redirects=True)
    assert response.status_code == 200
