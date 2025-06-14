from pydantic_settings import BaseSettings
from pathlib import Path
import os
from typing import List

class Settings(BaseSettings):
    # Базовые пути
    BASE_DIR: Path = Path(__file__).parent.parent.parent.absolute()
    DATA_DIR: Path = BASE_DIR / 'data'
    LOGS_DIR: Path = BASE_DIR / 'logs'

    # Настройки API
    HOST: str = "0.0.0.0"
    PORT: int = 7000
    DEBUG: bool = False
    
    # Настройки парсинга
    SITEMAP_URL: str = 'https://www.mvideo.ru/sitemap.xml'
    RESULTS_FILE: str = str(DATA_DIR / 'results.json')
    PRODUCT_LINKS_FILE: str = str(DATA_DIR / 'product_links.json')
    PARSING_STATUS_FILE: str = str(DATA_DIR / 'parsing_status.json')
    URL_UPDATE_STATUS_FILE: str = str(DATA_DIR / 'url_update_status.json')
    LOG_FILE: str = str(LOGS_DIR / 'crawler.log')

    # Настройки производительности
    MAX_WORKERS: int = 1
    DRIVER_POOL_SIZE: int = MAX_WORKERS
    BATCH_SIZE: int = 10  # Размер батча для обработки URL
    MIN_DELAY: float = 1.0
    MAX_DELAY: float = 3.0
    MAX_RETRIES: int = 3
    TIMEOUT: int = 30

    # Настройки планировщика
    URL_UPDATE_INTERVAL: int = 12 * 60 * 60  # 12 часов
    PARSING_INTERVAL: int = 24 * 60 * 60  # 24 часа
    MAX_RUNTIME: int = 23 * 60 * 60  # 23 часа
    URL_UPDATE_MAX_RUNTIME: int = 11 * 60 * 60  # 11 часов

    # Настройки логирования
    LOG_LEVEL: str = 'INFO'
    LOG_ROTATION: str = '1 day'
    LOG_BACKUP_COUNT: int = 7

    # User-Agents для ротации
    USER_AGENTS: List[str] = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
    ]

    # Настройки мониторинга
    HEARTBEAT_INTERVAL: int = 300  # 5 минут

    class Config:
        env_file = ".env"
        case_sensitive = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Создаем необходимые директории
        self.DATA_DIR.mkdir(exist_ok=True)
        self.LOGS_DIR.mkdir(exist_ok=True)

settings = Settings() 