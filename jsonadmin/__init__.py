"""Публичный API библиотеки json-admin."""

from jsonadmin.admin import Admin
from jsonadmin.pages import BasePage, HtmlPage, JsonPage

__all__ = ["Admin", "BasePage", "JsonPage", "HtmlPage"]
