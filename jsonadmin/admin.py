"""Минимальная админка для редактирования JSON-файлов на Litestar."""

import asyncio
import hashlib
import hmac
import json
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape
from litestar import Litestar, Request, Response, get, post
from litestar.datastructures import Cookie
from pydantic import BaseModel

from jsonadmin.page import JsonPage


class Admin:
    """Управляет JSON-страницами и авторизацией по единому паролю."""

    def __init__(
        self,
        app: Litestar,
        passwd: str,
        pages: list[JsonPage] | None = None,
        title: str = "JSON Admin",
        templates_dir: str | Path | None = None,
        index: str = "index.html",
        login: str = "login.html",
        base_url: str = "/",
    ) -> None:
        """Инициализирует админ-панель и регистрирует маршруты.

        Args:
            app: Экземпляр Litestar-приложения.
            passwd: Пароль для входа в админку.
            pages: Список вкладок админки.
            title: Название приложения в интерфейсе админки.
            templates_dir: Директория с пользовательскими HTML-шаблонами.
                По умолчанию используется `jsonadmin/html`.
            index: Имя шаблона страницы редактора.
            login: Имя шаблона страницы входа.
            base_url: Базовый URL, на котором будет доступна админка.

        """
        self._app: Litestar = app
        self._passwd: str = passwd
        self._title: str = title
        self._base_url: str = self._normalize_base_url(base_url)
        if templates_dir is None:
            self._templates_dir = Path(__file__).resolve().parent / "html"
        else:
            self._templates_dir = Path(templates_dir)
        self._index_template: str = index
        self._login_template: str = login
        self._template_env: Environment | None = self._init_template_env(self._templates_dir)
        self._cookie_name: str = "jsonadmin_session"
        self._pages: dict[str, JsonPage] = {}
        self._token_secret: str = hashlib.sha256(passwd.encode("utf-8")).hexdigest()
        self._register_routes()

        for page in pages or []:
            self.add_page(page)

    def add_page(self, page: JsonPage) -> None:
        """Регистрирует новую вкладку админки.

        Args:
            page: Описание страницы админки.

        Raises:
            ValueError: Если slug уже занят.

        """
        page.validate()
        if page.slug in self._pages:
            raise ValueError(f"Page with slug='{page.slug}' is already registered")
        self._pages[page.slug] = page

    def _register_routes(self) -> None:
        """Добавляет маршруты админки в Litestar-приложение."""

        @get(path=self._route(""))
        async def index(request: Request[Any, Any, Any]) -> Response[str]:
            """Отображает главную страницу или форму входа.

            Args:
                request: Входящий HTTP-запрос.

            Returns:
                Response[str]: HTML-ответ.

            """
            if not self._is_authorized(request):
                return self._login_page(error_text="")

            if not self._pages:
                return self._html_response(f"<h1>{self._title}</h1><p>No registered pages.</p>")

            first_slug = next(iter(self._pages))
            return self._redirect(self._route(f"/page/{first_slug}"))

        @post(path=self._route("/login"))
        async def login(request: Request[Any, Any, Any]) -> Response[str]:
            """Проверяет пароль и устанавливает сессионную cookie.

            Args:
                request: Входящий HTTP-запрос.

            Returns:
                Response[str]: Редирект на страницу админки или форма с ошибкой.

            """
            form = await request.form()
            input_passwd = str(form.get("passwd", ""))
            if not hmac.compare_digest(input_passwd, self._passwd):
                return self._login_page(error_text="Invalid password")

            response = self._redirect(self._route(""))
            response.set_cookie(self._auth_cookie())
            return response

        @post(path=self._route("/logout"))
        async def logout() -> Response[str]:
            """Удаляет сессионную cookie и завершает сессию.

            Returns:
                Response[str]: Редирект на форму входа.

            """
            response = self._redirect(self._route(""))
            response.delete_cookie(key=self._cookie_name, path=self._route(""))
            return response

        @get(path=self._route("/page/{slug:str}"))
        async def page_view(request: Request[Any, Any, Any], slug: str) -> Response[str]:
            """Показывает страницу редактирования JSON.

            Args:
                request: Входящий HTTP-запрос.
                slug: Идентификатор страницы.

            Returns:
                Response[str]: HTML страницы редактора.

            """
            if not self._is_authorized(request):
                return self._redirect(self._route(""))

            page = self._pages.get(slug)
            if page is None:
                return self._html_response("<h1>404</h1><p>Page not found</p>", status_code=404)

            payload, load_error = await self._read_json_payload(page.path)
            pretty_json = json.dumps(payload, ensure_ascii=False, indent=2)
            schema_text = self._build_schema_text(page.model)
            return self._editor_page(
                page=page, json_text=pretty_json, schema_text=schema_text, error_text=load_error
            )

        @post(path=self._route("/page/{slug:str}"))
        async def save_page(request: Request[Any, Any, Any], slug: str) -> Response[str]:
            """Сохраняет JSON после валидации.

            Args:
                request: Входящий HTTP-запрос.
                slug: Идентификатор страницы.

            Returns:
                Response[str]: HTML страницы редактора с результатом операции.

            """
            if not self._is_authorized(request):
                return self._redirect(self._route(""))

            page = self._pages.get(slug)
            if page is None:
                return self._html_response("<h1>404</h1><p>Page not found</p>", status_code=404)

            form = await request.form()
            json_text = str(form.get("payload", ""))

            try:
                raw_payload = json.loads(json_text)
            except json.JSONDecodeError as exc:
                schema_text = self._build_schema_text(page.model)
                return self._editor_page(
                    page=page,
                    json_text=json_text,
                    schema_text=schema_text,
                    error_text=f"JSON error: {exc}",
                )

            try:
                saved_payload = page.validate_payload(raw_payload)
            except Exception as exc:  # noqa: BLE001
                schema_text = self._build_schema_text(page.model)
                return self._editor_page(
                    page=page,
                    json_text=json_text,
                    schema_text=schema_text,
                    error_text=f"Model validation error: {exc}",
                )

            await self._write_json_payload(page.path, saved_payload)
            pretty_json = json.dumps(saved_payload, ensure_ascii=False, indent=2)
            schema_text = self._build_schema_text(page.model)
            return self._editor_page(
                page=page,
                json_text=pretty_json,
                schema_text=schema_text,
                error_text="",
                success_text="Изменения сохранены",
            )

        # Регистрируем обработчики в Litestar-приложении.
        for handler in (index, login, logout, page_view, save_page):
            self._app.register(handler)

    def _init_template_env(self, templates_dir: Path) -> Environment | None:
        """Создает Jinja-окружение для HTML-шаблонов.

        Args:
            templates_dir: Директория с шаблонами.

        Returns:
            Environment | None: Настроенное окружение или `None`, если директории нет.

        """
        if not templates_dir.exists() or not templates_dir.is_dir():
            return None

        return Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(enabled_extensions=("html", "htm")),
        )

    def _render_editor_template(
        self,
        page: JsonPage,
        json_text: str,
        schema_text: str,
        error_text: str,
        success_text: str,
    ) -> str | None:
        """Рендерит пользовательский HTML-шаблон editor-страницы.

        Args:
            page: Активная страница.
            json_text: Содержимое JSON в textarea.
            schema_text: JSON-схема модели.
            error_text: Сообщение об ошибке.
            success_text: Сообщение об успехе.

        Returns:
            str | None: HTML-контент или `None`, если шаблоны недоступны.

        """
        if self._template_env is None:
            return None

        try:
            template = self._template_env.get_template(self._index_template)
        except TemplateNotFound:
            return None

        nav_pages: list[dict[str, str | bool]] = []
        for nav_page in self._pages.values():
            nav_pages.append(  # noqa
                {
                    "slug": nav_page.slug,
                    "title": nav_page.title,
                    "href": self._route(f"/page/{nav_page.slug}"),
                    "active": nav_page.slug == page.slug,
                }
            )

        return template.render(
            app_title=self._title,
            page_title=page.title,
            nav_pages=nav_pages,
            save_action=self._route(f"/page/{page.slug}"),
            logout_action=self._route("/logout"),
            payload=json_text,
            schema_text=schema_text,
            error_text=error_text,
            success_text=success_text,
        )

    def _render_login_template(self, error_text: str) -> str | None:
        """Рендерит пользовательский HTML-шаблон страницы входа.

        Args:
            error_text: Сообщение об ошибке входа.

        Returns:
            str | None: HTML-контент или `None`, если шаблоны недоступны.

        """
        if self._template_env is None:
            return None

        try:
            template = self._template_env.get_template(self._login_template)
        except TemplateNotFound:
            return None

        return template.render(
            app_title=self._title,
            page_title="Login",
            login_action=self._route("/login"),
            error_text=error_text,
        )

    def _normalize_base_url(self, base_url: str) -> str:
        """Нормализует базовый URL для стабильного роутинга.

        Args:
            base_url: Исходный URL.

        Returns:
            str: Нормализованный путь, начинающийся с `/`.

        """
        if not base_url:
            return "/"

        if not base_url.startswith("/"):
            base_url = f"/{base_url}"

        if len(base_url) > 1 and base_url.endswith("/"):
            base_url = base_url[:-1]

        return base_url

    def _route(self, suffix: str) -> str:
        """Строит конечный путь маршрута.

        Args:
            suffix: Дополнение к базовому URL.

        Returns:
            str: Полный маршрут.

        """
        suffix = suffix or ""
        if suffix and not suffix.startswith("/"):
            suffix = f"/{suffix}"

        if self._base_url == "/":
            return suffix or "/"

        return f"{self._base_url}{suffix}"

    def _make_session_token(self) -> str:
        """Создает подпись текущей сессии на основе пароля.

        Returns:
            str: Токен сессионной cookie.

        """
        return hmac.new(
            key=self._token_secret.encode("utf-8"),
            msg=b"jsonadmin-authenticated",
            digestmod=hashlib.sha256,
        ).hexdigest()

    def _is_authorized(self, request: Request[Any, Any, Any]) -> bool:
        """Проверяет валидность cookie авторизации.

        Args:
            request: Входящий HTTP-запрос.

        Returns:
            bool: `True`, если сессия подтверждена.

        """
        cookie = request.cookies.get(self._cookie_name)
        if not cookie:
            return False
        return hmac.compare_digest(cookie, self._make_session_token())

    def _auth_cookie(self) -> Cookie:
        """Создает защищенную cookie после успешного входа.

        Returns:
            Cookie: Конфигурация cookie авторизации.

        """
        return Cookie(
            key=self._cookie_name,
            value=self._make_session_token(),
            httponly=True,
            secure=False,
            samesite="strict",
            path=self._route(""),
        )

    async def _read_json_payload(self, file_path: Path) -> tuple[Any, str]:
        """Читает JSON-файл и возвращает данные либо ошибку.

        Args:
            file_path: Путь до файла.

        Returns:
            tuple[Any, str]: Распарсенные данные и текст ошибки.

        """
        if not file_path.exists():
            return {}, ""

        def _read_text() -> str:
            return file_path.read_text(encoding="utf-8")

        text = await asyncio.to_thread(_read_text)
        if not text.strip():
            return {}, ""

        try:
            return json.loads(text), ""
        except json.JSONDecodeError as exc:
            return {}, f"File contains invalid JSON: {exc}"

    async def _write_json_payload(self, file_path: Path, payload: Any) -> None:
        """Сохраняет JSON в файл в читаемом формате.

        Args:
            file_path: Путь до файла.
            payload: Данные для сериализации.

        """
        json_text = json.dumps(payload, ensure_ascii=False, indent=2)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        def _write_text() -> None:
            file_path.write_text(json_text, encoding="utf-8")

        await asyncio.to_thread(_write_text)

    def _build_schema_text(self, model: type[BaseModel]) -> str:
        """Формирует текст JSON-схемы из Pydantic-модели.

        Args:
            model: Модель страницы.

        Returns:
            str: Схема или пустая строка.

        """
        schema = model.model_json_schema()
        return json.dumps(schema, ensure_ascii=False, indent=2)

    def _login_page(self, error_text: str) -> Response[str]:
        """Строит HTML формы входа.

        Args:
            error_text: Сообщение об ошибке авторизации.

        Returns:
            Response[str]: HTML-ответ.

        """
        rendered_html = self._render_login_template(error_text=error_text)
        if rendered_html is not None:
            return self._html_response(rendered_html)

        error_html = f"<p>{error_text}</p>" if error_text else ""
        html = f"""
<!doctype html>
<html lang="ru">
<head><meta charset="utf-8"><title>Вход</title></head>
<body>
  <h1>{self._title}</h1>
  {error_html}
  <form method="post" action="{self._route("/login")}">
    <label for="passwd">Password</label><br>
    <input id="passwd" name="passwd" type="password" required autofocus><br><br>
    <button type="submit">Sign in</button>
  </form>
</body>
</html>
"""
        return self._html_response(html)

    def _editor_page(
        self,
        page: JsonPage,
        json_text: str,
        schema_text: str,
        error_text: str,
        success_text: str = "",
    ) -> Response[str]:
        """Строит HTML-страницу редактирования JSON.

        Args:
            page: Конфигурация активной вкладки.
            json_text: Текущий JSON для textarea.
            schema_text: JSON-схема модели для показа.
            error_text: Read or save error message.
            success_text: Сообщение об успешном сохранении.

        Returns:
            Response[str]: HTML-ответ страницы.

        """
        rendered_html = self._render_editor_template(
            page=page,
            json_text=json_text,
            schema_text=schema_text,
            error_text=error_text,
            success_text=success_text,
        )
        if rendered_html is not None:
            return self._html_response(rendered_html)

        nav_parts: list[str] = []
        for nav_page in self._pages.values():
            if nav_page.slug == page.slug:
                nav_parts.append(f"<b>{nav_page.title}</b>")
            else:
                nav_parts.append(
                    f'<a href="{self._route(f"/page/{nav_page.slug}")}">{nav_page.title}</a>'
                )

        nav_html = " | ".join(nav_parts)
        error_html = f"<p>{error_text}</p>" if error_text else ""
        success_html = f"<p>{success_text}</p>" if success_text else ""
        schema_html = f"<h3>Схема модели</h3><pre>{schema_text}</pre>" if schema_text else ""

        html = f"""
<!doctype html>
<html lang="ru">
<head><meta charset="utf-8"><title>{page.title}</title></head>
<body>
  <h1>{self._title}</h1>
  <p>{nav_html}</p>
  <form method="post" action="{self._route(f"/page/{page.slug}")}">
    <h2>{page.title}</h2>
    {error_html}
    {success_html}
    <textarea name="payload" rows="30" cols="120">{json_text}</textarea><br><br>
    <button type="submit">Сохранить</button>
  </form>
  <form method="post" action="{self._route("/logout")}">
    <button type="submit">Выйти</button>
  </form>
  {schema_html}
</body>
</html>
"""
        return self._html_response(html)

    def _html_response(self, content: str, status_code: int = 200) -> Response[str]:
        """Создает HTML-ответ с едиными заголовками.

        Args:
            content: Тело HTML-страницы.
            status_code: HTTP-код ответа.

        Returns:
            Response[str]: Готовый HTTP-ответ.

        """
        return Response(
            content=content,
            media_type="text/html; charset=utf-8",
            status_code=status_code,
        )

    def _redirect(self, location: str) -> Response[str]:
        """Создает HTTP-редирект.

        Args:
            location: URL для перехода.

        Returns:
            Response[str]: Ответ с кодом 303.

        """
        return Response(content="", status_code=303, headers={"Location": location})
