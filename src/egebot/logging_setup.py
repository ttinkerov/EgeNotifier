from __future__ import annotations

import logging
import sys

from loguru import logger


class _InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        logger.opt(depth=6, exception=record.exc_info).log(level, record.getMessage())


def setup_logging(level: str = "INFO") -> None:
    logger.remove()
    logger.add(
        sys.stderr,
        level=level.upper(),
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> "
            "<level>{level:<7}</level> "
            "<cyan>[{name}]</cyan> {message}"
        ),
        colorize=True,
    )
    logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)
    for name in ("aiogram", "aiohttp", "asyncpg"):
        logging.getLogger(name).setLevel(logging.INFO)
