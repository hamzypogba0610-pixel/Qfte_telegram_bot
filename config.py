"""
QFTE V13 — Configuration centrale
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Charger .env s'il existe
load_dotenv()

# Racine du projet
BASE_DIR = Path(__file__).resolve().parent

# Environnement
APP_ENV = os.getenv("APP_ENV", "development")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_ADMIN_IDS = [
    int(x.strip())
    for x in os.getenv("TELEGRAM_ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
]

# Base de données
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite+aiosqlite:///{BASE_DIR / 'data' / 'qfte.db'}"
)

# Trading
SYMBOLS = [
    s.strip()
    for s in os.getenv("SYMBOLS", "BTCUSDT,ETHUSDT,BNBUSDT").split(",")
    if s.strip()
]

TIMEFRAMES = [
    t.strip()
    for t in os.getenv("TIMEFRAMES", "1m,5m,15m,1h,4h").split(",")
    if t.strip()
]
