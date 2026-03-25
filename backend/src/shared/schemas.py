from typing import Any

from dataclasses import asdict

from pydantic import BaseModel, Field, PositiveInt, model_serializer

from .domain.entities import Entity


class PageParams(BaseModel):
    """Параметры пагинации, которые приходят от клиента (query params)"""

    page: PositiveInt = Field(default=1, ge=1, description="Номер страницы, начинается с 1")
    size: PositiveInt = Field(
        default=10, ge=1, le=100, description="Размер страницы (количество элементов на странице"
    )

    @property
    def offset(self) -> int:
        """Смещение пагинации"""

        return (self.page - 1) * self.size


class Page[T: Entity](BaseModel):
    """Полный ответ с пагинацией"""

    page: PositiveInt = Field(..., description="Текущая страница")
    size: PositiveInt = Field(..., description="Количество элементов на странице")
    total_items: PositiveInt = Field(..., description="Всего элементов на сервере")
    total_pages: PositiveInt = Field(..., description="Всего страниц")
    has_next: bool = Field(..., description="Есть ли следующая страница")
    has_prev: bool = Field(..., description="Есть ли предыдущая страница")
    items: list[T] = Field(default_factory=list, description="Полученные элементы")

    @model_serializer
    def serialize(self) -> dict[str, Any]:
        return {
            "page": self.page,
            "size": self.size,
            "total_items": self.total_items,
            "total_pages": self.total_pages,
            "has_next": self.has_next,
            "has_prev": self.has_prev,
            "items": [asdict(item) for item in self.items],
        }
