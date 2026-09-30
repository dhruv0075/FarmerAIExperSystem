import io
import sqlite3
from datetime import date

import pytest

from test_extended_flows import setup_client
from services.official_market_service import parse_records
from services.expert_system import evaluate_expert_system


def test_official_market_rejects_bad_values():
    row = dict(commodity='Rice', market='Test', district='District', state='State',
               arrival_date=date.today().strftime('%d/%m/%Y'), min_price='100', modal_price='150', max_price='200')
    assert parse_records([row])['commodities']['rice']['prices']
    assert not parse_records([dict(row, modal_price='nan')])['commodities']
    assert not parse_records([dict(row, modal_price='250')])['commodities']


def test_unknown_soil_never_claimed_measured():
    result = evaluate_expert_system('Rice', 'Vegetative', {'current': {}}, {})
    assert result['facts']['soil_nitrogen_kgha'] is None
    assert result['facts']['current_temperature_c'] is None


def test_real_html_finance_form_fields(tmp_path):
    _, client, db = setup_client(tmp_path)
    client.post('/add-expense', data={'category': 'SEEDS', 'amount': 250, 'date': '2026-01-01', 'vendor': 'Test'})
    client.post('/add-sale', data={'commodity': 'Rice', 'quantity_sold': 5, 'price_per_unit': 2000, 'unit': 'Quintal'})
    with sqlite3.connect(db) as conn:
        assert conn.execute('SELECT date, vendor FROM farm_expenses').fetchone() == ('2026-01-01', 'Test')
        assert conn.execute('SELECT total_amount, unit FROM sales').fetchone() == (10000, 'Quintal')


def test_invalid_image_rejected(tmp_path):
    _, client, db = setup_client(tmp_path)
    result = client.post('/report-problem', data={'photo': (io.BytesIO(b'not an image'), 'bad.png', 'image/png')})
    assert result.status_code == 400
    with sqlite3.connect(db) as conn:
        assert conn.execute('SELECT COUNT(*) FROM disease_reports').fetchone()[0] == 0


def test_resource_submission_visible(tmp_path):
    _, client, _ = setup_client(tmp_path)
    result = client.post('/add-resource', data={'name': 'Test Seller', 'category': 'SEED', 'latitude': 18.5, 'longitude': 73.8}, follow_redirects=True)
    assert result.status_code == 200
    assert b'Test Seller' in result.data


def test_csrf_rejects_unverified_post(tmp_path):
    app, client, _ = setup_client(tmp_path)
    app.config['CSRF_ENABLED'] = True
    assert client.post('/add-expense', data={'amount': 10}).status_code == 400
    with client.session_transaction() as session:
        token = session['csrf_token']
    assert client.post('/add-expense', data={'amount': 10, 'csrf_token': token}).status_code == 302


def test_rescheduled_task_is_not_completed(tmp_path):
    _, client, db = setup_client(tmp_path)
    client.post('/activities/create', data={'title': 'Water check', 'activity_type': 'Irrigation'})
    with sqlite3.connect(db) as conn:
        activity_id = conn.execute('SELECT id FROM farm_activities').fetchone()[0]
    client.post(f'/activities/{activity_id}/status', data={'status': 'RESCHEDULED', 'rescheduled_date': '2026-12-01'})
    with sqlite3.connect(db) as conn:
        assert conn.execute('SELECT status, due_date, completed_at FROM farm_activities').fetchone() == ('PENDING', '2026-12-01', None)
