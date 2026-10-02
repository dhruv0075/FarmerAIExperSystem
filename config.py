"""Read-only configuration; runtime directories are created only when needed."""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
SERVERLESS = bool(os.environ.get("VERCEL"))
DATA_DIR = Path(os.environ.get("AGRIWISE_DATA_DIR", "/tmp/agriwise" if SERVERLESS else str(BASE_DIR)))
DB_PATH = DATABASE_PATH = DATA_DIR / "database.db"
UPLOAD_DIR = DATA_DIR / "private_uploads"
CACHE_DIR = DATA_DIR / "cache"
GENERATED_DIR = DATA_DIR / "generated"
MARKET_CACHE_PATH = DATA_DIR / "official_market_cache.json"
SECRET_KEY = os.environ.get("AGRIWISE_SECRET_KEY") or os.urandom(32)
# Third-party plotting libraries must not create a config cache in the deployment.
os.environ.setdefault("MPLCONFIGDIR", str(CACHE_DIR / "matplotlib"))
