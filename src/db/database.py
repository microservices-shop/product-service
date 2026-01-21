from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from src.config import settings


class Base(DeclarativeBase):
    __abstract__ = True


engine = create_async_engine(url=settings.DATABASE_URL)
session_factory = async_sessionmaker(engine, expire_on_commit=False)
