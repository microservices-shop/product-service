import pytest

from src.utils import normalize_title


class TestNormalizeTitle:
    """Тесты для normalize_title."""

    # Успешные сценарии

    def test_strips_leading_and_trailing_spaces(self):
        """Удаляет пробелы в начале и конце строки."""
        assert normalize_title("  hello  ") == "Hello"

    def test_capitalizes_first_letter(self):
        """Капитализирует первую букву."""
        assert normalize_title("iphone pro") == "Iphone pro"

    def test_already_capitalized(self):
        """Уже капитализированная строка не меняется."""
        assert normalize_title("Смартфоны") == "Смартфоны"

    def test_single_character(self):
        """Одиночный символ капитализируется."""
        assert normalize_title("a") == "A"

    def test_cyrillic_title(self):
        """Корректно работает с кириллицей."""
        assert normalize_title("ноутбуки") == "Ноутбуки"

    def test_mixed_spaces(self):
        """Удаляет только крайние пробелы, внутренние остаются."""
        assert normalize_title("  iphone 15 pro  ") == "Iphone 15 pro"

    def test_uppercase_input_lowered(self):
        """capitalize() приводит первую к верхнему, остальные к нижнему регистру."""
        assert normalize_title("IPHONE") == "Iphone"

    def test_tabs_and_newlines_stripped(self):
        """strip() удаляет табуляции и переносы строк."""
        assert normalize_title("\t hello \n") == "Hello"

    # Ошибочные сценарии

    def test_empty_string_raises_value_error(self):
        """Пустая строка вызывает ValueError."""
        with pytest.raises(ValueError, match="Название не может быть пустым"):
            normalize_title("")

    def test_only_spaces_raises_value_error(self):
        """Строка из одних пробелов вызывает ValueError."""
        with pytest.raises(ValueError, match="Название не может быть пустым"):
            normalize_title("   ")

    def test_only_tabs_raises_value_error(self):
        """Строка из одних табуляций вызывает ValueError."""
        with pytest.raises(ValueError, match="Название не может быть пустым"):
            normalize_title("\t\t")
