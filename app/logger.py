import logging
import os


LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def setup_logging() -> None:
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    root_logger = logging.getLogger()

    if root_logger.handlers:
        root_logger.setLevel(log_level)
        return

    logging.basicConfig(level=log_level, format=LOG_FORMAT)


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)
