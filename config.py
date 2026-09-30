"""Environment configuration shared by the app and persistent services."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')
DATA_DIR = Path(os.environ.get('AGRIWISE_DATA_DIR', str(BASE_DIR)))
DATABASE_PATH = DATA_DIR / 'database.db'
UPLOAD_DIR = DATA_DIR / 'private_uploads'
MARKET_CACHE_PATH = (DATA_DIR / 'official_market_cache.json' if os.environ.get('AGRIWISE_DATA_DIR')
                     else BASE_DIR / 'data' / 'official_market_cache.json')
