from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data-xlsx"
DB_PATH = BASE_DIR / "myinvest.db"
DB_URL = f"sqlite:///{DB_PATH}"

DEFAULT_EXCEL_FILE = DATA_DIR / "data.xlsx"

MOEX_ISS_BASE_URL = "https://iss.moex.com/iss"

# Logs
LOGS_DIR = BASE_DIR / "logs"
QUOTES_LOG_FILE = LOGS_DIR / "quotes.log"
IMPORT_LOG_FILE = LOGS_DIR / "import.log"
EXPORT_LOG_FILE = LOGS_DIR / "export.log"
APP_LOG_FILE = LOGS_DIR / "app.log"

SHEET_NAMES = {
    "accounts": "Счета",
    "assets": "Активы",
    "bonds": "Облигации",
    "transactions": "Транзакции",
    "valuations": "Стоимость активов",
}
