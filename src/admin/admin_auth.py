"""
Аутентификация для SQLAdmin через Google OAuth 2.0.
"""

import httpx
from authlib.integrations.starlette_client import OAuth, OAuthError
from itsdangerous import URLSafeSerializer, BadSignature
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import RedirectResponse, PlainTextResponse

from src.config import settings
from src.logging import logger


ADMIN_COOKIE_NAME = "admin_token"

serializer = URLSafeSerializer(settings.SESSION_SECRET_KEY)

oauth = OAuth()

if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
    oauth.register(
        name="google",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={
            "scope": "openid email profile",
        },
    )


class AdminAuth(AuthenticationBackend):
    """AuthenticationBackend для SQLAdmin с Google OAuth."""

    async def login(self, request: Request) -> bool:
        """POST /admin/login — не используется, redirect через middleware."""
        return False

    async def logout(self, request: Request) -> bool:
        """Реальный выход перехватывается в middleware, здесь просто возвращаем True."""
        return True

    async def authenticate(self, request: Request) -> bool:
        """Проверяет подписанную cookie при каждом запросе."""
        token = request.cookies.get(ADMIN_COOKIE_NAME)
        if not token:
            return False
        try:
            data = serializer.loads(token)
            return bool(data.get("email"))
        except BadSignature:
            return False


class AdminOAuthRedirectMiddleware:
    """
    Pure ASGI middleware: перехватывает GET /admin/login
    и перенаправляет на Google OAuth.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            path = scope.get("path", "")
            method = scope.get("method", "GET")

            # Перехват выхода (удалили cookie)
            if path == "/admin/logout" and method == "GET":
                response = RedirectResponse(url="/admin/login")
                response.delete_cookie(ADMIN_COOKIE_NAME)
                await response(scope, receive, send)
                return

            if path == "/admin/login" and method == "GET":
                # Проверяем admin cookie
                request = Request(scope, receive, send)
                token = request.cookies.get(ADMIN_COOKIE_NAME)
                is_authenticated = False
                if token:
                    try:
                        data = serializer.loads(token)
                        is_authenticated = bool(data.get("email"))
                    except BadSignature:
                        pass

                if not is_authenticated:
                    if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
                        redirect_uri = str(request.url_for("admin_oauth_callback"))
                        response = await oauth.google.authorize_redirect(
                            request, redirect_uri
                        )
                        await response(scope, receive, send)
                        return

        await self.app(scope, receive, send)


async def admin_oauth_callback(request: Request):
    """
    Callback после Google OAuth.
    Проверяет роль через auth-service и ставит подписанную cookie.
    """
    # Обмен кода на токен
    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError as e:
        logger.error(f"[ADMIN AUTH] OAuthError: {e}")
        return PlainTextResponse(
            f"OAuth Error: {e}\n\nПопробуйте снова: /admin",
            status_code=400,
        )
    except Exception as e:
        logger.error(f"[ADMIN AUTH] Token exchange error: {type(e).__name__}: {e}")
        return PlainTextResponse(
            f"Token exchange error: {type(e).__name__}: {e}",
            status_code=500,
        )

    # Извлечение email
    user_info = token.get("userinfo")
    if not user_info or not user_info.get("email"):
        return PlainTextResponse("Google не вернул email", status_code=400)

    email = user_info["email"]
    logger.info(f"[ADMIN AUTH] Google user: {email}")

    # Проверка роли через auth-service
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{settings.AUTH_SERVICE_URL}/internal/users/by-email/{email}",
                timeout=10.0,
            )

        if resp.status_code == 404:
            return PlainTextResponse(
                f"Пользователь {email} не найден.\n"
                f"Сначала войдите на сайт через Google OAuth.",
                status_code=403,
            )

        if resp.status_code != 200:
            return PlainTextResponse(
                f"Ошибка auth-service: {resp.status_code}",
                status_code=502,
            )

        user_data = resp.json()
        if user_data.get("role") != "admin":
            return PlainTextResponse(
                "Доступ запрещён.\n\n",
                status_code=403,
            )

    except httpx.RequestError as e:
        return PlainTextResponse(
            f"Auth-service недоступен: {e}\nURL: {settings.AUTH_SERVICE_URL}",
            status_code=502,
        )

    logger.info(f"[ADMIN AUTH] Login OK: {email}")
    response = RedirectResponse(url="/admin", status_code=302)
    signed_value = serializer.dumps({"email": email})
    response.set_cookie(
        ADMIN_COOKIE_NAME,
        signed_value,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 8,  # 8 часов
    )
    return response
