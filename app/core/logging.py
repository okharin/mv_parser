from loguru import logger
import sys
from pathlib import Path
from app.core.config import settings

def setup_logging():
    """Настройка логирования с использованием loguru"""
    # Удаляем стандартный обработчик
    logger.remove()
    
    # Добавляем обработчик для вывода в консоль
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | [Thread-{thread}] | <level>{message}</level>",
        level=settings.LOG_LEVEL,
        colorize=True
    )
    
    # Добавляем обработчик для записи в файл с ротацией
    logger.add(
        settings.LOG_FILE,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | [Thread-{thread}] | {message}",
        level=settings.LOG_LEVEL,
        rotation=settings.LOG_ROTATION,
        retention=settings.LOG_BACKUP_COUNT,
        compression="zip",
        encoding="utf-8"
    )
    
    return logger 