import xml.etree.ElementTree as ET
from typing import List, Dict, Optional, Any
from urllib.parse import urlparse
import re

from app.core.logging import logger

def parse_sitemap(content: str) -> List[Dict[str, Any]]:
    """Парсинг sitemap XML"""
    urls = []
    try:
        root = ET.fromstring(content)
        
        # Получаем namespace
        ns_match = root.tag[root.tag.find('{'):root.tag.find('}')+1] if '{' in root.tag else ''
        
        # Обрабатываем вложенные sitemap
        sitemaps = root.findall(f'.//{ns_match}sitemap')
        for sitemap in sitemaps:
            loc = sitemap.find(f'{ns_match}loc')
            if loc is not None and loc.text and loc.text.strip():
                urls.append({
                    'url': loc.text.strip(),
                    'type': 'sitemap',
                    'last_modified': None
                })
        
        # Обрабатываем URL
        url_tags = root.findall(f'.//{ns_match}url')
        for url_tag in url_tags:
            loc = url_tag.find(f'{ns_match}loc')
            lastmod = url_tag.find(f'{ns_match}lastmod')
            if loc is not None and loc.text and loc.text.strip():
                urls.append({
                    'url': loc.text.strip(),
                    'type': 'url',
                    'last_modified': lastmod.text if lastmod is not None else None
                })
                
        return urls
    except ET.ParseError as e:
        logger.error(f"Ошибка при парсинге XML: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Неожиданная ошибка при парсинге XML: {str(e)}")
        return []

def is_valid_url(url: str) -> bool:
    """Проверка валидности URL"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def is_product_url(url: str) -> bool:
    """Проверка, является ли URL товаром"""
    return bool(re.search(r'/products/[^/]*$', url))

def filter_product_urls(urls: List[Dict[str, Any]], category: Optional[str] = None) -> List[Dict[str, Any]]:
    """Фильтрация URL товаров"""
    filtered_urls = []
    
    for url_info in urls:
        url = url_info.get('url', '')
        
        # Проверяем валидность URL
        if not is_valid_url(url):
            continue
            
        # Проверяем, является ли URL товаром
        if not is_product_url(url):
            continue
            
        # Фильтруем по категории, если указана
        if category:
            if not re.search(f'/products/{category}[^/]*$', url):
                continue
                
        filtered_urls.append(url_info)
        
    return filtered_urls

def extract_category_from_url(url: str) -> Optional[str]:
    """Извлечение категории из URL"""
    try:
        match = re.search(r'/products/([^/]+)', url)
        if match:
            return match.group(1)
        return None
    except:
        return None

def get_urls_by_category(urls: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Группировка URL по категориям"""
    categories = {}
    
    for url_info in urls:
        url = url_info.get('url', '')
        category = extract_category_from_url(url)
        
        if category:
            if category not in categories:
                categories[category] = []
            categories[category].append(url_info)
            
    return categories

def sort_urls_by_date(urls: List[Dict[str, Any]], reverse: bool = True) -> List[Dict[str, Any]]:
    """Сортировка URL по дате последнего изменения"""
    def get_date(url_info: Dict[str, Any]) -> str:
        return url_info.get('last_modified', '') or ''
        
    return sorted(urls, key=get_date, reverse=reverse)

def get_unique_urls(urls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Получение уникальных URL"""
    seen = set()
    unique_urls = []
    
    for url_info in urls:
        url = url_info.get('url', '')
        if url and url not in seen:
            seen.add(url)
            unique_urls.append(url_info)
            
    return unique_urls

def merge_url_lists(urls1: List[Dict[str, Any]], urls2: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Объединение списков URL с сохранением уникальности"""
    all_urls = urls1 + urls2
    return get_unique_urls(all_urls)

def filter_urls_by_pattern(urls: List[Dict[str, Any]], pattern: str) -> List[Dict[str, Any]]:
    """Фильтрация URL по регулярному выражению"""
    try:
        regex = re.compile(pattern)
        return [
            url_info for url_info in urls 
            if regex.search(url_info.get('url', ''))
        ]
    except re.error as e:
        logger.error(f"Ошибка в регулярном выражении: {str(e)}")
        return []

def get_urls_without_category(urls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Получение URL без категории"""
    return [
        url_info for url_info in urls 
        if not extract_category_from_url(url_info.get('url', ''))
    ]

def get_urls_with_category(urls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Получение URL с категорией"""
    return [
        url_info for url_info in urls 
        if extract_category_from_url(url_info.get('url', ''))
    ]

def get_urls_by_type(urls: List[Dict[str, Any]], url_type: str) -> List[Dict[str, Any]]:
    """Получение URL по типу"""
    return [
        url_info for url_info in urls 
        if url_info.get('type') == url_type
    ]

def get_urls_without_last_modified(urls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Получение URL без даты последнего изменения"""
    return [
        url_info for url_info in urls 
        if not url_info.get('last_modified')
    ]

def get_urls_with_last_modified(urls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Получение URL с датой последнего изменения"""
    return [
        url_info for url_info in urls 
        if url_info.get('last_modified')
    ] 