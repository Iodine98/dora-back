from logging.config import dictConfig
from typing import Any
import os


def set_logging_config(
    directory: str, max_bytes: int = 1_000_000, backup_count: int = 5
):
    if directory == "":
        raise ValueError("Directory cannot be empty.")

    os.makedirs(directory, exist_ok=True)
    log_files = ["app.log", "error.log", "debug.log"]

    handlers: dict[str, Any] = {
        "console": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "default",
        }
    }

    for log_file in log_files:
        handlers[log_file] = {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(directory, log_file),
            "maxBytes": max_bytes,
            "backupCount": backup_count,
            "formatter": "default",
        }

    dictConfig(
        {
            "version": 1,
            "formatters": {
                "default": {
                    "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
                }
            },
            "handlers": handlers,
            "root": {"level": "INFO", "handlers": list(handlers.keys())},
        }
    )
