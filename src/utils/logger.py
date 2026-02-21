"""
src/utils/logger.py
Structured logger with console (Rich) + rotating file output.
"""
import logging
import os
from logging.handlers import RotatingFileHandler

from rich.logging import RichHandler

_loggers: dict[str, logging.Logger] = {}


def get_logger(name: str = "vietlott") -> logging.Logger:
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, level, logging.INFO))

    if not logger.handlers:
        # Console handler (Rich)
        console = RichHandler(rich_tracebacks=True, show_path=False)
        console.setLevel(logging.DEBUG)
        logger.addHandler(console)

        # Rotating file handler
        os.makedirs("logs", exist_ok=True)
        file_handler = RotatingFileHandler(
            f"logs/{name}.log",
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
        )
        logger.addHandler(file_handler)

    _loggers[name] = logger
    return logger
