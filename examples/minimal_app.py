"""Демонстрационный пример json-admin для быстрого показа.

Запуск:
    uv run litestar --app examples.minimal_app:app run --reload
"""

from __future__ import annotations

from litestar import Litestar
from pydantic import BaseModel, Field

from jsonadmin import Admin, HtmlPage, JsonPage


class AppSettings(BaseModel):
    """Схема настроек приложения."""

    debug: bool = Field(default=False, description="Включает debug-режим")
    retries: int = Field(default=3, ge=0, description="Количество повторных попыток")


class FeatureFlags(BaseModel):
    """Схема feature-флагов."""

    use_cache: bool = Field(default=True, description="Включает кеширование")
    beta_mode: bool = Field(default=False, description="Включает beta-режим")


def build_welcome_block() -> str:
    """Возвращает HTML-блок приветствия для read-only вкладки.

    Returns:
        str: HTML-контент, встроенный в центральный блок интерфейса.

    """
    return """
    <h2 style="margin: 0 0 8px;">Добро пожаловать в demo json-admin</h2>
    <p style="margin: 0 0 8px;">Это пример простой админки для управления JSON-файлами.</p>
    <ol style="margin: 0; padding-left: 18px;">
      <li>Вкладка <b>Настройки</b> редактирует <code>app_settings.json</code>.</li>
      <li>Вкладка <b>Флаги</b> редактирует <code>feature_flags.json</code>.</li>
      <li>Все изменения валидируются через Pydantic-модели.</li>
    </ol>
    """


APP_TITLE = "Json Admin Demo"
ADMIN_PASSWORD = "admin"

app = Litestar(route_handlers=[])

admin = Admin(
    app=app,
    passwd=ADMIN_PASSWORD,
    title=APP_TITLE,
    index="index.html",
    login="login.html",
    pages=[
        HtmlPage(
            slug="about",
            title="О проекте",
            icon="fa-solid fa-circle-info",
            content=build_welcome_block,
        ),
        JsonPage(
            slug="settings",
            title="Настройки",
            icon="fa-solid fa-gear",
            file_path="examples/data/app_settings.json",
            model=AppSettings,
            autocreate=True,
        ),
        JsonPage(
            slug="flags",
            title="Флаги",
            icon="fa-solid fa-flag",
            file_path="examples/data/feature_flags.json",
            model=FeatureFlags,
            autocreate=True,
        ),
    ],
    base_url="/",
)
