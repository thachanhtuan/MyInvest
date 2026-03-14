"""Quick test to verify logging is working"""
from app.services.quotes_service import logger as quotes_logger
from app.config import QUOTES_LOG_FILE

quotes_logger.info("=" * 80)
quotes_logger.info("TEST: Quotes logging verification")
quotes_logger.info(f"Log file: {QUOTES_LOG_FILE}")
quotes_logger.info(f"Log file exists: {QUOTES_LOG_FILE.exists()}")
quotes_logger.info("=" * 80)

