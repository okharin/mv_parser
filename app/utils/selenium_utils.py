from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from typing import Optional, List, Dict, Any
import random
import time
import threading
from contextlib import contextmanager

from app.core.config import settings
from app.core.logging import logger

class SeleniumPool:
    """Пул драйверов Selenium"""
    
    def __init__(self, pool_size: int = settings.DRIVER_POOL_SIZE):
        self.pool_size = pool_size
        self.drivers: List[webdriver.Chrome] = []
        self.lock = threading.Lock()
        self.init_pool()
        
    def init_pool(self):
        """Инициализация пула драйверов"""
        for _ in range(self.pool_size):
            try:
                driver = self.create_driver()
                self.drivers.append(driver)
            except Exception as e:
                logger.error(f"Ошибка при создании драйвера для пула: {str(e)}")
                
    def create_driver(self) -> webdriver.Chrome:
        """Создание нового драйвера"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument(f'user-agent={random.choice(settings.USER_AGENTS)}')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        service = Service()
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Устанавливаем User-Agent
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": random.choice(settings.USER_AGENTS)
        })
        
        # Настраиваем заголовки
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
        
    @contextmanager
    def get_driver(self):
        """Получение драйвера из пула"""
        driver = None
        try:
            with self.lock:
                if self.drivers:
                    driver = self.drivers.pop()
                else:
                    driver = self.create_driver()
            yield driver
        finally:
            if driver:
                with self.lock:
                    if len(self.drivers) < self.pool_size:
                        self.drivers.append(driver)
                    else:
                        try:
                            driver.quit()
                        except:
                            pass
                            
    def cleanup(self):
        """Очистка пула драйверов"""
        with self.lock:
            for driver in self.drivers:
                try:
                    driver.quit()
                except:
                    pass
            self.drivers.clear()

class SeleniumHelper:
    """Вспомогательный класс для работы с Selenium"""
    
    def __init__(self, driver: webdriver.Chrome):
        self.driver = driver
        self.wait = WebDriverWait(driver, settings.TIMEOUT)
        
    def get_element(self, by: By, value: str, timeout: Optional[int] = None) -> Optional[Any]:
        """Получение элемента с ожиданием"""
        try:
            wait = WebDriverWait(self.driver, timeout or settings.TIMEOUT)
            return wait.until(EC.presence_of_element_located((by, value)))
        except TimeoutException:
            logger.error(f"Таймаут при ожидании элемента {value}")
            return None
        except Exception as e:
            logger.error(f"Ошибка при получении элемента {value}: {str(e)}")
            return None
            
    def get_elements(self, by: By, value: str, timeout: Optional[int] = None) -> List[Any]:
        """Получение списка элементов с ожиданием"""
        try:
            wait = WebDriverWait(self.driver, timeout or settings.TIMEOUT)
            return wait.until(EC.presence_of_all_elements_located((by, value)))
        except TimeoutException:
            logger.error(f"Таймаут при ожидании элементов {value}")
            return []
        except Exception as e:
            logger.error(f"Ошибка при получении элементов {value}: {str(e)}")
            return []
            
    def wait_for_element(self, by: By, value: str, timeout: Optional[int] = None) -> bool:
        """Ожидание появления элемента"""
        try:
            wait = WebDriverWait(self.driver, timeout or settings.TIMEOUT)
            wait.until(EC.presence_of_element_located((by, value)))
            return True
        except TimeoutException:
            logger.error(f"Таймаут при ожидании элемента {value}")
            return False
        except Exception as e:
            logger.error(f"Ошибка при ожидании элемента {value}: {str(e)}")
            return False
            
    def wait_for_elements(self, by: By, value: str, timeout: Optional[int] = None) -> bool:
        """Ожидание появления элементов"""
        try:
            wait = WebDriverWait(self.driver, timeout or settings.TIMEOUT)
            wait.until(EC.presence_of_all_elements_located((by, value)))
            return True
        except TimeoutException:
            logger.error(f"Таймаут при ожидании элементов {value}")
            return False
        except Exception as e:
            logger.error(f"Ошибка при ожидании элементов {value}: {str(e)}")
            return False
            
    def get_text(self, by: By, value: str, timeout: Optional[int] = None) -> Optional[str]:
        """Получение текста элемента"""
        element = self.get_element(by, value, timeout)
        if element:
            try:
                return element.text.strip()
            except:
                return None
        return None
        
    def get_attribute(self, by: By, value: str, attribute: str, timeout: Optional[int] = None) -> Optional[str]:
        """Получение атрибута элемента"""
        element = self.get_element(by, value, timeout)
        if element:
            try:
                return element.get_attribute(attribute)
            except:
                return None
        return None
        
    def click(self, by: By, value: str, timeout: Optional[int] = None) -> bool:
        """Клик по элементу"""
        element = self.get_element(by, value, timeout)
        if element:
            try:
                element.click()
                return True
            except:
                return False
        return False
        
    def input_text(self, by: By, value: str, text: str, timeout: Optional[int] = None) -> bool:
        """Ввод текста в элемент"""
        element = self.get_element(by, value, timeout)
        if element:
            try:
                element.clear()
                element.send_keys(text)
                return True
            except:
                return False
        return False
        
    def scroll_to_element(self, by: By, value: str, timeout: Optional[int] = None) -> bool:
        """Прокрутка к элементу"""
        element = self.get_element(by, value, timeout)
        if element:
            try:
                self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                return True
            except:
                return False
        return False
        
    def scroll_to_bottom(self):
        """Прокрутка страницы вниз"""
        try:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            return True
        except:
            return False
            
    def scroll_to_top(self):
        """Прокрутка страницы вверх"""
        try:
            self.driver.execute_script("window.scrollTo(0, 0);")
            return True
        except:
            return False
            
    def get_page_source(self) -> str:
        """Получение исходного кода страницы"""
        try:
            return self.driver.page_source
        except:
            return ""
            
    def get_current_url(self) -> str:
        """Получение текущего URL"""
        try:
            return self.driver.current_url
        except:
            return ""
            
    def navigate_to(self, url: str) -> bool:
        """Переход по URL"""
        try:
            self.driver.get(url)
            return True
        except:
            return False
            
    def refresh(self) -> bool:
        """Обновление страницы"""
        try:
            self.driver.refresh()
            return True
        except:
            return False
            
    def back(self) -> bool:
        """Возврат на предыдущую страницу"""
        try:
            self.driver.back()
            return True
        except:
            return False
            
    def forward(self) -> bool:
        """Переход на следующую страницу"""
        try:
            self.driver.forward()
            return True
        except:
            return False
            
    def add_cookie(self, name: str, value: str) -> bool:
        """Добавление cookie"""
        try:
            self.driver.add_cookie({'name': name, 'value': value})
            return True
        except:
            return False
            
    def get_cookie(self, name: str) -> Optional[str]:
        """Получение cookie"""
        try:
            cookie = self.driver.get_cookie(name)
            return cookie.get('value') if cookie else None
        except:
            return None
            
    def delete_cookie(self, name: str) -> bool:
        """Удаление cookie"""
        try:
            self.driver.delete_cookie(name)
            return True
        except:
            return False
            
    def delete_all_cookies(self) -> bool:
        """Удаление всех cookie"""
        try:
            self.driver.delete_all_cookies()
            return True
        except:
            return False
            
    def execute_script(self, script: str, *args) -> Any:
        """Выполнение JavaScript"""
        try:
            return self.driver.execute_script(script, *args)
        except:
            return None
            
    def take_screenshot(self, path: str) -> bool:
        """Создание скриншота"""
        try:
            self.driver.save_screenshot(path)
            return True
        except:
            return False
            
    def get_window_size(self) -> Dict[str, int]:
        """Получение размеров окна"""
        try:
            size = self.driver.get_window_size()
            return {
                'width': size['width'],
                'height': size['height']
            }
        except:
            return {'width': 0, 'height': 0}
            
    def set_window_size(self, width: int, height: int) -> bool:
        """Установка размеров окна"""
        try:
            self.driver.set_window_size(width, height)
            return True
        except:
            return False
            
    def maximize_window(self) -> bool:
        """Максимизация окна"""
        try:
            self.driver.maximize_window()
            return True
        except:
            return False
            
    def minimize_window(self) -> bool:
        """Минимизация окна"""
        try:
            self.driver.minimize_window()
            return True
        except:
            return False 