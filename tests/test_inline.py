from bot.routers.inline import parse_inline_query


def test_parse_inline_query_valid():
    """Парсинг целой суммы и описания."""
    result = parse_inline_query("3000 за ужин")
    assert result == (300000, "за ужин")


def test_parse_inline_query_decimal():
    """Парсинг дробных сумм (точка и запятая)."""
    assert parse_inline_query("500.50 кофе") == (50050, "кофе")
    assert parse_inline_query("500,50 кофе") == (50050, "кофе")
    assert parse_inline_query("99.9 чай") == (9990, "чай")


def test_parse_inline_query_invalid():
    """Невалидный ввод возвращает None."""
    assert parse_inline_query("abc") is None
    assert parse_inline_query("") is None
    assert parse_inline_query("  ") is None
    # Слишком маленькая сумма (< 1₽)
    assert parse_inline_query("0.50 мелочь") is None
    # Слишком большая сумма (> 1 000 000₽)
    assert parse_inline_query("1000001 дорого") is None


def test_parse_inline_query_no_description():
    """Сумма без описания — None."""
    assert parse_inline_query("3000") is None
    assert parse_inline_query("500.50") is None


def test_parse_inline_query_boundary():
    """Граничные значения суммы."""
    # Минимум — 1₽
    assert parse_inline_query("1 минимум") == (100, "минимум")
    # Максимум — 1 000 000₽
    assert parse_inline_query("1000000 максимум") == (100_000_000, "максимум")
