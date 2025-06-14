from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime

class ProductInfo(BaseModel):
    """Схема информации о товаре"""
    url: str
    title: str
    price: str
    product_code: str
    image_urls: List[str] = Field(default_factory=list)
    characteristics: Dict[str, Dict[str, str]] = Field(default_factory=dict)
    parsed_at: datetime

class ParserStatus(BaseModel):
    """Схема статуса парсера"""
    status: str
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    total_products: int = 0
    processed_products: int = 0
    errors: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    heartbeat: Optional[datetime] = None
    current_category: Optional[str] = None

class URLUpdaterStatus(BaseModel):
    """Схема статуса обновления URL"""
    status: str
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    total_urls: int = 0
    errors: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    heartbeat: Optional[datetime] = None 