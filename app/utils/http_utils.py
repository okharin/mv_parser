import aiohttp
import asyncio
from typing import Optional, Dict, Any
import random
from fake_useragent import UserAgent

from app.core.config import settings
from app.core.logging import logger

class HTTPClient:
    """Клиент для HTTP запросов"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.user_agents = settings.USER_AGENTS
        
    async def __aenter__(self):
        """Создание сессии при входе в контекстный менеджер"""
        if not self.session:
            self.session = aiohttp.ClientSession(
                headers=self._get_default_headers(),
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Закрытие сессии при выходе из контекстного менеджера"""
        if self.session:
            await self.session.close()
            self.session = None
            
    def _get_default_headers(self) -> Dict[str, str]:
        """Получение заголовков по умолчанию"""
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'Cookie': '__hash_=9f34a6d2bf9e2b0f6790985d3e3ff7d8'
        }
        
    async def get(self, url: str, **kwargs) -> Optional[str]:
        """Выполнение GET запроса"""
        if not self.session:
            raise RuntimeError("Сессия не создана. Используйте контекстный менеджер.")
            
        try:
            # Добавляем случайную задержку
            await asyncio.sleep(random.uniform(settings.MIN_DELAY, settings.MAX_DELAY))
            
            # Обновляем User-Agent для каждого запроса
            headers = kwargs.pop('headers', {})
            headers['User-Agent'] = random.choice(self.user_agents)
            
            async with self.session.get(url, headers=headers, **kwargs) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    logger.error(f"Ошибка при выполнении GET запроса к {url}: статус {response.status}")
                    return None
        except aiohttp.ClientError as e:
            logger.error(f"Ошибка сети при выполнении GET запроса к {url}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Неожиданная ошибка при выполнении GET запроса к {url}: {str(e)}")
            return None
            
    async def post(self, url: str, data: Dict[str, Any], **kwargs) -> Optional[str]:
        """Выполнение POST запроса"""
        if not self.session:
            raise RuntimeError("Сессия не создана. Используйте контекстный менеджер.")
            
        try:
            # Добавляем случайную задержку
            await asyncio.sleep(random.uniform(settings.MIN_DELAY, settings.MAX_DELAY))
            
            # Обновляем User-Agent для каждого запроса
            headers = kwargs.pop('headers', {})
            headers['User-Agent'] = random.choice(self.user_agents)
            
            async with self.session.post(url, json=data, headers=headers, **kwargs) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    logger.error(f"Ошибка при выполнении POST запроса к {url}: статус {response.status}")
                    return None
        except aiohttp.ClientError as e:
            logger.error(f"Ошибка сети при выполнении POST запроса к {url}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Неожиданная ошибка при выполнении POST запроса к {url}: {str(e)}")
            return None
            
async def make_request(url: str, method: str = "GET", data: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Удобная функция для выполнения HTTP запросов"""
    async with HTTPClient() as client:
        if method.upper() == "GET":
            return await client.get(url)
        elif method.upper() == "POST":
            if data is None:
                raise ValueError("Для POST запроса необходимо указать data")
            return await client.post(url, data)
        else:
            raise ValueError(f"Неподдерживаемый метод: {method}") 