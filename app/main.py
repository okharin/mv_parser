from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict
import uvicorn
from datetime import datetime
import json
import os
from pathlib import Path

from app.core.config import settings
from app.services.parser import ParserService
from app.services.url_updater import URLUpdater
from app.schemas.parser import ParserStatus, URLUpdaterStatus, ProductInfo
from app.core.logging import setup_logging

# Настройка логирования
logger = setup_logging()

app = FastAPI(
    title="MVideo Parser API",
    description="API для парсинга товаров с сайта MVideo",
    version="1.0.0"
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Инициализация сервисов
parser_service = ParserService()
url_updater = URLUpdater()

@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {"message": "MVideo Parser API"}

@app.get("/status/parser", response_model=ParserStatus)
async def get_parser_status():
    """Получить статус парсера"""
    try:
        status = parser_service.get_status()
        return status
    except Exception as e:
        logger.error(f"Ошибка при получении статуса парсера: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/url-updater", response_model=URLUpdaterStatus)
async def get_url_updater_status():
    """Получить статус обновления URL"""
    try:
        status = url_updater.get_status()
        return status
    except Exception as e:
        logger.error(f"Ошибка при получении статуса URL updater: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/parse/{category}")
async def start_parsing(
    category: str,
    background_tasks: BackgroundTasks,
    force: bool = Query(False, description="Принудительный запуск парсинга"),
    limit: int = Query(0, description="Максимальное количество товаров для обработки (0 = все товары)")
):
    """Запустить парсинг для указанной категории
    
    Args:
        category: Категория товаров для парсинга
        force: Принудительный запуск парсинга
        limit: Максимальное количество товаров для обработки (0 = все товары)
    """
    try:
        if parser_service.is_running and not force:
            raise HTTPException(
                status_code=400,
                detail="Парсер уже запущен. Используйте force=true для принудительного запуска"
            )
        
        background_tasks.add_task(parser_service.start_parsing, category, limit)
        return {"message": f"Парсинг категории {category} запущен (лимит: {limit if limit > 0 else 'без ограничений'})"}
    except Exception as e:
        logger.error(f"Ошибка при запуске парсинга: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/update-urls")
async def start_url_update(
    background_tasks: BackgroundTasks,
    force: bool = Query(False, description="Принудительное обновление URL")
):
    """Запустить обновление URL"""
    try:
        if url_updater.is_running and not force:
            raise HTTPException(
                status_code=400,
                detail="URL updater уже запущен. Используйте force=true для принудительного запуска"
            )
        
        background_tasks.add_task(url_updater.update_urls)
        return {"message": "Обновление URL запущено"}
    except Exception as e:
        logger.error(f"Ошибка при запуске обновления URL: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/products", response_model=List[ProductInfo])
async def get_products(
    category: Optional[str] = None,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Получить список товаров с пагинацией"""
    try:
        products = parser_service.get_products(category, limit, offset)
        return products
    except Exception as e:
        logger.error(f"Ошибка при получении списка товаров: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/products/{product_id}", response_model=ProductInfo)
async def get_product(product_id: str):
    """Получить информацию о конкретном товаре"""
    try:
        product = parser_service.get_product(product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Товар не найден")
        return product
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении информации о товаре: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stop/parser")
async def stop_parser():
    """Остановить парсер"""
    try:
        parser_service.stop()
        return {"message": "Парсер остановлен"}
    except Exception as e:
        logger.error(f"Ошибка при остановке парсера: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stop/url-updater")
async def stop_url_updater():
    """Остановить URL updater"""
    try:
        url_updater.stop()
        return {"message": "URL updater остановлен"}
    except Exception as e:
        logger.error(f"Ошибка при остановке URL updater: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    ) 