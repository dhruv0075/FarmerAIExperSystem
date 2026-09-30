import json
import time
import threading
from datetime import date

import requests

from services import official_market_service as market


def reset(monkeypatch, tmp_path):
    monkeypatch.setattr(market, '_cache', {})
    monkeypatch.setattr(market, '_next_attempt', 0)
    monkeypatch.setattr(market, '_refresh_after', {})
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
    market.refresh_market_data({'commodity': 'Rice'})
    assert len(calls) == 3
    assert delays == [0.5, 1.0]
    assert market._cache['{}'] == saved
    assert market._next_attempt > time.time()
    assert 'stage=TCP connection exception=ConnectTimeout' in caplog.text
    assert 'test-secret-never-log' not in caplog.text


def test_background_refresh_does_not_block_caller(monkeypatch, tmp_path):
    reset(monkeypatch, tmp_path)
    started = []
    class Thread:
        def __init__(self, **kwargs): self.kwargs = kwargs
        def start(self): started.append(self.kwargs)
    monkeypatch.setattr(market.threading, 'Thread', Thread)
    result = market.load_official_market_data({'commodity': 'Rice'})
    assert result['message'] == 'Market data temporarily unavailable'
    assert started[0]['daemon']
    assert not result['commodities']


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
    def refresh(filters):
        calls.append(filters)
        entered.set()
        release.wait(5)
    monkeypatch.setattr(market, 'refresh_market_data', refresh)
    threads = [threading.Thread(target=market.load_official_market_data, args=({'commodity': 'Rice'},)) for _ in range(12)]
    try:
        for thread in threads: thread.start()
        for thread in threads: thread.join(2)
        assert entered.wait(2)
        assert len(calls) == 1
        assert market.load_official_market_data()['refresh_in_progress']
    finally:
        release.set()


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
