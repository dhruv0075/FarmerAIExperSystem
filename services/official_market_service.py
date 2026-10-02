"""Cache-only page reads and explicit, bounded official market refreshes."""
import json
import logging
import math
import os
import time
import threading
from datetime import datetime, timezone
from pathlib import Path
import requests
from config import MARKET_CACHE_PATH

SOURCE = 'https://www.data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi'
CACHE_PATH = MARKET_CACHE_PATH
RESOURCE = '9ef84268-d588-465a-a308-a864a43d0070'
ENDPOINT = f'https://api.data.gov.in/resource/{RESOURCE}'
TIMEOUT = (3.05, 5)
MAX_ATTEMPTS = 3
_cache = {}
_next_attempt = 0
_refresh_after = {}
_inflight = False
_loaded = False
_lock = threading.Lock()
logger = logging.getLogger(__name__)


def query_parameters(key, filters=None):
    params = {'api-key': key, 'format': 'json', 'limit': 10, 'offset': 0}
    for field, value in (filters or {}).items():
        if field in {'commodity', 'state', 'district', 'market'} and value:
            params[f'filters[{field}]'] = value.strip()
    return params


def request_sample(key, filters=None):
    """Minimal request; never log the URL because its query contains the key."""
    response = requests.get(ENDPOINT, params=query_parameters(key, filters),
                            timeout=TIMEOUT, verify=True, allow_redirects=False)
    headers = {k: response.headers.get(k) for k in ('Content-Type', 'Retry-After', 'Date') if response.headers.get(k)}
    logger.info('Market stage=HTTP response status=%s headers=%s', response.status_code, headers)
    if response.status_code in (401, 403):
        logger.warning('Market stage=authentication exception=HTTPError status=%s', response.status_code)
    response.raise_for_status()
    if response.status_code != 200:
        raise ValueError('Unexpected HTTP response; redirects are not followed with credentials')
    try:
        payload = response.json()
        if payload.get('error') or str(payload.get('status', '')).lower() == 'error':
            raise ValueError('Provider returned an API error envelope')
        if not isinstance(payload.get('records'), list):
            raise ValueError('Missing records array')
    except (ValueError, AttributeError) as exc:
        logger.warning('Market stage=JSON parsing exception=%s', type(exc).__name__)
        raise
    return payload


def failure_stage(exc):
    if isinstance(exc, requests.exceptions.SSLError): return 'TLS handshake'
    if isinstance(exc, requests.exceptions.ConnectTimeout): return 'TCP connection'
    if isinstance(exc, requests.exceptions.ReadTimeout): return 'HTTP response'
    if isinstance(exc, requests.exceptions.HTTPError):
        return 'authentication' if exc.response is not None and exc.response.status_code in (401, 403) else 'HTTP response'
    # Inspect nested names only; never expose exception strings containing URLs.
    if 'NameResolutionError' in repr(exc): return 'DNS resolution'
    if isinstance(exc, requests.exceptions.ConnectionError): return 'TCP connection'
    if isinstance(exc, (ValueError, AttributeError, KeyError)): return 'JSON parsing'
    return 'cache persistence'


def refresh_market_data(filters=None):
    global _inflight, _next_attempt, _cache
    load_official_market_data(filters)
    key = os.environ.get('DATA_GOV_IN_API_KEY')
    query_key = json.dumps(filters or {}, sort_keys=True)
    with _lock:
        if not key or _inflight or time.time() < max(_next_attempt, _refresh_after.get(query_key, 0)):
            return False
        _inflight = True
    try:
        for attempt in range(MAX_ATTEMPTS):
            try:
                # Validate credentials/connectivity with a small real sample first.
                if not _cache and filters:
                    request_sample(key)
                payload = request_sample(key, filters)
                parsed = parse_records(payload['records'])
                parsed['raw_records'] = payload['records']
                parsed['filters'] = filters or {}
                with _lock:
                    _cache[query_key] = parsed
                    snapshot = {'source_url': SOURCE, 'queries': _cache}
                    temporary = CACHE_PATH.with_suffix('.tmp')
                    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
                    temporary.write_text(json.dumps(snapshot), encoding='utf-8')
                    temporary.replace(CACHE_PATH)
                    _refresh_after[query_key] = time.time() + 1800
                    _next_attempt = time.time() + 5
                return
            except (requests.RequestException, ValueError, KeyError, TypeError, OSError) as exc:
                logger.warning('Market stage=%s exception=%s attempt=%s/%s', failure_stage(exc), type(exc).__name__, attempt + 1, MAX_ATTEMPTS)
                if isinstance(exc, requests.exceptions.HTTPError) and exc.response is not None and 400 <= exc.response.status_code < 500 and exc.response.status_code != 429:
                    break
                if attempt + 1 < MAX_ATTEMPTS:
                    time.sleep(min(0.5 * (2 ** attempt), 2))
        with _lock: _next_attempt = time.time() + 300
    finally:
        with _lock: _inflight = False


