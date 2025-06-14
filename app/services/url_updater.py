import json
import threading
import time
from datetime import datetime
import asyncio
from pathlib import Path
import os

from app.core.config import settings
from app.core.logging import logger
from app.schemas.parser import URLUpdaterStatus
from app.utils.parser import Parser

class URLUpdater:
    def __init__(self):
        self.is_running = False
        self.start_time = None
        self.parser = Parser()
        self.status = URLUpdaterStatus(
            status='stopped',
            last_run=None,
            next_run=None,
            total_urls=0,
            errors=0,
            start_time=None,
            end_time=None,
            heartbeat=None
        )
        self._status_lock = threading.Lock()
        self._update_status()

    def _update_status(self, **kwargs):
        """Обновление статуса сервиса"""
        with self._status_lock:
            self.status = self.status.model_copy(update=kwargs)
            self.status.heartbeat = datetime.now()
            try:
                with open(settings.URL_UPDATE_STATUS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(self.status.model_dump(), f, ensure_ascii=False, indent=2, default=str)
            except Exception as e:
                logger.error(f"Ошибка при обновлении статуса: {str(e)}")

    def get_status(self) -> URLUpdaterStatus:
        """Получить текущий статус URL updater"""
        with self._status_lock:
            return self.status

    async def update_urls(self):
        """Запуск процесса обновления URL"""
        if self.is_running:
            logger.warning("URL updater уже запущен")
            return

        self.is_running = True
        self.start_time = time.time()
        self._update_status(
            status='running',
            start_time=datetime.now(),
            errors=0
        )

        try:
            # Запускаем обновление URL в отдельном потоке
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._run_update)
        except Exception as e:
            logger.error(f"Ошибка при запуске обновления URL: {str(e)}")
            self._update_status(
                status='error',
                end_time=datetime.now(),
                errors=self.status.errors + 1
            )
        finally:
            self.cleanup()

    def _run_update(self):
        """Выполнение обновления URL в отдельном потоке"""
        try:
            # Получаем URL из sitemap
            urls_with_dates = self.parser.get_urls_from_sitemap(settings.SITEMAP_URL)
            if not urls_with_dates:
                logger.error("Не удалось получить URL из sitemap")
                self._update_status(
                    status='failed',
                    end_time=datetime.now()
                )
                return

            # Фильтруем только URL товаров
            product_urls = [
                url_info for url_info in urls_with_dates 
                if self.parser.is_product_url(url_info['url'])
            ]

            if not product_urls:
                logger.error("Не найдено URL товаров")
                self._update_status(
                    status='failed',
                    end_time=datetime.now()
                )
                return

            self._update_status(
                total_urls=len(product_urls)
            )

            # Сохраняем обновленный список URL
            try:
                urls_dict = {url_info['url']: {
                    'last_modified': url_info['last_modified']
                } for url_info in product_urls}
                
                # Создаем временный файл для атомарной записи
                temp_file = f"{settings.PRODUCT_LINKS_FILE}.tmp"
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(urls_dict, f, ensure_ascii=False, indent=2)
                
                # Атомарно заменяем старый файл новым
                os.replace(temp_file, settings.PRODUCT_LINKS_FILE)
                
                self._update_status(
                    status='completed',
                    end_time=datetime.now()
                )
                logger.info(f"Список URL обновлен. Всего URL: {len(product_urls)}")
                
            except Exception as e:
                logger.error(f"Ошибка при сохранении списка URL: {str(e)}")
                self._update_status(
                    status='error',
                    end_time=datetime.now(),
                    errors=self.status.errors + 1
                )

        except Exception as e:
            logger.error(f"Ошибка при выполнении обновления URL: {str(e)}")
            self._update_status(
                status='error',
                end_time=datetime.now(),
                errors=self.status.errors + 1
            )

    def cleanup(self):
        """Очистка ресурсов"""
        logger.info("Очистка ресурсов URL updater")
        self.is_running = False
        if not self.status.end_time:
            self._update_status(
                status='stopped',
                end_time=datetime.now()
            )

    def stop(self):
        """Остановка сервиса"""
        if not self.is_running:
            return

        logger.info("Остановка URL updater...")
        self.is_running = False
        self.cleanup()
        logger.info("URL updater остановлен") 