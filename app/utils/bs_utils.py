from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Any, Union
import re
from urllib.parse import urljoin, urlparse

from app.core.logging import logger

def parse_html(html: str) -> Optional[BeautifulSoup]:
    """Парсинг HTML с помощью BeautifulSoup"""
    try:
        return BeautifulSoup(html, 'html.parser')
    except Exception as e:
        logger.error(f"Ошибка при парсинге HTML: {str(e)}")
        return None

def find_element(soup: BeautifulSoup, tag: str, attrs: Dict[str, str]) -> Optional[Any]:
    """Поиск элемента по тегу и атрибутам"""
    try:
        return soup.find(tag, attrs=attrs)
    except Exception as e:
        logger.error(f"Ошибка при поиске элемента {tag}: {str(e)}")
        return None

def find_elements(soup: BeautifulSoup, tag: str, attrs: Dict[str, str]) -> List[Any]:
    """Поиск элементов по тегу и атрибутам"""
    try:
        return soup.find_all(tag, attrs=attrs)
    except Exception as e:
        logger.error(f"Ошибка при поиске элементов {tag}: {str(e)}")
        return []

def get_text(element: Any) -> str:
    """Получение текста элемента"""
    try:
        return element.get_text(strip=True)
    except:
        return ""

def get_attribute(element: Any, attr: str) -> Optional[str]:
    """Получение атрибута элемента"""
    try:
        return element.get(attr)
    except:
        return None

def get_href(element: Any, base_url: str) -> Optional[str]:
    """Получение абсолютного URL из href атрибута"""
    try:
        href = element.get('href')
        if href:
            return urljoin(base_url, href)
        return None
    except:
        return None

def get_src(element: Any, base_url: str) -> Optional[str]:
    """Получение абсолютного URL из src атрибута"""
    try:
        src = element.get('src')
        if src:
            return urljoin(base_url, src)
        return None
    except:
        return None

def get_links(soup: BeautifulSoup, base_url: str) -> List[str]:
    """Получение всех ссылок со страницы"""
    links = []
    try:
        for a in soup.find_all('a', href=True):
            href = get_href(a, base_url)
            if href and is_valid_url(href):
                links.append(href)
        return list(set(links))
    except Exception as e:
        logger.error(f"Ошибка при получении ссылок: {str(e)}")
        return []

def get_images(soup: BeautifulSoup, base_url: str) -> List[str]:
    """Получение всех изображений со страницы"""
    images = []
    try:
        for img in soup.find_all('img', src=True):
            src = get_src(img, base_url)
            if src and is_valid_url(src):
                images.append(src)
        return list(set(images))
    except Exception as e:
        logger.error(f"Ошибка при получении изображений: {str(e)}")
        return []

def get_meta_tags(soup: BeautifulSoup) -> Dict[str, str]:
    """Получение мета-тегов"""
    meta_tags = {}
    try:
        for meta in soup.find_all('meta'):
            name = meta.get('name') or meta.get('property')
            content = meta.get('content')
            if name and content:
                meta_tags[name] = content
        return meta_tags
    except Exception as e:
        logger.error(f"Ошибка при получении мета-тегов: {str(e)}")
        return {}

def get_title(soup: BeautifulSoup) -> str:
    """Получение заголовка страницы"""
    try:
        title = soup.find('title')
        return get_text(title) if title else ""
    except Exception as e:
        logger.error(f"Ошибка при получении заголовка: {str(e)}")
        return ""

def get_description(soup: BeautifulSoup) -> str:
    """Получение описания страницы"""
    try:
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        return get_attribute(meta_desc, 'content') or ""
    except Exception as e:
        logger.error(f"Ошибка при получении описания: {str(e)}")
        return ""

def get_keywords(soup: BeautifulSoup) -> List[str]:
    """Получение ключевых слов"""
    try:
        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
        if meta_keywords:
            content = get_attribute(meta_keywords, 'content')
            if content:
                return [k.strip() for k in content.split(',')]
        return []
    except Exception as e:
        logger.error(f"Ошибка при получении ключевых слов: {str(e)}")
        return []

