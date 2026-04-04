"""Публичный API библиотеки json-admin."""

from .admin import Admin
from .extra import JsonProvider, JsonProxy, build_json_model_loader
from .icons import FAIcon
from .pages import BasePage, HtmlPage, JsonPage

__all__ = [
    "Admin",
    "BasePage",
    "JsonPage",
    "HtmlPage",
    "FAIcon",
    "JsonProvider",
    "JsonProxy",
    "build_json_model_loader",
]
