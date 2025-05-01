# logger_config.py
import logging
from logging.handlers import RotatingFileHandler
import os

def get_logger(name=__name__, log_to_file=True):
    logger = logging.getLogger(name)
    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.INFO)

    # === Console handler ===
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter("[%(asctime)s] %(levelname)s - %(name)s - %(message)s", "%H:%M:%S")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # === File handler (optional) ===
    # === Rotating File Handler ===
    if log_to_file:
        os.makedirs("logs", exist_ok=True)
        file_handler = RotatingFileHandler(
            filename="logs/app.log",
            maxBytes=1024 * 100,      # 🔁 Rotate at 100KB
            backupCount=5,            # 🔁 Keep 5 old logs
            encoding="utf-8"
        )
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s", "%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

         # === Error File Handler (Only ERROR+) ===
        error_handler = RotatingFileHandler(
            filename="logs/error.log",
            maxBytes=1024 * 50,      # 50 KB
            backupCount=3,
            encoding="utf-8"
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        logger.addHandler(error_handler)        

    return logger