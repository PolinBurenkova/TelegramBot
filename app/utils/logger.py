"""Logging setup: rotating bot/errors/api logs."""
from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path

from app.config import LoggingSettings


def _ensure_dir(path: str) -> Path:
    """Create directory if missing and return Path."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _file_handler(
    path: Path, level: int, rotation_mb: int, backup_count: int
) -> logging.Handler:
    """Build a rotating file handler."""
    handler = logging.handlers.RotatingFileHandler(
        filename=str(path),
        maxBytes=rotation_mb * 1024 * 1024,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setLevel(level)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-7s %(name)s — %(message)s")
    )
    return handler


def setup_logging(settings: LoggingSettings) -> None:
    """Configure root logger once with console + rotating file handlers."""
    log_dir = _ensure_dir(settings.dir)
    level = getattr(logging, settings.level.upper(), logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)

    # Idempotent: avoid duplicate file handlers on re-import
    if any(isinstance(h, logging.handlers.RotatingFileHandler) for h in root.handlers):
        return

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-7s %(name)s — %(message)s")
    )
    root.addHandler(console)

    root.addHandler(
        _file_handler(log_dir / "bot.log", level, settings.rotation_mb, settings.backup_count)
    )
    root.addHandler(
        _file_handler(
            log_dir / "errors.log",
            logging.ERROR,
            settings.rotation_mb,
            settings.backup_count,
        )
    )
    root.addHandler(
        _file_handler(
            log_dir / "api.log",
            logging.INFO,
            settings.rotation_mb,
            settings.backup_count,
        )
    )