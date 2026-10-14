"""Standalone staged connectivity diagnostic; never save API keys or raw records."""
import json
import logging
import socket
import ssl
import sys
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
import os
import requests
from services.official_market_service import (
    ENDPOINT, RESOURCE, TIMEOUT, failure_stage, parse_records, request_sample,
)


def probe_connectivity(host):
    stages = []
    stage = 'DNS resolution'
    try:
        addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        stages.append({'stage': stage, 'status': 'success', 'address_count': len(addresses)})
        stage = 'TCP connection'
        with socket.create_connection((host, 443), timeout=5) as raw:
            stages.append({'stage': stage, 'status': 'success'})
            stage = 'TLS handshake'
            with ssl.create_default_context().wrap_socket(raw, server_hostname=host) as tls:
                stages.append({'stage': stage, 'status': 'success', 'version': tls.version()})
    except (OSError, ssl.SSLError) as exc:
        stages.append({
            'stage': stage, 'status': 'failed',
            'exception_type': type(exc).__name__, 'errno': getattr(exc, 'errno', None),
        })
    return stages


def build_diagnostic(key, connectivity_probe=None, api_request=None):
    host = urlsplit(ENDPOINT).hostname
    connectivity_probe = connectivity_probe or probe_connectivity
    api_request = api_request or request_sample
    results = {
        'endpoint': ENDPOINT,
        'resource_id': RESOURCE,
        'key_configured': bool(key),
        'ssl_verification': True,
        'timeout_seconds': TIMEOUT,
        'key_placement': 'api-key query parameter (redacted)',
        'query': {'format': 'json', 'limit': 10, 'offset': 0},
        'stages': connectivity_probe(host),
    }
    if not key:
        results['stages'].extend([
            {'stage': 'HTTP response', 'status': 'not tested: key missing'},
            {'stage': 'authentication', 'status': 'not tested: key missing'},
            {'stage': 'JSON response', 'status': 'not tested: key missing'},
            {'stage': 'usable price records', 'status': 'not tested: key missing'},
        ])
        return results

    try:
        payload = api_request(key)
    except (requests.RequestException, ValueError, AttributeError, KeyError, TypeError, OSError) as exc:
        status_code = getattr(getattr(exc, 'response', None), 'status_code', None)
        failed_stage = failure_stage(exc)
        results['stages'].append({
            'stage': failed_stage,
            'status': 'failed',
            'exception_type': type(exc).__name__,
            **({'http_status': status_code} if status_code is not None else {}),
        })
        if failed_stage == 'authentication':
            results['stages'].append({'stage': 'authentication', 'status': 'rejected'})
            results['stages'].append({'stage': 'JSON response', 'status': 'not tested: request rejected'})
            results['stages'].append({'stage': 'usable price records', 'status': 'not tested: request rejected'})
        else:
            results['stages'].append({'stage': 'authentication', 'status': 'not verified'})
            results['stages'].append({'stage': 'JSON response', 'status': 'not verified'})
            results['stages'].append({'stage': 'usable price records', 'status': 'not verified'})
        return results

    usable_record_count = parse_records(payload['records'])['usable_record_count']
    results['stages'].extend([
        {'stage': 'HTTP response', 'status': 'success', 'http_status': 200},
        {'stage': 'authentication', 'status': 'no rejection observed; whether the key is required is not established'},
        {'stage': 'JSON response', 'status': 'valid', 'record_count': len(payload['records'])},
        {'stage': 'usable price records', 'status': 'success' if usable_record_count else 'none found',
         'record_count': usable_record_count},
    ])
    return results


def main():
    load_dotenv(Path(__file__).resolve().parent.parent / '.env')
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    results = build_diagnostic(os.environ.get('DATA_GOV_IN_API_KEY'))
    Path('artifacts').mkdir(exist_ok=True)
    Path('artifacts/market_diagnostic.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
