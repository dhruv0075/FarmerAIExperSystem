"""Cache-only page reads and explicit, bounded official market refreshes."""
import json
import logging
import math
import os
import time
import threading
from datetime import datetime, timedelta, timezone
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
_last_refresh_errors = {}
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


def refresh_error_message(exc):
    if isinstance(exc, requests.exceptions.HTTPError) and exc.response is not None:
        status = exc.response.status_code
        if status in (401, 403):
            return f'data.gov.in rejected the configured API key (HTTP {status}). Check its validity and permissions in your data.gov.in account.'
        if status == 429:
            return 'data.gov.in rate-limited the request. Wait before refreshing again.'
    if isinstance(exc, requests.exceptions.ReadTimeout):
        return 'data.gov.in did not return an HTTP response before the timeout; key acceptance and market records could not be verified.'
    if isinstance(exc, requests.exceptions.ConnectTimeout):
        return 'Could not connect to data.gov.in before the connection timeout.'
    if isinstance(exc, requests.exceptions.SSLError):
        return 'The TLS connection to data.gov.in could not be verified.'
    if isinstance(exc, requests.exceptions.ConnectionError):
        return 'Could not connect to data.gov.in. Check network access and try again later.'
    if isinstance(exc, (ValueError, AttributeError, KeyError, TypeError)):
        return 'data.gov.in returned a response that did not match the expected market-record format.'
    if isinstance(exc, OSError):
        return 'The official market response could not be saved to the configured data directory.'
    return 'The official market refresh failed. Check the server logs for the failure stage.'


def refresh_market_data(filters=None):
    global _inflight, _next_attempt, _cache
    load_official_market_data(filters)
    key = os.environ.get('DATA_GOV_IN_API_KEY')
    query_key = json.dumps(filters or {}, sort_keys=True)
    if not key:
        return {'status': 'missing_key', 'message': 'Market refresh was not attempted: DATA_GOV_IN_API_KEY is not configured. Set it in your local .env file or hosting environment.'}
    with _lock:
        if _inflight:
            return {'status': 'in_progress', 'message': 'A market refresh is already in progress.'}
        if time.time() < max(_next_attempt, _refresh_after.get(query_key, 0)):
            return {'status': 'cooldown', 'message': 'A market refresh is in its retry cooldown. Please try again later.'}
        _inflight = True
    try:
        last_error = None
        for attempt in range(MAX_ATTEMPTS):
            try:
                # Validate credentials/connectivity with a small real sample first.
                if not _cache and filters:
                    request_sample(key)
                payload = request_sample(key, filters)
                previous_records = _cache.get(query_key, {}).get('raw_records', [])
                combined_records = {}
                for record in [*previous_records, *payload['records']]:
                    identity = (
                        str(record.get('commodity', '')).strip().casefold(),
                        str(record.get('market', '')).strip().casefold(),
                        str(record.get('district', '')).strip().casefold(),
                        str(record.get('state', '')).strip().casefold(),
                        str(record.get('variety', 'Unspecified')).strip().casefold(),
                        str(record.get('arrival_date', '')).strip(),
                    )
                    combined_records[identity] = record
                raw_records = list(combined_records.values())
                parsed = parse_records(raw_records)
                parsed['raw_records'] = raw_records
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
                    _last_refresh_errors.pop(query_key, None)
                usable_records = parsed['usable_record_count']
                return {
                    'status': 'success' if usable_records else 'empty',
                    'message': f'Market refresh completed with {usable_records} usable official price record(s).' if usable_records else 'The provider responded, but no usable market price records were returned.',
                }
            except (requests.RequestException, ValueError, KeyError, TypeError, OSError) as exc:
                last_error = exc
                logger.warning('Market stage=%s exception=%s attempt=%s/%s', failure_stage(exc), type(exc).__name__, attempt + 1, MAX_ATTEMPTS)
                if isinstance(exc, requests.exceptions.HTTPError) and exc.response is not None and 400 <= exc.response.status_code < 500 and exc.response.status_code != 429:
                    break
                if attempt + 1 < MAX_ATTEMPTS:
                    time.sleep(min(0.5 * (2 ** attempt), 2))
        error_message = refresh_error_message(last_error)
        with _lock:
            _next_attempt = time.time() + 300
            _last_refresh_errors[query_key] = error_message
        return {'status': 'failed', 'message': error_message}
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
    message = _last_refresh_errors.get(query_key)
    if not message and not os.environ.get('DATA_GOV_IN_API_KEY'):
        message = 'Official market data is not configured. Set DATA_GOV_IN_API_KEY in your local .env file or hosting environment.'
    if not message:
        message = 'No official market records are cached for these filters yet. Refresh to request a small sample from data.gov.in.'
    return {'markets': [], 'commodities': {}, 'source': 'data.gov.in / DMI', 'source_url': SOURCE,
            'message': message, 'updated_at': None,
            'refresh_status': 'unavailable', 'refresh_in_progress': _inflight,
            'retry_after_seconds': max(0, round(_next_attempt - time.time()))}


def parse_records(records):
    data = {'markets': [], 'commodities': {}, 'source': 'data.gov.in / DMI',
            'source_url': SOURCE, 'updated_at': datetime.now(timezone.utc).isoformat(),
            'usable_record_count': 0}
    markets = {}
    history = {}
    for record in records:
        try:
            commodity = str(record['commodity']).strip().lower()
            market = str(record['market']).strip()
            state, district = str(record['state']).strip(), str(record['district']).strip()
            variety = str(record.get('variety') or 'Unspecified').strip()
            identity = f'{market}, {district}, {state}'
            observed = datetime.strptime(record['arrival_date'], '%d/%m/%Y').date()
            prices = [float(record[k]) for k in ('min_price', 'modal_price', 'max_price')]
            if not commodity or not market or not state or not district or not all(math.isfinite(p) and p >= 0 for p in prices):
                continue
            if not prices[0] <= prices[1] <= prices[2] or observed > datetime.now(timezone.utc).date():
                continue
        except (ValueError, KeyError, TypeError):
            continue
        data['usable_record_count'] += 1
        markets[identity] = {'name': identity, 'district': district, 'state': state}
        # Keep varieties separate: never merge historical observations across markets.
        item = data['commodities'].setdefault(commodity, {'unit': 'INR / quintal', 'prices': {}, 'history_30d': []})
        price_key = f"{identity} ({variety})"
        markets[price_key] = dict(markets[identity], name=price_key)
        if observed >= datetime.now(timezone.utc).date() - timedelta(days=30):
            history.setdefault(commodity, {})[(price_key, observed.isoformat())] = {
                'date': observed.isoformat(),
                'modal': prices[1],
                'market_name': price_key,
                'variety': variety,
            }
        previous = item['prices'].get(price_key)
        if not previous or previous['date'] <= observed.isoformat():
            item['prices'][price_key] = {'min': prices[0], 'modal': prices[1], 'max': prices[2], 'date': observed.isoformat(), 'trend': 'Not available'}
    for commodity, entries in history.items():
        data['commodities'][commodity]['history_30d'] = sorted(
            entries.values(), key=lambda observation: (observation['market_name'], observation['date'])
        )
    data['markets'] = list(markets.values())
    return data
