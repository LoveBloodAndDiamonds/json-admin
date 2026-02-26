"""Описание страницы админки для редактирования JSON."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel


@dataclass(slots=True, frozen=True)
class JsonPage:
    """Конфигурация вкладки админки.

    Attributes:
        slug: Уникальный идентификатор страницы для URL.
        title: Заголовок вкладки в интерфейсе.
        icon: CSS-класс иконки (например, `fa-solid fa-gear`).
        file_path: Абсолютный или относительный путь до JSON-файла.
        model: Обязательная Pydantic BaseModel для валидации.

    """

    slug: str
    title: str
    file_path: str | Path
    model: type[BaseModel]
    icon: str = ""

    def validate(self) -> None:
        """Проверяет корректность конфигурации страницы.

        Raises:
            ValueError: Если обязательные поля не заполнены или model запрещенного типа.

        """
        if not self.slug:
            raise ValueError("JsonPage: slug required")
        if not self.title:
            raise ValueError("JsonPage: title required")
        if not isinstance(self.icon, str):
            raise ValueError("JsonPage: icon must be string")
        if not str(self.file_path):
            raise ValueError("JsonPage: file_path required")
        if not isinstance(self.model, type) or not issubclass(self.model, BaseModel):
            raise ValueError("JsonPage: model must inherit from `pydantic.BaseModel`")

    @property
    def path(self) -> Path:
        """Возвращает путь к JSON-файлу как Path."""
        return Path(self.file_path)

    def validate_payload(self, payload: Any) -> Any:
        """Проверяет JSON через модель страницы.

        Args:
            payload: Данные, распарсенные из JSON.

        Returns:
            Any: Проверенные данные для сохранения.

        """
        validated = self.model.model_validate(payload)
        return validated.model_dump(mode="json")
