import logging
import os
import sys


def setup_logging(level: str | None = None) -> None:
    """
    Инициализирует базовую конфигурацию логирования.
    Уровень берётся из LOG_LEVEL или переданного level (по умолчанию INFO).

    :param level: опционально — строковое имя уровня (DEBUG, INFO, WARNING, ERROR, CRITICAL).
                  Если не задано, читается os.getenv("LOG_LEVEL", "INFO").
    """
    level_name = (level or os.getenv("LOG_LEVEL") or "INFO").upper()
    level_num = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level_num,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
