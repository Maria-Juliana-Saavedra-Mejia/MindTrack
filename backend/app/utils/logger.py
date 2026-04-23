# app/utils/logger.py
"""Centralized logging with console and rotating file output."""

import logging
import os
import threading
from logging.handlers import RotatingFileHandler

_logger_init_lock = threading.Lock()
_shared_file_handler: RotatingFileHandler | None = None
_shared_console_handler: logging.StreamHandler | None = None


def _dedupe_rotating_file_handlers(logger: logging.Logger) -> None:
    """Drop extra RotatingFileHandlers pointing at the same path (same emit → duplicate lines)."""
    seen: set[str] = set()
    for h in list(logger.handlers):
        if isinstance(h, RotatingFileHandler):
            raw = getattr(h, "baseFilename", "") or ""
            try:
                p = os.path.normcase(os.path.realpath(raw))
            except OSError:
                p = raw
            if p in seen:
                logger.removeHandler(h)
            else:
                seen.add(p)


def _ensure_shared_handlers():
    """One RotatingFileHandler + StreamHandler for the whole process (no duplicates per emit)."""
    global _shared_file_handler, _shared_console_handler
    if _shared_file_handler is not None:
        return
    log_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "mindtrack.log")
    fmt = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    _shared_file_handler = RotatingFileHandler(
        log_path, maxBytes=5 * 1024 * 1024, backupCount=3
    )
    _shared_file_handler.setFormatter(fmt)
    _shared_console_handler = logging.StreamHandler()
    _shared_console_handler.setFormatter(fmt)


def get_logger(name):
    """
    Return a module-level logger writing to console and logs/mindtrack.log.

    Format: [TIMESTAMP] [LEVEL] [MODULE] message
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        _dedupe_rotating_file_handlers(logger)
        logger.propagate = False
        return logger
    with _logger_init_lock:
        if logger.handlers:
            _dedupe_rotating_file_handlers(logger)
            logger.propagate = False
            return logger
        _ensure_shared_handlers()
        logger.setLevel(logging.INFO)
        if not any(h is _shared_file_handler for h in logger.handlers):
            logger.addHandler(_shared_file_handler)
        if not any(h is _shared_console_handler for h in logger.handlers):
            logger.addHandler(_shared_console_handler)
        _dedupe_rotating_file_handlers(logger)
        logger.propagate = False
    return logger
