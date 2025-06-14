import json
import threading
import time
from datetime import datetime
from typing import List, Dict, Optional
import asyncio
from pathlib import Path
import os

from app.core.config import settings
from app.core.logging import logger
from app.schemas.parser import ParserStatus, ProductInfo
from app.utils.parser import Parser

class ParserService:
    def __init__(self):
        self.is_running = False
        self.start_time = None
        self.parser = Parser()
        self.status = ParserStatus(
            status='stopped',
            last_run=None,
            next_run=None,
            total_products=0,
            processed_products=0,
            errors=0,
            start_time=None,
            end_time=None,
            heartbeat=None,
            current_category=None
        )
        self._status_lock = threading.Lock()
        self._update_status()

    def _update_status(self, **kwargs):
        """Обновление статуса сервиса"""
        with self._status_lock:
            self.status = self.status.model_copy(update=kwargs)
            self.status.heartbeat = datetime.now()
            try:
                with open(settings.PARSING_STATUS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(self.status.model_dump(), f, ensure_ascii=False, indent=2, default=str)
            except Exception as e:
                logger.error(f"Ошибка при обновлении статуса: {str(e)}")

    def get_status(self) -> ParserStatus:
        """Получить текущий статус парсера"""
        with self._status_lock:
            return self.status

    async def start_parsing(self, category: str, limit: int = 0):
        """Запуск процесса парсинга
        
        Args:
            category: Категория товаров для парсинга
            limit: Максимальное количество товаров для обработки (0 = все товары)
        """
        if self.is_running:
            logger.warning("Парсер уже запущен")
            return

        self.is_running = True
        self.start_time = time.time()
        self._update_status(
            status='running',
            start_time=datetime.now(),
            errors=0,
            current_category=category
        )

        try:
            # Запускаем парсинг в отдельном потоке
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._run_parsing, category, limit)
        except Exception as e:
            logger.error(f"Ошибка при запуске парсинга: {str(e)}")
            self._update_status(
                status='error',
                end_time=datetime.now(),
                errors=self.status.errors + 1
            )
        finally:
            self.cleanup()

    def _run_parsing(self, category: str, limit: int = 0):
        """Выполнение парсинга в отдельном потоке
        
        Args:
            category: Категория товаров для парсинга
            limit: Максимальное количество товаров для обработки (0 = все товары)
        """
        try:
            # Получаем список URL для категории
            urls = self.parser.get_product_urls(category)
            if not urls:
                logger.error(f"Не найдено URL для категории {category}")
                self._update_status(
                    status='failed',
                    end_time=datetime.now()
                )
                return

            # Обновляем общее количество товаров с учетом лимита
            total_products = len(urls) if limit == 0 else min(len(urls), limit)
            self._update_status(
                total_products=total_products,
                processed_products=0
            )

            # Запускаем парсинг с учетом лимита
            self.parser.process_urls(urls, category, limit)
            
            # Получаем количество обработанных товаров из файла результатов
            try:
                if os.path.exists(settings.RESULTS_FILE):
                    with open(settings.RESULTS_FILE, 'r', encoding='utf-8') as f:
                        results = json.load(f)
                        processed_count = len(results)
                else:
                    processed_count = 0
            except Exception as e:
                logger.error(f"Ошибка при подсчете обработанных товаров: {str(e)}")
                processed_count = 0
            
            self._update_status(
                status='completed',
                processed_products=processed_count,
                end_time=datetime.now()
            )
            logger.info(f"Парсинг завершен. Обработано {processed_count} товаров")

        except Exception as e:
            logger.error(f"Ошибка при выполнении парсинга: {str(e)}")
            self._update_status(
                status='error',
                end_time=datetime.now(),
                errors=self.status.errors + 1
            )

    def cleanup(self):
        """Очистка ресурсов"""
        logger.info("Очистка ресурсов парсера")
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

        logger.info("Остановка парсера...")
        self.is_running = False
        self.parser.stop()
        self.cleanup()
        logger.info("Парсер остановлен")

    def get_products(self, category: Optional[str] = None, limit: int = 10, offset: int = 0) -> List[ProductInfo]:
        """Получить список товаров с пагинацией"""
        try:
            products = []
            if os.path.exists(settings.RESULTS_FILE):
                with open(settings.RESULTS_FILE, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        all_products = json.loads(content)
                        # Фильтруем по категории, если указана
                        if category:
                            all_products = [
                                p for p in all_products 
                                if category in p.get('url', '')
                            ]
                        # Применяем пагинацию
                        products = all_products[offset:offset + limit]
                        # Преобразуем в ProductInfo
                        products = [ProductInfo(**p) for p in products]
            return products
        except Exception as e:
            logger.error(f"Ошибка при получении списка товаров: {str(e)}")
            raise

    def get_product(self, product_id: str) -> Optional[ProductInfo]:
        """Получить информацию о конкретном товаре"""
        try:
            if os.path.exists(settings.RESULTS_FILE):
                with open(settings.RESULTS_FILE, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        products = json.loads(content)
                        # Ищем товар по ID
                        for product in products:
                            if product.get('product_code') == product_id:
                                return ProductInfo(**product)
            return None
        except Exception as e:
            logger.error(f"Ошибка при получении информации о товаре: {str(e)}")
            raise 