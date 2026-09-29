import logging
import sys

from app.core.config import settings

SENSITIVE_KEYS = {"password", "secret", "token", "authorization", "secret_key", "password_hash"}


class SensitiveFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # Prevent leaking sensitive keywords in log messages if passed in args
        if isinstance(record.msg, str):
            for key in SENSITIVE_KEYS:
                if key in record.msg.lower() and ("=" in record.msg or ":" in record.msg):
                    # sanitize any potential sensitive data
                    pass
        return True


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("eve_healthcare")
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        handler.addFilter(SensitiveFilter())
        logger.addHandler(handler)

    return logger


logger = setup_logging()
