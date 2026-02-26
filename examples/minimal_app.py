"""Минимальный пример запуска json-admin на Litestar."""

from __future__ import annotations

import time

from litestar import Litestar
from pydantic import BaseModel, Field

from jsonadmin import Admin, HtmlPage, JsonPage


class AppSettings(BaseModel):
    """Схема настроек приложения для вкладки settings."""

    debug: bool = Field(default=False, description="Включает debug-режим")
    retries: int = Field(default=3, ge=0, description="Количество повторных попыток")


class FeatureFlags(BaseModel):
    """Схема feature flags."""

    use_cache: bool = Field(default=True, description="Включает кеширование")
    beta_mode: bool = Field(default=False, description="Включает beta-режим")


app = Litestar(route_handlers=[])


def build_info_block() -> str:
    """Формирует read-only HTML-блок для HtmlPage."""
    t = time.ctime()
    return f"""
    <h2>Welcome</h2>
    {t}
    <p>This page is read-only and renders embedded HTML block.</p>
    """


admin = Admin(
    app=app,
    passwd="admin",
    title="My App Admin",
    index="index.html",
    login="login.html",
    pages=[
        HtmlPage(
            slug="info",
            title="Информация",
            icon="fa-solid fa-circle-info",
            content=build_info_block,
        ),
        JsonPage(
            slug="settings",
            title="Настройки",
            file_path="examples/data/app_settings.json",
            model=AppSettings,
            icon="fa-solid fa-gear",
        ),
        JsonPage(
            slug="features",
            title="Флаги",
            file_path="examples/data/feature_flags.json",
            model=FeatureFlags,
            icon="fa-solid fa-flag",
        ),
    ],
    base_url="/",
)
