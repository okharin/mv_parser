import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
import aiofiles
import asyncio
from pathlib import Path

from app.core.config import settings
from app.core.logging import logger
from app.models.product import Product

async def read_json_file(file_path: str) -> List[Dict[str, Any]]:
    """Асинхронное чтение JSON файла"""
    try:
        if not os.path.exists(file_path):
            return []
            
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            content = await f.read()
            if not content.strip():
                return []
            return json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка при чтении JSON файла {file_path}: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Неожиданная ошибка при чтении файла {file_path}: {str(e)}")
        return []

async def write_json_file(file_path: str, data: List[Dict[str, Any]]) -> bool:
    """Асинхронная запись в JSON файл"""
    try:
        # Создаем временный файл
        temp_file = f"{file_path}.tmp"
        
        # Записываем во временный файл
        async with aiofiles.open(temp_file, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(data, ensure_ascii=False, indent=2))
        
        # Атомарно заменяем старый файл новым
        os.replace(temp_file, file_path)
        return True
    except Exception as e:
        logger.error(f"Ошибка при записи в файл {file_path}: {str(e)}")
        # Удаляем временный файл в случае ошибки
        try:
            os.remove(temp_file)
        except:
            pass
        return False

async def append_to_json_file(file_path: str, new_data: Dict[str, Any]) -> bool:
    """Асинхронное добавление данных в JSON файл"""
    try:
        # Читаем существующие данные
        existing_data = await read_json_file(file_path)
        
        # Добавляем новые данные
        existing_data.append(new_data)
        
        # Записываем обновленные данные
        return await write_json_file(file_path, existing_data)
    except Exception as e:
        logger.error(f"Ошибка при добавлении данных в файл {file_path}: {str(e)}")
        return False

async def get_products(
    category: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> List[Product]:
    """Получение списка товаров с пагинацией"""
    try:
        # Читаем данные из файла
        data = await read_json_file(settings.RESULTS_FILE)
        
        # Фильтруем по категории, если указана
        if category:
            data = [
                item for item in data 
                if category in item.get('url', '')
            ]
        
        # Применяем пагинацию
        start = offset
        end = offset + limit
        paginated_data = data[start:end]
        
        # Преобразуем в модели Product
        products = [Product.from_dict(item) for item in paginated_data]
        return products
    except Exception as e:
        logger.error(f"Ошибка при получении списка товаров: {str(e)}")
        return []

async def get_product(product_id: str) -> Optional[Product]:
    """Получение товара по ID"""
    try:
        # Читаем данные из файла
        data = await read_json_file(settings.RESULTS_FILE)
        
        # Ищем товар по ID
        for item in data:
            product = Product.from_dict(item)
            if product.id == product_id:
                return product
        return None
    except Exception as e:
        logger.error(f"Ошибка при получении товара {product_id}: {str(e)}")
        return None

def ensure_directories():
    """Создание необходимых директорий"""
    directories = [
        settings.DATA_DIR,
        settings.LOGS_DIR,
        os.path.dirname(settings.RESULTS_FILE),
        os.path.dirname(settings.PRODUCT_LINKS_FILE),
        os.path.dirname(settings.PARSING_STATUS_FILE),
        os.path.dirname(settings.URL_UPDATE_STATUS_FILE)
    ]
    
    for directory in directories:
        try:
            Path(directory).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Ошибка при создании директории {directory}: {str(e)}")
            raise 