import requests
from bs4 import BeautifulSoup
import logging
import random
import time
from fake_useragent import UserAgent
from urllib.parse import urlparse
import json
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import xml.etree.ElementTree as ET
from urllib.parse import urljoin
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional
import threading
import os
from datetime import datetime

from app.core.config import settings
from app.core.logging import logger

def get_thread_id():
    """Получение ID текущего потока"""
    return threading.current_thread().ident

class Parser:
    def __init__(self):
        self.drivers = []
        self.driver_lock = threading.Lock()
        self.processed_urls = set()
        self.init_driver_pool()
        # Настройка форматирования логгера уже происходит в app.core.logging

        # Загружаем ранее обработанные URL при старте
        try:
            if os.path.exists('data/processed_urls.json'):
                with open('data/processed_urls.json', 'r', encoding='utf-8') as f:
                    self.processed_urls = set(json.load(f))
                logger.info(f"Загружено {len(self.processed_urls)} ранее обработанных URL")
        except Exception as e:
            logger.error(f"Ошибка при загрузке обработанных URL: {str(e)}")

    def init_driver_pool(self):
        """Инициализирует пул драйверов"""
        for _ in range(settings.DRIVER_POOL_SIZE):
            try:
                driver = self.create_driver()
                self.drivers.append(driver)
            except Exception as e:
                logger.error(f"Ошибка при создании драйвера для пула: {str(e)}")

    def create_driver(self) -> webdriver.Chrome:
        """Создает новый экземпляр драйвера с настройками"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument(f'user-agent={self.get_random_user_agent()}')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        service = Service()
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": self.get_random_user_agent()
        })
        
        driver.execute_cdp_cmd('Network.enable', {})
        driver.execute_cdp_cmd('Network.setExtraHTTPHeaders', {
            'headers': {
                'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'max-age=0'
            }
        })
        
        return driver

    def get_driver(self) -> webdriver.Chrome:
        """Получает драйвер из пула или создает новый"""
        with self.driver_lock:
            if self.drivers:
                return self.drivers.pop()
            return self.create_driver()

    def release_driver(self, driver: webdriver.Chrome):
        """Возвращает драйвер в пул"""
        try:
            with self.driver_lock:
                if len(self.drivers) < settings.DRIVER_POOL_SIZE:
                    self.drivers.append(driver)
                else:
                    driver.quit()
        except Exception as e:
            logger.error(f"Ошибка при возврате драйвера в пул: {str(e)}")
            try:
                driver.quit()
            except:
                pass

    def get_random_delay(self) -> float:
        """Возвращает случайную задержку между запросами"""
        return random.uniform(settings.MIN_DELAY, settings.MAX_DELAY)

    def get_random_user_agent(self) -> str:
        """Возвращает случайный User-Agent из списка"""
        return random.choice(settings.USER_AGENTS)

    def is_product_url(self, url: str) -> bool:
        """Проверяет, является ли URL товаром"""
        return bool(re.search(r'/products/[^/]*$', url))

    def get_urls_from_sitemap(self, sitemap_url: str) -> List[Dict]:
        """Получает URL из sitemap"""
        urls_with_dates = []
        try:
            headers = {
                'User-Agent': self.get_random_user_agent(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cookie': '__hash_=9f34a6d2bf9e2b0f6790985d3e3ff7d8'
            }
            
            logger.info(f"Пытаемся получить sitemap: {sitemap_url}")
            session = requests.Session()
            session.headers.update(headers)
            
            response = session.get(sitemap_url, timeout=30, allow_redirects=True)
            logger.info(f"Статус ответа: {response.status_code}")
            logger.info(f"URL после перенаправления: {response.url}")

            if response.status_code == 200:
                logger.info("Получен успешный ответ от сервера")
                try:
                    root = ET.fromstring(response.content)
                    logger.info("XML успешно распарсен")
                    ns_match = root.tag[root.tag.find('{'):root.tag.find('}')+1] if '{' in root.tag else ''
                    logger.info(f"Найден namespace: {ns_match}")
                    
                    sitemaps = root.findall(f'.//{ns_match}sitemap')
                    logger.info(f"Найдено {len(sitemaps)} вложенных sitemap")
                    for sitemap_tag in sitemaps:
                        loc = sitemap_tag.find(f'{ns_match}loc')
                        if loc is not None and loc.text and loc.text.strip() and loc.text.endswith('.xml'):
                            logger.info(f"Обрабатываем вложенный sitemap: {loc.text}")
                            nested_urls = self.get_urls_from_sitemap(loc.text)
                            urls_with_dates.extend(nested_urls)
                    
                    url_tags = root.findall(f'.//{ns_match}url')
                    logger.info(f"Найдено {len(url_tags)} URL в текущем sitemap")
                    for url_tag in url_tags:
                        loc = url_tag.find(f'{ns_match}loc')
                        lastmod = url_tag.find(f'{ns_match}lastmod')
                        if loc is not None and loc.text and loc.text.strip():
                            url = loc.text.strip()
                            if url and url.startswith('http'):
                                url_info = {
                                    'url': url,
                                    'last_modified': lastmod.text if lastmod is not None else None
                                }
                                urls_with_dates.append(url_info)
                except ET.ParseError as e:
                    logger.error(f"Ошибка парсинга XML: {str(e)}")
                    logger.error(f"Содержимое ответа: {response.text[:500]}...")
            else:
                logger.error(f"Ошибка при получении sitemap: статус {response.status_code}")
                logger.error(f"Заголовки ответа: {dict(response.headers)}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка сети при получении sitemap {sitemap_url}: {str(e)}")
        except Exception as e:
            logger.error(f"Неожиданная ошибка при получении sitemap {sitemap_url}: {str(e)}")
            logger.exception(e)
        return urls_with_dates

    def get_product_urls(self, category: Optional[str] = None) -> List[Dict]:
        """Получает список URL товаров из сохраненного файла"""
        try:
            if not os.path.exists(settings.PRODUCT_LINKS_FILE):
                logger.error(f"Файл с URL товаров не найден: {settings.PRODUCT_LINKS_FILE}")
                return []

            # Читаем URL из файла
            with open(settings.PRODUCT_LINKS_FILE, 'r', encoding='utf-8') as f:
                urls_dict = json.load(f)
            
            # Преобразуем словарь в список словарей с URL и датой последнего изменения
            product_urls = [
                {
                    'url': url,
                    'last_modified': info.get('last_modified')
                }
                for url, info in urls_dict.items()
            ]
            
            # Фильтруем по категории, если указана
            if category:
                category_pattern = f'/products/{category}[^/]*$'
                product_urls = [
                    url_info for url_info in product_urls 
                    if re.search(category_pattern, url_info['url'])
                ]
            
            logger.info(f"Загружено {len(product_urls)} URL товаров из файла")
            return product_urls
            
        except Exception as e:
            logger.error(f"Ошибка при получении списка URL товаров из файла: {str(e)}")
            return []

    def process_duplicate_characteristics(self, characteristics: Dict[str, Dict[str, str]]) -> Dict[str, Dict[str, str]]:
        """Обработка дублирующихся названий характеристик - добавляет цифры к дублирующимся названиям"""
        processed_characteristics = {}
        all_used_names = set()  # Отслеживаем все использованные названия во всех группах
        
        for group_name, group_specs in characteristics.items():
            processed_group = {}
            
            for spec_name, spec_value in group_specs.items():
                original_name = spec_name
                counter = 1
                
                # Если название уже использовано в любой группе, добавляем цифру
                while spec_name in all_used_names:
                    spec_name = f"{original_name} {counter}"
                    counter += 1
                
                # Логируем, если название было изменено
                if spec_name != original_name:
                    logger.info(f"Дублирующееся название характеристики '{original_name}' переименовано в '{spec_name}' (значение: {spec_value})")
                
                all_used_names.add(spec_name)
                processed_group[spec_name] = spec_value
            
            processed_characteristics[group_name] = processed_group
        
        return processed_characteristics

    def extract_product_info(self, driver: webdriver.Chrome, url: str) -> Optional[Dict]:
        """Извлечение информации о товаре"""
        thread_id = get_thread_id()
        try:
            # Проверяем редирект и статус страницы
            try:
                driver.get(url)
                time.sleep(2)  # Даем время на загрузку
                current_url = driver.current_url
                if current_url != url:
                    logger.warning(f"Начинаем обработку товара {url} на {current_url}")
                if "404" in driver.title or "страница не найдена" in driver.title.lower():
                    logger.error(f"Страница не найдена (404): {current_url}")
                    return None
                if "доступ запрещен" in driver.title.lower() or "access denied" in driver.title.lower():
                    logger.error(f"Доступ запрещен: {current_url}")
                    return None
            except Exception as e:
                logger.error(f"Ошибка при загрузке страницы {url}: {str(e)}")
                return None

            wait = WebDriverWait(driver, settings.TIMEOUT)
            
            # Название товара
            try:
                title_selectors = [
                    "h1.title",
                    "h1.pdp-header__title",
                    "h1[class*='title']",
                    "h1.product-title"
                ]
                
                title = ''
                for selector in title_selectors:
                    try:
                        title_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                        title = title_element.text.strip()
                        if title:
                            logger.info(f"Получено название товара (селектор {selector}): {title}")
                            break
                    except Exception as e:
                        logger.debug(f"Не удалось получить название по селектору {selector}: {str(e)}")
                        continue
                        
                if not title:
                    logger.error(f"Не удалось получить название товара ни по одному из селекторов")
                    try:
                        logger.error(f"HTML страницы: {driver.page_source[:2000]}...")
                        logger.error(f"Текущий URL: {driver.current_url}")
                    except:
                        pass
                    
            except Exception as e:
                logger.error(f"Ошибка при получении названия товара: {str(e)}")
                try:
                    logger.error(f"HTML страницы: {driver.page_source[:2000]}...")
                    logger.error(f"Текущий URL: {driver.current_url}")
                except:
                    pass
                title = ''
                

                
            # Код товара
            product_code = ''
            try:
                code_selectors = [
                    ".product-code-container span:last-child",
                    ".product-code",
                    "[data-product-code]"
                ]
                
                for selector in code_selectors:
                    try:
                        product_code_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                        product_code_text = product_code_element.text.strip()
                        if not product_code_text and selector == "[data-product-code]":
                            product_code_text = product_code_element.get_attribute("data-product-code")
                        # Очищаем код товара от пробелов и специальных символов
                        product_code = re.sub(r'\s+', '', product_code_text)  # Удаляем все пробелы
                        product_code = product_code.replace("&nbsp;", "")  # Удаляем HTML-пробелы
                        product_code = product_code.strip()  # Удаляем пробелы в начале и конце
                        if product_code:
                            logger.info(f"Получен код товара (селектор {selector}): {product_code}")
                            break
                    except Exception:
                        continue
                
                if not product_code:
                    logger.error(f"Не удалось получить код товара ни по одному из селекторов")
                    
            except Exception as e:
                logger.error(f"Ошибка при извлечении кода товара: {str(e)}")
                product_code = ''
                
            # Получение изображений
            image_urls = []
            try:
                # Ждем загрузки страницы
                time.sleep(2)  # Даем время для загрузки динамического контента
                
                # Список селекторов для галереи
                gallery_selectors = [
                    ".wrapper.mv-hide-scrollbar",
                    ".product-gallery",
                    ".product-images",
                    ".pdp-gallery",
                    "[data-gallery]"
                ]
                
                gallery = None
                for selector in gallery_selectors:
                    try:
                        gallery = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                        if gallery:
                            logger.info(f"Найдена галерея по селектору: {selector}")
                            break
                    except Exception:
                        continue
                
                if gallery:
                    # Ищем изображения в галерее
                    image_selectors = [
                        "img[src*='.jpg']",
                        "img[src*='.jpeg']", 
                        "img[src*='.png']",
                        "img[src*='.webp']",
                        "img[data-src*='.jpg']",
                        "img[data-src*='.jpeg']",
                        "img[data-src*='.png']",
                        "img[data-src*='.webp']"
                    ]
                    
                    for selector in image_selectors:
                        try:
                            images = gallery.find_elements(By.CSS_SELECTOR, selector)
                            for img in images:
                                # Пробуем разные атрибуты для получения URL
                                img_url = None
                                for attr in ['src', 'data-src', 'data-original']:
                                    try:
                                        img_url = img.get_attribute(attr)
                                        if img_url and img_url.startswith('http'):
                                            break
                                    except:
                                        continue
                                
                                if img_url and img_url not in image_urls:
                                    image_urls.append(img_url)
                                    logger.info(f"Добавлено изображение: {img_url}")
                        except Exception as e:
                            logger.debug(f"Ошибка при извлечении изображений по селектору {selector}: {str(e)}")
                            continue
                else:
                    logger.warning(f"Галерея не найдена для товара {url}")
                
            except Exception as e:
                logger.error(f"Ошибка при извлечении изображений: {str(e)}")
                logger.error(f"Текущий URL страницы: {driver.current_url}")
                try:
                    logger.error(f"HTML галереи: {gallery.get_attribute('outerHTML')[:1000] if gallery else 'Галерея не найдена'}")
                except:
                    pass
            
            # Получаем характеристики
            characteristics = self.get_specifications_from_spec_page(driver, url)
            
            # Обрабатываем дублирующиеся названия характеристик
            processed_characteristics = self.process_duplicate_characteristics(characteristics)
            
            # Формируем строку с информацией о товаре
            product_info_parts = [
                f"Артикул: {product_code}",
                f"Наименование: {title}"
            ]
            
            # Добавляем характеристики
            if processed_characteristics:
                for group_name, group_specs in processed_characteristics.items():
                    for spec_name, spec_value in group_specs.items():
                        # Если значение - список, объединяем через запятую
                        if isinstance(spec_value, list):
                            spec_value = ", ".join(spec_value)
                        # Удаляем кавычки из значения
                        if isinstance(spec_value, str):
                            spec_value = spec_value.replace('"', '').replace('"', '').replace('"', '')
                        product_info_parts.append(f"{spec_name}: {spec_value}")
            
            # Добавляем изображения
            # if image_urls:
            #     product_info_parts.append(f"Изображения: {', '.join(image_urls)}")
            
            # Объединяем все части в одну строку
            product_info = "\n".join(product_info_parts)
            
            return {
                "title": title,
                "product_code": product_code,
                "image_urls": image_urls,
                "characteristics": processed_characteristics,
                "product_info": product_info
            }
            
        except Exception as e:
            logger.error(f"Ошибка при извлечении информации о товаре {url}: {str(e)}")
            return None

    def get_specifications_from_spec_page(self, driver: webdriver.Chrome, base_url: str) -> Dict:
        """Получение характеристик со страницы спецификации"""
        thread_id = get_thread_id()
        specs = {}
        try:
            spec_url = f"{base_url}/specification"
            logger.info(f"Переход на страницу спецификации: {spec_url}")
            driver.get(spec_url)
            time.sleep(self.get_random_delay())
            
            wait = WebDriverWait(driver, settings.TIMEOUT)
            
            # Ждем загрузки групп характеристик
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "section.characteristics__group")))
            
            # Получаем количество групп
            spec_groups = driver.find_elements(By.CSS_SELECTOR, "section.characteristics__group")
            logger.info(f"Найдено групп характеристик: {len(spec_groups)}")
            
            # Обрабатываем каждую группу
            for i in range(len(spec_groups)):
                try:
                    # Каждый раз заново находим элементы, чтобы избежать stale reference
                    spec_groups = driver.find_elements(By.CSS_SELECTOR, "section.characteristics__group")
                    if i >= len(spec_groups):
                        logger.warning(f"Группа {i} больше не найдена, пропускаем")
                        continue
                        
                    group = spec_groups[i]
                    group_title = group.find_element(By.CSS_SELECTOR, "h2.characteristics__group-title").text.strip()
                    logger.info(f"Обработка группы: {group_title}")
                    
                    # Логируем HTML структуру группы для отладки
                    try:
                        logger.debug(f"HTML структура группы {group_title}: {group.get_attribute('outerHTML')[:1000]}")
                    except:
                        pass
                    
                    # Находим элементы характеристик внутри группы
                    items = group.find_elements(By.CSS_SELECTOR, "dl.characteristics__list > mvid-item-with-dots")
                    group_specs = {}
                    used_names_in_group = set()  # Отслеживаем использованные названия в группе
                    
                    for item in items:
                        try:
                            # Пробуем разные селекторы для названия и значения
                            name_selectors = [
                                "dt.item-with-dots__title span.item-with-dots__text",
                                "dt.characteristics__name",
                                "dt[class*='title']",
                                "dt[class*='name']"
                            ]
                            
                            value_selectors = [
                                "dd.item-with-dots__value",
                                "dd.characteristics__value",
                                "dd[class*='value']"
                            ]
                            
                            name = None
                            value = None
                            
                            # Пробуем найти название по разным селекторам
                            for selector in name_selectors:
                                try:
                                    name_element = item.find_element(By.CSS_SELECTOR, selector)
                                    name = name_element.text.strip()
                                    if name:
                                        break
                                except:
                                    continue
                                    
                            # Пробуем найти значение по разным селекторам
                            for selector in value_selectors:
                                try:
                                    value_element = item.find_element(By.CSS_SELECTOR, selector)
                                    value = value_element.text.strip()
                                    if value:
                                        break
                                except:
                                    continue
                            
                            if name and value:
                                # Обрабатываем дублирующиеся названия в группе
                                original_name = name
                                counter = 1
                                while name in used_names_in_group:
                                    name = f"{original_name} {counter}"
                                    counter += 1
                                
                                # Логируем, если название было изменено
                                if name != original_name:
                                    logger.info(f"Дублирующееся название характеристики '{original_name}' переименовано в '{name}' (значение: {value})")
                                
                                used_names_in_group.add(name)
                                group_specs[name] = value
                                logger.info(f"Добавлена характеристика: {name} = {value}")
                            else:
                                # Логируем HTML элемента для отладки
                                try:
                                    logger.debug(f"HTML элемента характеристики: {item.get_attribute('outerHTML')[:500]}")
                                except:
                                    pass
                                logger.warning(f"Не удалось извлечь название или значение характеристики в группе {group_title}")
                                
                        except Exception as e:
                            logger.error(f"Ошибка при извлечении характеристики в группе {group_title}: {str(e)}")
                            continue
                            
                    if group_specs:
                        specs[group_title] = group_specs
                except Exception as e:
                    logger.error(f"Ошибка при обработке группы характеристик: {str(e)}")
                    continue
                    
            logger.info(f"Успешно извлечено {len(specs)} групп характеристик")
            return specs
            
        except Exception as e:
            logger.error(f"Ошибка при получении характеристик со страницы спецификации: {str(e)}")
            try:
                logger.error(f"HTML страницы: {driver.page_source[:1000]}...")
            except:
                pass
            return {}

    def process_urls(self, urls: List[Dict], category: Optional[str] = None, limit: Optional[int] = None) -> None:
        """Обработка списка URL"""
        thread_id = get_thread_id()
        if urls is None:
            logger.error("Передан None вместо списка URL")
            return
            
        if not urls:
            logger.warning(f"Список URL пуст")
            return
            
        if limit:
            urls = urls[:limit]
            logger.info(f"Установлен лимит на обработку {limit} товаров")
            
        total_urls = len(urls)
        logger.info(f"Загружено {total_urls} URL товаров из файла")
        
        # Разбиваем URL на батчи для параллельной обработки
        batch_size = settings.BATCH_SIZE
        url_batches = [urls[i:i + batch_size] for i in range(0, len(urls), batch_size)]
        
        with ThreadPoolExecutor(max_workers=settings.MAX_WORKERS) as executor:
            futures = []
            for batch_index, batch in enumerate(url_batches):
                start_index = batch_index * batch_size
                futures.append(
                    executor.submit(
                        self.process_url_batch,
                        batch,
                        category,
                        start_index + 1,  # Номер первого товара в батче
                        total_urls  # Общее количество товаров
                    )
                )
            
            # Ждем завершения всех задач
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Ошибка при обработке батча: {str(e)}")

    def save_processed_urls(self) -> None:
        """Сохранение списка обработанных URL в файл"""
        thread_id = get_thread_id()
        try:
            # Создаем директорию data, если её нет
            os.makedirs('data', exist_ok=True)
            
            # Сохраняем множество URL в файл
            with open('data/processed_urls.json', 'w', encoding='utf-8') as f:
                json.dump(list(self.processed_urls), f, ensure_ascii=False, indent=2)
            
            logger.info(f"[Thread-{thread_id}] Сохранено {len(self.processed_urls)} обработанных URL в файл")
        except Exception as e:
            logger.error(f"[Thread-{thread_id}] Ошибка при сохранении обработанных URL: {str(e)}")

    def send_to_api(self, product_info: str, product_code: str, image_urls: List[str] = None) -> None:
        """Отправка данных о товаре на API"""
        thread_id = get_thread_id()
        try:
            url = "https://duomind.ru/api/product-card"
            
            # В img отправляем все url через запятую
            img_url = ", ".join(image_urls) if image_urls else ""
            
            payload = {
                "product_info": product_info,
                "ean": product_code,
                "source": "МВидео",
                "template_id": 0,
                "img": img_url,
                "parsing_result": {},
                "check_result": {}
            }
            
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': self.get_random_user_agent()
            }
            
            logger.info(f"[Thread-{thread_id}] Отправка данных на API для товара {product_code}. Payload: {json.dumps(payload, ensure_ascii=False)}")
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                logger.info(f"[Thread-{thread_id}] Успешная отправка данных на API. Ответ: {response.text}")
                # Сохраняем обработанные URL после успешной отправки
                self.save_processed_urls()
            else:
                logger.error(f"[Thread-{thread_id}] Ошибка при отправке данных на API. Статус: {response.status_code}, Ответ: {response.text}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"[Thread-{thread_id}] Ошибка сети при отправке данных на API: {str(e)}")
        except Exception as e:
            logger.error(f"[Thread-{thread_id}] Неожиданная ошибка при отправке данных на API: {str(e)}")

    def process_url_batch(self, urls_batch: List[Dict], category: Optional[str], start_item_number: int, total_items: int) -> None:
        """Обработка батча URL"""
        thread_id = get_thread_id()
        driver = None
        try:
            driver = self.get_driver()
            for i, url_data in enumerate(urls_batch):
                url = url_data["url"]
                current_item_number = start_item_number + i
                logger.info(f"Начинаем обработку товара {current_item_number} из {total_items}: {url}")
                
                if url in self.processed_urls:
                    logger.info(f"URL уже обработан: {url}")
                    continue
                    
                try:
                    product_info = self.extract_product_info(driver, url)
                    if product_info:
                        self.processed_urls.add(url)
                        logger.info(f"Успешно обработан товар {current_item_number} из {total_items}: {url}")
                        
                        # Сохраняем результат
                        result = {
                            "url": url,
                            "title": product_info["title"],
                            "product_code": product_info["product_code"],
                            "image_urls": product_info["image_urls"],
                            "characteristics": product_info["characteristics"],
                            "product_info": product_info["product_info"],
                            "parsed_at": datetime.now().isoformat()
                        }
                        
                        # Сохраняем в файл
                        self.save_result(result)
                        logger.info(f"Результат сохранен для товара {current_item_number} из {total_items}: {url}")
                        
                        # Отправляем данные на API
                        self.send_to_api(
                            product_info=product_info["product_info"],
                            product_code=product_info["product_code"],
                            image_urls=product_info["image_urls"]
                        )
                    else:
                        logger.error(f"Не удалось получить информацию о товаре {current_item_number} из {total_items}: {url}")
                except Exception as e:
                    logger.error(f"Ошибка при обработке товара {current_item_number} из {total_items} {url}: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Ошибка при обработке батча: {str(e)}")
        finally:
            if driver:
                self.release_driver(driver)

    def stop(self):
        """Остановка парсера и очистка ресурсов"""
        try:
            with self.driver_lock:
                for driver in self.drivers:
                    try:
                        driver.quit()
                    except:
                        pass
                self.drivers.clear()
        except Exception as e:
            logger.error(f"Ошибка при закрытии пула драйверов: {str(e)}")

    def save_result(self, result: Dict) -> None:
        """Сохранение результата парсинга в файл
        
        Args:
            result: Словарь с информацией о товаре
        """
        thread_id = get_thread_id()
        try:
            # Читаем существующие результаты
            existing_results = []
            if os.path.exists(settings.RESULTS_FILE):
                try:
                    with open(settings.RESULTS_FILE, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if content:  # Проверяем, что файл не пустой
                            existing_results = json.loads(content)
                        else:
                            existing_results = []
                except json.JSONDecodeError:
                    logger.warning(f"Файл {settings.RESULTS_FILE} поврежден, начинаем с пустого списка")
                    existing_results = []
            
            # Добавляем новый результат
            existing_results.append(result)
            
            # Создаем временный файл для атомарной записи
            temp_file = f"{settings.RESULTS_FILE}.tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(existing_results, f, ensure_ascii=False, indent=2)
            
            # Атомарно заменяем старый файл новым
            os.replace(temp_file, settings.RESULTS_FILE)
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении результата: {str(e)}")
            raise 