"""Модели страниц для админки."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BasePage(BaseModel):
    """Общая модель страницы админки.

    Attributes:
        slug: Уникальный идентификатор страницы для URL.
        title: Заголовок вкладки в интерфейсе.
        icon: CSS-класс иконки (например, `fa-solid fa-gear`).

    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    slug: str = Field(min_length=1)
    title: str = Field(min_length=1)
    icon: str = ""


class JsonPage(BasePage):
    """Конфигурация вкладки редактирования JSON.

    Attributes:
        file_path: Путь до JSON-файла.
        model: Pydantic-модель для валидации содержимого.

    """

    file_path: str | Path
    model: type[BaseModel]

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


class HtmlPage(BasePage):
    """Конфигурация read-only HTML вкладки.

    Attributes:
        content: Контент вкладки.
            Поддерживается:
            - str (встроенный HTML),
            - str/Path к .html файлу,
            - Callable[[], str] для динамической генерации.

    """

    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    content: str | Path | Callable[[], str]
