from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from src.config import settings


class Base(DeclarativeBase):
    __abstract__ = True


try:
    if settings.DB_HOST and settings.DB_PORT:
        engine = create_async_engine(url=settings.DATABASE_URL)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
    else:
        engine = None
        session_factory = None
except Exception:
    engine = None
    session_factory = None
