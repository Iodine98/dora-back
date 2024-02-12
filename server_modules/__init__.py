from logging.config import dictConfig
import os

def set_logging_config(filename: str, max_bytes: int = 1_000_000, backup_count: int = 5):
    if filename == "":
        raise ValueError("Filename cannot be empty.")
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    dictConfig(
    {
        "version": 1,
        "formatters": {
            "default": {
                "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "formatter": "default",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": filename,
                "maxBytes": max_bytes,
                "backupCount": backup_count,
                "formatter": "default",
            },
        },
        "root": {"level": "INFO", "handlers": ["console", "file"]},
    }
)