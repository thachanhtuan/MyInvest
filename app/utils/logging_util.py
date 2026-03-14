from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_file_handler(
    logger: logging.Logger,
    log_file: Path,
    log_level: int = logging.INFO,
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 3,
) -> None:
    """Configure file handler with rotation for a logger.

    Idempotent: skips setup if a RotatingFileHandler for this file already exists.
    """
    # Idempotent: don't re-add if handler for this file is already present
    log_file_str = str(log_file.resolve())
    for handler in logger.handlers:
        if isinstance(handler, RotatingFileHandler) and handler.baseFilename == log_file_str:
            return

    logger.setLevel(log_level)
    logger.propagate = False

    # Ensure logs directory exists
    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"ERROR: Could not create logs directory: {e}", flush=True)
        return

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler with rotation
    try:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
            delay=False,
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"ERROR: Could not setup file handler for {log_file}: {e}", flush=True)
        return

    # Console handler
    try:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    except Exception as e:
        print(f"ERROR: Could not setup console handler: {e}", flush=True)


def flush_all_handlers(logger: logging.Logger) -> None:
    """Flush all handlers to ensure logs are written immediately."""
    for handler in logger.handlers:
        handler.flush()
