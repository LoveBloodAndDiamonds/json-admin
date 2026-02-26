"""Демонстрационный пример json-admin для быстрого показа.

Запуск:
    uv run litestar --app examples.minimal_app:app run --reload
"""

from __future__ import annotations

from html import escape

from litestar import Litestar
from pydantic import BaseModel, Field

from jsonadmin import Admin, HtmlPage, JsonPage
from jsonadmin.icons import FAIcon


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


def build_icons_gallery_block() -> str:
    """Возвращает HTML-блок с предпросмотром всех иконок из `FAIcon`.

    Returns:
        str: HTML-контент с сеткой иконок.

    """
    items_html: list[str] = []
    for icon in FAIcon:
        icon_name = escape(icon.name)
        icon_value = escape(icon.value)
        items_html.append(
            f"""
            <div style="border: 1px solid var(--border); border-radius: 8px; padding: 10px;">
              <div style="display: flex; gap: 8px; align-items: center; margin-bottom: 8px;">
                <i class="{icon_value}" title="solid"></i>
              </div>
              <div style="font-size: 11px; color: var(--muted);">{icon_name}</div>
              <code style="font-size: 11px;">{icon_value}</code>
            </div>
            """
        )

    grid = "".join(items_html)
    return f"""
    <h2 style="margin: 0 0 8px;">Галерея иконок Font Awesome</h2>
    <p style="margin: 0 0 12px;">Всего иконок в enum: <b>{len(FAIcon)}</b></p>
    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 8px;">
      {grid}
    </div>
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
            content=build_welcome_block,
        ),
        HtmlPage(
            slug="icons",
            title="Иконки",
            content=build_icons_gallery_block,
        ),
        JsonPage(
            slug="settings",
            title="Настройки",
            file_path="examples/data/app_settings.json",
            model=AppSettings,
            autocreate=True,
        ),
        JsonPage(
            slug="flags",
            title="Флаги",
            file_path="examples/data/feature_flags.json",
            model=FeatureFlags,
            autocreate=True,
        ),
    ],
    base_url="/",
)