def get_structured_data(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """Получение структурированных данных"""
    structured_data = []
    try:
        # Ищем JSON-LD
        for script in soup.find_all('script', attrs={'type': 'application/ld+json'}):
            try:
                import json
                data = json.loads(get_text(script))
                structured_data.append(data)
            except:
                continue
                
        # Ищем микроразметку
        for element in soup.find_all(attrs={'itemtype': True}):
            try:
                item_type = element.get('itemtype')
                if item_type:
                    structured_data.append({
                        'type': item_type,
                        'properties': {
                            prop.get('itemprop'): get_text(prop)
                            for prop in element.find_all(attrs={'itemprop': True})
                        }
                    })
            except:
                continue
                
        return structured_data
    except Exception as e:
        logger.error(f"Ошибка при получении структурированных данных: {str(e)}")
        return []

def get_forms(soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
    """Получение форм"""
    forms = []
    try:
        for form in soup.find_all('form'):
            form_data = {
                'action': get_href(form, base_url),
                'method': form.get('method', 'get').lower(),
                'inputs': []
            }
            
            for input_tag in form.find_all(['input', 'select', 'textarea']):
                input_data = {
                    'type': input_tag.get('type', 'text'),
                    'name': input_tag.get('name', ''),
                    'id': input_tag.get('id', ''),
                    'required': input_tag.get('required') is not None
                }
                
                if input_tag.name == 'select':
                    input_data['options'] = [
                        {'value': option.get('value', ''), 'text': get_text(option)}
                        for option in input_tag.find_all('option')
                    ]
                    
                form_data['inputs'].append(input_data)
                
            forms.append(form_data)
            
        return forms
    except Exception as e:
        logger.error(f"Ошибка при получении форм: {str(e)}")
        return []

def get_tables(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """Получение таблиц"""
    tables = []
    try:
        for table in soup.find_all('table'):
            table_data = {
                'headers': [],
                'rows': []
            }
            
            # Получаем заголовки
            headers = table.find_all('th')
            if headers:
                table_data['headers'] = [get_text(h) for h in headers]
            else:
                # Если нет th, берем первую строку
                first_row = table.find('tr')
                if first_row:
                    table_data['headers'] = [get_text(cell) for cell in first_row.find_all(['td', 'th'])]
                    
            # Получаем строки
            for row in table.find_all('tr')[1:]:  # Пропускаем первую строку, если она заголовок
                cells = row.find_all(['td', 'th'])
                if cells:
                    table_data['rows'].append([get_text(cell) for cell in cells])
                    
            tables.append(table_data)
            
        return tables
    except Exception as e:
        logger.error(f"Ошибка при получении таблиц: {str(e)}")
        return []

def get_lists(soup: BeautifulSoup) -> Dict[str, List[str]]:
    """Получение списков"""
    lists = {
        'ul': [],
        'ol': []
    }
    try:
        for list_type in ['ul', 'ol']:
            for list_element in soup.find_all(list_type):
                items = [get_text(li) for li in list_element.find_all('li')]
                if items:
                    lists[list_type].append(items)
        return lists
    except Exception as e:
        logger.error(f"Ошибка при получении списков: {str(e)}")
        return {'ul': [], 'ol': []}

def get_headers(soup: BeautifulSoup) -> Dict[str, List[str]]:
    """Получение заголовков"""
    headers = {
        'h1': [],
        'h2': [],
        'h3': [],
        'h4': [],
        'h5': [],
        'h6': []
    }
    try:
        for level in range(1, 7):
            tag = f'h{level}'
            headers[tag] = [get_text(h) for h in soup.find_all(tag)]
        return headers
    except Exception as e:
        logger.error(f"Ошибка при получении заголовков: {str(e)}")
        return {f'h{i}': [] for i in range(1, 7)}

def get_paragraphs(soup: BeautifulSoup) -> List[str]:
    """Получение параграфов"""
    try:
        return [get_text(p) for p in soup.find_all('p')]
    except Exception as e:
        logger.error(f"Ошибка при получении параграфов: {str(e)}")
        return []

def get_divs_with_class(soup: BeautifulSoup, class_name: str) -> List[Any]:
    """Получение div с определенным классом"""
    try:
        return soup.find_all('div', class_=class_name)
    except Exception as e:
        logger.error(f"Ошибка при получении div с классом {class_name}: {str(e)}")
        return []

def get_elements_by_class(soup: BeautifulSoup, tag: str, class_name: str) -> List[Any]:
    """Получение элементов по тегу и классу"""
    try:
        return soup.find_all(tag, class_=class_name)
    except Exception as e:
        logger.error(f"Ошибка при получении элементов {tag} с классом {class_name}: {str(e)}")
        return []

def get_elements_by_id(soup: BeautifulSoup, tag: str, element_id: str) -> List[Any]:
    """Получение элементов по тегу и id"""
    try:
        return soup.find_all(tag, id=element_id)
    except Exception as e:
        logger.error(f"Ошибка при получении элементов {tag} с id {element_id}: {str(e)}")
        return []

def get_elements_by_attr(soup: BeautifulSoup, tag: str, attr: str, value: str) -> List[Any]:
    """Получение элементов по тегу и атрибуту"""
    try:
        return soup.find_all(tag, attrs={attr: value})
    except Exception as e:
        logger.error(f"Ошибка при получении элементов {tag} с атрибутом {attr}={value}: {str(e)}")
        return []

def get_elements_by_text(soup: BeautifulSoup, tag: str, text: str) -> List[Any]:
    """Получение элементов по тегу и тексту"""
    try:
        return soup.find_all(tag, string=re.compile(text, re.IGNORECASE))
    except Exception as e:
        logger.error(f"Ошибка при получении элементов {tag} с текстом {text}: {str(e)}")
        return []

def get_elements_by_selector(soup: BeautifulSoup, selector: str) -> List[Any]:
    """Получение элементов по CSS селектору"""
    try:
        return soup.select(selector)
    except Exception as e:
        logger.error(f"Ошибка при получении элементов по селектору {selector}: {str(e)}")
        return []

def get_element_by_selector(soup: BeautifulSoup, selector: str) -> Optional[Any]:
    """Получение элемента по CSS селектору"""
    try:
        return soup.select_one(selector)
    except Exception as e:
        logger.error(f"Ошибка при получении элемента по селектору {selector}: {str(e)}")
        return None

def get_parent(element: Any) -> Optional[Any]:
    """Получение родительского элемента"""
    try:
        return element.parent
    except:
        return None

def get_children(element: Any) -> List[Any]:
    """Получение дочерних элементов"""
    try:
        return list(element.children)
    except:
        return []

def get_next_sibling(element: Any) -> Optional[Any]:
    """Получение следующего соседнего элемента"""
    try:
        return element.next_sibling
    except:
        return None

def get_previous_sibling(element: Any) -> Optional[Any]:
    """Получение предыдущего соседнего элемента"""
    try:
        return element.previous_sibling
    except:
        return None

def get_next_element(element: Any) -> Optional[Any]:
    """Получение следующего элемента"""
    try:
        return element.next_element
    except:
        return None

def get_previous_element(element: Any) -> Optional[Any]:
    """Получение предыдущего элемента"""
    try:
        return element.previous_element
    except:
        return None

def get_ancestors(element: Any) -> List[Any]:
    """Получение всех предков элемента"""
    try:
        return list(element.parents)
    except:
        return []

def get_descendants(element: Any) -> List[Any]:
    """Получение всех потомков элемента"""
    try:
        return list(element.descendants)
    except:
        return []

def get_siblings(element: Any) -> List[Any]:
    """Получение всех соседних элементов"""
    try:
        return list(element.next_siblings) + list(element.previous_siblings)
    except:
        return []

def get_elements_between(start: Any, end: Any) -> List[Any]:
    """Получение элементов между двумя элементами"""
    try:
        elements = []
        current = start.next_element
        while current and current != end:
            elements.append(current)
            current = current.next_element
        return elements
    except:
        return []

def get_elements_by_regex(soup: BeautifulSoup, tag: str, pattern: str) -> List[Any]:
    """Получение элементов по тегу и регулярному выражению"""
    try:
        regex = re.compile(pattern)
        return soup.find_all(tag, string=regex)
    except Exception as e:
        logger.error(f"Ошибка при получении элементов {tag} по регулярному выражению {pattern}: {str(e)}")
        return []

def get_elements_by_function(soup: BeautifulSoup, tag: str, function: callable) -> List[Any]:
    """Получение элементов по тегу и функции-фильтру"""
    try:
        return soup.find_all(tag, function)
    except Exception as e:
        logger.error(f"Ошибка при получении элементов {tag} по функции: {str(e)}")
        return []

def get_elements_by_lambda(soup: BeautifulSoup, tag: str, lambda_func: callable) -> List[Any]:
    """Получение элементов по тегу и лямбда-функции"""
    try:
        return soup.find_all(tag, lambda_func)
    except Exception as e:
        logger.error(f"Ошибка при получении элементов {tag} по лямбда-функции: {str(e)}")
        return []

def get_elements_by_custom(soup: BeautifulSoup, tag: str, **kwargs) -> List[Any]:
    """Получение элементов по тегу и пользовательским параметрам"""
    try:
        return soup.find_all(tag, **kwargs)
    except Exception as e:
        logger.error(f"Ошибка при получении элементов {tag} по пользовательским параметрам: {str(e)}")
        return []

def get_elements_by_multiple(soup: BeautifulSoup, **kwargs) -> List[Any]:
    """Получение элементов по нескольким параметрам"""
    try:
        return soup.find_all(**kwargs)
    except Exception as e:
        logger.error(f"Ошибка при получении элементов по нескольким параметрам: {str(e)}")
        return []

def get_elements_by_attrs(soup: BeautifulSoup, tag: str, **attrs) -> List[Any]:
    """Получение элементов по тегу и нескольким атрибутам"""
    try:
        return soup.find_all(tag, attrs=attrs)
    except Exception as e:
        logger.error(f"Ошибка при получении элементов {tag} по нескольким атрибутам: {str(e)}")
        return []

def get_elements_by_string(soup: BeautifulSoup, string: str) -> List[Any]:
    """Получение элементов по строке"""
    try:
        return soup.find_all(string=string)
    except Exception as e:
        logger.error(f"Ошибка при получении элементов по строке {string}: {str(e)}")
        return []

def get_elements_by_strings(soup: BeautifulSoup, strings: List[str]) -> List[Any]:
    """Получение элементов по списку строк"""
    try:
        return soup.find_all(string=strings)
    except Exception as e:
        logger.error(f"Ошибка при получении элементов по списку строк: {str(e)}")
        return []

def get_elements_by_regex_strings(soup: BeautifulSoup, patterns: List[str]) -> List[Any]:
    """Получение элементов по списку регулярных выражений"""
    try:
        regexes = [re.compile(pattern) for pattern in patterns]
        return soup.find_all(string=regexes)
    except Exception as e:
        logger.error(f"Ошибка при получении элементов по списку регулярных выражений: {str(e)}")
        return []

def get_elements_by_function_strings(soup: BeautifulSoup, functions: List[callable]) -> List[Any]:
    """Получение элементов по списку функций"""
    try:
        return soup.find_all(string=functions)
    except Exception as e:
        logger.error(f"Ошибка при получении элементов по списку функций: {str(e)}")
        return []

def get_elements_by_lambda_strings(soup: BeautifulSoup, lambda_funcs: List[callable]) -> List[Any]:
    """Получение элементов по списку лямбда-функций"""
    try:
        return soup.find_all(string=lambda_funcs)
    except Exception as e:
        logger.error(f"Ошибка при получении элементов по списку лямбда-функций: {str(e)}")
        return []

def get_elements_by_custom_strings(soup: BeautifulSoup, **kwargs) -> List[Any]:
    """Получение элементов по пользовательским параметрам строк"""
    try:
        return soup.find_all(string=kwargs)
    except Exception as e:
        logger.error(f"Ошибка при получении элементов по пользовательским параметрам строк: {str(e)}")
        return []

def get_elements_by_multiple_strings(soup: BeautifulSoup, **kwargs) -> List[Any]:
    """Получение элементов по нескольким параметрам строк"""
    try:
        return soup.find_all(**kwargs)
    except Exception as e:
        logger.error(f"Ошибка при получении элементов по нескольким параметрам строк: {str(e)}")
        return []

def get_elements_by_attrs_strings(soup: BeautifulSoup, **attrs) -> List[Any]:
    """Получение элементов по нескольким атрибутам и строкам"""
    try:
        return soup.find_all(attrs=attrs)
    except Exception as e:
        logger.error(f"Ошибка при получении элементов по нескольким атрибутам и строкам: {str(e)}")
        return []

def get_elements_by_string_attrs(soup: BeautifulSoup, string: str, **attrs) -> List[Any]:
    """Получение элементов по строке и нескольким атрибутам"""
    try:
        return soup.find_all(string=string, attrs=attrs)
    except Exception as e:
        logger.error(f"Ошибка при получении элементов по строке и нескольким атрибутам: {str(e)}")
        return []

def get_elements_by_strings_attrs(soup: BeautifulSoup, strings: List[str], **attrs) -> List[Any]:
    """Получение элементов по списку строк и нескольким атрибутам"""
    try:
        return soup.find_all(string=strings, attrs=attrs)
    except Exception as e:
        logger.error(f"Ошибка при получении элементов по списку строк и нескольким атрибутам: {str(e)}")
        return []

def get_elements_by_regex_strings_attrs(soup: BeautifulSoup, patterns: List[str], **attrs) -> List[Any]:
    """Получение элементов по списку регулярных выражений и нескольким атрибутам"""
    try:
        regexes = [re.compile(pattern) for pattern in patterns]
        return soup.find_all(string=regexes, attrs=attrs)
    except Exception as e:
        logger.error(f"Ошибка при получении элементов по списку регулярных выражений и нескольким атрибутам: {str(e)}")
        return []

def get_elements_by_function_strings_attrs(soup: BeautifulSoup, functions: List[callable], **attrs) -> List[Any]:
    """Получение элементов по списку функций и нескольким атрибутам"""
    try:
        return soup.find_all(string=functions, attrs=attrs)
    except Exception as e:
        logger.error(f"Ошибка при получении элементов по списку функций и нескольким атрибутам: {str(e)}")
        return []

def get_elements_by_lambda_strings_attrs(soup: BeautifulSoup, lambda_funcs: List[callable], **attrs) -> List[Any]:
    """Получение элементов по списку лямбда-функций и нескольким атрибутам"""
    try:
        return soup.find_all(string=lambda_funcs, attrs=attrs)
    except Exception as e:
        logger.error(f"Ошибка при получении элементов по списку лямбда-функций и нескольким атрибутам: {str(e)}")
        return []

def get_elements_by_custom_strings_attrs(soup: BeautifulSoup, **kwargs) -> List[Any]:
    """Получение элементов по пользовательским параметрам строк и нескольким атрибутам"""
    try:
        return soup.find_all(**kwargs)
    except Exception as e:
        logger.error(f"Ошибка при получении элементов по пользовательским параметрам строк и нескольким атрибутам: {str(e)}")
        return []

def get_elements_by_multiple_strings_attrs(soup: BeautifulSoup, **kwargs) -> List[Any]:
    """Получение элементов по нескольким параметрам строк и атрибутов"""
    try:
        return soup.find_all(**kwargs)
    except Exception as e:
        logger.error(f"Ошибка при получении элементов по нескольким параметрам строк и атрибутов: {str(e)}")
        return []

def get_elements_by_attrs_strings_attrs(soup: BeautifulSoup, **attrs) -> List[Any]:
    """Получение элементов по нескольким атрибутам и строкам"""
    try:
        return soup.find_all(attrs=attrs)
    except Exception as e:
        logger.error(f"Ошибка при получении элементов по нескольким атрибутам и строкам: {str(e)}")
        return []

def is_valid_url(url: str) -> bool:
    """Проверка валидности URL"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False 