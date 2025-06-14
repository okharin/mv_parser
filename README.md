# Парсер страниц товаров

Парсер для сбора информации о товарах.

## Возможности

- Парсинг товаров с сайта
- Извлечение характеристик товаров
- Сбор изображений
- Многопоточная обработка
- Сохранение результатов в JSON
- Отправка данных на API

## Требования

- Python 3.8+
- Chrome/Chromium браузер
- Зависимости из requirements.txt
- Docker и Docker Compose (для запуска в контейнере)

## Установка

### Запуск через Docker

1. Соберите и запустите контейнер:
```bash
docker-compose up --build
```

Для запуска в фоновом режиме:
```bash
docker-compose up -d --build
```

Для остановки:
```bash
docker-compose down
```

### Ручная установка

1. Создайте виртуальное окружение и установите зависимости:
```bash
python -m venv venv
source venv/bin/activate  # для Linux/Mac
# или
venv\Scripts\activate  # для Windows
pip install -r requirements.txt
```

2. Установите Chrome/Chromium браузер
