"""Deny repository writes while importing and exercising the serverless app.

Run with AGRIWISE_DATA_DIR pointing to an isolated temporary directory.
This is a filesystem contract test, not a hosted Vercel deployment test.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
assert os.environ.get('AGRIWISE_DATA_DIR'), 'Set an isolated AGRIWISE_DATA_DIR first'


def audit(event, args):
    paths = []
    if event == 'open' and isinstance(args[0], (str, bytes)):
        mode, flags = args[1], args[2]
        if (mode and any(c in mode for c in 'wax+')) or (flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT)):
            paths.append(args[0])
    elif event in ('os.mkdir', 'os.remove', 'os.rmdir'):
        paths.append(args[0])
    elif event == 'os.rename':
        paths.extend(args[:2])
    elif event == 'sqlite3.connect' and args[0] != ':memory:':
        paths.append(args[0])
    for value in paths:
        path = Path(os.fsdecode(value)).resolve()
        if path.is_relative_to(ROOT):
            raise PermissionError(f'Repository write prohibited: {path}')


sys.addaudithook(audit)
import app
from config import DATA_DIR, DATABASE_PATH, UPLOAD_DIR, CACHE_DIR, MARKET_CACHE_PATH
from services.official_market_service import load_official_market_data

for path in (DATABASE_PATH, UPLOAD_DIR, CACHE_DIR, MARKET_CACHE_PATH):
    assert path.is_relative_to(DATA_DIR)
assert app.app.test_client().get('/healthz').status_code == 200
assert load_official_market_data()['refresh_status'] in ('fresh', 'cached', 'stale', 'unavailable')
print('APP IMPORT SUCCESS; repository write guard passed')
print(f'Database: {DATABASE_PATH}\nUploads: {UPLOAD_DIR}\nCache: {CACHE_DIR}\nMarket cache: {MARKET_CACHE_PATH}')
