"""Модели страниц для админки."""

from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .icons import FAIcon


class BasePage(BaseModel):
    """Общая модель страницы админки.

    Attributes:
        slug: Уникальный идентификатор страницы для URL.
        title: Заголовок вкладки в интерфейсе.
        icon: CSS-класс иконки.

    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    slug: str = Field(min_length=1)
    title: str = Field(min_length=1)
    icon: FAIcon = FAIcon.FAR_FILE


class JsonPage(BasePage):
    """Конфигурация вкладки редактирования JSON.

    Attributes:
        file_path: Путь до JSON-файла.
        model: Pydantic-модель для валидации содержимого.
        icon: CSS-класс иконки.
        sync_mode: Режим синхронизации файла с моделью.
            - "none": ничего не делать автоматически,
            - "create": создать файл из модели, если его нет,
            - "migrate": всегда прогонять содержимое через модель.
        autocreate: Устаревший флаг, эквивалент `sync_mode="create"`.

    """

    file_path: str | Path
    model: type[BaseModel]
    icon: FAIcon = FAIcon.FAR_FILE_CODE
    sync_mode: Literal["none", "create", "migrate"] = "none"

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
