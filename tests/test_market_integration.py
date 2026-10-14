import json
import time
import threading
from datetime import date

import pytest
import requests

from services import official_market_service as market
from scripts.diagnose_market_api import build_diagnostic


def reset(monkeypatch, tmp_path):
    monkeypatch.setattr(market, '_cache', {})
    monkeypatch.setattr(market, '_next_attempt', 0)
    monkeypatch.setattr(market, '_refresh_after', {})
    monkeypatch.setattr(market, '_last_refresh_errors', {})
    monkeypatch.setattr(market, '_inflight', False)
    monkeypatch.setattr(market, '_loaded', True)
    monkeypatch.setattr(market, 'CACHE_PATH', tmp_path / 'cache.json')
    monkeypatch.setenv('DATA_GOV_IN_API_KEY', 'test-secret-never-log')


def test_bounded_backoff_preserves_cache_and_redacts_key(monkeypatch, tmp_path, caplog):
    reset(monkeypatch, tmp_path)
    saved = {'updated_at': '2026-01-01T00:00:00+00:00', 'commodities': {'rice': {}}, 'markets': []}
    market._cache['{}'] = saved
    delays, calls = [], []
    def fail(*args, **kwargs):
        calls.append(1)
        raise requests.ConnectTimeout('secret request URL test-secret-never-log')
    monkeypatch.setattr(market, 'request_sample', fail)
    monkeypatch.setattr(market.time, 'sleep', delays.append)
    result = market.refresh_market_data({'commodity': 'Rice'})
    assert len(calls) == 3
    assert delays == [0.5, 1.0]
    assert market._cache['{}'] == saved
    assert market._next_attempt > time.time()
    assert result['status'] == 'failed'
    assert 'before the connection timeout' in result['message']
    assert 'stage=TCP connection exception=ConnectTimeout' in caplog.text
    assert 'test-secret-never-log' not in caplog.text


def test_page_read_never_starts_network_or_thread(monkeypatch, tmp_path):
    reset(monkeypatch, tmp_path)
    def forbidden(*args, **kwargs):
        raise AssertionError("Page read started external work")
    monkeypatch.setattr(market, 'request_sample', forbidden)
    monkeypatch.setattr(market.threading, 'Thread', forbidden)
    for _ in range(3):
        result = market.load_official_market_data({'commodity': 'Rice'})
        assert result['refresh_status'] == 'unavailable'


def test_small_sample_then_filtered_request_and_disk_cache(monkeypatch, tmp_path):
    reset(monkeypatch, tmp_path)
    calls = []
    record = {'commodity': 'Rice', 'market': 'Test', 'district': 'District', 'state': 'State',
              'arrival_date': date.today().strftime('%d/%m/%Y'), 'min_price': '100', 'modal_price': '150', 'max_price': '200'}
    def fetch(key, filters=None):
        calls.append(filters)
        return {'records': [record]}
    monkeypatch.setattr(market, 'request_sample', fetch)
    filters = {'commodity': 'Rice', 'state': 'State', 'district': 'District', 'market': 'Test'}
    market.refresh_market_data(filters)
    assert calls == [None, filters]
    disk = json.loads(market.CACHE_PATH.read_text())
    assert disk['source_url'] == market.SOURCE
    assert disk['queries'][json.dumps(filters, sort_keys=True)]['raw_records'] == [record]
    assert 'test-secret' not in market.CACHE_PATH.read_text()
    params = market.query_parameters('redacted', filters)
    assert params['limit'] == 10
    assert params['filters[district]'] == 'District'


def test_concurrent_page_loads_start_one_refresh(monkeypatch, tmp_path):
    reset(monkeypatch, tmp_path)
    entered, release = threading.Event(), threading.Event()
    calls = []
    def fetch(*args):
        calls.append(1)
        entered.set()
        release.wait(5)
        return {'records': []}
    monkeypatch.setattr(market, 'request_sample', fetch)
    threads = [threading.Thread(target=market.refresh_market_data) for _ in range(12)]
    try:
        for thread in threads: thread.start()
        assert entered.wait(2)
        assert len(calls) == 1
        assert market.load_official_market_data()['refresh_in_progress']
    finally:
        release.set()
        for thread in threads: thread.join(5)


