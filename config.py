import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = PROJECT_ROOT / "logs"

DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

class ScraperConfig:
    MAX_WORKERS = int(os.getenv("MAX_WORKERS", 5))
    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", 10))
    RETRY_ATTEMPTS = int(os.getenv("RETRY_ATTEMPTS", 3))
    DELAY_BETWEEN_REQUESTS = float(os.getenv("DELAY_BETWEEN_REQUESTS", 2))
    USER_AGENT_ROTATION = os.getenv("USER_AGENT_ROTATION", "true").lower() == "true"
    
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

class SalesConfig:
    MIN_MONTHLY_SALES = int(os.getenv("MIN_MONTHLY_SALES", 50000))
    MAX_MONTHLY_SALES = int(os.getenv("MAX_MONTHLY_SALES", 100000))
    AVG_REVIEW_RATE = 0.08
    REPEAT_PURCHASE_RATE = 0.75

class ChinaShippingConfig:
    DETECT_ENABLED = os.getenv("DETECT_CHINA_SHIPPING", "true").lower() == "true"
    CHINA_KEYWORDS_CN = ["中国", "北京", "上海", "深圳", "广州", "杭州"]

class OutputConfig:
    OUTPUT_FORMAT = os.getenv("OUTPUT_FORMAT", "json").lower()
    OUTPUT_PATH = Path(os.getenv("OUTPUT_PATH", str(DATA_DIR / "results")))

class LogConfig:
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_PATH = Path(os.getenv("LOG_PATH", str(LOG_DIR)))
    LOG_FILE = LOG_PATH / "scraper.log"