"""Пример работы с JsonProvider и JsonProxy.

Запуск:
    uv run python examples/provider_demo.py
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from pydantic import BaseModel, Field

from jsonadmin import JsonProvider, JsonProxy, build_json_model_loader


class RuntimeConfig(BaseModel):
    """Модель runtime-конфига для демонстрации провайдера.

    Attributes:
        enabled: Включен ли функционал.
        timeout_ms: Таймаут операции в миллисекундах.

    """

    enabled: bool = Field(default=True, description="Включен ли функционал.")
    timeout_ms: int = Field(default=300, ge=0, description="Таймаут операции в мс.")


def _build_config_proxy(config_path: Path) -> JsonProxy[RuntimeConfig]:
    """Создает прокси для чтения актуального runtime-конфига.

    Args:
        config_path: Путь до JSON-конфига.

    Returns:
        JsonProxy[RuntimeConfig]: Прокси, который прозрачно отдает актуальную модель.

    """
    provider = JsonProvider(
        loader=build_json_model_loader(
            model=RuntimeConfig,
            file_path=config_path,
            create_if_missing=True,
        ),
        refresh_interval_sec=2,
    )
    return JsonProxy(provider)


async def _background_reader(config: JsonProxy[RuntimeConfig]) -> None:
    """Периодически читает конфиг и показывает текущие значения.

    Args:
        config: Прокси к runtime-конфигу.

    Returns:
        None: Функция только печатает текущие значения.

    """
    for _ in range(6):
        print(
            f"[reader] enabled={config.enabled} timeout_ms={config.timeout_ms}",
        )
        await asyncio.sleep(1)


def _update_config_file(config_path: Path) -> None:
    """Имитирует внешнее изменение JSON-файла.

    Args:
        config_path: Путь до JSON-конфига.

    Returns:
        None: Функция перезаписывает файл новыми значениями.

    """
    payload = RuntimeConfig(enabled=False, timeout_ms=1500)
    config_path.write_text(payload.model_dump_json(indent=2), encoding="utf-8")


async def _background_writer(config_path: Path) -> None:
    """Ждет несколько секунд и обновляет конфиг, как внешний процесс.

    Args:
        config_path: Путь до JSON-конфига.

    Returns:
        None: Функция обновляет файл и завершает работу.

    """
    await asyncio.sleep(3)
    _update_config_file(config_path)
    print("[writer] config file updated")


async def main() -> None:
    """Запускает демонстрацию автообновления конфигурации.

    Returns:
        None: Демонстрация выводит значения в консоль.

    """
    config_path = Path("examples/data/runtime_config.json")
    config = _build_config_proxy(config_path)

    await asyncio.gather(
        _background_reader(config),
        _background_writer(config_path),
    )


if __name__ == "__main__":
    asyncio.run(main())