def test_cooldown_and_freshness_states(monkeypatch, tmp_path):
    from datetime import datetime, timezone, timedelta
    reset(monkeypatch, tmp_path)
    monkeypatch.setattr(market, '_next_attempt', time.time() + 300)
    def forbidden(**kwargs):
        raise AssertionError('Refresh started during cooldown')
    monkeypatch.setattr(market.threading, 'Thread', forbidden)
    for age, expected in [(5, 'fresh'), (120, 'cached'), (2000, 'stale')]:
        stamp = (datetime.now(timezone.utc) - timedelta(seconds=age)).isoformat()
        market._cache['{}'] = {'updated_at': stamp, 'source_url': market.SOURCE, 'commodities': {}, 'markets': []}
        result = market.load_official_market_data()
        assert result['refresh_status'] == expected
        assert result['updated_at'] == stamp
        assert result['retry_after_seconds'] > 0
    market._cache.clear()
    assert market.load_official_market_data()['refresh_status'] == 'unavailable'


def test_missing_key_reports_configuration_without_request(monkeypatch, tmp_path):
    reset(monkeypatch, tmp_path)
    monkeypatch.delenv('DATA_GOV_IN_API_KEY')
    def forbidden(*args, **kwargs):
        raise AssertionError('Request made without a configured key')
    monkeypatch.setattr(market, 'request_sample', forbidden)

    result = market.refresh_market_data({'commodity': 'Rice'})
    page_data = market.load_official_market_data({'commodity': 'Rice'})
    assert result['status'] == 'missing_key'
    assert 'DATA_GOV_IN_API_KEY' in result['message']
    assert 'local .env' in page_data['message']


def test_diagnostic_reports_usable_records_without_saving_payload():
    record = {
        'commodity': 'Rice', 'market': 'Test', 'district': 'District', 'state': 'State',
        'arrival_date': date.today().strftime('%d/%m/%Y'),
        'min_price': '100', 'modal_price': '150', 'max_price': '200',
    }
    diagnostic = build_diagnostic(
        'private-test-key',
        connectivity_probe=lambda host: [{'stage': 'TLS handshake', 'status': 'success'}],
        api_request=lambda key: {'records': [record]},
    )
    assert diagnostic['key_configured'] is True
    assert {'stage': 'JSON response', 'status': 'valid', 'record_count': 1} in diagnostic['stages']
    assert {'stage': 'usable price records', 'status': 'success', 'record_count': 1} in diagnostic['stages']
    assert 'private-test-key' not in json.dumps(diagnostic)
    assert record not in diagnostic['stages']


def test_diagnostic_marks_auth_and_response_unverified_on_timeout():
    def timeout(key):
        raise requests.ReadTimeout('request URL contains private-test-key')
    diagnostic = build_diagnostic(
        'private-test-key',
        connectivity_probe=lambda host: [],
        api_request=timeout,
    )
    assert {'stage': 'HTTP response', 'status': 'failed', 'exception_type': 'ReadTimeout'} in diagnostic['stages']
    assert {'stage': 'authentication', 'status': 'not verified'} in diagnostic['stages']
    assert {'stage': 'JSON response', 'status': 'not verified'} in diagnostic['stages']
    assert 'private-test-key' not in json.dumps(diagnostic)


def test_diagnostic_with_missing_key_does_not_call_api():
    def forbidden(key):
        raise AssertionError('Request made without a configured key')
    diagnostic = build_diagnostic(None, connectivity_probe=lambda host: [], api_request=forbidden)
    assert diagnostic['key_configured'] is False
    assert {'stage': 'authentication', 'status': 'not tested: key missing'} in diagnostic['stages']


def test_request_sample_uses_redacted_query_key_and_validates_payload(monkeypatch, caplog):
    calls = []
    class Response:
        status_code = 200
        headers = {'Content-Type': 'application/json'}
        def raise_for_status(self):
            return None
        def json(self):
            return {'records': []}
    def get(url, **kwargs):
        calls.append((url, kwargs))
        return Response()
    monkeypatch.setattr(market.requests, 'get', get)

    assert market.request_sample('private-test-key') == {'records': []}
    url, kwargs = calls[0]
    assert url == market.ENDPOINT
    assert kwargs['params']['api-key'] == 'private-test-key'
    assert kwargs['verify'] is True and kwargs['allow_redirects'] is False
    assert 'private-test-key' not in caplog.text


def test_request_sample_reports_auth_rejection_without_leaking_key(monkeypatch, caplog):
    class Response:
        status_code = 403
        headers = {'Content-Type': 'application/json'}
        def raise_for_status(self):
            raise requests.HTTPError('Forbidden', response=self)
    monkeypatch.setattr(market.requests, 'get', lambda *args, **kwargs: Response())

    with pytest.raises(requests.HTTPError):
        market.request_sample('private-test-key')
    assert 'status=403' in caplog.text
    assert 'private-test-key' not in caplog.text
