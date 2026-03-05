"""Primary WSGI entrypoint for production servers."""

from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler

from app import app


def _configure_file_logging():
    project_root = Path(__file__).resolve().parent
    log_dir = project_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "app.log"

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    has_file_handler = any(
        isinstance(h, RotatingFileHandler)
        and getattr(h, "baseFilename", "") == str(log_file)
        for h in app.logger.handlers
    )

    if not has_file_handler:
        file_handler = RotatingFileHandler(
            log_file, maxBytes=2 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)

        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)

        werkzeug_logger = logging.getLogger("werkzeug")
        if not any(
            isinstance(h, RotatingFileHandler)
            and getattr(h, "baseFilename", "") == str(log_file)
            for h in werkzeug_logger.handlers
        ):
            werkzeug_logger.addHandler(file_handler)
        werkzeug_logger.setLevel(logging.INFO)

    app.logger.info("WSGI application initialized.")


_configure_file_logging()

application = app
