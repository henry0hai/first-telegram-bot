# src/utils/logging_utils.py
import os
import logging
from logging.handlers import RotatingFileHandler


def get_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        log_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs"
        )
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "telegram_bot.log")
        file_handler = RotatingFileHandler(
            log_file, maxBytes=5 * 1024 * 1024, backupCount=2
        )
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Colored formatter for console
        class ColoredFormatter(logging.Formatter):
            COLORS = {
                "INFO": "\033[32m",  # Green
                "WARNING": "\033[33m",  # Yellow
                "ERROR": "\033[31m",  # Red
                "CRITICAL": "\033[41m",  # Red background
                "RESET": "\033[0m",
            }

            def format(self, record):
                color = self.COLORS.get(record.levelname, "")
                reset = self.COLORS["RESET"] if color else ""
                msg = super().format(record)
                if color:
                    msg = f"{color}{msg}{reset}"
                return msg

        console_handler = logging.StreamHandler()
        color_formatter = ColoredFormatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s"
        )
        console_handler.setFormatter(color_formatter)
        logger.addHandler(console_handler)

    return logger
