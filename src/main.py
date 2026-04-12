from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from src.messaging import consumers  # noqa: F401 — регистрирует @subscriber
from src.messaging.broker import broker
from starlette.middleware.sessions import SessionMiddleware

from src.api.v1.router import api_router
from src.api.internal.router import internal_router
from src.config import settings
from src.exceptions import (
    NotFoundException,
    BadRequestException,
    ConflictException,
    ValidationException,
)
from src.logging import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    logger.info("Сервис 'Каталог товаров' запускается...")
    broker.include_router(consumers.router)
    await broker.connect()
    await broker.start()
    yield
    await broker.close()
    logger.info("Сервис 'Каталог товаров' останавливается...")


def create_app() -> FastAPI:
    """Фабрика для создания FastAPI приложения"""
    app = FastAPI(
        title="Product Service API",
        version="1.0.0",
        description="API для управления товарами и категориями",
        lifespan=lifespan,
    )

    # Session middleware (для OAuth state и admin сессий)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.SESSION_SECRET_KEY,
    )

    # CORS настройки
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Глобальные обработчики исключений
    @app.exception_handler(NotFoundException)
    async def not_found_handler(request: Request, exc: NotFoundException):
        return JSONResponse(
            status_code=404,
            content={"detail": exc.message, "error_type": "not_found"},
        )

    @app.exception_handler(BadRequestException)
    async def bad_request_handler(request: Request, exc: BadRequestException):
        return JSONResponse(
            status_code=400,
            content={"detail": exc.message, "error_type": "bad_request"},
        )

    @app.exception_handler(ConflictException)
    async def conflict_handler(request: Request, exc: ConflictException):
        return JSONResponse(
            status_code=409,
            content={"detail": exc.message, "error_type": "conflict"},
        )

    @app.exception_handler(ValidationException)
    async def validation_handler(request: Request, exc: ValidationException):
        return JSONResponse(
            status_code=422,
            content={
                "detail": exc.message,
                "error_type": "validation_error",
                "errors": exc.errors,
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.exception(f"Необработанная ошибка: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Внутренняя ошибка сервера",
                "error_type": "internal_error",
            },
        )

    app.include_router(api_router)
    app.include_router(internal_router)

    @app.get("/health", tags=["System"])
    async def health_check():
        return {"status": "healthy", "service": "product-service"}

    return app


app = create_app()
