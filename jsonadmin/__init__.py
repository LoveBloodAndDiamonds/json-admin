"""Публичный API библиотеки json-admin."""

from .admin import Admin
from .icons import FAIcon
from .pages import BasePage, HtmlPage, JsonPage

__all__ = ["Admin", "BasePage", "JsonPage", "HtmlPage", "FAIcon"]
