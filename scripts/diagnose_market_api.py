"""Standalone staged connectivity diagnostic; no Flask import or credential logging."""
import json
import logging
import socket
import ssl
import sys
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
from services.official_market_service import ENDPOINT, RESOURCE, TIMEOUT, failure_stage, request_sample
import os


def main():
    load_dotenv(Path(__file__).resolve().parent.parent / '.env')
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    host = urlsplit(ENDPOINT).hostname
    results = {'endpoint': ENDPOINT, 'resource_id': RESOURCE, 'ssl_verification': True,
               'timeout_seconds': TIMEOUT, 'key_placement': 'api-key query parameter (redacted)',
               'query': {'format': 'json', 'limit': 10, 'offset': 0}, 'stages': []}
    stage = 'DNS resolution'
    try:
        addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        results['stages'].append({'stage': stage, 'status': 'success', 'address_count': len(addresses)})
        stage = 'TCP connection'
        with socket.create_connection((host, 443), timeout=5) as raw:
            results['stages'].append({'stage': stage, 'status': 'success'})
            stage = 'TLS handshake'
            with ssl.create_default_context().wrap_socket(raw, server_hostname=host) as tls:
                results['stages'].append({'stage': stage, 'status': 'success', 'version': tls.version()})
    except (OSError, ssl.SSLError) as exc:
        results['stages'].append({'stage': stage, 'status': 'failed', 'exception_type': type(exc).__name__, 'errno': getattr(exc, 'errno', None)})
    key = os.environ.get('DATA_GOV_IN_API_KEY')
    if key:
        try:
            sample = request_sample(key)
            results['stages'].append({'stage': 'HTTP/authentication/JSON', 'status': 'success', 'record_count': len(sample['records'])})
            Path('artifacts').mkdir(exist_ok=True)
            Path('artifacts/official_market_sample.json').write_text(json.dumps(sample['records'], indent=2), encoding='utf-8')
        except Exception as exc:
            results['stages'].append({'stage': failure_stage(exc), 'status': 'failed', 'exception_type': type(exc).__name__})
    else:
        results['stages'].append({'stage': 'authentication', 'status': 'not tested: key missing'})
    Path('artifacts').mkdir(exist_ok=True)
    Path('artifacts/market_diagnostic.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
