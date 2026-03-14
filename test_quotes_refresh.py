"""Test quotes refresh and logging"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from app.services.quotes_service import fetch_all_quotes
from app.config import QUOTES_LOG_FILE

print(f"Testing quotes refresh...")
print(f"Log file: {QUOTES_LOG_FILE}")
print(f"Log exists before: {QUOTES_LOG_FILE.exists()}")

db = SessionLocal()
try:
    result = fetch_all_quotes(db)
    print(f"\nResult:")
    print(f"  Updated: {result.updated}")
    print(f"  Failed: {result.failed}")
    print(f"  Skipped: {result.skipped}")
    print(f"  Errors: {len(result.errors)}")
    print(f"  Log file: {result.log_file}")
finally:
    db.close()

print(f"\nLog exists after: {QUOTES_LOG_FILE.exists()}")
if QUOTES_LOG_FILE.exists():
    size = QUOTES_LOG_FILE.stat().st_size
    print(f"Log file size: {size} bytes")
    if size > 0:
        print(f"\nLast 30 lines of log:")
        with open(QUOTES_LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for line in lines[-30:]:
                print(line.rstrip())
    else:
        print("WARNING: Log file is empty!")
else:
    print("ERROR: Log file was not created!")
