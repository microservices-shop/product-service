import sys
from loguru import logger

# Флаг для отслеживания, было ли логирование настроено
_logging_configured = False

# Формат логирования
CONSOLE_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

FILE_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
)


def setup_logging(
    level: str = "INFO",
    log_file: str | None = None,
    rotation: str = "10 MB",
    retention: str = "7 days",
) -> None:
    """
    Настройка логирования для приложения.

    Args:
        level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Путь к файлу для записи логов (опционально)
        rotation: Условие ротации логов (размер или время)
        retention: Время хранения старых логов
    """
    global _logging_configured

    if _logging_configured:
        return

    logger.remove()

    logger.add(
        sys.stdout,
        format=CONSOLE_FORMAT,
        level=level.upper(),
        colorize=True,
    )

    if log_file:
        logger.add(
            log_file,
            format=FILE_FORMAT,
            level=level.upper(),
            rotation=rotation,
            retention=retention,
            compression="zip",
        )

    _logging_configured = True
    logger.debug("Logging configured successfully")


__all__ = ["logger", "setup_logging"]
