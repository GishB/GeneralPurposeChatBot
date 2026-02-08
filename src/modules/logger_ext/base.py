import logging
import os
import sys
from dataclasses import dataclass
from typing import Optional


DEFAULT_FMT = (
    "%(asctime)s | %(levelname)s | %(name)s | pid=%(process)d | "
    "%(filename)s:%(lineno)d | %(message)s"
)
DEFAULT_DATEFMT = "%Y-%m-%d %H:%M:%S"


@dataclass(frozen=True)
class LoggerConfig:
    name: str = "unionchatbot"
    level: int = logging.INFO
    fmt: str = DEFAULT_FMT
    datefmt: str = DEFAULT_DATEFMT


class _SingletonLoggerFactory:
    _logger: Optional[logging.Logger] = None
    _configured_key: Optional[tuple] = None

    @classmethod
    def get(cls, cfg: LoggerConfig) -> logging.Logger:
        key = (cfg.name, cfg.level, cfg.fmt, cfg.datefmt)

        if cls._logger is not None and cls._configured_key == key:
            return cls._logger

        logger = logging.getLogger(cfg.name)
        logger.setLevel(cfg.level)
        logger.propagate = False

        if not _has_our_handler(logger):
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(cfg.level)
            handler.setFormatter(logging.Formatter(cfg.fmt, datefmt=cfg.datefmt))
            logger.addHandler(handler)
        else:
            # Обновим уровни/формат, если конфиг поменяли
            for h in logger.handlers:
                if getattr(h, "_unionchatbot_handler", False):
                    h.setLevel(cfg.level)
                    h.setFormatter(logging.Formatter(cfg.fmt, datefmt=cfg.datefmt))

        cls._logger = logger
        cls._configured_key = key
        return logger


def _has_our_handler(logger: logging.Logger) -> bool:
    for h in logger.handlers:
        if getattr(h, "_unionchatbot_handler", False):
            return True
    return False


def _mark_handler(handler: logging.Handler) -> None:
    setattr(handler, "_unionchatbot_handler", True)


def get_logger(
    name: str = "unionchatbot",
    level: Optional[int] = None,
) -> logging.Logger:
    """
    Singleton logger getter.

    - level: если None, берём из env UNIONCHATBOT_LOG_LEVEL или INFO.
    """
    if level is None:
        env_level = os.getenv("UNIONCHATBOT_LOG_LEVEL", "INFO").upper()
        level = logging.getLevelName(env_level)
        if not isinstance(level, int):
            level = logging.INFO

    cfg = LoggerConfig(name=name, level=level)
    logger = _SingletonLoggerFactory.get(cfg)

    for h in logger.handlers:
        if isinstance(h, logging.StreamHandler) and not getattr(h, "_unionchatbot_handler", False):
            _mark_handler(h)

    return logger
