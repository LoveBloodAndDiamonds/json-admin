"""Дополнительные утилиты для работы с JSON-конфигами."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from time import monotonic
from typing import Any

from pydantic import BaseModel, ValidationError

__all__ = ["JsonProvider", "JsonProxy", "build_json_model_loader"]


def build_json_model_loader[TModel: BaseModel](
    model: type[TModel],
    file_path: str | Path,
    *,
    create_if_missing: bool = False,
) -> Callable[[], TModel]:
    """Создает функцию-лоадер Pydantic-модели из JSON-файла.

    Args:
        model: Класс Pydantic-модели.
        file_path: Путь к JSON-файлу.
        create_if_missing: Создавать файл из дефолтов модели, если его нет.

    Returns:
        Callable[[], TModel]: Функция, которая читает JSON и валидирует его через модель.

    Raises:
        ValueError: Если файл отсутствует и его нельзя создать из дефолтов.

    """
    path = Path(file_path)

    def _loader() -> TModel:
        """Читает JSON и возвращает провалидированную модель."""
        if not path.exists():
            if not create_if_missing:
                raise FileNotFoundError(f"JSON file does not exist: '{path}'")

            try:
                default_model = model.model_validate({})
            except ValidationError as exc:
                raise ValueError(
                    f"Cannot create '{path}': model '{model.__name__}' has required fields without defaults."
                ) from exc

            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(default_model.model_dump_json(indent=2), encoding="utf-8")
            return default_model

        payload = json.loads(path.read_text(encoding="utf-8"))
        return model.model_validate(payload)

    return _loader


class JsonProvider[TModel: BaseModel]:
    """Кэширует модель и автоматически обновляет ее по таймеру."""

    def __init__(
        self,
        loader: Callable[[], TModel],
        refresh_interval_sec: float,
    ) -> None:
        """Инициализирует провайдер.

        Args:
            loader: Функция загрузки актуальной модели.
            refresh_interval_sec: Интервал автообновления в секундах.

        Raises:
            ValueError: Если передан неположительный интервал обновления.

        """
        if refresh_interval_sec <= 0:
            raise ValueError("refresh_interval_sec must be greater than 0")

        self._loader = loader
        self._refresh_interval_sec = refresh_interval_sec
        self._cached: TModel | None = None
        self._last_loaded_at: float | None = None

    def _is_reload_required(self) -> bool:
        """Возвращает True, если пора перечитать данные из источника."""
        if self._cached is None or self._last_loaded_at is None:
            return True
        return monotonic() - self._last_loaded_at >= self._refresh_interval_sec

    @property
    def value(self) -> TModel:
        """Возвращает актуальное значение из кэша с автообновлением."""
        if self._is_reload_required():
            self.reload()

        if self._cached is None:
            raise RuntimeError("Provider cache is empty after reload")

        return self._cached

    def reload(self) -> TModel:
        """Принудительно перечитывает значение и обновляет кэш."""
        self._cached = self._loader()
        self._last_loaded_at = monotonic()
        return self._cached


class JsonProxy[TModel: BaseModel]:
    """Проксирует доступ к текущей модели через JsonProvider."""

    def __init__(self, provider: JsonProvider[TModel]) -> None:
        """Инициализирует прокси.

        Args:
            provider: Источник актуального состояния модели.

        """
        self._provider = provider

    def __getattr__(self, name: str) -> Any:
        """Делегирует доступ к атрибутам текущей модели."""
        return getattr(self._provider.value, name)

    @property
    def value(self) -> TModel:
        """Возвращает текущую модель целиком."""
        return self._provider.value

    def reload(self) -> TModel:
        """Принудительно перечитывает модель."""
        return self._provider.reload()
