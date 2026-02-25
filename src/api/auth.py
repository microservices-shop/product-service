from fastapi import Header, HTTPException, status


async def require_admin(
    x_user_role: str | None = Header(default=None, alias="X-User-Role"),
) -> str:
    """
    Проверяет роль администратора из заголовка X-User-Role.

    Если заголовок отсутствует — доступ разрешён
    (обратная совместимость до внедрения API Gateway).
    Если указана роль, отличная от admin — 403.
    """
    if x_user_role is not None and x_user_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещён. Требуется роль администратора.",
        )
    return x_user_role or "anonymous"