def load_official_market_data(filters=None):
    global _loaded, _cache, _inflight
    with _lock:
        if not _loaded:
            _loaded = True
            try:
                saved = json.loads(CACHE_PATH.read_text(encoding='utf-8'))
                if saved.get('source_url') == SOURCE:
                    _cache = saved.get('queries', {})
                    for cached_key, cached in _cache.items():
                        try:
                            _refresh_after[cached_key] = datetime.fromisoformat(cached['updated_at']).timestamp() + 1800
                        except (KeyError, TypeError, ValueError):
                            pass
            except (OSError, ValueError, TypeError):
                pass
        query_key = json.dumps(filters or {}, sort_keys=True)
        result = _cache.get(query_key)
        if result:
            result = dict(result)
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(result['updated_at'])).total_seconds()
            result['is_cached'] = True
            result['is_stale'] = age > 1800
            result['refresh_status'] = 'fresh' if age < 60 else 'cached' if age <= 1800 else 'stale'
            result['refresh_in_progress'] = _inflight
            result['retry_after_seconds'] = max(0, round(max(_next_attempt, _refresh_after.get(query_key, 0)) - time.time()))
            return result
    return {'markets': [], 'commodities': {}, 'source': 'data.gov.in / DMI', 'source_url': SOURCE,
            'message': 'Market data temporarily unavailable', 'updated_at': None,
            'refresh_status': 'unavailable', 'refresh_in_progress': _inflight,
            'retry_after_seconds': max(0, round(_next_attempt - time.time()))}


def parse_records(records):
    data = {'markets': [], 'commodities': {}, 'source': 'data.gov.in / DMI',
            'source_url': SOURCE, 'updated_at': datetime.now(timezone.utc).isoformat()}
    markets = {}
    for record in records:
        try:
            commodity = str(record['commodity']).strip().lower()
            market = str(record['market']).strip()
            state, district = record['state'], record['district']
            identity = f'{market}, {district}, {state}'
            observed = datetime.strptime(record['arrival_date'], '%d/%m/%Y').date()
            prices = [float(record[k]) for k in ('min_price', 'modal_price', 'max_price')]
            if not commodity or not market or not all(math.isfinite(p) and p >= 0 for p in prices):
                continue
            if not prices[0] <= prices[1] <= prices[2] or observed > datetime.now(timezone.utc).date():
                continue
        except (ValueError, KeyError, TypeError):
            continue
        markets[identity] = {'name': identity, 'district': district, 'state': state}
        # Keep varieties separate: never merge historical observations across markets.
        item = data['commodities'].setdefault(commodity, {'unit': 'INR / quintal', 'prices': {}, 'history_30d': []})
        price_key = f"{identity} ({record.get('variety', 'Unspecified')})"
        markets[price_key] = dict(markets[identity], name=price_key)
        previous = item['prices'].get(price_key)
        if not previous or previous['date'] < observed.isoformat():
            item['prices'][price_key] = {'min': prices[0], 'modal': prices[1], 'max': prices[2], 'date': observed.isoformat(), 'trend': 'Not available'}
    data['markets'] = list(markets.values())
    return data
