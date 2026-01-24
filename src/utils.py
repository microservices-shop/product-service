"""Общие утилиты для product-service"""


def normalize_title(title: str) -> str:
    """
    Нормализует название: удаляет лишние пробелы и капитализирует первую букву

    :raises ValueError: Если название пустое или содержит только пробелы
    """
    title = title.strip()
    if not title:
        raise ValueError("Название не может быть пустым")
    return title.capitalize()
