from fastapi import APIRouter

from src.api.internal import products

internal_router = APIRouter(prefix="/internal")
internal_router.include_router(products.router)
