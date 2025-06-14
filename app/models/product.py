from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class ProductCharacteristics(BaseModel):
    """Модель характеристик товара"""
    name: str
    value: str

class ProductGroup(BaseModel):
    """Модель группы характеристик товара"""
    group_name: str = Field(..., alias="group_name")
    characteristics: List[ProductCharacteristics]

class Product(BaseModel):
    """Модель товара"""
    url: str
    title: str
    price: str
    product_code: str
    image_urls: List[str] = Field(default_factory=list)
    characteristics: Dict[str, Dict[str, str]] = Field(default_factory=dict)
    parsed_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        
    @property
    def id(self) -> str:
        """Возвращает уникальный идентификатор товара"""
        return self.product_code or self.url.split('/')[-1]
    
    def to_dict(self) -> Dict:
        """Преобразует модель в словарь"""
        return {
            "id": self.id,
            "url": self.url,
            "title": self.title,
            "price": self.price,
            "product_code": self.product_code,
            "image_urls": self.image_urls,
            "characteristics": self.characteristics,
            "parsed_at": self.parsed_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Product":
        """Создает модель из словаря"""
        if isinstance(data.get("parsed_at"), str):
            data["parsed_at"] = datetime.fromisoformat(data["parsed_at"])
        return cls(**data) 